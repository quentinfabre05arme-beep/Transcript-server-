import os
import requests
from flask import Flask, jsonify, request, make_response

app = Flask(__name__)

SUPADATA_API_KEY = os.environ.get('SUPADATA_API_KEY', '')

def cors(r):
    r.headers['Access-Control-Allow-Origin'] = '*'
    r.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    r.headers['Access-Control-Allow-Headers'] = '*'
    return r

@app.before_request
def preflight():
    if request.method == 'OPTIONS':
        return cors(make_response('', 204))

@app.after_request
def after(r):
    return cors(r)

@app.route('/')
def home():
    return jsonify({"status": "ok", "version": "7"})

@app.route('/transcript')
def transcript():
    vid = request.args.get('id', '').strip()
    if not vid:
        return jsonify({"error": "Missing ?id="}), 400
    if not SUPADATA_API_KEY:
        return jsonify({"error": "SUPADATA_API_KEY not set"}), 500

    url = f'https://www.youtube.com/watch?v={vid}'
    r = requests.get(
        'https://api.supadata.ai/v1/youtube/transcript',
        params={'url': url, 'text': 'true', 'lang': 'en'},
        headers={'x-api-key': SUPADATA_API_KEY}
    )

    if r.status_code != 200:
        return jsonify({"error": f"Supadata error {r.status_code}", "detail": r.text[:200]}), r.status_code

    data = r.json()
    text = data.get('content', '')
    lang = data.get('lang', 'en')

    return jsonify({
        "video_id": vid,
        "language": lang,
        "is_generated": False,
        "length": len(text),
        "transcript": text
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
    
