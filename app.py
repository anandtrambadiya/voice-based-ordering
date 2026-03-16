from flask import Flask
from models import db

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'restaurant-voice-billing-2024'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # Register blueprints
    from routes.menu    import menu_bp
    from routes.orders  import orders_bp
    from routes.billing import billing_bp
    from routes.voice   import voice_bp

    app.register_blueprint(menu_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(voice_bp)

    with app.app_context():
        db.create_all()
        _seed_sample_menu()

    return app


def _seed_sample_menu():
    """Add sample items if DB is empty."""
    from models import MenuItem
    if MenuItem.query.first():
        return
    items = [
        MenuItem(name='Butter Chicken',  price=280, category='Main Course'),
        MenuItem(name='Paneer Tikka',    price=220, category='Starters'),
        MenuItem(name='Dal Makhani',     price=180, category='Main Course'),
        MenuItem(name='Garlic Naan',     price=40,  category='Breads'),
        MenuItem(name='Butter Naan',     price=35,  category='Breads'),
        MenuItem(name='Jeera Rice',      price=120, category='Rice'),
        MenuItem(name='Biryani',         price=320, category='Rice'),
        MenuItem(name='Mango Lassi',     price=80,  category='Drinks'),
        MenuItem(name='Masala Chai',     price=30,  category='Drinks'),
        MenuItem(name='Gulab Jamun',     price=60,  category='Desserts'),
    ]
    db.session.bulk_save_objects(items)
    db.session.commit()


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)