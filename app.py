from flask import Flask, request, send_file, g
import requests
import ffmpeg
import os
import tempfile

app = Flask(__name__)

@app.after_request
def cleanup_mp3(response):
    if hasattr(g, 'mp3_to_delete'):
        try:
            os.remove(g.mp3_to_delete)
        except OSError:
            pass
    return response

@app.route('/convert', methods=['POST'])
def convert_mp4_to_mp3():
    data = request.get_json()
    mp4_url = data.get('mp4_url')
    if not mp4_url:
        return {'error': 'mp4_url is required'}, 400

    # Download MP4
    try:
        response = requests.get(mp4_url, stream=True)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_mp4:
            for chunk in response.iter_content(chunk_size=8192):
                temp_mp4.write(chunk)
            temp_mp4_path = temp_mp4.name
    except Exception as e:
        return {'error': f'Failed to download MP4: {str(e)}'}, 400

    # Convert to MP3
    temp_mp3_path = temp_mp4_path.replace('.mp4', '.mp3')
    try:
        ffmpeg.input(temp_mp4_path).output(temp_mp3_path, acodec='mp3').run()
    except Exception as e:
        os.remove(temp_mp4_path)
        if os.path.exists(temp_mp3_path):
            os.remove(temp_mp3_path)
        return {'error': f'Failed to convert to MP3: {str(e)}'}, 500

    # Clean up MP4
    os.remove(temp_mp4_path)

    # Return MP3 and schedule cleanup
    g.mp3_to_delete = temp_mp3_path
    return send_file(temp_mp3_path, as_attachment=True, download_name='converted.mp3')

if __name__ == '__main__':
    app.run(debug=True)