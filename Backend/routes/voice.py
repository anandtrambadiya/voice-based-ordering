from flask import Blueprint, request, jsonify, session
from models import MenuItem
from utils.auth import login_required
import traceback

voice_bp = Blueprint('voice', __name__)


@voice_bp.route('/api/voice/transcribe', methods=['POST'])
@login_required
def transcribe():
    from voice.transcribe import transcribe_audio, parse_order

    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file uploaded'}), 400

    audio_file  = request.files['audio']
    audio_bytes = audio_file.read()
    print(f"[Voice] Received {len(audio_bytes)} bytes, filename: {audio_file.filename}")

    if len(audio_bytes) < 1000:
        return jsonify({'error': 'Audio too short — hold the mic longer'}), 400

    # Detect extension from filename (webm, wav, ogg, etc.)
    filename = audio_file.filename or 'audio.webm'
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'webm'

    try:
        transcript = transcribe_audio(audio_bytes, ext=ext)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Transcription failed: {str(e)}'}), 500

    if not transcript:
        return jsonify({'error': 'Nothing heard — speak clearly and try again'}), 400

    rid        = session['restaurant_id']
    menu_items = [i.to_dict() for i in MenuItem.query.filter_by(restaurant_id=rid, available=True).all()]

    try:
        parsed = parse_order(transcript, menu_items)
    except Exception as e:
        return jsonify({'transcript': transcript, 'items': [], 'error': str(e)}), 200

    print(f"[Voice] '{transcript}' -> {len(parsed)} items")
    return jsonify({'transcript': transcript, 'items': parsed})