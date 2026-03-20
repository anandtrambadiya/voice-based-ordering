from flask import Blueprint, send_file, session
from models import Order, Restaurant
import os

billing_bp = Blueprint('billing', __name__)


@billing_bp.route('/api/orders/<int:order_id>/invoice', methods=['GET'])
def generate_invoice(order_id):
    order = Order.query.get_or_404(order_id)
    restaurant = Restaurant.query.get(order.restaurant_id)
    biz_name = restaurant.name if restaurant else ''
    prefix   = ''.join(w[0] for w in biz_name.upper().split()[:3]) or 'ORD'
    from models import db, Order as O
    from sqlalchemy import func
    seq = db.session.query(func.count(O.id)).filter(
        O.restaurant_id == order.restaurant_id, O.id <= order.id
    ).scalar() or order.id
    short_id = f'{prefix}-{seq:04d}'
    pdf_path = _generate_pdf(order, restaurant, short_id)
    return send_file(pdf_path, as_attachment=True,
                     download_name=f'{short_id}.pdf',
                     mimetype='application/pdf')


def _generate_pdf(order, restaurant, short_id=None):
    from fpdf import FPDF

    biz_name    = restaurant.name if restaurant else 'VoiceBill'
    biz_address = restaurant.address or 'Rajkot, Gujarat'
    biz_phone   = restaurant.phone or ''
    biz_type    = restaurant.business_type if restaurant else 'restaurant'

    TEAL   = (14, 165, 160)
    DARK   = (12, 31, 31)
    GRAY   = (100, 110, 110)
    LGRAY  = (220, 230, 230)
    WHITE  = (255, 255, 255)
    BG     = (248, 250, 252)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    W = pdf.w - 36  # usable width

    # ── Teal accent bar at top ──────────────────────
    pdf.set_fill_color(*TEAL)
    pdf.rect(0, 0, pdf.w, 3, 'F')

    pdf.ln(6)

    # ── Business name ───────────────────────────────
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(*TEAL)
    pdf.cell(0, 11, biz_name.upper(), ln=True, align='C')

    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*GRAY)
    if biz_address:
        pdf.cell(0, 5, biz_address, ln=True, align='C')
    if biz_phone:
        pdf.cell(0, 5, f'Ph: {biz_phone}', ln=True, align='C')
    pdf.cell(0, 5, 'Powered by VoiceBill', ln=True, align='C')

    pdf.ln(4)

    # ── Divider ─────────────────────────────────────
    pdf.set_draw_color(*TEAL)
    pdf.set_line_width(0.6)
    pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
    pdf.ln(5)

    # ── TAX INVOICE label ───────────────────────────
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 8, 'TAX INVOICE', ln=True, align='C')
    pdf.ln(2)

    # ── Order meta box ──────────────────────────────
    pdf.set_fill_color(*BG)
    pdf.set_draw_color(*LGRAY)
    pdf.set_line_width(0.3)
    box_y = pdf.get_y()
    pdf.rect(18, box_y, W, 22, 'DF')

    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*GRAY)
    pdf.set_y(box_y + 3)
    pdf.set_x(22)
    pdf.cell(W/2 - 4, 5, f'Invoice No:  {short_id}', ln=False)
    pdf.cell(W/2 - 4, 5, f'Date:  {order.created_at.strftime("%d %b %Y, %I:%M %p")}', ln=True, align='R')
    pdf.set_x(22)
    pdf.cell(W/2 - 4, 5, f'Table No:  {order.table_no}', ln=False)
    pdf.cell(W/2 - 4, 5, f'Items:  {len(order.items)}', ln=True, align='R')
    pdf.ln(6)

    # ── Items table header ──────────────────────────
    pdf.set_fill_color(*TEAL)
    pdf.set_text_color(*WHITE)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(W * 0.48, 8, '  Item', border=0, fill=True)
    pdf.cell(W * 0.12, 8, 'Qty', border=0, fill=True, align='C')
    pdf.cell(W * 0.20, 8, 'Rate (Rs.)', border=0, fill=True, align='R')
    pdf.cell(W * 0.20, 8, 'Amt (Rs.)', border=0, fill=True, align='R', ln=True)

    # ── Items rows ──────────────────────────────────
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*DARK)
    for idx, item in enumerate(order.items):
        if idx % 2 == 0:
            pdf.set_fill_color(*WHITE)
        else:
            pdf.set_fill_color(*BG)
        pdf.cell(W * 0.48, 7.5, f'  {item.name}', border=0, fill=True)
        pdf.cell(W * 0.12, 7.5, str(item.quantity), border=0, fill=True, align='C')
        pdf.cell(W * 0.20, 7.5, f'{item.price:.2f}', border=0, fill=True, align='R')
        pdf.cell(W * 0.20, 7.5, f'{item.price * item.quantity:.2f}', border=0, fill=True, align='R', ln=True)

    pdf.ln(2)

    # ── Thin separator ──────────────────────────────
    pdf.set_draw_color(*LGRAY)
    pdf.set_line_width(0.3)
    pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
    pdf.ln(4)

    # ── Totals ──────────────────────────────────────
    half_tax = round(order.tax / 2, 2)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*GRAY)

    pdf.cell(W * 0.78, 6, 'Subtotal', align='R')
    pdf.cell(W * 0.22, 6, f'Rs. {order.subtotal:.2f}', align='R', ln=True)

    pdf.cell(W * 0.78, 6, 'CGST @ 2.5%', align='R')
    pdf.cell(W * 0.22, 6, f'Rs. {half_tax:.2f}', align='R', ln=True)

    pdf.cell(W * 0.78, 6, 'SGST @ 2.5%', align='R')
    pdf.cell(W * 0.22, 6, f'Rs. {half_tax:.2f}', align='R', ln=True)

    pdf.ln(2)

    # ── Grand total box ─────────────────────────────
    pdf.set_fill_color(*TEAL)
    pdf.set_text_color(*WHITE)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(W * 0.72, 10, '  TOTAL PAYABLE', border=0, fill=True)
    pdf.cell(W * 0.28, 10, f'Rs. {order.total:.2f}', border=0, fill=True, align='R', ln=True)

    pdf.ln(8)

    # ── Footer ──────────────────────────────────────
    pdf.set_draw_color(*TEAL)
    pdf.set_line_width(0.4)
    pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
    pdf.ln(4)

    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 5, f'Thank you for visiting {biz_name}! We hope to see you again.', ln=True, align='C')
    pdf.cell(0, 5, 'This is a computer generated invoice.', ln=True, align='C')

    # ── Bottom teal bar ─────────────────────────────
    pdf.set_fill_color(*TEAL)
    pdf.rect(0, pdf.h - 3, pdf.w, 3, 'F')

    os.makedirs('invoices', exist_ok=True)
    path = f'invoices/order_{order.id}.pdf'
    pdf.output(path)
    return path