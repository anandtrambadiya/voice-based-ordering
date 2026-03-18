from flask import Blueprint, render_template, request, jsonify, abort, session, g, redirect
from models import db, Restaurant, MenuItem, Order, OrderItem
import hashlib

customer_bp = Blueprint('customer', __name__)

def _make_token(rid):
    return hashlib.md5(f"vb-{rid}-token".encode()).hexdigest()[:10]

def get_restaurant_by_token(token):
    for r in Restaurant.query.filter_by(active=True).all():
        if _make_token(r.id) == token:
            return r
    return None

@customer_bp.route('/menu/<int:table_no>')
def customer_order(table_no):
    token = request.args.get('r', '')
    restaurant = get_restaurant_by_token(token)
    if not restaurant:
        abort(404)
    # Set session so /api/menu works without login
    session['restaurant_id'] = restaurant.id
    session['user_id'] = None
    return render_template('order.html',
        current_restaurant=restaurant,
        customer_table=table_no,
        customer_token=token
    )


@customer_bp.route('/api/customer/menu')
def customer_menu():
    token = request.args.get('r', '')
    restaurant = get_restaurant_by_token(token)
    if not restaurant:
        abort(404)
    items = MenuItem.query.filter_by(restaurant_id=restaurant.id, available=True).all()
    return jsonify([i.to_dict() for i in items])

@customer_bp.route('/api/customer/order', methods=['POST'])
def customer_place_order():
    data  = request.get_json() or {}
    token = data.get('token', '')
    restaurant = get_restaurant_by_token(token)
    if not restaurant:
        return jsonify({'error': 'Invalid'}), 403
    items = data.get('items', [])
    if not items:
        return jsonify({'error': 'No items'}), 400
    order = Order(restaurant_id=restaurant.id, table_no=str(data.get('table_no','1')), status='placed')
    db.session.add(order)
    db.session.flush()
    subtotal = 0
    for it in items:
        m = MenuItem.query.filter_by(id=it['menu_item_id'], restaurant_id=restaurant.id).first()
        if not m: continue
        qty = int(it.get('quantity', 1))
        db.session.add(OrderItem(order_id=order.id, menu_item_id=m.id, name=m.name, price=m.price, quantity=qty))
        subtotal += m.price * qty
    order.subtotal = round(subtotal, 2)
    order.tax      = round(subtotal * 0.05, 2)
    order.total    = round(order.subtotal + order.tax, 2)
    db.session.commit()
    return jsonify({'order_id': order.id, 'total': order.total}), 201

@customer_bp.route('/api/customer/qr-url')
def qr_url():
    rid = session.get('restaurant_id')
    if not rid: return jsonify({'error': 'Not logged in'}), 401
    table = request.args.get('table', '1')
    token = _make_token(rid)
    url   = f"{request.host_url.rstrip('/')}/menu/{table}?r={token}"
    return jsonify({'url': url, 'token': token})

@customer_bp.route('/tables')
def tables_page():
    from utils.auth import owner_required
    if not session.get('user_id'):
        return redirect('/login')
    if session.get('role') != 'owner':
        return redirect('/order/new')
    return render_template('tables.html')