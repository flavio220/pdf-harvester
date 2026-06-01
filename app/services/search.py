"""
Moteur de recherche — priorité COURS puis académique puis web.
Sources : OpenClassrooms, Scribd, SlideShare, Coursera, edX,
          Khan Academy, MIT OCW, Stanford, FreeCodeCamp, W3Schools,
          + 16 sources académiques + scraping web intelligent.
"""
import urllib.parse, os, re, hashlib
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

try:
    import langdetect
    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False

TIMEOUT     = 14
MAX_WORKERS = 10

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0 Safari/537.36'
    ),
    'Accept-Language': 'fr,en;q=0.9',
}

LANG_WORDS = {
    'fr': ['french','français','francophone'],
    'en': ['english'],
    'es': ['spanish','español'],
    'ar': ['arabic','arabe'],
    'pt': ['portuguese','português'],
    'de': ['german','deutsch'],
    'zh': ['chinese','中文'],
    'ru': ['russian','russe'],
}

GUTENBERG_LANG = {
    'fr':'fr','en':'en','es':'es','de':'de',
    'pt':'pt','ar':'ar','zh':'zh','ru':'ru',
}

# Priorités : 1 = plus haute (cours), 3 = académique, 5 = web générique
PRIORITY = {
    'cours': 1,
    'tutorial': 1,
    'book': 2,
    'academic': 3,
    'medical': 3,
    'government': 4,
    'document': 4,
    'scraped': 5,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get(url, **kw):
    return requests.get(url, headers=HEADERS, timeout=TIMEOUT, **kw)

def _detect_lang(text):
    if not HAS_LANGDETECT or not text or len(text.strip()) < 20:
        return None
    try:
        return langdetect.detect(text)
    except Exception:
        return None

def _lang_ok(res, lang):
    if not lang:
        return True
    declared = res.get('lang', '')
    if declared:
        return declared.startswith(lang)
    text = f"{res.get('title','')} {res.get('description','')}"
    detected = _detect_lang(text)
    if detected:
        return detected.startswith(lang)
    return True

def _url_key(url):
    return hashlib.md5(url.strip().lower().encode()).hexdigest()

def _title_key(title):
    return re.sub(r'\W+', '', title.lower())[:60]

def _make(title, url, source, desc='', authors='', doc_type='document',
          year='', lang='', priority=None):
    if priority is None:
        priority = PRIORITY.get(doc_type, 4)
    return {
        'title':       title.strip()[:200],
        'url':         url.strip(),
        'source':      source,
        'description': desc.strip()[:280],
        'authors':     authors.strip()[:120],
        'type':        doc_type,
        'year':        str(year),
        'lang':        lang,
        'priority':    priority,
    }

def _dedup(results):
    seen_urls, seen_titles, out = set(), set(), []
    for r in results:
        uk = _url_key(r['url'])
        tk = _title_key(r['title'])
        if uk in seen_urls or (tk and tk in seen_titles):
            continue
        seen_urls.add(uk)
        if tk:
            seen_titles.add(tk)
        out.append(r)
    return out

def _relevance(result, query):
    words = set(re.sub(r'\W+', ' ', query.lower()).split())
    text  = f"{result['title']} {result['description']}".lower()
    hits  = sum(1 for w in words if len(w) > 2 and w in text)
    return hits / max(len(words), 1)


# ══════════════════════════════════════════════════════════════════════════════
# TIER 1 — SOURCES DE COURS (priorité maximale)
# ══════════════════════════════════════════════════════════════════════════════

def search_openclassrooms(query, lang='', n=15):
    """OpenClassrooms — cours en français principalement."""
    try:
        r = _get(
            f"https://openclassrooms.com/api/search?query={urllib.parse.quote(query)}"
            f"&types=course&lang={'fr' if not lang or lang=='fr' else lang}&limit={n*2}"
        )
        out = []
        for item in r.json().get('courses', r.json().get('results', [])):
            title = item.get('title') or item.get('name','')
            slug  = item.get('slug') or item.get('id','')
            url   = f"https://openclassrooms.com/fr/courses/{slug}"
            desc  = item.get('shortDescription') or item.get('description','')
            if not title: continue
            res = _make(title, url, 'OpenClassrooms', desc[:280],
                        doc_type='cours', lang='fr', priority=1)
            if _lang_ok(res, lang): out.append(res)
        return out[:n]
    except Exception:
        return _scrape_openclassrooms(query, lang, n)

def _scrape_openclassrooms(query, lang='', n=10):
    """Fallback scraping OpenClassrooms."""
    try:
        r = _get(f"https://openclassrooms.com/fr/search?query={urllib.parse.quote(query)}")
        soup = BeautifulSoup(r.text, 'html.parser')
        out  = []
        for card in soup.select('[class*="course-card"], [class*="CourseCard"], .course'):
            title_el = card.select_one('h2, h3, [class*="title"]')
            link_el  = card.select_one('a[href*="/courses/"]')
            if not title_el or not link_el: continue
            title = title_el.get_text(strip=True)
            href  = link_el['href']
            url   = href if href.startswith('http') else f"https://openclassrooms.com{href}"
            desc_el = card.select_one('p, [class*="description"]')
            desc  = desc_el.get_text(strip=True) if desc_el else ''
            out.append(_make(title, url, 'OpenClassrooms', desc, doc_type='cours', lang='fr', priority=1))
        return out[:n]
    except Exception:
        return []


def search_mit_ocw(query, lang='', n=10):
    """MIT OpenCourseWare — cours universitaires MIT gratuits."""
    try:
        r = _get(
            f"https://ocw.mit.edu/search/?q={urllib.parse.quote(query)}"
            f"&type=course&s=department_num&f=true"
        )
        soup = BeautifulSoup(r.text, 'html.parser')
        out  = []
        for card in soup.select('.course-card, .learn-card, [class*="CourseCard"]'):
            title_el = card.select_one('h3, h2, [class*="title"]')
            link_el  = card.select_one('a')
            if not title_el or not link_el: continue
            title = title_el.get_text(strip=True)
            href  = link_el.get('href','')
            url   = href if href.startswith('http') else f"https://ocw.mit.edu{href}"
            desc_el = card.select_one('p, [class*="description"]')
            desc  = desc_el.get_text(strip=True) if desc_el else 'Cours MIT OpenCourseWare'
            out.append(_make(title, url, 'MIT OpenCourseWare', desc, 'MIT', 'cours', lang='en', priority=1))
            if len(out) >= n: break
        return out
    except Exception:
        return []


def search_freecodecamp(query, lang='', n=8):
    """freeCodeCamp — tutoriels développement."""
    try:
        r = _get(f"https://www.freecodecamp.org/news/search/?query={urllib.parse.quote(query)}")
        soup = BeautifulSoup(r.text, 'html.parser')
        out  = []
        for article in soup.select('article, .post-card'):
            title_el = article.select_one('h2, h3, [class*="title"]')
            link_el  = article.select_one('a')
            if not title_el or not link_el: continue
            title = title_el.get_text(strip=True)
            href  = link_el.get('href','')
            url   = href if href.startswith('http') else f"https://www.freecodecamp.org{href}"
            desc_el = article.select_one('p')
            desc  = desc_el.get_text(strip=True) if desc_el else ''
            out.append(_make(title, url, 'freeCodeCamp', desc, doc_type='tutorial', lang='en', priority=1))
            if len(out) >= n: break
        return out
    except Exception:
        return []


def search_w3schools(query, lang='', n=6):
    """W3Schools — tutoriels web/dev."""
    try:
        r = _get(f"https://www.w3schools.com/search/search_result.asp?search={urllib.parse.quote(query)}")
        soup = BeautifulSoup(r.text, 'html.parser')
        out  = []
        for item in soup.select('.w3-bar-item, .searchresult, a[href*="w3schools.com"]'):
            href  = item.get('href','')
            if not href or not href.startswith('http'): continue
            title = item.get_text(strip=True) or href
            out.append(_make(title, href, 'W3Schools', 'Tutoriel W3Schools', doc_type='tutorial', lang='en', priority=1))
            if len(out) >= n: break
        return out
    except Exception:
        return []


def search_coursera_web(query, lang='', n=10):
    """Scrape Coursera pour les cours (sans API)."""
    try:
        r = _get(f"https://www.coursera.org/search?query={urllib.parse.quote(query)}&language={'fr' if lang=='fr' else 'en'}")
        soup = BeautifulSoup(r.text, 'html.parser')
        out  = []
        for card in soup.select('[data-e2e="product-card"], .rc-ProductCard, [class*="CourseCard"]'):
            title_el = card.select_one('h2, h3, [class*="card-title"], [class*="title"]')
            link_el  = card.select_one('a')
            if not title_el or not link_el: continue
            title = title_el.get_text(strip=True)
            href  = link_el.get('href','')
            url   = href if href.startswith('http') else f"https://www.coursera.org{href}"
            desc_el = card.select_one('p, [class*="description"]')
            desc  = desc_el.get_text(strip=True) if desc_el else ''
            out.append(_make(title, url, 'Coursera', desc, doc_type='cours', priority=1))
            if len(out) >= n: break
        return out
    except Exception:
        return []


def search_edx_web(query, lang='', n=10):
    """Scrape edX."""
    try:
        r = _get(f"https://www.edx.org/search?q={urllib.parse.quote(query)}")
        soup = BeautifulSoup(r.text, 'html.parser')
        out  = []
        for card in soup.select('[class*="course-card"], [class*="CourseCard"], .discovery-card'):
            title_el = card.select_one('h3, h2, [class*="title"]')
            link_el  = card.select_one('a')
            if not title_el or not link_el: continue
            title = title_el.get_text(strip=True)
            href  = link_el.get('href','')
            url   = href if href.startswith('http') else f"https://www.edx.org{href}"
            desc_el = card.select_one('p')
            desc  = desc_el.get_text(strip=True) if desc_el else ''
            out.append(_make(title, url, 'edX', desc, doc_type='cours', priority=1))
            if len(out) >= n: break
        return out
    except Exception:
        return []


def search_udemy_free(query, lang='', n=8):
    """Udemy cours gratuits via API publique."""
    try:
        r = _get(
            f"https://www.udemy.com/api-2.0/courses/?search={urllib.parse.quote(query)}"
            f"&price=price-free&page_size={n*2}&language={'fr' if lang=='fr' else 'en'}&ordering=relevance",
            headers={**HEADERS, 'Accept': 'application/json, text/plain, */*'}
        )
        out = []
        for c in r.json().get('results', []):
            title = c.get('title','')
            slug  = c.get('url','')
            url   = f"https://www.udemy.com{slug}" if slug else ''
            if not title or not url: continue
            desc = c.get('headline','')
            out.append(_make(title, url, 'Udemy (gratuit)', desc, doc_type='cours', priority=1))
        return out[:n]
    except Exception:
        return []


def search_khan_academy(query, lang='', n=8):
    """Khan Academy."""
    try:
        r = _get(f"https://www.khanacademy.org/api/internal/search/translate?query={urllib.parse.quote(query)}&lang={'fr' if lang=='fr' else 'en'}")
        out = []
        for item in r.json().get('hits', {}).get('hits', [])[:n*2]:
            src   = item.get('_source',{})
            title = src.get('translated_title') or src.get('title','')
            slug  = src.get('slug','')
            url   = f"https://fr.khanacademy.org{slug}" if lang=='fr' else f"https://www.khanacademy.org{slug}"
            desc  = src.get('translated_description') or src.get('description','')
            if not title or not slug: continue
            out.append(_make(title, url, 'Khan Academy', desc[:280], doc_type='cours', priority=1))
        return out[:n]
    except Exception:
        return []


def search_slideshare(query, lang='', n=10):
    """SlideShare — présentations et cours."""
    try:
        r = _get(f"https://www.slideshare.net/search/slideshow?searchfrom=header&q={urllib.parse.quote(query)}&lang={'fr' if lang=='fr' else 'en'}")
        soup = BeautifulSoup(r.text, 'html.parser')
        out  = []
        for item in soup.select('[class*="slide-list-item"], .slide-item, [data-id]'):
            title_el = item.select_one('a[title], h3, h2')
            if not title_el: continue
            title = title_el.get('title','') or title_el.get_text(strip=True)
            href  = title_el.get('href','') if title_el.name == 'a' else (item.select_one('a') or {}).get('href','')
            if not href: continue
            url = href if href.startswith('http') else f"https://www.slideshare.net{href}"
            desc_el = item.select_one('p, [class*="description"]')
            desc = desc_el.get_text(strip=True) if desc_el else ''
            out.append(_make(title, url, 'SlideShare', desc, doc_type='cours', priority=1))
            if len(out) >= n: break
        return out
    except Exception:
        return []


def search_scribd_free(query, lang='', n=10):
    """Scribd documents libres."""
    try:
        r = _get(f"https://www.scribd.com/search?query={urllib.parse.quote(query)}&language={'fr' if lang=='fr' else 'en'}&content_type=documents")
        soup = BeautifulSoup(r.text, 'html.parser')
        out  = []
        for item in soup.select('[class*="DocThumb"], [class*="document-card"], .cell'):
            title_el = item.select_one('a[title], h3, h2, [class*="title"]')
            link_el  = item.select_one('a[href*="/document/"], a[href*="/doc/"]')
            if not title_el or not link_el: continue
            title = title_el.get('title','') or title_el.get_text(strip=True)
            href  = link_el.get('href','')
            url   = href if href.startswith('http') else f"https://www.scribd.com{href}"
            out.append(_make(title, url, 'Scribd', '', doc_type='cours', priority=1))
            if len(out) >= n: break
        return out
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# TIER 2 — SOURCES ACADÉMIQUES
# ══════════════════════════════════════════════════════════════════════════════

def search_arxiv(query, lang='', n=12):
    try:
        q = query
        if lang and lang in LANG_WORDS:
            q = f"{query} {LANG_WORDS[lang][0]}"
        r = _get(f"https://export.arxiv.org/api/query?search_query=all:{urllib.parse.quote(q)}&max_results={n*2}&sortBy=relevance")
        soup = BeautifulSoup(r.text, 'xml')
        out  = []
        for e in soup.find_all('entry'):
            aid  = e.find('id').text.strip()
            summ = e.find('summary').text.strip()
            res  = _make(
                title   = e.find('title').text.strip(),
                url     = aid.replace('abs','pdf') + '.pdf',
                source  = 'arXiv',
                desc    = summ[:280],
                authors = ', '.join(a.find('name').text for a in e.find_all('author'))[:80],
                doc_type= 'academic',
                lang    = _detect_lang(summ) or 'en',
            )
            if _lang_ok(res, lang): out.append(res)
        return out[:n]
    except Exception:
        return []


def search_hal(query, lang='', n=10):
    try:
        lf = f" AND language_s:{lang}" if lang else ""
        r  = _get(
            f"https://api.archives-ouvertes.fr/search/?q={urllib.parse.quote(query+lf)}"
            f"&fl=title_s,authFullName_s,abstract_s,fileMain_s,producedDate_s,language_s"
            f"&fq=openAccess_bool:true&rows={n*2}&wt=json"
        )
        out = []
        for doc in r.json().get('response',{}).get('docs',[]):
            url = doc.get('fileMain_s','')
            if not url or not url.startswith('http'): continue
            title   = (doc.get('title_s') or [''])[0]
            desc    = (doc.get('abstract_s') or [''])[0][:280]
            authors = ', '.join((doc.get('authFullName_s') or [])[:3])
            dl      = (doc.get('language_s') or [''])[0]
            res     = _make(title, url, 'HAL', desc, authors, 'academic',
                            year=(doc.get('producedDate_s','') or '')[:4], lang=dl)
            if _lang_ok(res, lang): out.append(res)
        return out[:n]
    except Exception:
        return []


def search_base(query, lang='', n=10):
    try:
        lf = f"&boolang={lang}" if lang else ""
        r  = _get(
            f"https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi"
            f"?func=PerformSearch&query={urllib.parse.quote(query)}&hits={n*2}&boost=oa{lf}&format=json"
        )
        out = []
        for doc in r.json().get('response',{}).get('docs',[]):
            urls = doc.get('dclink',[])
            url  = urls[0] if urls else ''
            if not url: continue
            title   = doc.get('dctitle','')
            if isinstance(title, list): title = title[0]
            desc    = doc.get('dcdescription','')
            if isinstance(desc, list): desc = ' '.join(desc)
            authors = ', '.join((doc.get('dccreator') or [])[:3])
            dl      = doc.get('dclanguage','')
            if isinstance(dl, list): dl = dl[0] if dl else ''
            res = _make(title, url, 'BASE', desc[:280], authors, 'academic',
                        year=str(doc.get('dcdate',''))[:4], lang=dl)
            if _lang_ok(res, lang): out.append(res)
        return out[:n]
    except Exception:
        return []


def search_gutenberg(query, lang='', n=12):
    try:
        lp = f"&languages={GUTENBERG_LANG[lang]}" if lang in GUTENBERG_LANG else ""
        r  = _get(f"https://gutendex.com/books/?search={urllib.parse.quote(query)}{lp}")
        out = []
        for b in r.json().get('results',[])[:n*2]:
            fmts = b.get('formats',{})
            url  = (fmts.get('application/pdf')
                    or fmts.get('application/epub+zip')
                    or next((v for k,v in fmts.items() if 'pdf' in k or 'epub' in k),''))
            if not url: continue
            langs = b.get('languages',[])
            out.append(_make(
                title   = b.get('title',''),
                url     = url,
                source  = 'Project Gutenberg',
                desc    = f"Domaine public | Langue : {', '.join(langs)}",
                authors = ', '.join(a['name'] for a in b.get('authors',[]))[:80],
                doc_type= 'book',
                lang    = langs[0] if langs else '',
            ))
        return out[:n]
    except Exception:
        return []


def search_openlibrary(query, lang='', n=10):
    try:
        lp = f"&language={lang}" if lang else ""
        r  = _get(f"https://openlibrary.org/search.json?q={urllib.parse.quote(query)}&limit={n*2}{lp}")
        out = []
        for d in r.json().get('docs',[]):
            if not d.get('ia'): continue
            ia    = d['ia'][0] if isinstance(d['ia'],list) else d['ia']
            langs = d.get('language',[])
            if lang and langs and lang not in langs: continue
            out.append(_make(
                title   = d.get('title',''),
                url     = f'https://archive.org/download/{ia}/{ia}.pdf',
                source  = 'Open Library',
                desc    = f"Publié en {d.get('first_publish_year','N/A')}",
                authors = ', '.join(d.get('author_name',['Inconnu'])[:2]),
                doc_type= 'book',
                year    = d.get('first_publish_year',''),
                lang    = langs[0] if langs else '',
            ))
        return out[:n]
    except Exception:
        return []


def search_semantic(query, lang='', n=12):
    try:
        r = requests.get(
            f"https://api.semanticscholar.org/graph/v1/paper/search"
            f"?query={urllib.parse.quote(query)}&fields=title,authors,year,openAccessPdf,abstract&limit={n*2}",
            timeout=TIMEOUT, headers={'User-Agent':'PDFHarvester/3.0'},
        )
        out = []
        for p in r.json().get('data',[]):
            url = (p.get('openAccessPdf') or {}).get('url','')
            if not url: continue
            title = p.get('title','')
            desc  = (p.get('abstract') or '')[:280]
            res = _make(title, url, 'Semantic Scholar', desc,
                        ', '.join(a.get('name','') for a in p.get('authors',[])[:3]),
                        'academic', str(p.get('year','')),
                        lang=_detect_lang(f"{title} {desc}") or 'en')
            if _lang_ok(res, lang): out.append(res)
        return out[:n]
    except Exception:
        return []


def search_doaj(query, lang='', n=10):
    try:
        r = _get(f"https://doaj.org/api/search/articles/{urllib.parse.quote(query)}?pageSize={n*2}")
        out = []
        for item in r.json().get('results',[]):
            bib = item.get('bibjson',{})
            url = next((l['url'] for l in bib.get('link',[]) if l.get('type')=='fulltext'),'')
            if not url: continue
            authors = [a.get('name','') for a in bib.get('author',[])]
            dl = (bib.get('journal',{}).get('language') or [''])[0].lower()
            res = _make(bib.get('title',''), url, 'DOAJ', bib.get('abstract','')[:280],
                        ', '.join(authors[:3]), 'academic', str(bib.get('year','')), lang=dl)
            if lang and dl and not dl.startswith(lang): continue
            out.append(res)
        return out[:n]
    except Exception:
        return []


def search_internet_archive(query, lang='', n=10):
    try:
        lf = f" AND language:{lang}" if lang else ""
        r  = _get(
            f"https://archive.org/advancedsearch.php"
            f"?q={urllib.parse.quote(query+lf)}&fl=identifier,title,creator,description,language,year"
            f"&rows={n*2}&output=json&mediatype=texts"
        )
        out = []
        for doc in r.json().get('response',{}).get('docs',[]):
            uid = doc.get('identifier','')
            if not uid: continue
            url = f"https://archive.org/download/{uid}/{uid}.pdf"
            dl  = doc.get('language','')
            if isinstance(dl,list): dl = dl[0] if dl else ''
            res = _make(doc.get('title',''), url, 'Internet Archive',
                        (doc.get('description') or '')[:280],
                        doc.get('creator','')[:100], 'book',
                        str(doc.get('year','')), lang=dl.lower()[:2] if dl else '')
            if _lang_ok(res, lang): out.append(res)
        return out[:n]
    except Exception:
        return []


def search_pubmed(query, lang='', n=8):
    try:
        r = _get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pmc&term={urllib.parse.quote(query)}&retmax={n}&retmode=json")
        ids = r.json().get('esearchresult',{}).get('idlist',[])
        out = []
        for i in ids:
            res = _make(f'Article PMC{i}',
                        f'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{i}/pdf/',
                        'PubMed Central', f'Article médical open access PMC{i}',
                        doc_type='medical', lang='en')
            if _lang_ok(res, lang): out.append(res)
        return out[:n]
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# TIER 3 — RECHERCHE WEB INTELLIGENTE (fallback)
# ══════════════════════════════════════════════════════════════════════════════

def _smart_web_search(query, lang='', n=20):
    """Scrape moteurs de recherche pour trouver cours et docs."""
    results = []

    # DuckDuckGo — cours + PDF
    try:
        for suffix in [f"{query} cours tutoriel site:openclassrooms.com OR site:coursera.org OR site:edx.org",
                       f"{query} cours pdf gratuit {'en français' if lang=='fr' else ''}",
                       f"{query} filetype:pdf cours"]:
            r = _get(f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(suffix)}")
            soup = BeautifulSoup(r.text, 'html.parser')
            for item in soup.select('.result'):
                title_el = item.select_one('.result__title a')
                if not title_el: continue
                href  = title_el.get('href','')
                if not href or not href.startswith('http'): continue
                title = title_el.get_text(strip=True)
                desc_el = item.select_one('.result__snippet')
                desc  = desc_el.get_text(strip=True) if desc_el else ''
                # Détecter si c'est un cours
                is_cours = any(x in href.lower() for x in [
                    'openclassrooms','coursera','edx','udemy','khan','slideshare',
                    'scribd','ocw.mit','freecodecamp','w3schools','cours','tutorial'
                ])
                dtype = 'cours' if is_cours else ('document' if '.pdf' in href.lower() else 'document')
                prio  = 1 if is_cours else 4
                res = _make(title, href, 'Web', desc[:280],
                            doc_type=dtype, priority=prio,
                            lang=_detect_lang(f"{title} {desc}") or lang)
                if _lang_ok(res, lang): results.append(res)
            if len(results) >= n: break
    except Exception:
        pass

    # Bing — cours et PDFs
    try:
        q = f"{query} cours tutoriel {'français' if lang=='fr' else ''} filetype:pdf OR site:coursera.org OR site:edx.org"
        r = _get(f"https://www.bing.com/search?q={urllib.parse.quote(q)}&count=20")
        soup = BeautifulSoup(r.text, 'html.parser')
        for item in soup.select('.b_algo'):
            title_el = item.select_one('h2 a')
            if not title_el: continue
            href  = title_el.get('href','')
            if not href or not href.startswith('http'): continue
            title = title_el.get_text(strip=True)
            desc_el = item.select_one('.b_caption p')
            desc  = desc_el.get_text(strip=True) if desc_el else ''
            is_cours = any(x in href.lower() for x in [
                'openclassrooms','coursera','edx','udemy','khan','slideshare','scribd','cours'
            ])
            dtype = 'cours' if is_cours else 'document'
            prio  = 1 if is_cours else 4
            res = _make(title, href, 'Web (Bing)', desc[:280],
                        doc_type=dtype, priority=prio,
                        lang=_detect_lang(f"{title} {desc}") or lang)
            if _lang_ok(res, lang): results.append(res)
    except Exception:
        pass

    return _dedup(results)[:n]


# ══════════════════════════════════════════════════════════════════════════════
# DISPATCHER
# ══════════════════════════════════════════════════════════════════════════════

COURSE_SOURCES = {
    'openclassrooms': search_openclassrooms,
    'mit_ocw':        search_mit_ocw,
    'freecodecamp':   search_freecodecamp,
    'w3schools':      search_w3schools,
    'coursera':       search_coursera_web,
    'edx':            search_edx_web,
    'udemy_free':     search_udemy_free,
    'khan_academy':   search_khan_academy,
    'slideshare':     search_slideshare,
    'scribd':         search_scribd_free,
}

ACADEMIC_SOURCES = {
    'arxiv':           search_arxiv,
    'hal':             search_hal,
    'base':            search_base,
    'gutenberg':       search_gutenberg,
    'openlibrary':     search_openlibrary,
    'semantic':        search_semantic,
    'doaj':            search_doaj,
    'internet_archive':search_internet_archive,
    'pubmed':          search_pubmed,
}

ALL_SOURCES = {**COURSE_SOURCES, **ACADEMIC_SOURCES}


def run_search(query, sources, n, lang='', doc_type=''):
    results = []
    per = max(8, n // max(len(ALL_SOURCES), 1))

    # Recherche parallèle sur toutes les sources
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(fn, query, lang, per): name
                   for name, fn in ALL_SOURCES.items()}
        for future in as_completed(futures, timeout=30):
            try:
                results += future.result()
            except Exception:
                pass

    # Si peu de résultats → recherche web intelligente
    if len(results) < 15:
        results += _smart_web_search(query, lang, n=25)

    # Filtre par type si demandé
    if doc_type and doc_type not in ('', 'all'):
        results = [r for r in results if r.get('type') == doc_type]

    # Déduplication
    results = _dedup(results)

    # Tri : priorité d'abord, puis pertinence
    results.sort(key=lambda r: (
        r.get('priority', 4),
        -_relevance(r, query)
    ))

    return results[:n]


def scrape_page_for_pdfs(target_url):
    try:
        r = _get(target_url)
        soup = BeautifulSoup(r.text, 'html.parser')
        out, seen = [], set()
        for a in soup.find_all('a', href=True):
            href = a['href'].lower()
            if any(ext in href for ext in ['.pdf','.epub','.docx','.ppt','.pptx']):
                full = urljoin(target_url, a['href'])
                if full not in seen:
                    seen.add(full)
                    out.append(_make(
                        title   = a.get_text(strip=True) or os.path.basename(a['href']),
                        url     = full,
                        source  = urlparse(target_url).netloc,
                        desc    = f'Extrait de {target_url}',
                        doc_type= 'document',
                    ))
        return out
    except Exception as e:
        return {'error': str(e)}
