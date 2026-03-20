"""
POST /api/onboard
Called by teammate's admin panel after approving a client.
Creates restaurant + owner account, returns credentials.
"""
from flask import Blueprint, request, jsonify
from models import db, Restaurant, User, MenuItem, generate_password

onboard_bp = Blueprint('onboard', __name__)

# Shared secret — teammate's admin panel must send this header
API_SECRET = 'spicegarden-onboard-secret-2024'

# Default menu items per business type
DEFAULT_ITEMS = {
    'restaurant': [
        ('Butter Chicken', 280, 'Main Course'), ('Paneer Tikka', 220, 'Starters'),
        ('Dal Makhani', 180, 'Main Course'),    ('Garlic Naan', 40, 'Breads'),
        ('Jeera Rice', 120, 'Rice'),            ('Mango Lassi', 80, 'Drinks'),
    ],
    'grocery': [
        ('Rice 1kg', 60, 'Grains'),    ('Wheat Flour 1kg', 45, 'Grains'),
        ('Sugar 1kg', 50, 'Essentials'), ('Salt 1kg', 20, 'Essentials'),
        ('Milk 1L', 60, 'Dairy'),      ('Butter 100g', 55, 'Dairy'),
    ],
    'medical': [
        ('Paracetamol 500mg', 25, 'Tablets'), ('Cetirizine 10mg', 30, 'Tablets'),
        ('Bandage Roll', 40, 'First Aid'),    ('Hand Sanitizer', 80, 'Hygiene'),
        ('Vitamin C 500mg', 120, 'Vitamins'), ('ORS Sachet', 15, 'Rehydration'),
    ],
    'mart': [
        ('Water Bottle 1L', 20, 'Beverages'), ('Biscuits Pack', 30, 'Snacks'),
        ('Chips Pack', 20, 'Snacks'),         ('Soap Bar', 40, 'Personal Care'),
        ('Shampoo 200ml', 120, 'Personal Care'), ('Pen', 10, 'Stationery'),
    ],
    'cafe': [
        ('Espresso', 80, 'Coffee'),   ('Cappuccino', 120, 'Coffee'),
        ('Cold Coffee', 140, 'Cold'), ('Sandwich', 120, 'Food'),
        ('Brownie', 80, 'Desserts'),  ('Lemonade', 60, 'Cold'),
    ],
}


@onboard_bp.route('/api/onboard', methods=['POST'])
def onboard():
    # Verify secret header
    if request.headers.get('X-API-Secret') != API_SECRET:
        return jsonify({'error': 'Unauthorized'}), 401

    data      = request.get_json()
    name      = data.get('business_name', '').strip()
    email     = data.get('email', '').strip().lower()
    biz_type  = data.get('business_type', 'restaurant').lower()
    address   = data.get('address', '').strip()
    phone     = data.get('phone', '').strip()
    plan      = data.get('plan', 'new_website')

    if not name or not email:
        return jsonify({'error': 'business_name and email are required'}), 400

    if Restaurant.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 409

    # Auto-generate password
    password = generate_password(10)

    # Create restaurant
    restaurant = Restaurant(
        name=name, email=email, business_type=biz_type,
        address=address, phone=phone, plan=plan
    )
    db.session.add(restaurant)
    db.session.flush()

    # Create owner user
    owner = User(
        restaurant_id=restaurant.id,
        name=name, email=email,
        password=password, role='owner'
    )
    db.session.add(owner)

    # Seed default menu items for this business type
    defaults = DEFAULT_ITEMS.get(biz_type, DEFAULT_ITEMS['restaurant'])
    for item_name, price, category in defaults:
        db.session.add(MenuItem(
            restaurant_id=restaurant.id,
            name=item_name, price=price, category=category
        ))

    db.session.commit()

    return jsonify({
        'success':    True,
        'id':         restaurant.id,
        'email':      email,
        'password':   password,
        'login_url':  f'/login',
        'message':    f'Account created for {name}'
    }), 201