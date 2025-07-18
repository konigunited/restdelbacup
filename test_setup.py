import os
import json
from dotenv import load_dotenv

# Загружаем переменные среды
load_dotenv()

def test_setup():
    print("🧪 Проверка настройки...")
    
    # Проверяем .env
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    claude_key = os.getenv('CLAUDE_API_KEY')
    template_id = os.getenv('SIMPLE_TEMPLATE_ID')
    
    print(f"✅ Telegram Token: {'✓' if telegram_token else '✗'}")
    print(f"✅ Claude API Key: {'✓' if claude_key else '✗'}")
    print(f"✅ Template ID: {'✓' if template_id else '✗'}")
    
    # Проверяем credentials.json
    try:
        with open('credentials.json', 'r') as f:
            creds = json.load(f)
        print(f"✅ Service Account: {creds['client_email']}")
        print(f"✅ Project ID: {creds['project_id']}")
    except Exception as e:
        print(f"✗ Ошибка credentials.json: {e}")
    
    print("\n🎯 Настройка завершена!")

if __name__ == "__main__":
    test_setup()