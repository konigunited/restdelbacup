import json
import os
from dotenv import load_dotenv

load_dotenv()

def check_credentials():
    print("🔍 Проверка credentials...")
    
    # Проверяем .env
    creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
    print(f"📁 Путь к credentials: {creds_path}")
    
    # Проверяем файл
    if os.path.exists(creds_path):
        with open(creds_path, 'r') as f:
            creds = json.load(f)
        
        print(f"✅ Файл найден")
        print(f"📧 Client email: {creds.get('client_email', 'НЕ НАЙДЕН')}")
        print(f"🆔 Project ID: {creds.get('project_id', 'НЕ НАЙДЕН')}")
        print(f"🔑 Type: {creds.get('type', 'НЕ НАЙДЕН')}")
        
        # Проверяем какой project_id
        if creds.get('project_id') == 'restdel':
            print("✅ Используется ПРАВИЛЬНЫЙ project_id: restdel")
        else:
            print(f"❌ Используется НЕПРАВИЛЬНЫЙ project_id: {creds.get('project_id')}")
            print("❌ НУЖНО ЗАМЕНИТЬ credentials.json!")
        
    else:
        print(f"❌ Файл {creds_path} НЕ НАЙДЕН!")
    
    # Проверяем рабочую директорию
    print(f"📂 Рабочая директория: {os.getcwd()}")
    print(f"📋 Файлы в директории:")
    for file in os.listdir('.'):
        if 'credentials' in file.lower() or file.endswith('.json'):
            print(f"  - {file}")

if __name__ == "__main__":
    check_credentials()