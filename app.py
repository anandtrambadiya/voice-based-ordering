from flask import Flask, g
from datetime import timedelta
from models import db


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY']                 = 'spicegarden-secret-v2-2024'
    app.config['SQLALCHEMY_DATABASE_URI']    = 'sqlite:///restaurant.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

    db.init_app(app)

    # Register blueprints
    from routes.menu     import menu_bp
    from routes.orders   import orders_bp
    from routes.billing  import billing_bp
    from routes.voice    import voice_bp
    from routes.auth     import auth_bp
    from routes.onboard   import onboard_bp
    from routes.analytics import analytics_bp
    from routes.customer  import customer_bp
    from routes.staff     import staff_bp
    from routes.public import public_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(menu_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(voice_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(onboard_bp)

    # Load current user into g on every request
    from utils.auth import load_user
    app.before_request(load_user)

    # Inject g.restaurant into all templates automatically
    @app.context_processor
    def inject_globals():
        DINE_IN = ['restaurant', 'cafe']
        btype   = g.restaurant.business_type if g.restaurant else 'restaurant'
        return {
            'current_restaurant': g.restaurant,
            'current_user':       g.user,
            'current_role':       g.user.role if g.user else None,
            'biz_mode':           'dine_in' if btype in DINE_IN else 'direct',
            'biz_labels':         g.restaurant.labels if g.restaurant else {},
        }

    with app.app_context():
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)