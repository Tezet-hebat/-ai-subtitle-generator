from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from faster_whisper import WhisperModel
import os, tempfile, uuid, subprocess, shutil

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), 'ai_subtitle_uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED = {'mp4', 'mov', 'mkv', 'webm', 'avi', 'mp3', 'wav', 'm4a', 'aac'}
model = None

def get_model():
    global model
    if model is None:
        # First run downloads the small multilingual model (~ size varies by version).
        model = WhisperModel(os.getenv('WHISPER_MODEL', 'small'), device='cpu', compute_type='int8')
    return model

def stamp(seconds, comma=True):
    ms = max(0, int(round(float(seconds) * 1000)))
    h, rem = divmod(ms, 3600000); m, rem = divmod(rem, 60000); s, ms = divmod(rem, 1000)
    sep = ',' if comma else '.'
    return f'{h:02}:{m:02}:{s:02}{sep}{ms:03}'

@app.get('/')
def home():
    return render_template('index.html')

@app.post('/api/transcribe')
def transcribe():
    f = request.files.get('media')
    if not f or not f.filename:
        return jsonify(error='Pilih video atau audio terlebih dahulu.'), 400
    ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
    if ext not in ALLOWED:
        return jsonify(error='Format file belum didukung.'), 400
    lang = request.form.get('language', 'auto')
    path = os.path.join(UPLOAD_DIR, f'{uuid.uuid4().hex}.{secure_filename(ext)}')
    f.save(path)
    try:
        kwargs = {'beam_size': 5, 'vad_filter': True}
        if lang != 'auto': kwargs['language'] = lang
        segments, info = get_model().transcribe(path, **kwargs)
        result = [{'start': round(s.start, 2), 'end': round(s.end, 2), 'text': s.text.strip()} for s in segments]
        return jsonify(segments=result, detected_language=info.language, language_probability=round(info.language_probability, 3))
    except Exception as e:
        return jsonify(error=f'Transkripsi gagal: {str(e)}'), 500
    finally:
        try: os.remove(path)
        except OSError: pass

@app.post('/api/export')
def export_subtitles():
    data = request.get_json(silent=True) or {}
    segments = data.get('segments', [])
    fmt = data.get('format', 'srt').lower()
    if fmt not in ('srt', 'vtt'):
        return jsonify(error='Format ekspor tidak valid.'), 400
    lines = ['WEBVTT', ''] if fmt == 'vtt' else []
    for i, seg in enumerate(segments, 1):
        try:
            start, end = float(seg['start']), float(seg['end'])
            text = str(seg.get('text', '')).strip()
            if end < start: continue
            if fmt == 'srt': lines += [str(i), f'{stamp(start)} --> {stamp(end)}', text, '']
            else: lines += [f'{stamp(start, False)} --> {stamp(end, False)}', text, '']
        except (KeyError, TypeError, ValueError):
            continue
    content = '\n'.join(lines)
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix=f'.{fmt}', encoding='utf-8', delete=False)
    tmp.write(content); tmp.close()
    return send_file(tmp.name, as_attachment=True, download_name=f'subtitle.{fmt}', mimetype='text/plain')

@app.get('/health')
def health():
    return jsonify(status='ok', model_loaded=model is not None)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=False)
