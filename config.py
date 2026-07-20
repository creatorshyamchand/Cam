import os

CONFIG = {
    'bot_token': '8844616707:AAH-pSiVYN09NCfPlhh8X4VkZjX_vn1Q4zA',
    'admin_username': 'nexxon',
    'admin_password': 'exploits@1234',
    'photos_dir': '/tmp/photos' if os.environ.get('VERCEL') else 'photos',
    'data_dir': '/tmp/data' if os.environ.get('VERCEL') else 'data'
}

# Auto-create directories
os.makedirs(CONFIG['photos_dir'], exist_ok=True)
os.makedirs(CONFIG['data_dir'], exist_ok=True)
