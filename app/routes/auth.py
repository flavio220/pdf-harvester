import re
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template

from ..models.user import (
    create_user, get_user_by_email, get_user_by_id,
    check_pw, hash_pw, update_user, safe_user
)
from ..services.auth import login_required
from ..services.email import (
    send_verification_email, send_reset_email,
    verify_token, make_verify_token
)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data     = request.json or {}
    email    = (data.get('email') or '').strip().lower()
    password = data.get('password', '')
    name     = (data.get('name') or '').strip()
    ref_code = (data.get('ref_code') or '').strip().upper()

    if not email or not password or not name:
        return jsonify({'error': 'Tous les champs sont requis'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Mot de passe trop court (6 caractères min)'}), 400
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return jsonify({'error': 'Email invalide'}), 400
    if get_user_by_email(email):
        return jsonify({'error': 'Email déjà utilisé'}), 409

    user = create_user(email, name, password, ref_code)
    session['user_id'] = user['id']

    # Envoi email de vérification (non bloquant)
    send_verification_email(email, user['id'], name)

    return jsonify({'user': safe_user(user), 'redirect': '/app'})


@auth_bp.route('/login', methods=['POST'])
def login():
    data     = request.json or {}
    email    = (data.get('email') or '').strip().lower()
    password = data.get('password', '')

    user = get_user_by_email(email)
    if not user or not check_pw(password, user['password_hash']):
        return jsonify({'error': 'Email ou mot de passe incorrect'}), 401

    session['user_id'] = user['id']
    return jsonify({'user': safe_user(user), 'redirect': '/app'})


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'redirect': '/auth'})


@auth_bp.route('/me')
@login_required
def me():
    user = get_user_by_id(session['user_id'])
    return jsonify({'user': safe_user(user)})


# ── Vérification email ────────────────────────────────────────────────────────

@auth_bp.route('/resend-verification', methods=['POST'])
@login_required
def resend_verification():
    user = get_user_by_id(session['user_id'])
    if user.get('email_verified'):
        return jsonify({'message': 'Email déjà vérifié'}), 200
    send_verification_email(user['email'], user['id'], user['name'])
    return jsonify({'message': 'Email de vérification envoyé'})


# ── Mot de passe oublié ───────────────────────────────────────────────────────

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data  = request.json or {}
    email = (data.get('email') or '').strip().lower()
    user  = get_user_by_email(email)
    # Toujours répondre OK (sécurité : ne pas révéler si l'email existe)
    if user:
        send_reset_email(email, user['id'], user['name'])
    return jsonify({'message': 'Si cet email est enregistré, un lien de réinitialisation a été envoyé.'})
