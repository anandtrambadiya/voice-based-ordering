from flask import Blueprint, request, jsonify, render_template
from models import db, MenuItem

menu_bp = Blueprint('menu', __name__)


@menu_bp.route('/')
def dashboard():
    return render_template('dashboard.html')


@menu_bp.route('/menu')
def menu_page():
    return render_template('menu.html')


# ── API ──────────────────────────────────────────────

@menu_bp.route('/api/menu', methods=['GET'])
def get_menu():
    items = MenuItem.query.filter_by(available=True).order_by(MenuItem.category).all()
    return jsonify([i.to_dict() for i in items])


@menu_bp.route('/api/menu', methods=['POST'])
def add_item():
    data = request.get_json()
    name     = data.get('name', '').strip()
    price    = data.get('price')
    category = data.get('category', 'General').strip()

    if not name or price is None:
        return jsonify({'error': 'Name and price are required'}), 400

    item = MenuItem(name=name, price=float(price), category=category)
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@menu_bp.route('/api/menu/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    data = request.get_json()
    item.name     = data.get('name', item.name).strip()
    item.price    = float(data.get('price', item.price))
    item.category = data.get('category', item.category).strip()
    db.session.commit()
    return jsonify(item.to_dict())


@menu_bp.route('/api/menu/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    item.available = False          # soft delete
    db.session.commit()
    return jsonify({'success': True})