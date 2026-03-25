from flask import Blueprint, request, jsonify, render_template, session
from models import db
from utils.auth import owner_required
import json, os
from datetime import datetime

reg_bp = Blueprint('registrations', __name__)

REG_FILE = 'registrations.json'

def load_regs():
    if not os.path.exists(REG_FILE):
        return []
    try:
        with open(REG_FILE) as f:
            return json.load(f)
    except:
        return []

def save_regs(data):
    with open(REG_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def send_email(to_email, subject, body):
    api_key = os.environ.get('BREVO_API_KEY', '')
    if not api_key:
        return False, 'BREVO_API_KEY not set in environment'
    try:
        payload = _json.dumps({
            'sender':      {'name': 'VoiceBill', 'email': 'anandcoc67@gmail.com'},
            'to':          [{'email': to_email}],
            'subject':     subject,
            'textContent': body,
        }).encode()
        req = urllib.request.Request(
            'https://api.brevo.com/v3/smtp/email',
            data    = payload,
            headers = {
                'api-key':      api_key,
                'Content-Type': 'application/json',
                'Accept':       'application/json',
            }
        )
        urllib.request.urlopen(req, timeout=15)
        return True, None
    except Exception as e:
        return False, str(e)

@reg_bp.route('/api/registrations', methods=['POST'])
def submit_registration():
    """Public endpoint — called from landing page registration form."""
    data = request.get_json() or {}
    regs = load_regs()
    # Avoid duplicates by ref id
    if any(r.get('id') == data.get('id') for r in regs):
        return jsonify({'ok': True, 'msg': 'already exists'})
    data['receivedAt'] = datetime.utcnow().isoformat()
    regs.append(data)
    save_regs(regs)

    subject = f'VoiceBill Registration Received'
    body = f"""Dear Admin,
    New Business want to join us.

Please log in and check at
https://voice-based-ordering-1.onrender.com/admin
id - voicebill
password - VB@admin2026

— Team VoiceBill"""

    sent, err = send_email("prashantbhuva085@gmail.com", subject, body)
    print(err, sent)

    return jsonify({'ok': True}), 201


@reg_bp.route('/api/registrations', methods=['GET'])
@owner_required
def list_registrations():
    """Admin only — list all registration requests."""
    return jsonify(load_regs())


@reg_bp.route('/api/registrations/<reg_id>/approve', methods=['POST'])
@owner_required
def approve_registration(reg_id):
    regs = load_regs()
    reg  = next((r for r in regs if r.get('id') == reg_id), None)
    if not reg:
        return jsonify({'error': 'Not found'}), 404
    reg['status']     = 'approved'
    reg['approvedAt'] = datetime.utcnow().isoformat()
    save_regs(regs)
    return jsonify({'ok': True})


@reg_bp.route('/api/registrations/<reg_id>/reject', methods=['POST'])
@owner_required
def reject_registration(reg_id):
    regs = load_regs()
    reg  = next((r for r in regs if r.get('id') == reg_id), None)
    if not reg:
        return jsonify({'error': 'Not found'}), 404
    reg['status']     = 'rejected'
    reg['rejectedAt'] = datetime.utcnow().isoformat()
    save_regs(regs)
    return jsonify({'ok': True})
