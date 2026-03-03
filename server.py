import os
import json
import requests
from flask import Flask, jsonify, request, make_response, redirect

app = Flask(__name__)

# ── CORS ──
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

# ── CONFIG (set these as Railway environment variables) ──
CLIENT_ID     = os.environ.get('GOOGLE_CLIENT_ID', '')
CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
REFRESH_TOKEN = os.environ.get('GOOGLE_REFRESH_TOKEN', '')
BASE_URL      = os.environ.get('RAILWAY_PUBLIC_DOMAIN', '')
if BASE_URL:
    BASE_URL = f'https://{BASE_URL}'

SCOPES        = 'https://www.googleapis.com/auth/youtube.force-ssl'
TOKEN_URL     = 'https://oauth2.googleapis.com/token'

# ── GET FRESH ACCESS TOKEN ──
def get_access_token():
    if not REFRESH_TOKEN:
        raise Exception('GOOGLE_REFRESH_TOKEN not set. Visit /auth first.')
    r = requests.post(TOKEN_URL, data={
        'client_id':     CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN,
        'grant_type':    'refresh_token'
    })
    data = r.json()
    if 'access_token' not in data:
        raise Exception(f'Token refresh failed: {data}')
    return data['access_token']

# ── ROUTES ──
@app.route('/')
def home():
    status = 'ready' if REFRESH_TOKEN else 'needs_auth'
    return jsonify({"status": "ok", "version": "6", "auth": status})

# Step 1: visit this URL to start OAuth flow
@app.route('/auth')
def auth():
    if not CLIENT_ID:
        return jsonify({"error": "GOOGLE_CLIENT_ID not set"}), 500
    callback = f'{BASE_URL}/callback'
    url = (
        f'https://accounts.google.com/o/oauth2/v2/auth'
        f'?client_id={CLIENT_ID}'
        f'&redirect_uri={callback}'
        f'&response_type=code'
        f'&scope={SCOPES}'
        f'&access_type=offline'
        f'&prompt=consent'
    )
    return redirect(url)

# Step 2: Google redirects here with auth code
@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "No code returned"}), 400
    callback = f'{BASE_URL}/callback'
    r = requests.post(TOKEN_URL, data={
        'code':          code,
        'client_id':     CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri':  callback,
        'grant_type':    'authorization_code'
    })
    data = r.json()
    refresh_token = data.get('refresh_token', '')
    if not refresh_token:
        return jsonify({"error": "No refresh token", "response": data}), 400

    # Show the token — copy it and add to Railway env vars
    return f"""
    <html><body style="font-family:monospace;padding:2rem;background:#0a0a0f;color:#e8e6f0">
    <h2 style="color:#3ddc84">✓ Auth successful!</h2>
    <p>Copy this refresh token and add it to Railway as <strong>GOOGLE_REFRESH_TOKEN</strong>:</p>
    <textarea rows="4" style="width:100%;background:#1a1a24;color:#fff;border:1px solid #2a2a38;padding:1rem;font-size:0.9rem">{refresh_token}</textarea>
    <p style="color:#6a6880;margin-top:1rem">Railway → your service → Variables → add GOOGLE_REFRESH_TOKEN</p>
    </body></html>
    """

# ── TRANSCRIPT ──
@app.route('/transcript')
def transcript():
    vid = request.args.get('id', '').strip()
    if not vid:
        return jsonify({"error": "Missing ?id="}), 400

    try:
        access_token = get_access_token()
    except Exception as e:
        return jsonify({"error": str(e), "hint": f"Visit {BASE_URL}/auth to authorize"}), 401

    # Step 1: list captions for the video
    captions_url = f'https://www.googleapis.com/youtube/v3/captions?part=snippet&videoId={vid}'
    r = requests.get(captions_url, headers={'Authorization': f'Bearer {access_token}'})
    captions_data = r.json()

    if 'error' in captions_data:
        return jsonify({"error": captions_data['error']['message']}), 400

    items = captions_data.get('items', [])
    if not items:
        return jsonify({"error": "No captions found for this video"}), 404

    # Pick best caption track: prefer manual English, then auto English, then anything
    chosen = None
    for track in items:
        s = track['snippet']
        if s['language'] in ['en', 'en-US', 'en-GB'] and s['trackKind'] == 'standard':
            chosen = track
            break
    if not chosen:
        for track in items:
            s = track['snippet']
            if s['language'] in ['en', 'en-US', 'en-GB']:
                chosen = track
                break
    if not chosen:
        chosen = items[0]

    caption_id = chosen['id']
    lang = chosen['snippet']['language']
    is_generated = chosen['snippet']['trackKind'] == 'asr'

    # Step 2: download the caption track (SRT format)
    dl_url = f'https://www.googleapis.com/youtube/v3/captions/{caption_id}?tfmt=srt'
    r = requests.get(dl_url, headers={'Authorization': f'Bearer {access_token}'})

    if r.status_code != 200:
        return jsonify({"error": f"Caption download failed: {r.status_code}", "body": r.text[:200]}), 400

    # Parse SRT → plain text
    text = parse_srt(r.text)

    return jsonify({
        "video_id": vid,
        "language": lang,
        "is_generated": is_generated,
        "length": len(text),
        "transcript": text
    })

def parse_srt(srt):
    """Strip SRT timestamps and sequence numbers, return plain text."""
    import re
    # Remove sequence numbers and timestamps
    text = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n', '', srt)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Collapse whitespace
    text = re.sub(r'\n+', ' ', text).strip()
    return text

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
