import os
from pathlib import Path

class Config:
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Claude API
    CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
    
    # Google Sheets
    GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'config/google_credentials.json')
    SIMPLE_TEMPLATE_ID = os.getenv('SIMPLE_TEMPLATE_ID')
    COMPLEX_TEMPLATE_ID = os.getenv('COMPLEX_TEMPLATE_ID')
    
    @classmethod
    def validate(cls):
        required_vars = [
            'TELEGRAM_BOT_TOKEN',
            'CLAUDE_API_KEY',
            'SIMPLE_TEMPLATE_ID'
        ]
        
        missing = []
        for var in required_vars:
            if not getattr(cls, var):
                missing.append(var)
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        # Проверяем файл credentials
        if not Path(cls.GOOGLE_CREDENTIALS_PATH).exists():
            raise FileNotFoundError(f"Google credentials file not found: {cls.GOOGLE_CREDENTIALS_PATH}")
