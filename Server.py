from flask import Flask, jsonify, request
from flask_cors import CORS
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

app = Flask(__name__)
CORS(app)  # allows your browser app to call this server

@app.route('/')
def home():
    return jsonify({"status": "ok", "message": "Transcript server running"})

@app.route('/transcript')
def transcript():
    video_id = request.args.get('id', '').strip()
    if not video_id:
        return jsonify({"error": "Missing ?id= parameter"}), 400

    # Try languages in order of preference
    langs = ['en', 'en-US', 'en-GB', 'a.en']

    try:
        # First try manually created captions
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        transcript = None
        # Try manual first, then auto-generated
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
            # Last resort: grab whatever is available
            for t in transcript_list:
                transcript = t
                break

        if not transcript:
            return jsonify({"error": "No transcript available for this video"}), 404

        data = transcript.fetch()
        # Join all text snippets into clean plain text
        full_text = ' '.join(entry['text'] for entry in data)
        # Basic cleanup
        full_text = full_text.replace('\n', ' ').replace('  ', ' ').strip()

        return jsonify({
            "video_id": video_id,
            "language": transcript.language_code,
            "is_generated": transcript.is_generated,
            "length": len(full_text),
            "transcript": full_text
        })

    except TranscriptsDisabled:
        return jsonify({"error": "Transcripts are disabled for this video"}), 403
    except NoTranscriptFound:
        return jsonify({"error": "No transcript found for this video"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
flask
flask-cors
youtube-transcript-api
gunicorn
web: gunicorn server:app --bind 0.0.0.0:$PORT
