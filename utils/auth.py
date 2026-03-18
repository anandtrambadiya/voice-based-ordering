from functools import wraps
from flask import session, redirect, url_for, jsonify, request, g
from models import Restaurant, User


def load_user():
    """Call at start of every request — populates g.restaurant and g.user."""
    g.restaurant = None
    g.user       = None
    rid = session.get('restaurant_id')
    uid = session.get('user_id')
    if rid and uid:
        g.restaurant = Restaurant.query.get(rid)
        g.user       = User.query.get(uid)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Not logged in'}), 401
            return redirect(url_for('auth.login_page'))
        return f(*args, **kwargs)
    return decorated


def owner_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Not logged in'}), 401
            return redirect(url_for('auth.login_page'))
        if session.get('role') != 'owner':
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Owner access required'}), 403
            return redirect(url_for('orders.new_order_page'))
        return f(*args, **kwargs)
    return decorated