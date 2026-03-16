from flask import Blueprint, request, jsonify, render_template, session
from models import db, Order, OrderItem, MenuItem

orders_bp = Blueprint('orders', __name__)


@orders_bp.route('/order/new')
def new_order_page():
    return render_template('order.html')


@orders_bp.route('/orders')
def orders_list_page():
    return render_template('orders.html')


# ── API ──────────────────────────────────────────────

@orders_bp.route('/api/orders', methods=['POST'])
def create_order():
    """Start a fresh order."""
    data     = request.get_json() or {}
    table_no = data.get('table_no', '1')
    order    = Order(table_no=table_no)
    db.session.add(order)
    db.session.commit()
    return jsonify(order.to_dict()), 201


@orders_bp.route('/api/orders/<int:order_id>/items', methods=['POST'])
def add_or_update_item(order_id):
    """Add item to cart or update quantity (+1 / set qty)."""
    order = Order.query.get_or_404(order_id)
    data  = request.get_json()

    menu_item_id = data.get('menu_item_id')
    quantity     = int(data.get('quantity', 1))
    menu_item    = MenuItem.query.get_or_404(menu_item_id)

    # Check if item already in cart
    existing = OrderItem.query.filter_by(
        order_id=order_id, menu_item_id=menu_item_id
    ).first()

    if existing:
        existing.quantity = quantity
        if existing.quantity <= 0:
            db.session.delete(existing)
    else:
        if quantity > 0:
            oi = OrderItem(
                order_id=order_id,
                menu_item_id=menu_item_id,
                name=menu_item.name,
                price=menu_item.price,
                quantity=quantity
            )
            db.session.add(oi)

    _recalculate(order)
    db.session.commit()
    return jsonify(order.to_dict())


@orders_bp.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    order = Order.query.get_or_404(order_id)
    return jsonify(order.to_dict())


@orders_bp.route('/api/orders/<int:order_id>/place', methods=['POST'])
def place_order(order_id):
    """Finalize and save the order."""
    order = Order.query.get_or_404(order_id)
    if not order.items:
        return jsonify({'error': 'Cart is empty'}), 400
    order.status = 'placed'
    _recalculate(order)
    db.session.commit()
    return jsonify(order.to_dict())


@orders_bp.route('/api/orders', methods=['GET'])
def list_orders():
    orders = Order.query.order_by(Order.created_at.desc()).limit(50).all()
    return jsonify([o.to_dict() for o in orders])


def _recalculate(order):
    TAX_RATE    = 0.05          # 5% GST
    subtotal    = sum(i.price * i.quantity for i in order.items)
    tax         = round(subtotal * TAX_RATE, 2)
    order.subtotal = round(subtotal, 2)
    order.tax      = tax
    order.total    = round(subtotal + tax, 2)