from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import secrets, string

db = SQLAlchemy()

# Business type → UI label mapping
BUSINESS_LABELS = {
    'restaurant': {'item': 'Item',     'category': 'Category', 'table': 'Table',   'order': 'Order'},
    'grocery':    {'item': 'Product',  'category': 'Aisle',    'table': 'Counter', 'order': 'Bill'},
    'medical':    {'item': 'Medicine', 'category': 'Type',     'table': 'Counter', 'order': 'Order'},
    'mart':       {'item': 'Product',  'category': 'Section',  'table': 'Counter', 'order': 'Bill'},
    'cafe':       {'item': 'Item',     'category': 'Category', 'table': 'Table',   'order': 'Order'},
}


class Restaurant(db.Model):
    """One row per business/client. Name kept as 'Restaurant' internally but supports all types."""
    __tablename__ = 'restaurants'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(150), nullable=False)
    email         = db.Column(db.String(150), unique=True, nullable=False)
    password      = db.Column(db.String(100), nullable=True)
    business_type = db.Column(db.String(50), default='restaurant')
    address       = db.Column(db.String(300))
    phone         = db.Column(db.String(20))
    plan          = db.Column(db.String(50), default='new_website')
    active        = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    menu_items    = db.relationship('MenuItem', backref='restaurant', lazy=True, cascade='all, delete-orphan')
    orders        = db.relationship('Order',    backref='restaurant', lazy=True, cascade='all, delete-orphan')

    @property
    def labels(self):
        return BUSINESS_LABELS.get(self.business_type, BUSINESS_LABELS['restaurant'])

    def to_dict(self):
        return {
            'id':            self.id,
            'name':          self.name,
            'email':         self.email,
            'business_type': self.business_type,
            'address':       self.address,
            'phone':         self.phone,
            'plan':          self.plan,
            'active':        self.active,
        }


class User(db.Model):
    """Staff accounts — owner or cashier — linked to a Restaurant."""
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(150), nullable=False)
    password      = db.Column(db.String(100), nullable=True)
    role          = db.Column(db.String(20), default='cashier')  # owner | cashier
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('restaurant_id', 'email'),)


class MenuItem(db.Model):
    __tablename__ = 'menu_items'
    id            = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    name          = db.Column(db.String(100), nullable=False)
    price         = db.Column(db.Float, nullable=False)
    category      = db.Column(db.String(50), default='General')
    available     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':       self.id,
            'name':     self.name,
            'price':    self.price,
            'category': self.category,
            'available':self.available
        }


class Order(db.Model):
    __tablename__ = 'orders'
    id            = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    table_no        = db.Column(db.String(10), default='1')
    customer_mobile = db.Column(db.String(15), nullable=True)
    status          = db.Column(db.String(20), default='placed')
    subtotal      = db.Column(db.Float, default=0.0)
    tax           = db.Column(db.Float, default=0.0)
    total         = db.Column(db.Float, default=0.0)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    items         = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        # Short biz prefix for order ID
        biz_name = self.restaurant.name if self.restaurant else ''
        prefix   = ''.join(w[0] for w in biz_name.upper().split()[:3]) or 'ORD'
        # Per-restaurant sequence count
        from sqlalchemy import func
        seq = db.session.query(func.count(Order.id)).filter(
            Order.restaurant_id == self.restaurant_id,
            Order.id <= self.id
        ).scalar() or self.id
        short_id = f'{prefix}-{seq:04d}'
        return {
            'id':              self.id,
            'short_id':        short_id,
            'table_no':        self.table_no,
            'customer_mobile': self.customer_mobile,
            'status':          self.status,
            'subtotal':   self.subtotal,
            'tax':        self.tax,
            'total':      self.total,
            'created_at': self.created_at.strftime('%d %b %Y, %I:%M %p'),
            'items':      [i.to_dict() for i in self.items]
        }


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id            = db.Column(db.Integer, primary_key=True)
    order_id      = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    menu_item_id  = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    name          = db.Column(db.String(100))
    price         = db.Column(db.Float)
    quantity      = db.Column(db.Integer, default=1)

    def to_dict(self):
        return {
            'id':       self.id,
            'name':     self.name,
            'price':    self.price,
            'quantity': self.quantity,
            'subtotal': round(self.price * self.quantity, 2)
        }



class Registration(db.Model):
    __tablename__ = 'registrations'
    id            = db.Column(db.Integer, primary_key=True)
    ref_id        = db.Column(db.String(20), unique=True, nullable=False)
    business_name = db.Column(db.String(150), nullable=False)
    business_type = db.Column(db.String(50))
    owner_name    = db.Column(db.String(100))
    email         = db.Column(db.String(150), nullable=False)
    phone         = db.Column(db.String(20))
    city          = db.Column(db.String(100))
    plan          = db.Column(db.String(50))
    status        = db.Column(db.String(20), default='pending')  # pending/approved/rejected
    submitted_at  = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at   = db.Column(db.DateTime, nullable=True)
    notes         = db.Column(db.String(300), nullable=True)

    def to_dict(self):
        return {
            'id':            self.id,
            'ref_id':        self.ref_id,
            'business_name': self.business_name,
            'business_type': self.business_type,
            'owner_name':    self.owner_name,
            'email':         self.email,
            'phone':         self.phone,
            'city':          self.city,
            'plan':          self.plan,
            'status':        self.status,
            'submitted_at':  self.submitted_at.strftime('%d %b %Y, %I:%M %p') if self.submitted_at else None,
            'approved_at':   self.approved_at.strftime('%d %b %Y') if self.approved_at else None,
        }

def generate_password(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))