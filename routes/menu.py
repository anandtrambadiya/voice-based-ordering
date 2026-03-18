from flask import Blueprint, request, jsonify, render_template, session
from models import db, MenuItem
from utils.auth import login_required, owner_required

menu_bp = Blueprint('menu', __name__)


@menu_bp.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')


@menu_bp.route('/menu')
@owner_required
def menu_page():
    return render_template('menu.html')


@menu_bp.route('/api/menu', methods=['GET'])
@login_required
def get_menu():
    rid   = session['restaurant_id']
    items = MenuItem.query.filter_by(restaurant_id=rid, available=True).order_by(MenuItem.category).all()
    return jsonify([i.to_dict() for i in items])


@menu_bp.route('/api/menu', methods=['POST'])
@owner_required
def add_item():
    rid  = session['restaurant_id']
    data = request.get_json()
    name     = data.get('name', '').strip()
    price    = data.get('price')
    category = data.get('category', 'General').strip()
    if not name or price is None:
        return jsonify({'error': 'Name and price are required'}), 400
    item = MenuItem(restaurant_id=rid, name=name, price=float(price), category=category)
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@menu_bp.route('/api/menu/<int:item_id>', methods=['PUT'])
@owner_required
def update_item(item_id):
    rid  = session['restaurant_id']
    item = MenuItem.query.filter_by(id=item_id, restaurant_id=rid).first_or_404()
    data = request.get_json()
    item.name     = data.get('name', item.name).strip()
    item.price    = float(data.get('price', item.price))
    item.category = data.get('category', item.category).strip()
    db.session.commit()
    return jsonify(item.to_dict())


@menu_bp.route('/api/menu/<int:item_id>', methods=['DELETE'])
@owner_required
def delete_item(item_id):
    rid  = session['restaurant_id']
    item = MenuItem.query.filter_by(id=item_id, restaurant_id=rid).first_or_404()
    item.available = False
    db.session.commit()
    return jsonify({'success': True})