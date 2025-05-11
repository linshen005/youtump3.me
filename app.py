from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import yt_dlp
import os
import logging
from logging.handlers import RotatingFileHandler
from functools import wraps
import time
from datetime import datetime
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)
# 使用更宽松的CORS配置
CORS(app, origins=["http://localhost:8000", "https://youtomp3.me", "https://youtomp3.pages.dev"], 
     methods=["GET", "POST", "OPTIONS"], 
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"])

# 配置日志
if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler(
    os.getenv('LOG_FILE', 'logs/app.log'),
    maxBytes=10240,
    backupCount=10
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(os.getenv('LOG_LEVEL', 'INFO'))
app.logger.addHandler(file_handler)
app.logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))
app.logger.info('YouTube to MP3 startup')

# 请求频率限制
RATE_LIMIT = int(os.getenv('RATE_LIMIT', 10))
RATE_WINDOW = int(os.getenv('RATE_WINDOW', 60))
request_history = {}

def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        now = time.time()
        client_ip = request.remote_addr
        
        if client_ip in request_history:
            request_history[client_ip] = [t for t in request_history[client_ip] if now - t < RATE_WINDOW]
        
        if client_ip in request_history and len(request_history[client_ip]) >= RATE_LIMIT:
            app.logger.warning(f'Rate limit exceeded for IP: {client_ip}')
            return jsonify({'error': 'Too many requests. Please try again later.'}), 429
        
        if client_ip not in request_history:
            request_history[client_ip] = []
        request_history[client_ip].append(now)
        
        return f(*args, **kwargs)
    return decorated_function

@app.errorhandler(404)
def not_found_error(error):
    app.logger.warning(f'Page not found: {request.url}')
    return jsonify({'error': 'The requested URL was not found on the server.'}), 404

@app.errorhandler(Exception)
def handle_error(error):
    app.logger.error(f'Unhandled error: {str(error)}')
    return jsonify({
        'error': 'An unexpected error occurred. Please try again later.'
    }), 500

@app.route('/')
def index():
    return jsonify({
        'status': 'ok',
        'message': 'Welcome to YouTube MP3 Converter API',
        'version': '1.0.0',
        'endpoints': {
            'convert': '/api/download',
            'download': '/download/<filename>',
            'health': '/health'
        }
    })

@app.route('/api/download', methods=['POST'])
@rate_limit
def download():
    try:
        data = request.get_json()
        url = data.get('url')
        if not url:
            app.logger.warning('No URL provided in request')
            return jsonify({'error': 'No URL provided'}), 400

        app.logger.info(f'Processing download request for URL: {url}')
        
        ydl_opts = {
            'quiet': False,
            'format': 'bestaudio/best',
            'forcejson': True,
            'outtmpl': os.path.join(os.getenv('STATIC_FOLDER', 'static'), '%(id)s.%(ext)s'),
            'verbose': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                app.logger.info('Extracting video info...')
                info = ydl.extract_info(url, download=False)
                formats = info.get('formats', [])
                audio_formats = [f for f in formats if f.get('ext') == 'mp3' or f.get('ext') == 'm4a']
                
                if not audio_formats:
                    app.logger.warning(f'No audio formats found for URL: {url}')
                    return jsonify({'error': 'No audio formats available for this video'}), 400
                
                app.logger.info(f'Successfully processed video: {info.get("title")}')
                app.logger.info(f'Found {len(audio_formats)} audio formats')
                
                return jsonify({
                    'title': info.get('title'),
                    'audio': audio_formats
                })
        except yt_dlp.utils.DownloadError as e:
            app.logger.error(f'YouTube-DL error: {str(e)}')
            return jsonify({'error': f'Download error: {str(e)}'}), 400
            
    except Exception as e:
        app.logger.error(f'Error processing download: {str(e)}')
        import traceback
        app.logger.error(f'Traceback: {traceback.format_exc()}')
        return jsonify({'error': 'Failed to process video. Please check the URL and try again.'}), 500

@app.route('/download/<filename>')
@rate_limit
def download_file(filename):
    try:
        file_path = os.path.join(os.getenv('STATIC_FOLDER', 'static'), filename)
        if not os.path.exists(file_path):
            app.logger.warning(f'File not found: {filename}')
            return jsonify({'error': 'File not found'}), 404
            
        app.logger.info(f'Downloading file: {filename}')
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        app.logger.error(f'Error downloading file {filename}: {str(e)}')
        return jsonify({'error': 'Failed to download file'}), 500

@app.route('/health')
def health_check():
    try:
        # 检查静态目录
        static_folder = os.getenv('STATIC_FOLDER', 'static')
        if not os.path.exists(static_folder):
            os.makedirs(static_folder)
            
        # 检查日志目录
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'environment': os.getenv('FLASK_ENV', 'production'),
            'static_folder': static_folder,
            'rate_limit': RATE_LIMIT,
            'rate_window': RATE_WINDOW
        })
    except Exception as e:
        app.logger.error(f'Health check failed: {str(e)}')
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(host=host, port=port, debug=debug)