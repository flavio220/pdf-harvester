"""
Opérations CRUD sur la table users + helpers métier.
"""
import uuid, random, string
from datetime import datetime
from .db import get_db
from ..config import PLANS, REFERRAL_BONUS, REFERRAL_MILESTONE
import bcrypt


# ── Helpers ──────────────────────────────────────────────────────────────────

def hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_pw(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def gen_ref_code() -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


AVATAR_COLORS = ['#4fffb0', '#7b61ff', '#ff6b6b', '#f5c842', '#60bfff', '#ff9f7e']


# ── Lecture ───────────────────────────────────────────────────────────────────

def get_user_by_id(uid: str):
    row = get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    return dict(row) if row else None


def get_user_by_email(email: str):
    row = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return dict(row) if row else None


def get_user_by_ref_code(code: str):
    row = get_db().execute("SELECT * FROM users WHERE ref_code = ?", (code,)).fetchone()
    return dict(row) if row else None


def get_referred_users(uid: str):
    rows = get_db().execute(
        "SELECT name, created_at FROM users WHERE referred_by = ?", (uid,)
    ).fetchall()
    return [dict(r) for r in rows]


# ── Écriture ──────────────────────────────────────────────────────────────────

def create_user(email: str, name: str, password: str, ref_code_used: str = '') -> dict:
    db = get_db()
    uid = str(uuid.uuid4())
    ref_code = gen_ref_code()
    color = random.choice(AVATAR_COLORS)
    now = datetime.now().strftime('%d/%m/%Y')

    db.execute(
        """INSERT INTO users
           (id, email, name, bio, avatar_color, password_hash, plan,
            downloads_used, bonus_downloads, ref_code, referred_by,
            referrals_count, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (uid, email, name, '', color, hash_pw(password), 'free',
         0, 0, ref_code, None, 0, now)
    )

    # Traiter le parrainage
    if ref_code_used:
        referrer = get_user_by_ref_code(ref_code_used)
        if referrer and referrer['id'] != uid:
            new_count = referrer['referrals_count'] + 1
            bonus = REFERRAL_BONUS
            # Palier atteint ?
            milestone_bonus = REFERRAL_MILESTONE.get(new_count, {}).get('bonus_dl', 0)
            db.execute(
                """UPDATE users SET
                   referrals_count = referrals_count + 1,
                   bonus_downloads  = bonus_downloads + ?
                   WHERE id = ?""",
                (bonus + milestone_bonus, referrer['id'])
            )
            db.execute("UPDATE users SET referred_by = ? WHERE id = ?", (referrer['id'], uid))

    db.commit()
    return get_user_by_id(uid)


def update_user(uid: str, **fields) -> dict:
    if not fields:
        return get_user_by_id(uid)
    db = get_db()
    cols = ', '.join(f"{k} = ?" for k in fields)
    db.execute(f"UPDATE users SET {cols} WHERE id = ?", (*fields.values(), uid))
    db.commit()
    return get_user_by_id(uid)


def increment_downloads(uid: str):
    db = get_db()
    db.execute("UPDATE users SET downloads_used = downloads_used + 1 WHERE id = ?", (uid,))
    db.commit()


# ── Sérialisation publique ────────────────────────────────────────────────────

def safe_user(u: dict) -> dict:
    plan_info = PLANS[u.get('plan', 'free')]
    limit = plan_info['download_limit']
    used  = u.get('downloads_used', 0)
    bonus = u.get('bonus_downloads', 0)
    effective = limit + bonus if limit < 9_999_999 else limit
    refs = u.get('referrals_count', 0)

    badge = None
    for t in sorted(REFERRAL_MILESTONE, reverse=True):
        if refs >= t:
            badge = REFERRAL_MILESTONE[t]
            break

    return {
        'id':              u['id'],
        'email':           u['email'],
        'name':            u['name'],
        'bio':             u.get('bio', ''),
        'avatar_color':    u.get('avatar_color', '#4fffb0'),
        'plan':            u.get('plan', 'free'),
        'plan_name':       plan_info['name'],
        'downloads_used':  used,
        'download_limit':  effective,
        'bonus_downloads': bonus,
        'downloads_left':  max(0, effective - used) if effective < 9_999_999 else '∞',
        'deep_search':     plan_info['deep_search'],
        'ref_code':        u.get('ref_code', ''),
        'referrals_count': refs,
        'badge':           badge,
        'created_at':      u.get('created_at', ''),
        'email_verified':  bool(u.get('email_verified', 0)),
        'is_admin':        bool(u.get('is_admin', 0)),
        'is_banned':       bool(u.get('is_banned', 0)),
    }


def get_all_users() -> list:
    rows = get_db().execute(
        "SELECT * FROM users ORDER BY created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def get_user_count() -> int:
    return get_db().execute("SELECT COUNT(*) FROM users").fetchone()[0]


def get_stats() -> dict:
    db = get_db()
    return {
        'total_users':    db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        'verified_users': db.execute("SELECT COUNT(*) FROM users WHERE email_verified=1").fetchone()[0],
        'free_users':     db.execute("SELECT COUNT(*) FROM users WHERE plan='free'").fetchone()[0],
        'scholar_users':  db.execute("SELECT COUNT(*) FROM users WHERE plan='scholar'").fetchone()[0],
        'elite_users':    db.execute("SELECT COUNT(*) FROM users WHERE plan='elite'").fetchone()[0],
        'banned_users':   db.execute("SELECT COUNT(*) FROM users WHERE is_banned=1").fetchone()[0],
        'total_downloads':db.execute("SELECT COALESCE(SUM(downloads_used),0) FROM users").fetchone()[0],
    }
