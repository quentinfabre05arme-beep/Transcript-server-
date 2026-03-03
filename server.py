from flask import Flask, jsonify, request, make_response
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

app = Flask(__name__)

def cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = '*'
    return response

@app.before_request
def handle_preflight():
    if request.method == 'OPTIONS':
        return cors(make_response('', 204))

@app.after_request
def after(response):
    return cors(response)

@app.route('/')
def home():
    return jsonify({"status": "ok"})

@app.route('/transcript')
def transcript():
    video_id = request.args.get('id', '').strip()
    if not video_id:
        return jsonify({"error": "Missing ?id="}), 400
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = None
        for fn in [
            lambda: transcript_list.find_manually_created_transcript(['en','en-US','en-GB']),
            lambda: transcript_list.find_generated_transcript(['en','en-US','en-GB','a.en']),
        ]:
            try: transcript = fn(); break
            except: continue
        if not transcript:
            for t in transcript_list: transcript = t; break
        if not transcript:
            return jsonify({"error": "No transcript available"}), 404
        data = transcript.fetch()
        text = ' '.join(e['text'] for e in data).replace('\n', ' ').strip()
        return jsonify({
            "video_id": video_id,
            "language": transcript.language_code,
            "is_generated": transcript.is_generated,
            "length": len(text),
            "transcript": text
        })
    except TranscriptsDisabled:
        return jsonify({"error": "Transcripts disabled"}), 403
    except NoTranscriptFound:
        return jsonify({"error": "No transcript found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
