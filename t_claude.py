import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv('CLAUDE_API_KEY'))

# Возможные названия Claude 4 моделей
claude4_models = [
    "claude-4-20250514",
    "claude-sonnet-4-20250514", 
    "claude-4-sonnet-20250514",
    "claude-4",
    "claude-4-sonnet",
    "claude-3-5-sonnet-20241022",  # Последняя доступная
    "claude-3-5-sonnet-latest"
]

async def test_models():
    for model in claude4_models:
        try:
            print(f"\n🧪 Тестирую модель: {model}")
            
            message = client.messages.create(
                model=model,
                max_tokens=100,
                messages=[{
                    "role": "user", 
                    "content": "Привет! Ты Claude 4?"
                }]
            )
            
            response = message.content[0].text
            print(f"✅ {model} РАБОТАЕТ!")
            print(f"📝 Ответ: {response}")
            
            # Если модель работает, обновляем expert.py
            if "claude-4" in model.lower():
                print(f"🎯 НАЙДЕН Claude 4: {model}")
                return model
                
        except Exception as e:
            print(f"❌ {model} не работает: {str(e)}")
    
    return None

if __name__ == "__main__":
    import asyncio
    working_model = asyncio.run(test_models())
    
    if working_model:
        print(f"\n🚀 Используй эту модель: {working_model}")
    else:
        print(f"\n⚠️ Claude 4 пока недоступен, используй: claude-3-5-sonnet-20241022")