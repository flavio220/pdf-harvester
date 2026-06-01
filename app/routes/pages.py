from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify

from ..models.user import get_user_by_id, update_user, hash_pw
from ..services.email import verify_token

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
def index():
    return render_template('landing.html')


@pages_bp.route('/auth')
def auth_page():
    if 'user_id' in session:
        return redirect(url_for('pages.app_page'))
    return render_template(
        'auth.html',
        ref_code=request.args.get('ref', ''),
        tab=request.args.get('tab', 'login'),
        q=request.args.get('q', ''),
    )


@pages_bp.route('/app')
def app_page():
    if 'user_id' not in session:
        return redirect(url_for('pages.auth_page'))
    return render_template('app.html')


@pages_bp.route('/verify-email/<token>')
def verify_email(token):
    uid = verify_token(token, salt='email-verify', max_age=3600)
    if not uid:
        return render_template('message.html',
            icon='❌', title='Lien invalide ou expiré',
            message='Ce lien de vérification est invalide ou a expiré.',
            link='/app', link_label='Retour au dashboard')

    user = get_user_by_id(uid)
    if not user:
        return redirect('/auth')

    update_user(uid, email_verified=1)
    return render_template('message.html',
        icon='✅', title='Email vérifié !',
        message=f'Bienvenue {user["name"]}, ton compte est maintenant vérifié.',
        link='/app', link_label='Aller au dashboard')


@pages_bp.route('/reset-password/<token>')
def reset_password_page(token):
    uid = verify_token(token, salt='password-reset', max_age=3600)
    if not uid:
        return render_template('message.html',
            icon='❌', title='Lien invalide ou expiré',
            message='Ce lien de réinitialisation est invalide ou a expiré.',
            link='/auth', link_label='Retour à la connexion')
    return render_template('reset_password.html', token=token)


@pages_bp.route('/api/reset-password', methods=['POST'])
def do_reset_password():
    data     = request.json or {}
    token    = data.get('token', '')
    password = data.get('password', '')

    uid = verify_token(token, salt='password-reset', max_age=3600)
    if not uid:
        return jsonify({'error': 'Lien invalide ou expiré'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Mot de passe trop court (6 caractères min)'}), 400

    update_user(uid, password_hash=hash_pw(password))
    return jsonify({'message': 'Mot de passe mis à jour !', 'redirect': '/auth'})
