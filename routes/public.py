import os
from flask import Blueprint, render_template, request, jsonify, session, redirect
from models import db, Registration, Restaurant, User, generate_password
from utils.auth import admin_required
from datetime import datetime
import hashlib, secrets, string

public_bp = Blueprint('public', __name__)

# ── PUBLIC PAGES ──────────────────────────────────────────────

@public_bp.route('/', endpoint='landing')
def landing():
    if session.get('user_id'):
        return redirect('/dashboard') if session.get('role') == 'owner' else redirect('/order/new')
    return render_template('public/landing.html')

@public_bp.route('/demo')
def demo():
    return render_template('public/demo.html')

@public_bp.route('/register')
def register():
    return render_template('public/register.html')

@public_bp.route('/plans/payg')
def plan_payg():
    return render_template('public/Voicebill-payg.html')

@public_bp.route('/plans/oti')
def plan_oti():
    return render_template('public/Voicebill-oti.html')

@public_bp.route('/plans/newwebsite')
def plan_newwebsite():
    return render_template('public/Voicebill-newwebsite.html')

# ── REGISTRATION API (public) ─────────────────────────────────

@public_bp.route('/api/registrations', methods=['POST'])
def submit_registration():
    data = request.get_json() or {}

    ref_id = 'VB-' + ''.join(secrets.choice(string.digits) for _ in range(6))
    while Registration.query.filter_by(ref_id=ref_id).first():
        ref_id = 'VB-' + ''.join(secrets.choice(string.digits) for _ in range(6))

    reg = Registration(
        ref_id        = ref_id,
        business_name = data.get('name', '').strip(),
        business_type = data.get('type', '').strip(),
        owner_name    = data.get('owner', data.get('name', '')).strip(),
        email         = data.get('email', '').strip().lower(),
        phone         = data.get('phone', '').strip(),
        city          = data.get('city', '').strip(),
        plan          = data.get('plan', '').strip(),
        status        = 'pending'
    )
    db.session.add(reg)
    db.session.commit()
    return jsonify({'ok': True, 'ref_id': ref_id}), 201

# ── ADMIN AUTH ────────────────────────────────────────────────

ADMIN_USERNAME = 'voicebill'
ADMIN_PASSWORD = 'VB@admin2026'

@public_bp.route('/admin')
def admin_page():
    if session.get('is_admin'):
        return render_template('public/admin.html')
    return render_template('public/admin_login.html')

@public_bp.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json() or {}
    if data.get('username') == ADMIN_USERNAME and data.get('password') == ADMIN_PASSWORD:
        session['is_admin'] = True
        session.permanent = True
        return jsonify({'ok': True})
    return jsonify({'error': 'Invalid credentials'}), 401

@public_bp.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('is_admin', None)
    return jsonify({'ok': True})

# ── ADMIN API ─────────────────────────────────────────────────

@public_bp.route('/api/admin/registrations', methods=['GET'])
@admin_required
def list_registrations():
    status = request.args.get('status')
    q      = request.args.get('q', '').lower()
    query  = Registration.query
    if status:
        query = query.filter_by(status=status)
    regs = query.order_by(Registration.submitted_at.desc()).all()
    if q:
        regs = [r for r in regs if q in (r.business_name or '').lower()
                or q in (r.email or '').lower()
                or q in (r.city or '').lower()
                or q in (r.ref_id or '').lower()]
    return jsonify([r.to_dict() for r in regs])


