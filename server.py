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
    return jsonify({"status": "ok", "version": "2"})

@app.route('/transcript')
def transcript():
    vid = request.args.get('id', '').strip()
    if not vid:
        return jsonify({"error": "Missing ?id="}), 400
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        data = YouTubeTranscriptApi.fetch(vid, languages=['en','en-US','en-GB'])
        text = ' '.join(e['text'] for e in data).replace('\n', ' ').strip()
        return jsonify({"video_id": vid, "language": "en", "is_generated": False, "length": len(text), "transcript": text})
    except Exception as e1:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            data = YouTubeTranscriptApi.fetch(vid)
            text = ' '.join(e['text'] for e in data).replace('\n', ' ').strip()
            return jsonify({"video_id": vid, "language": "auto", "is_generated": True, "length": len(text), "transcript": text})
        except Exception as e2:
            return jsonify({"error": str(e2)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
