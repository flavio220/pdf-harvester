from functools import wraps
from flask import session, request, jsonify, redirect, url_for
from ..models.user import get_user_by_id


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        uid = session.get('user_id')
        if not uid:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'AUTH_REQUIRED'}), 401
            return redirect(url_for('pages.auth_page'))
        user = get_user_by_id(uid)
        if not user:
            session.clear()
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'AUTH_REQUIRED'}), 401
            return redirect(url_for('pages.auth_page'))
        if user.get('is_banned'):
            session.clear()
            return jsonify({'error': 'ACCOUNT_BANNED'}), 403
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        uid = session.get('user_id')
        if not uid:
            return redirect(url_for('pages.auth_page'))
        user = get_user_by_id(uid)
        if not user or not user.get('is_admin'):
            if request.is_json:
                return jsonify({'error': 'FORBIDDEN'}), 403
            return redirect(url_for('pages.index'))
        return f(*args, **kwargs)
    return decorated
