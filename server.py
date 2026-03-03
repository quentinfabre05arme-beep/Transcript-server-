from flask import Flask, jsonify, request, make_response
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

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
        # New API: try languages in order
        languages = ['en', 'en-US', 'en-GB']
        transcript = None
        language_used = 'en'
        is_generated = False

        try:
            transcript = YouTubeTranscriptApi.fetch(video_id, languages=languages)
            language_used = 'en'
        except Exception:
            try:
                # Try auto-generated
                transcript = YouTubeTranscriptApi.fetch(video_id, languages=['a.en'])
                language_used = 'a.en'
                is_generated = True
            except Exception:
                # Last resort: no language preference
                transcript = YouTubeTranscriptApi.fetch(video_id)
                language_used = 'unknown'

        if not transcript:
            return jsonify({"error": "No transcript available"}), 404

        text = ' '.join(e['text'] for e in transcript).replace('\n', ' ').strip()

        return jsonify({
            "video_id": video_id,
            "language": language_used,
            "is_generated": is_generated,
            "length": len(text),
            "transcript": text
        })

    except TranscriptsDisabled:
        return jsonify({"error": "Transcripts disabled for this video"}), 403
    except NoTranscriptFound:
        return jsonify({"error": "No transcript found"}), 404
    except VideoUnavailable:
        return jsonify({"error": "Video unavailable"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
