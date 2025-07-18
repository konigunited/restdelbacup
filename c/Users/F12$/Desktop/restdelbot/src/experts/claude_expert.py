import json
import logging
from typing import Dict, Optional
import anthropic
from .prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class ClaudeExpert:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        
    async def analyze_request(self, text: str) -> Dict:
        try:
            logger.info(f"Analyzing request: {text[:100]}...")
            
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",  # Claude 4 Sonnet
                max_tokens=4000,  # Увеличиваем лимит для Claude 4
                temperature=0.1,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": f"Проанализируй запрос клиента: {text}"
                }]
            )
            
            response_text = message.content[0].text
            logger.info(f"Claude 4 response: {response_text}")
            
            json_data = self._extract_json(response_text)
            
            if not json_data:
                # Fallback - попробуем более простой парсинг
                json_data = self._fallback_parsing(response_text, text)
                
            validated_data = self._validate_response(json_data)
            
            return validated_data
            
        except Exception as e:
            logger.error(f"Error analyzing request: {str(e)}")
            # Создаем базовый ответ если Claude не отвечает
            return self._create_fallback_response(text)
    
    def _extract_json(self, text: str) -> Optional[Dict]:
        try:
            # Ищем JSON блок в ответе Claude
            start_idx = text.find('{')
            end_idx = text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                return None
                
            json_str = text[start_idx:end_idx]
            return json.loads(json_str)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from: {text[:200]}... Error: {e}")
            return None
    
    def _fallback_parsing(self, response_text: str, original_text: str) -> Dict:
        """Резервный парсинг если JSON не найден"""
        logger.info("Using fallback parsing...")
        
        # Простой анализ ключевых слов
        text_lower = original_text.lower()
        
        # Определяем тип мероприятия
        event_type = "фуршет"  # по умолчанию
        if "банкет" in text_lower:
            event_type = "банкет"
        elif "кофе-брейк" in text_lower or "кофе брейк" in text_lower:
            event_type = "кофе-брейк"
        elif "фуршет" in text_lower:
            event_type = "фуршет"
        
        # Ищем количество гостей
        import re
        guests_match = re.search(r'(\d+)\s*(?:человек|персон|гост)', text_lower)
        guests_count = int(guests_match.group(1)) if guests_match else 0
        
        # Ищем бюджет
        budget_match = re.search(r'(\d+)(?:\s*(?:тыс|000|рубл))', text_lower)
        budget = int(budget_match.group(1)) * 1000 if budget_match else 0
        
        return {
            "event_type": event_type,
            "guests_count": guests_count,
            "budget_limit": budget,
            "confidence_level": 0.6,
            "missing_info": ["дата мероприятия"] if "июл" not in text_lower and "дата" not in text_lower else []
        }
    
    def _create_fallback_response(self, text: str) -> Dict:
        """Создаем базовый ответ при ошибке API"""
        return {
            "event_type": "фуршет",
            "guests_count": 0,
            "event_date": "",
            "event_time": "",
            "duration_hours": 2,
            "need_service": False,
            "need_equipment": False,
            "budget_limit": 0,
            "dietary_restrictions": [],
            "special_requests": "",
            "gramm_per_guest": 300,
            "service_staff": {"waiters": 0, "cooks": 0, "manager": False},
            "confidence_level": 0.1,
            "missing_info": ["все параметры требуют уточнения"]
        }
    
    def _validate_response(self, data: Dict) -> Dict:
        required_fields = {
            'event_type': 'фуршет',
            'guests_count': 0,
            'event_date': '',
            'event_time': '',
            'duration_hours': 2,
            'need_service': False,
            'need_equipment': False,
            'budget_limit': 0,
            'dietary_restrictions': [],
            'special_requests': '',
            'gramm_per_guest': 300,
            'service_staff': {
                'waiters': 0,
                'cooks': 0,
                'manager': False
            },
            'confidence_level': 0.5,
            'missing_info': []
        }
        
        for field, default_value in required_fields.items():
            if field not in data:
                data[field] = default_value
        
        # Дополнительная валидация
        if data['guests_count'] <= 0:
            data['missing_info'].append('количество гостей')
            data['confidence_level'] = min(data['confidence_level'], 0.3)
        
        return data
    
    def get_analysis_summary(self, data: Dict) -> str:
        event_types = {
            'кофе-брейк': 'Кофе-брейк',
            'фуршет': 'Фуршет', 
            'банкет': 'Банкет',
            'фуршет_с_горячим': 'Фуршет с горячим'
        }
        
        summary = f"🤖 Анализ мероприятия (Claude 4):\n\n"
        summary += f"🎪 Тип: {event_types.get(data['event_type'], data['event_type'])}\n"
        summary += f"👥 Гости: {data['guests_count']} человек\n"
        
        if data['event_date']:
            summary += f"📅 Дата: {data['event_date']}\n"
        if data['event_time']:
            summary += f"⏰ Время: {data['event_time']}\n"
        
        summary += f"🍽️ Граммовка: {data['gramm_per_guest']}г на гостя\n"
        
        if data['need_service']:
            summary += f"👨‍🍳 Обслуживание: Да\n"
        
        if data['budget_limit']:
            summary += f"💰 Бюджет: до {data['budget_limit']:,} руб.\n"
        
        # Показываем уровень уверенности
        confidence_emoji = "🟢" if data['confidence_level'] > 0.7 else "🟡" if data['confidence_level'] > 0.4 else "🔴"
        summary += f"{confidence_emoji} Уверенность: {data['confidence_level']:.0%}\n"
        
        if data['missing_info']:
            summary += f"\n❗ Нужно уточнить: {', '.join(data['missing_info'])}"
        
        return summary