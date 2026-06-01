"""
Service d'envoi d'emails — vérification compte + reset mot de passe.

Variables d'environnement requises (à configurer sur Render) :
  MAIL_HOST     smtp.gmail.com  (ou smtp.brevo.com, etc.)
  MAIL_PORT     587
  MAIL_USER     ton-email@gmail.com
  MAIL_PASS     ton-app-password-gmail
  APP_URL       https://pdf-harvester.onrender.com

Pour Gmail : activer "Mots de passe d'application" dans ton compte Google.
"""
import smtplib, os, logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from itsdangerous import URLSafeTimedSerializer

logger = logging.getLogger(__name__)

MAIL_HOST = os.environ.get('MAIL_HOST', 'smtp.gmail.com')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
MAIL_USER = os.environ.get('MAIL_USER', '')
MAIL_PASS = os.environ.get('MAIL_PASS', '')
APP_URL   = os.environ.get('APP_URL', 'http://localhost:5000').rstrip('/')
SECRET    = os.environ.get('SECRET_KEY', 'dev-secret')

_serializer = URLSafeTimedSerializer(SECRET)


# ── Tokens ────────────────────────────────────────────────────────────────────

def make_verify_token(uid: str) -> str:
    return _serializer.dumps(uid, salt='email-verify')

def make_reset_token(uid: str) -> str:
    return _serializer.dumps(uid, salt='password-reset')

def verify_token(token: str, salt: str, max_age: int = 3600) -> str | None:
    """Retourne l'uid si le token est valide, None sinon."""
    try:
        return _serializer.loads(token, salt=salt, max_age=max_age)
    except Exception:
        return None


# ── Envoi ─────────────────────────────────────────────────────────────────────

def _send(to: str, subject: str, html: str) -> bool:
    if not MAIL_USER or not MAIL_PASS:
        logger.warning("Email non configuré — MAIL_USER/MAIL_PASS manquants")
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f'PDF Harvester <{MAIL_USER}>'
        msg['To']      = to
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        with smtplib.SMTP(MAIL_HOST, MAIL_PORT) as s:
            s.starttls()
            s.login(MAIL_USER, MAIL_PASS)
            s.sendmail(MAIL_USER, to, msg.as_string())
        return True
    except Exception as e:
        logger.error(f"Erreur envoi email à {to} : {e}")
        return False


def send_verification_email(to: str, uid: str, name: str) -> bool:
    token = make_verify_token(uid)
    link  = f"{APP_URL}/verify-email/{token}"
    html  = f"""
    <div style="font-family:sans-serif;max-width:520px;margin:auto;background:#06080d;color:#e2e8f4;padding:40px;border-radius:16px;">
      <h1 style="color:#4fffb0;font-size:24px;margin-bottom:8px;">📄 PDF Harvester</h1>
      <p style="color:#506080;font-size:13px;margin-bottom:32px;">Open Knowledge Platform</p>
      <h2 style="font-size:20px;margin-bottom:12px;">Bienvenue, {name} 👋</h2>
      <p style="color:#a0b0c8;line-height:1.7;margin-bottom:28px;">
        Merci de t'être inscrit(e). Clique sur le bouton ci-dessous pour vérifier ton adresse email
        et activer ton compte.
      </p>
      <a href="{link}" style="display:inline-block;background:#4fffb0;color:#000;padding:14px 32px;border-radius:10px;font-weight:700;text-decoration:none;font-size:15px;">
        ✅ Vérifier mon email
      </a>
      <p style="color:#506080;font-size:11px;margin-top:28px;">
        Ce lien expire dans 1 heure. Si tu n'as pas créé de compte, ignore cet email.
      </p>
    </div>
    """
    return _send(to, "✅ Vérifiez votre email — PDF Harvester", html)


def send_reset_email(to: str, uid: str, name: str) -> bool:
    token = make_reset_token(uid)
    link  = f"{APP_URL}/reset-password/{token}"
    html  = f"""
    <div style="font-family:sans-serif;max-width:520px;margin:auto;background:#06080d;color:#e2e8f4;padding:40px;border-radius:16px;">
      <h1 style="color:#4fffb0;font-size:24px;margin-bottom:8px;">📄 PDF Harvester</h1>
      <p style="color:#506080;font-size:13px;margin-bottom:32px;">Open Knowledge Platform</p>
      <h2 style="font-size:20px;margin-bottom:12px;">Réinitialisation du mot de passe</h2>
      <p style="color:#a0b0c8;line-height:1.7;margin-bottom:28px;">
        Bonjour {name}, tu as demandé à réinitialiser ton mot de passe.<br>
        Clique ci-dessous pour en choisir un nouveau.
      </p>
      <a href="{link}" style="display:inline-block;background:#ff6b6b;color:#fff;padding:14px 32px;border-radius:10px;font-weight:700;text-decoration:none;font-size:15px;">
        🔑 Réinitialiser mon mot de passe
      </a>
      <p style="color:#506080;font-size:11px;margin-top:28px;">
        Ce lien expire dans 1 heure. Si tu n'as pas fait cette demande, ignore cet email.
      </p>
    </div>
    """
    return _send(to, "🔑 Réinitialisation mot de passe — PDF Harvester", html)
