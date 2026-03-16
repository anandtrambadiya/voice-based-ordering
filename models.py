from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class MenuItem(db.Model):
    __tablename__ = 'menu_items'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    price       = db.Column(db.Float, nullable=False)
    category    = db.Column(db.String(50), default='General')
    available   = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'category': self.category,
            'available': self.available
        }


class Order(db.Model):
    __tablename__ = 'orders'
    id           = db.Column(db.Integer, primary_key=True)
    table_no     = db.Column(db.String(10), default='1')
    status       = db.Column(db.String(20), default='pending')  # pending, paid
    subtotal     = db.Column(db.Float, default=0.0)
    tax          = db.Column(db.Float, default=0.0)
    total        = db.Column(db.Float, default=0.0)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    items        = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'table_no': self.table_no,
            'status': self.status,
            'subtotal': self.subtotal,
            'tax': self.tax,
            'total': self.total,
            'created_at': self.created_at.strftime('%d %b %Y, %I:%M %p'),
            'items': [i.to_dict() for i in self.items]
        }


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id           = db.Column(db.Integer, primary_key=True)
    order_id     = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    name         = db.Column(db.String(100))   # snapshot at time of order
    price        = db.Column(db.Float)
    quantity     = db.Column(db.Integer, default=1)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'quantity': self.quantity,
            'subtotal': round(self.price * self.quantity, 2)
        }