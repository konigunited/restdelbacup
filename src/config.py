import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
    SIMPLE_TEMPLATE_ID = os.getenv('SIMPLE_TEMPLATE_ID')
    COMPLEX_TEMPLATE_ID = os.getenv('COMPLEX_TEMPLATE_ID')
    
    
    @classmethod
    def validate(cls):
        required_vars = [
            'TELEGRAM_BOT_TOKEN',
            'GEMINI_API_KEY',
            'SIMPLE_TEMPLATE_ID',
            # 'COMPLEX_TEMPLATE_ID' # Временно отключено, так как используется только простой шаблон
        ]
        
        missing = []
        for var in required_vars:
            if not getattr(cls, var):
                missing.append(var)
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

# Вызываем валидацию при импорте
Config.validate()