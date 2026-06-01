import re, tempfile
from flask import Blueprint, request, jsonify, session, send_file

from ..models.user import get_user_by_id, increment_downloads, safe_user
from ..services.auth import login_required
from ..services.search import run_search, scrape_page_for_pdfs
from ..config import PLANS
import requests

search_bp = Blueprint('search', __name__)

HTTP_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0 Safari/537.36'
    )
}

LANG_NAMES = {
    'fr': 'french', 'en': 'english', 'es': 'spanish',
    'ar': 'arabic', 'pt': 'portuguese', 'de': 'german',
    'zh': 'chinese', 'ru': 'russian',
}


@search_bp.route('/search', methods=['POST'])
@login_required
def search():
    data     = request.json or {}
    query    = (data.get('query') or '').strip()
    lang     = (data.get('lang') or '').strip().lower()
    doc_type = (data.get('doc_type') or '').strip().lower()

    if not query:
        return jsonify({'error': 'Requête vide'}), 400

    # Langue passée directement aux sources

    user    = get_user_by_id(session['user_id'])
    plan    = PLANS[user.get('plan', 'free')]
    results = run_search(query, plan['sources'], plan['results_per_search'], lang=lang)

    # Filtrer par type si demandé
    if doc_type and doc_type != 'pdf':
        results = [r for r in results if r.get('type') == doc_type]

    return jsonify({'results': results, 'total': len(results)})


@search_bp.route('/scrape', methods=['POST'])
@login_required
def scrape():
    data = request.json or {}
    url  = (data.get('url') or '').strip()
    if not url:
        return jsonify({'error': 'URL vide'}), 400
    if not url.startswith('http'):
        url = 'https://' + url

    results = scrape_page_for_pdfs(url)
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500
    return jsonify({'results': results, 'total': len(results)})


@search_bp.route('/download', methods=['POST'])
@login_required
def download():
    uid  = session['user_id']
    user = get_user_by_id(uid)
    plan = PLANS[user.get('plan', 'free')]

    limit     = plan['download_limit']
    bonus     = user.get('bonus_downloads', 0)
    effective = limit + bonus if limit < 9_999_999 else limit
    used      = user.get('downloads_used', 0)

    if effective < 9_999_999 and used >= effective:
        return jsonify({
            'error': 'LIMIT_REACHED',
            'limit': effective,
            'plan':  user.get('plan'),
        }), 403

    data     = request.json or {}
    pdf_url  = (data.get('url') or '').strip()
    filename = data.get('filename', 'document')

    if not pdf_url:
        return jsonify({'error': 'URL manquante'}), 400

    try:
        r = requests.get(pdf_url, headers=HTTP_HEADERS, timeout=30, stream=True)
        r.raise_for_status()
        # Détecter le type depuis Content-Type
        ct = r.headers.get('Content-Type', 'application/octet-stream')
        ext = '.pdf'
        if 'epub' in ct:   ext = '.epub'
        elif 'html' in ct: ext = '.html'
        elif 'word' in ct or 'docx' in ct: ext = '.docx'

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        for chunk in r.iter_content(8192):
            tmp.write(chunk)
        tmp.close()
    except Exception as e:
        return jsonify({'error': f'Téléchargement impossible : {e}'}), 500

    increment_downloads(uid)

    safe_name = re.sub(r'[^\w\s\-]', '', filename)[:60].strip() + ext
    return send_file(tmp.name, as_attachment=True, download_name=safe_name,
                     mimetype=ct.split(';')[0])
