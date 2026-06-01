"""
Script à exécuter UNE SEULE FOIS sur Render Shell pour créer le compte admin.
Usage : python create_admin.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.models.user import get_user_by_email, create_user, update_user, safe_user

EMAIL    = 'flavioadantchede@gmail.com'
NAME     = 'Flavio ADH'
PASSWORD = 'ChangeMe2024!'

app = create_app()

with app.app_context():
    with app.test_request_context():
        user = get_user_by_email(EMAIL)

        if user:
            updated = update_user(user['id'], plan='elite', email_verified=1, is_admin=1)
            print(f"✅ Compte existant mis à jour")
        else:
            user    = create_user(EMAIL, NAME, PASSWORD)
            updated = update_user(user['id'], plan='elite', email_verified=1, is_admin=1)
            print(f"✅ Compte créé")
            print(f"   Mot de passe provisoire : {PASSWORD}")
            print(f"   ⚠️  Change-le après connexion !")

        info = safe_user(updated)
        print(f"\n   Email    : {EMAIL}")
        print(f"   Plan     : {info['plan_name']}")
        print(f"   Admin    : {'✅ Oui' if updated.get('is_admin') else '❌ Non'}")
        print(f"   Vérifié  : {'✅ Oui' if info['email_verified'] else '❌ Non'}")
        print(f"\n   Dashboard admin : https://pdf-harvester.onrender.com/admin")
