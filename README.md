# 📄 PDF Harvester v5

Application web Flask pour rechercher et télécharger des PDFs libres de droits.

## 🗂️ Structure

```
pdf-harvester-v5/
├── wsgi.py                  ← Point d'entrée Gunicorn / dev
├── requirements.txt
├── Procfile                 ← Pour Render / Heroku
├── render.yaml              ← Config déploiement Render.com
├── .gitignore
├── templates/
│   ├── landing.html
│   ├── auth.html
│   └── app.html
└── app/
    ├── __init__.py          ← App factory (create_app)
    ├── config.py            ← Plans, paliers parrainage, constantes
    ├── models/
    │   ├── db.py            ← SQLite (get_db, init_db)
    │   └── user.py          ← CRUD utilisateurs + safe_user()
    ├── services/
    │   ├── auth.py          ← Décorateur login_required
    │   └── search.py        ← Toutes les sources de recherche
    └── routes/
        ├── pages.py         ← /, /auth, /app
        ├── auth.py          ← /api/register, login, logout, me
        ├── profile.py       ← /api/profile/update, upgrade, referral/stats
        └── search.py        ← /api/search, scrape, download
```

## 🚀 Lancement local

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python wsgi.py
# → http://localhost:5000
```

## ☁️ Déploiement sur Render

1. Pusher ce dossier sur GitHub
2. Sur [render.com](https://render.com) → **New Web Service** → connecter le repo
3. Render détecte `render.yaml` automatiquement
4. Le **Persistent Disk** (`/var/data`) garde la base SQLite entre redémarrages
5. `SECRET_KEY` est auto-générée par Render

## 🔒 Améliorations v5

| Problème v4                     | Fix v5                                |
|---------------------------------|---------------------------------------|
| `users.json` (pas concurrent)   | SQLite avec WAL mode                  |
| SHA-256 pour les mots de passe  | `bcrypt` (hash lent + sel)            |
| `app.py` monolithique (400 lg)  | Blueprint Flask par domaine           |
| `ref_link` hardcodé localhost   | `request.host_url` dynamique          |
| Pas de `Procfile` correct       | `wsgi.py` + workers configurés        |

## 🔮 Prochaines étapes

- [ ] Intégrer Stripe pour les paiements Scholar / Élite
- [ ] Migrer vers PostgreSQL si trafic élevé (`psycopg2` + `DATABASE_URL`)
- [ ] Ajouter rate-limiting (`Flask-Limiter`)
- [ ] Email de confirmation à l'inscription (`Flask-Mail`)
