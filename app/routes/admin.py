from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from ..models.user import (
    get_all_users, get_user_by_id, update_user, safe_user, get_stats
)
from ..services.auth import admin_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin')
@admin_required
def admin_page():
    return render_template('admin.html')


# ── API Admin ─────────────────────────────────────────────────────────────────

@admin_bp.route('/api/admin/stats')
@admin_required
def admin_stats():
    return jsonify(get_stats())


@admin_bp.route('/api/admin/users')
@admin_required
def admin_users():
    users = get_all_users()
    result = []
    for u in users:
        result.append({
            'id':             u['id'],
            'name':           u['name'],
            'email':          u['email'],
            'plan':           u['plan'],
            'downloads_used': u['downloads_used'],
            'email_verified': bool(u.get('email_verified', 0)),
            'is_admin':       bool(u.get('is_admin', 0)),
            'is_banned':      bool(u.get('is_banned', 0)),
            'created_at':     u['created_at'],
            'referrals_count':u.get('referrals_count', 0),
        })
    return jsonify({'users': result})


@admin_bp.route('/api/admin/user/<uid>/plan', methods=['POST'])
@admin_required
def set_plan(uid):
    data = request.json or {}
    plan = data.get('plan')
    if plan not in ('free', 'scholar', 'elite'):
        return jsonify({'error': 'Plan invalide'}), 400
    update_user(uid, plan=plan)
    return jsonify({'ok': True})


@admin_bp.route('/api/admin/user/<uid>/ban', methods=['POST'])
@admin_required
def ban_user(uid):
    # Ne pas se bannir soi-même
    if uid == session.get('user_id'):
        return jsonify({'error': 'Impossible de se bannir soi-même'}), 400
    data    = request.json or {}
    banned  = 1 if data.get('ban') else 0
    update_user(uid, is_banned=banned)
    return jsonify({'ok': True})


@admin_bp.route('/api/admin/user/<uid>/verify', methods=['POST'])
@admin_required
def verify_user(uid):
    update_user(uid, email_verified=1)
    return jsonify({'ok': True})


@admin_bp.route('/api/admin/user/<uid>/admin', methods=['POST'])
@admin_required
def toggle_admin(uid):
    if uid == session.get('user_id'):
        return jsonify({'error': 'Impossible de modifier son propre statut admin'}), 400
    data     = request.json or {}
    is_admin = 1 if data.get('admin') else 0
    update_user(uid, is_admin=is_admin)
    return jsonify({'ok': True})


@admin_bp.route('/api/admin/user/<uid>/reset-downloads', methods=['POST'])
@admin_required
def reset_downloads(uid):
    update_user(uid, downloads_used=0)
    return jsonify({'ok': True})
