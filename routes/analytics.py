from flask import Blueprint, render_template, jsonify, session
from models import Order, OrderItem, db
from utils.auth import owner_required
from datetime import datetime, timedelta
from sqlalchemy import func

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/analytics')
@owner_required
def analytics_page():
    return render_template('analytics.html')


@analytics_bp.route('/api/analytics/summary')
@owner_required
def summary():
    rid   = session['restaurant_id']
    now   = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week  = today - timedelta(days=7)
    month = today - timedelta(days=30)

    def revenue_since(since):
        orders = Order.query.filter(
            Order.restaurant_id == rid,
            Order.status.in_(['placed','preparing','served']),
            Order.created_at >= since
        ).all()
        return round(sum(o.total for o in orders), 2), len(orders)

    rev_today, cnt_today   = revenue_since(today)
    rev_week,  cnt_week    = revenue_since(week)
    rev_month, cnt_month   = revenue_since(month)

    # Average order value (all time)
    all_orders = Order.query.filter(Order.restaurant_id==rid, Order.status.in_(['placed','preparing','served'])).all()
    avg_order  = round(sum(o.total for o in all_orders) / len(all_orders), 2) if all_orders else 0

    # Busiest hours — count orders per hour of day
    hour_counts = {}
    for o in all_orders:
        h = o.created_at.hour
        hour_counts[h] = hour_counts.get(h, 0) + 1

    hours_data = [{'hour': h, 'count': hour_counts.get(h, 0)} for h in range(24)]

    # Top items
    item_totals = {}
    for o in all_orders:
        for item in o.items:
            key = item.name
            if key not in item_totals:
                item_totals[key] = {'name': key, 'qty': 0, 'revenue': 0}
            item_totals[key]['qty']     += item.quantity
            item_totals[key]['revenue'] += round(item.price * item.quantity, 2)

    top_items = sorted(item_totals.values(), key=lambda x: x['qty'], reverse=True)[:5]

    return jsonify({
        'revenue': {
            'today': rev_today, 'today_orders': cnt_today,
            'week':  rev_week,  'week_orders':  cnt_week,
            'month': rev_month, 'month_orders': cnt_month,
        },
        'avg_order_value': avg_order,
        'total_orders':    len(all_orders),
        'hours':           hours_data,
        'top_items':       top_items,
    })