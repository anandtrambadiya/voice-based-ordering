from flask import Blueprint, request, jsonify, render_template, session
from models import db, Order, OrderItem, MenuItem
from utils.auth import login_required, owner_required, staff_required

orders_bp = Blueprint('orders', __name__)


@orders_bp.route('/order/new')
@login_required
def new_order_page():
    return render_template('order.html')


@orders_bp.route('/orders')
@login_required
def orders_list_page():
    return render_template('orders.html')


@orders_bp.route('/kitchen')
@login_required
def kitchen_page():
    return render_template('kitchen.html')


@orders_bp.route('/api/orders', methods=['POST'])
@login_required
def create_order():
    rid  = session['restaurant_id']
    data = request.get_json() or {}
    order = Order(
        restaurant_id   = rid,
        table_no        = data.get('table_no', '1'),
        status          = 'placed'                               # skip pending
    )
    db.session.add(order)
    db.session.commit()
    return jsonify(order.to_dict()), 201


@orders_bp.route('/api/orders/<int:order_id>/items', methods=['POST'])
@login_required
def add_or_update_item(order_id):
    rid   = session['restaurant_id']
    order = Order.query.filter_by(id=order_id, restaurant_id=rid).first_or_404()
    data  = request.get_json()

    menu_item_id = data.get('menu_item_id')
    quantity     = int(data.get('quantity', 1))
    menu_item    = MenuItem.query.filter_by(id=menu_item_id, restaurant_id=rid).first_or_404()

    existing = OrderItem.query.filter_by(order_id=order_id, menu_item_id=menu_item_id).first()
    if existing:
        existing.quantity = quantity
        if existing.quantity <= 0:
            db.session.delete(existing)
    else:
        if quantity > 0:
            db.session.add(OrderItem(
                order_id=order_id, menu_item_id=menu_item_id,
                name=menu_item.name, price=menu_item.price, quantity=quantity
            ))

    _recalculate(order)
    db.session.commit()
    return jsonify(order.to_dict())


@orders_bp.route('/api/orders/<int:order_id>', methods=['GET'])
@login_required
def get_order(order_id):
    rid   = session['restaurant_id']
    order = Order.query.filter_by(id=order_id, restaurant_id=rid).first_or_404()
    return jsonify(order.to_dict())


@orders_bp.route('/api/orders/<int:order_id>/place', methods=['POST'])
@login_required
def place_order(order_id):
    rid   = session['restaurant_id']
    order = Order.query.filter_by(id=order_id, restaurant_id=rid).first_or_404()
    if not order.items:
        return jsonify({'error': 'Cart is empty'}), 400
    order.status = 'placed'
    _recalculate(order)
    db.session.commit()
    return jsonify(order.to_dict())  # to_dict now includes short_id via relationship


@orders_bp.route('/api/orders', methods=['GET'])
@login_required
def list_orders():
    rid    = session['restaurant_id']
    orders = Order.query.filter_by(restaurant_id=rid).order_by(Order.created_at.desc()).limit(50).all()
    return jsonify([o.to_dict() for o in orders])



@orders_bp.route('/api/orders/<int:order_id>/status', methods=['POST'])
@login_required
def update_status(order_id):
    rid   = session['restaurant_id']
    order = Order.query.filter_by(id=order_id, restaurant_id=rid).first_or_404()
    data  = request.get_json() or {}
    new_status = data.get('status')
    allowed = ['placed', 'preparing', 'served']
    if new_status not in allowed:
        return jsonify({'error': 'Invalid status'}), 400
    order.status = new_status
    db.session.commit()
    return jsonify(order.to_dict())

def _recalculate(order):
    TAX_RATE       = 0.05
    subtotal       = sum(i.price * i.quantity for i in order.items)
    order.subtotal = round(subtotal, 2)
    order.tax      = round(subtotal * TAX_RATE, 2)
    order.total    = round(subtotal + order.tax, 2)