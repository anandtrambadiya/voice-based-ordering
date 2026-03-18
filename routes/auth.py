from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
from models import db, Restaurant, User, generate_password

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login')
def login_page():
    if session.get('user_id'):
        return redirect(url_for('menu.dashboard'))
    return render_template('login.html')


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    data  = request.get_json()
    email = data.get('email', '').strip().lower()
    pwd   = data.get('password', '').strip()

    user = User.query.filter_by(email=email).first()
    if not user or user.password != pwd:
        return jsonify({'error': 'Invalid email or password'}), 401

    restaurant = Restaurant.query.get(user.restaurant_id)
    if not restaurant or not restaurant.active:
        return jsonify({'error': 'Account is inactive. Contact support.'}), 403

    session.permanent = True
    session['user_id']       = user.id
    session['restaurant_id'] = restaurant.id
    session['role']          = user.role
    session['biz_name']      = restaurant.name
    session['biz_type']      = restaurant.business_type

    return jsonify({
        'role':      user.role,
        'biz_name':  restaurant.name,
        'biz_type':  restaurant.business_type,
        'redirect':  '/'
    })


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login_page'))


@auth_bp.route('/register')
def register_page():
    """Self-serve registration — for demo/hackathon. Teammate's admin panel replaces this."""
    if session.get('user_id'):
        return redirect(url_for('menu.dashboard'))
    return render_template('register.html')


@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    data     = request.get_json()
    name     = data.get('name', '').strip()
    email    = data.get('email', '').strip().lower()
    pwd      = data.get('password', '').strip()
    biz_type = data.get('business_type', 'restaurant')
    address  = data.get('address', '').strip()
    phone    = data.get('phone', '').strip()

    if not name or not email or not pwd:
        return jsonify({'error': 'Name, email and password are required'}), 400

    if Restaurant.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    # Create restaurant + owner user
    restaurant = Restaurant(
        name=name, email=email, business_type=biz_type,
        address=address, phone=phone, plan='new_website'
    )
    db.session.add(restaurant)
    db.session.flush()  # get restaurant.id

    owner = User(
        restaurant_id=restaurant.id,
        name=name, email=email, password=pwd, role='owner'
    )
    db.session.add(owner)
    db.session.commit()

    return jsonify({'success': True, 'redirect': '/login'})