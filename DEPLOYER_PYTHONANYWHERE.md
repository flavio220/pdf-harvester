# Déploiement GRATUIT sur PythonAnywhere

PythonAnywhere offre un hébergement Flask **100% gratuit**, sans carte bancaire.
URL : https://www.pythonanywhere.com

---

## Étapes

### 1. Créer un compte
Va sur pythonanywhere.com → Sign up → **Beginner account** (gratuit)
Choisis un username, ex: `flavioadh` → ton site sera sur `flavioadh.pythonanywhere.com`

### 2. Ouvrir un terminal Bash
Dashboard → **Consoles** → **Bash**

### 3. Uploader le projet
Dans le terminal PythonAnywhere :
```bash
# Cloner depuis GitHub
git clone https://github.com/flavio220/pdf-harvester.git
cd pdf-harvester
```

### 4. Installer les dépendances
```bash
pip3 install --user -r requirements.txt
```

### 5. Créer l'application web
Dashboard → **Web** → **Add a new web app**
- Framework : **Flask**
- Python version : **3.10**
- Source code : `/home/flavioadh/pdf-harvester`
- WSGI file : cliquer sur le lien du fichier WSGI

### 6. Configurer le fichier WSGI
Remplace tout le contenu du fichier WSGI par :
```python
import sys
import os

project_home = '/home/flavioadh/pdf-harvester'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ['SECRET_KEY'] = 'mets-une-vraie-cle-secrete-ici'
os.environ['DATABASE_PATH'] = '/home/flavioadh/pdf-harvester/instance/app.db'
os.environ['APP_URL'] = 'https://flavioadh.pythonanywhere.com'
os.environ['MAIL_HOST'] = 'smtp.gmail.com'
os.environ['MAIL_PORT'] = '587'
os.environ['MAIL_USER'] = 'flavioadantchede@gmail.com'
os.environ['MAIL_PASS'] = 'ton-app-password-gmail'

from wsgi import app as application
```
⚠️ Remplace `flavioadh` par ton vrai username PythonAnywhere partout.

### 7. Créer le dossier instance
Dans le terminal Bash :
```bash
mkdir -p /home/flavioadh/pdf-harvester/instance
```

### 8. Créer ton compte admin
```bash
cd /home/flavioadh/pdf-harvester
python3 create_admin.py
```

### 9. Reloader l'app
Dashboard → Web → bouton **Reload**

### 10. Accéder au site
`https://flavioadh.pythonanywhere.com`
`https://flavioadh.pythonanywhere.com/admin`

---

## Mettre à jour le site après un push GitHub

Dans le terminal Bash PythonAnywhere :
```bash
cd ~/pdf-harvester
git pull
```
Puis Dashboard → Web → **Reload**

---

## Limites du plan gratuit
- 1 application web
- 512 MB stockage
- CPU limité (suffisant pour usage normal)
- Domaine : `username.pythonanywhere.com` (pas de domaine custom)
- Trafic limité mais largement suffisant
