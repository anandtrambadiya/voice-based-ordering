from flask import Blueprint, render_template, request, jsonify, session
from models import db, User
from utils.auth import owner_required
import hashlib

staff_bp = Blueprint('staff', __name__)


@staff_bp.route('/staff')
@owner_required
def staff_page():
    return render_template('staff.html')


@staff_bp.route('/api/staff', methods=['GET'])
@owner_required
def list_staff():
    rid   = session['restaurant_id']
    users = User.query.filter_by(restaurant_id=rid).all()
    return jsonify([{
        'id':    u.id,
        'name':  u.name,
        'email': u.email,
        'role':  u.role,
    } for u in users])


@staff_bp.route('/api/staff', methods=['POST'])
@owner_required
def create_staff():
    rid  = session['restaurant_id']
    data = request.get_json() or {}
    name  = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    pwd   = data.get('password', '').strip()
    role  = 'staff'

    if not name or not email or not pwd:
        return jsonify({'error': 'Name, email and password required'}), 400

    if User.query.filter_by(restaurant_id=rid, email=email).first():
        return jsonify({'error': 'Email already exists'}), 409

    user = User(
        restaurant_id = rid,
        name          = name,
        email         = email,
        password      = hashlib.sha256(pwd.encode()).hexdigest(),
        role          = role
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role}), 201


@staff_bp.route('/api/staff/<int:user_id>', methods=['DELETE'])
@owner_required
def delete_staff(user_id):
    rid  = session['restaurant_id']
    user = User.query.filter_by(id=user_id, restaurant_id=rid).first_or_404()
    # Don't let owner delete themselves
    if str(user.id) == str(session.get('user_id')):
        return jsonify({'error': 'Cannot delete yourself'}), 400
    db.session.delete(user)
    db.session.commit()
    return jsonify({'ok': True})