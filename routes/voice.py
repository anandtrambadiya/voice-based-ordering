"""
routes/voice.py  —  /api/voice/transcribe endpoint
Receives audio blob, returns parsed cart items.
"""
from flask import Blueprint, request, jsonify
from models import MenuItem
import traceback

voice_bp = Blueprint('voice', __name__)


@voice_bp.route('/api/voice/transcribe', methods=['POST'])
def transcribe():
    from voice.transcribe import transcribe_audio, parse_order

    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file uploaded'}), 400

    audio_file  = request.files['audio']
    audio_bytes = audio_file.read()
    print(f"[Voice] Received audio: {len(audio_bytes)} bytes")

    if len(audio_bytes) < 1000:
        return jsonify({'error': 'Audio too short — hold the mic button longer'}), 400

    try:
        transcript = transcribe_audio(audio_bytes)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Transcription failed: {str(e)}'}), 500

    if not transcript:
        return jsonify({'error': 'Nothing heard — speak clearly and try again'}), 400

    menu_items = [i.to_dict() for i in MenuItem.query.filter_by(available=True).all()]
    try:
        parsed = parse_order(transcript, menu_items)
    except Exception as e:
        return jsonify({'transcript': transcript, 'items': [], 'error': str(e)}), 200

    print(f"[Voice] '{transcript}' → {len(parsed)} items")
    return jsonify({'transcript': transcript, 'items': parsed})