@public_bp.route('/api/admin/registrations/<int:reg_id>/approve', methods=['POST'])
@admin_required
def approve_registration(reg_id):
    reg = Registration.query.get_or_404(reg_id)
    reg.status      = 'approved'
    reg.approved_at = datetime.utcnow()

    NEW_WEBSITE_PLAN = 'Create New Website'
    result = {'ok': True, 'plan': reg.plan, 'email': reg.email}

    if reg.plan == NEW_WEBSITE_PLAN:
        existing = Restaurant.query.filter_by(email=reg.email).first()
        if not existing:
            btype_map = {
                'restaurant': 'restaurant', 'medical': 'medical',
                'grocery': 'grocery', 'supermart': 'mart'
            }
            btype = btype_map.get(reg.business_type, 'restaurant')
            pwd   = generate_password(10)

            restaurant = Restaurant(
                name          = reg.business_name,
                email         = reg.email,
                business_type = btype,
                phone         = reg.phone,
                address       = reg.city,
                plan          = reg.plan,
                active        = True
            )
            db.session.add(restaurant)
            db.session.flush()

            owner = User(
                restaurant_id = restaurant.id,
                name          = reg.owner_name or reg.business_name,
                email         = reg.email,
                password      = hashlib.sha256(pwd.encode()).hexdigest(),
                role          = 'owner'
            )
            db.session.add(owner)

            login_url = request.host_url.rstrip('/') + '/login'
            subject = f'Your VoiceBill Login — {reg.business_name}'
            body    = _new_website_email(reg, pwd, login_url)
            sent, err = send_email(reg.email, subject, body)
            result.update({
                'new_website':   True,
                'password':      pwd,
                'login_url':     login_url,
                'email_subject': subject,
                'email_body':    body,
                'email_sent':    sent,
                'email_error':   err
            })
        else:
            result['msg'] = 'Already onboarded'
    else:
        subject = f'VoiceBill Registration Received — {reg.business_name}'
        body    = _contact_email(reg)
        sent, err = send_email(reg.email, subject, body)
        result.update({
            'new_website':   False,
            'email_subject': subject,
            'email_body':    body,
            'email_sent':    sent,
            'email_error':   err
        })

    db.session.commit()
    return jsonify(result)


@public_bp.route('/api/admin/registrations/<int:reg_id>/reject', methods=['POST'])
@admin_required
def reject_registration(reg_id):
    reg = Registration.query.get_or_404(reg_id)
    reg.status = 'rejected'
    db.session.commit()
    return jsonify({'ok': True})


@public_bp.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    return jsonify({
        'total':    Registration.query.count(),
        'pending':  Registration.query.filter_by(status='pending').count(),
        'approved': Registration.query.filter_by(status='approved').count(),
        'rejected': Registration.query.filter_by(status='rejected').count(),
    })


# ── EMAIL SENDER ─────────────────────────────────────────────

GMAIL_USER = 'anandcoc67@gmail.com'
GMAIL_APP_PASSWORD = "gcxw dnfi elrw tshj"

def send_email(to_email, subject, body):
    """Send email via Resend API. Returns (True, None) or (False, error_msg)."""
    api_key = "re_CbBXowTf_8xfza7NZFVNVJ7wiHEwYFX6M"
    if not api_key:
        return False, 'RESEND_API_KEY not set'
    try:
        import resend
        resend.api_key = api_key
        resend.Emails.send({
            'from':    'VoiceBill <onboarding@resend.dev>',
            'to':      [to_email],
            'subject': subject,
            'text':    body,
        })
        return True, None
    except Exception as e:
        return False, str(e)

# ── EMAIL TEMPLATES ───────────────────────────────────────────

def _new_website_email(reg, pwd, login_url):
    return f"""Dear {reg.owner_name or reg.business_name},

Congratulations! Your registration for "{reg.business_name}" has been approved on VoiceBill.

Your new voice-powered billing system is ready. Here are your login credentials:

  Login URL : {login_url}
  Email     : {reg.email}
  Password  : {pwd}

Please log in and change your password after your first login.

Plan: {reg.plan}
Business Type: {reg.business_type}

If you have any questions, reach us at support@voicebill.in.

Welcome to VoiceBill! 🎙️
— Team VoiceBill"""


def _contact_email(reg):
    return f"""Dear {reg.owner_name or reg.business_name},

Thank you for registering your interest in VoiceBill!

We've received your registration for "{reg.business_name}" under the {reg.plan} plan.

Our team will reach out shortly to schedule a meeting and discuss the next steps.

Registration Reference: {reg.ref_id}
Plan Selected: {reg.plan}

We look forward to working with you!
— Team VoiceBill
support@voicebill.in"""