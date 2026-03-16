from flask import Blueprint, send_file, jsonify
from models import Order
import os

billing_bp = Blueprint('billing', __name__)


@billing_bp.route('/api/orders/<int:order_id>/invoice', methods=['GET'])
def generate_invoice(order_id):
    order = Order.query.get_or_404(order_id)

    pdf_path = _generate_pdf(order)
    return send_file(pdf_path, as_attachment=True,
                     download_name=f'invoice_order_{order.id}.pdf',
                     mimetype='application/pdf')


def _generate_pdf(order):
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    # ── Header ──────────────────────────────────────
    pdf.set_font('Helvetica', 'B', 22)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 12, 'SPICE GARDEN', ln=True, align='C')

    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, 'Multi Cuisine Restaurant  |  Rajkot, Gujarat', ln=True, align='C')
    pdf.cell(0, 6, 'GSTIN: 24ABCDE1234F1Z5  |  Ph: +91 98765 43210', ln=True, align='C')

    pdf.ln(4)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.4)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(4)

    # ── Order meta ───────────────────────────────────
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(95, 6, f'Invoice #: ORD-{order.id:04d}', ln=False)
    pdf.cell(95, 6, f'Date: {order.created_at.strftime("%d %b %Y, %I:%M %p")}', ln=True, align='R')
    pdf.cell(95, 6, f'Table No: {order.table_no}', ln=False)
    pdf.cell(95, 6, f'Status: {order.status.upper()}', ln=True, align='R')

    pdf.ln(4)

    # ── Table header ─────────────────────────────────
    pdf.set_fill_color(245, 245, 245)
    pdf.set_text_color(30, 30, 30)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(90, 9, 'Item', border='B', fill=True)
    pdf.cell(25, 9, 'Qty', border='B', fill=True, align='C')
    pdf.cell(35, 9, 'Rate (Rs.)', border='B', fill=True, align='R')
    pdf.cell(20, 9, 'Amt (Rs.)', border='B', fill=True, align='R', ln=True)

    # ── Items ─────────────────────────────────────────
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(50, 50, 50)
    for item in order.items:
        pdf.cell(90, 8, item.name)
        pdf.cell(25, 8, str(item.quantity), align='C')
        pdf.cell(35, 8, f'{item.price:.2f}', align='R')
        pdf.cell(20, 8, f'{item.price * item.quantity:.2f}', align='R', ln=True)

    pdf.ln(2)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(3)

    # ── Totals ───────────────────────────────────────
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(150, 7, 'Subtotal', align='R')
    pdf.cell(20, 7, f'{order.subtotal:.2f}', align='R', ln=True)

    pdf.cell(150, 7, 'GST (5%)', align='R')
    pdf.cell(20, 7, f'{order.tax:.2f}', align='R', ln=True)

    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(150, 9, 'TOTAL', align='R')
    pdf.cell(20, 9, f'Rs.{order.total:.2f}', align='R', ln=True)

    pdf.ln(6)
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(0, 6, 'Thank you for dining with us! Visit again :)', ln=True, align='C')

    # ── Save ─────────────────────────────────────────
    os.makedirs('invoices', exist_ok=True)
    path = f'invoices/order_{order.id}.pdf'
    pdf.output(path)
    return path