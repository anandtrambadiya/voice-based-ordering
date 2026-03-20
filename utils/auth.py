from functools import wraps
from flask import session, redirect, url_for, jsonify, request, g
from models import Restaurant, User


def load_user():
    g.restaurant = None
    g.user       = None
    rid = session.get('restaurant_id')
    uid = session.get('user_id')
    if rid and uid:
        g.restaurant = Restaurant.query.get(rid)
        g.user       = User.query.get(uid)


def _is_api():
    return request.path.startswith('/api/')

def _redirect_or_401():
    if _is_api():
        return jsonify({'error': 'Not logged in'}), 401
    return redirect(url_for('auth.login_page'))

def _forbidden_or_403(msg='Access denied'):
    if _is_api():
        return jsonify({'error': msg}), 403
    return redirect('/order/new')


def login_required(f):
    """Any logged-in user (owner or staff)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return _redirect_or_401()
        return f(*args, **kwargs)
    return decorated


def owner_required(f):
    """Owner only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return _redirect_or_401()
        if session.get('role') != 'owner':
            return _forbidden_or_403('Owner access required')
        return f(*args, **kwargs)
    return decorated


def staff_required(f):
    """Staff or owner (anyone logged in with a valid role)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return _redirect_or_401()
        if session.get('role') not in ('owner', 'staff'):
            return _forbidden_or_403('Staff access required')
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    """VoiceBill admin panel only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            if _is_api():
                return jsonify({'error': 'Admin access required'}), 401
            return redirect('/admin')
        return f(*args, **kwargs)
    return decorated