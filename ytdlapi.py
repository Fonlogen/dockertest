from flask import Flask, request, jsonify, send_from_directory
import json
import yt_dlp as ytdl
from flask_cors import CORS
import re
import os, sys, time

DELETE_AFTER = 30 # seconds
COOKIES_FILE = 'cookies.txt' # Path to your cookies file

## Create the app
app = Flask(__name__)
CORS(app)

headers = {
    'Content-Type': 'application/json', 
    'Access-Control-Allow-Origin': '*', 
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 
    'Access-Control-Allow-Headers': 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token', 
    'Access-Control-Max-Age': '3600',
}

@app.route('/')
def base():
    return 'Hello World'

@app.route('/downloadVideo', methods=['POST'])
def download_video():
    try:
        data = request.get_json()
        video_url = data.get('videoURL')
        format_id = data.get('format')
        format_ext = data.get('formatExt')
        audio_only = data.get('audioOnly')
        startTime = data.get('startTime')
        endTime = data.get('endTime')

        if not video_url or not format_id or not format_ext:
            return jsonify({'error': 'Invalid input'}), 400

        # Delete all files in downloads folder if creation date is older than DELETE_AFTER seconds 
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files')
        now = time.time()
        for f in os.listdir(path):
            if os.stat(os.path.join(path, f)).st_mtime < now - DELETE_AFTER:
                if os.path.isfile(os.path.join(path, f)):
                    os.remove(os.path.join(path, f))

        # Get the video info
        ytdl_opts = {
            'cookiefile': COOKIES_FILE,
        }
        video_info = ytdl.YoutubeDL(ytdl_opts).extract_info(video_url, download=False)

        # Get the video title
        video_title = video_info.get('title', None)

        file_name = video_title.encode('ascii', 'ignore').decode('ascii')
        file_name = re.sub(r"[!@#$%^&*()[]{};:,./<>?\\|`~-=_+]", "_", file_name)

        # Get the video formats
        video_details = {
            'title': video_title,
            'thumbnail': video_info.get('thumbnail', None),
            'author': video_info.get('uploader', None),
            'views': video_info.get('view_count', None),
            'length': video_info.get('duration', None),
            'size': video_info.get('filesize', None),
            'download_url': '/files/' + file_name + '.' + format_ext,
        }

        if os.path.exists(os.path.join(path, file_name + '.' + format_ext)):
            return jsonify(video_details), 200, headers

        # Video download options
        ytdl_opts.update({
            'outtmpl': os.path.join(path, file_name + f'.{format_id}'),
            'ffmpeg_location': os.path.join(sys.path[0], 'ffmpeg/ffmpeg.exe'),
            'format': f'{format_id}',
        })
        if not audio_only:
            with ytdl.YoutubeDL(ytdl_opts) as ydl:
                ydl.download([video_url])

        # Download best audio
        ytdl_opts['format'] = 'bestaudio'
        ytdl_opts['outtmpl'] = os.path.join(path, file_name + '.m4a')
        with ytdl.YoutubeDL(ytdl_opts) as ydl:
            ydl.download([video_url])

        if not audio_only:
            # Merge the audio and video using ffmpeg
            os.system(f'ffmpeg -i "{os.path.join(path, file_name + "." + format_id)}" -i "{os.path.join(path, file_name + ".m4a")}" -c copy "{os.path.join(path, file_name + "." + format_ext)}"')

            # Remove the audio and video files
            os.remove(os.path.join(path, file_name + '.' + format_id))
            os.remove(os.path.join(path, file_name + '.m4a'))

        if audio_only:
            # Rename the audio file to the desired format
            os.rename(os.path.join(path, file_name + '.m4a'), os.path.join(path, file_name + '.' + format_ext))

        if startTime or endTime:
            temp_file_name = file_name + '_temp.' + format_ext
            if startTime and endTime:
                # Trim the video
                os.system(f'ffmpeg -y -i "{os.path.join(path, file_name + "." + format_ext)}" -ss {startTime} -to {endTime} -c copy "{os.path.join(path, temp_file_name)}"')
            elif startTime:
                # Trim the video from start time to end
                os.system(f'ffmpeg -y -i "{os.path.join(path, file_name + "." + format_ext)}" -ss {startTime} -c copy "{os.path.join(path, temp_file_name)}"')
            elif endTime:
                # Trim the video from start to end time
                os.system(f'ffmpeg -y -i "{os.path.join(path, file_name + "." + format_ext)}" -to {endTime} -c copy "{os.path.join(path, temp_file_name)}"')
            
            # Remove existing file if it exists
            if os.path.exists(os.path.join(path, file_name + '.' + format_ext)):
                os.remove(os.path.join(path, file_name + '.' + format_ext))
            
            # Replace the original file with the trimmed file
            os.rename(os.path.join(path, temp_file_name), os.path.join(path, file_name + '.' + format_ext))

        video_details['download_url'] = '/files/' + file_name + '.' + format_ext

        return jsonify(video_details), 200, headers
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/files/<path:filename>')
def serve_file(filename):
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        return send_from_directory(os.path.join(base, 'files'), filename)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/getVideoFormats', methods=['POST'])
def get_video_formats():
    try:
        data = request.get_json()
        video_url = data.get('videoURL')
        
        if not video_url:
            return jsonify({'error': 'Invalid input'}), 400
        
        ytdl_opts = {
            'cookiefile': COOKIES_FILE,
        }
        video_info = ytdl.YoutubeDL(ytdl_opts).extract_info(video_url, download=False)
        video_formats = video_info.get('formats', None)

        video_details = {
            'title': video_info.get('title', None),
            'thumbnail': video_info.get('thumbnail', None),
            'author': video_info.get('uploader', None),
            'views': video_info.get('view_count', None),
            'length': video_info.get('duration', None),
            'size': video_info.get('filesize', None),
        }

        return jsonify({'available_formats': video_formats, 'video_details': video_details}), 200, headers
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return jsonify({'error': 'Internal Server Error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)