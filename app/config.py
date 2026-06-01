FREE_LIMIT     = 7
REFERRAL_BONUS = 5

REFERRAL_MILESTONE = {
    3:  {'label': 'Passeur de Savoir', 'bonus_dl': 15,  'badge': '🥉'},
    7:  {'label': 'Ambassadeur',        'bonus_dl': 30,  'badge': '🥈'},
    15: {'label': 'Grand Recruteur',    'bonus_dl': 75,  'badge': '🥇'},
    30: {'label': 'Légende Vivante',    'bonus_dl': 200, 'badge': '👑'},
}

ALL_SOURCES = [
    # Tier 1 — Cours
    'openclassrooms','mit_ocw','freecodecamp','w3schools',
    'coursera','edx','udemy_free','khan_academy','slideshare','scribd',
    # Tier 2 — Académique
    'arxiv','hal','base','gutenberg','openlibrary',
    'semantic','doaj','internet_archive','pubmed',
]

PLANS = {
    'free': {
        'name': 'Gratuit',
        'download_limit': FREE_LIMIT,
        'deep_search': False,
        'sources': ALL_SOURCES,
        'results_per_search': 40,
    },
    'scholar': {
        'name': 'Scholar',
        'price': '4.99€/mois',
        'download_limit': 100,
        'deep_search': True,
        'sources': ALL_SOURCES,
        'results_per_search': 100,
    },
    'elite': {
        'name': 'Élite',
        'price': '12.99€/mois',
        'download_limit': 9_999_999,
        'deep_search': True,
        'sources': ALL_SOURCES,
        'results_per_search': 250,
    },
}

HTTP_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0 Safari/537.36'
    )
}
