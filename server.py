from flask import Flask, jsonify, request, make_response

app = Flask(__name__)

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
    return jsonify({"status": "ok", "version": "5"})

@app.route('/transcript')
def transcript():
    vid = request.args.get('id', '').strip()
    if not vid:
        return jsonify({"error": "Missing ?id="}), 400
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        ytt = YouTubeTranscriptApi()
        try:
            data = ytt.fetch(vid, languages=['en', 'en-US', 'en-GB'])
        except Exception:
            data = ytt.fetch(vid)

        snippets = []
        for e in data:
            if hasattr(e, 'text'):
                snippets.append(e.text)
            elif isinstance(e, dict):
                snippets.append(e.get('text', ''))

        text = ' '.join(snippets).strip()

        return jsonify({
            "video_id": vid,
            "language": "en",
            "is_generated": False,
            "length": len(text),
            "transcript": text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
