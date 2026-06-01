from flask import Blueprint, request, jsonify, session

from ..models.user import (
    get_user_by_id, update_user, check_pw, hash_pw, safe_user,
    get_referred_users
)
from ..services.auth import login_required
from ..config import PLANS, REFERRAL_MILESTONE

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    data = request.json or {}
    uid  = session['user_id']
    user = get_user_by_id(uid)

    fields = {}
    name  = (data.get('name') or '').strip()
    bio   = (data.get('bio') or '').strip()[:200]
    color = data.get('avatar_color')

    if name:  fields['name'] = name
    fields['bio'] = bio
    if color: fields['avatar_color'] = color

    old_pw = data.get('old_password', '')
    new_pw = data.get('new_password', '')
    if old_pw and new_pw:
        if not check_pw(old_pw, user['password_hash']):
            return jsonify({'error': 'Ancien mot de passe incorrect'}), 400
        if len(new_pw) < 6:
            return jsonify({'error': 'Nouveau mot de passe trop court'}), 400
        fields['password_hash'] = hash_pw(new_pw)

    updated = update_user(uid, **fields)
    return jsonify({'user': safe_user(updated)})


@profile_bp.route('/upgrade', methods=['POST'])
@login_required
def upgrade():
    data = request.json or {}
    plan = data.get('plan')
    if plan not in ('scholar', 'elite'):
        return jsonify({'error': 'Plan invalide'}), 400
    uid     = session['user_id']
    updated = update_user(uid, plan=plan)
    return jsonify({'user': safe_user(updated)})


@profile_bp.route('/referral/stats')
@login_required
def referral_stats():
    uid  = session['user_id']
    user = get_user_by_id(uid)
    refs = get_referred_users(uid)

    from flask import request as req
    base_url = req.host_url.rstrip('/')
    ref_link = f"{base_url}/auth?ref={user.get('ref_code', '')}"

    count = user.get('referrals_count', 0)
    next_ms = next(
        (
            {**REFERRAL_MILESTONE[t], 'at': t, 'need': t - count}
            for t in sorted(REFERRAL_MILESTONE)
            if t > count
        ),
        None,
    )

    return jsonify({'stats': {
        'count':          count,
        'bonus_earned':   user.get('bonus_downloads', 0),
        'ref_code':       user.get('ref_code', ''),
        'ref_link':       ref_link,
        'referred_users': [{'name': r['name'], 'joined': r['created_at']} for r in refs],
        'next_milestone': next_ms,
    }})
