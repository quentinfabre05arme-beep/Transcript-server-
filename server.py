from flask import Flask, jsonify, request
from flask_cors import CORS
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

app = Flask(__name__)
CORS(app, origins="*", methods=["GET", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/')
def home():
    return jsonify({"status": "ok", "message": "Transcript server running"})

@app.route('/transcript')
def transcript():
    video_id = request.args.get('id', '').strip()
    if not video_id:
        return jsonify({"error": "Missing ?id= parameter"}), 400

    langs = ['en', 'en-US', 'en-GB', 'a.en']

    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = None

        for fetch_fn in [
            lambda: transcript_list.find_manually_created_transcript(langs),
            lambda: transcript_list.find_generated_transcript(langs),
            lambda: transcript_list.find_transcript(langs),
        ]:
            try:
                transcript = fetch_fn()
                break
            except Exception:
                continue

        if not transcript:
            for t in transcript_list:
                transcript = t
                break

        if not transcript:
            return jsonify({"error": "No transcript available"}), 404

        data = transcript.fetch()
        full_text = ' '.join(entry['text'] for entry in data)
        full_text = full_text.replace('\n', ' ').replace('  ', ' ').strip()

        return jsonify({
            "video_id": video_id,
            "language": transcript.language_code,
            "is_generated": transcript.is_generated,
            "length": len(full_text),
            "transcript": full_text
        })

    except TranscriptsDisabled:
        return jsonify({"error": "Transcripts disabled for this video"}), 403
    except NoTranscriptFound:
        return jsonify({"error": "No transcript found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
