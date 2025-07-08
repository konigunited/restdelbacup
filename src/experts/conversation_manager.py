"""
ConversationManager - Ведущий менеджер по продажам Rest Delivery
"""
import json
from typing import Dict, Any, Optional, List
from src.services.claude_service import claude_service, ClaudeMessage
from src.utils.logger import logger

class ConversationManager:
    """Эксперт по ведению диалогов и выявлению потребностей клиента"""
    
    SYSTEM_PROMPT = """
Ты - ведущий менеджер Rest Delivery с 10+ лет опыта в премиальном кейтеринге.

ТВОЯ РОЛЬ: Выявить потребности клиента и структурировать запрос для создания идеальной сметы.

КОНТЕКСТ КОМПАНИИ:
- Rest Delivery - премиальная доставка фуршетных блюд (Москва)
- Авторские сеты от шеф-повара
- Минимальный заказ: 10,000₽
- Целевая аудитория: корпоративы, частные лица с доходом выше среднего

ТИПЫ МЕРОПРИЯТИЙ:
1. Кофе-брейк (30 мин - 1.5 часа): 250-300г на гостя, 1,150-1,700₽ за человека
2. Фуршет (2-5 часов): 250-423г на гостя, 2,300-3,300₽ за человека  
3. Банкет (4-8 часов): 600-1000г на гостя, 4,700-8,600₽ за человека

КЛЮЧЕВЫЕ ВОПРОСЫ ДЛЯ ВЫЯСНЕНИЯ:
1. Тип мероприятия (кофе-брейк/фуршет/банкет)
2. Количество гостей
3. Дата, время и продолжительность
4. Ориентировочный бюджет
5. Нужно ли обслуживание (официанты, мебель, посуда)
6. Адрес и особенности площадки
7. Особые пожелания по меню

СТАНДАРТЫ ОБСЛУЖИВАНИЯ:
- Официант: 9,500₽ за 6 часов + 1,000₽/час сверх
- Доставка: бесплатно в МКАД, 1,500-3,000₽ за МКАД
- Заказы без обслуживания: за сутки до мероприятия
- Заказы с обслуживанием: за 2-3 суток

ТВОЙ СТИЛЬ:
- Профессиональный и дружелюбный
- Задавай уточняющие вопросы
- Предлагай варианты и альтернативы
- Объясняй стандарты и возможности
- Помогай определиться с форматом

ФОРМАТ ОТВЕТА:
Всегда структурируй информацию и делай выводы о потребностях клиента.
"""

    async def analyze_request(self, user_input: str, context: Optional[List[ClaudeMessage]] = None) -> Dict[str, Any]:
        """Анализ запроса клиента и выявление потребностей"""
        
        logger.info("ConversationManager analyzing request", input_length=len(user_input))
        
        user_message = f"""
Клиент обратился с запросом: "{user_input}"

Проанализируй запрос и определи:
1. Что уже понятно о мероприятии
2. Какие важные детали нужно уточнить
3. Какой тип мероприятия вероятнее всего подходит
4. Какие вопросы задать клиенту

Ответь в формате JSON:
{{
  "analysis": {{
    "detected_event_type": "coffee_break|buffet|banquet|unknown",
    "detected_guests": число или null,
    "detected_budget": число или null,
    "detected_date": "дата" или null,
    "detected_location": "адрес" или null,
    "needs_service": true/false/null,
    "confidence": 0.1-1.0
  }},
  "missing_info": [
    "список недостающей критичной информации"
  ],
  "questions": [
    "вопросы для уточнения у клиента"
  ],
  "recommendations": [
    "предложения по типу мероприятия и формату"
  ],
  "next_step": "описание следующего шага"
}}
"""
        
        try:
            # Исправляем передачу контекста - создаем список ClaudeMessage если нужно
            claude_context = []
            if context and isinstance(context, list):
                # Если контекст уже список ClaudeMessage, используем как есть
                if all(hasattr(msg, 'role') for msg in context):
                    claude_context = context
                else:
                    # Если это строки или другие объекты, конвертируем
                    for msg in context:
                        if isinstance(msg, str):
                            claude_context.append(ClaudeMessage(role="user", content=msg))
                        elif isinstance(msg, dict):
                            claude_context.append(ClaudeMessage(
                                role=msg.get("role", "user"),
                                content=msg.get("content", str(msg))
                            ))
                        else:
                            claude_context.append(ClaudeMessage(role="user", content=str(msg)))
            
            response = await claude_service.send_structured_request(
                system_prompt=self.SYSTEM_PROMPT,
                user_message=user_message,
                expected_format="json",
                context=claude_context
            )
            
            logger.info("ConversationManager analysis completed", 
                       detected_type=response.get("analysis", {}).get("detected_event_type"))
            return response
            
        except Exception as e:
            logger.error("ConversationManager analysis failed", error=str(e))
            # Возвращаем упрощенный анализ при ошибке
            return self._get_fallback_analysis(user_input)

    def _get_fallback_analysis(self, user_input: str) -> Dict[str, Any]:
        """Упрощенный анализ при ошибках Claude"""
        
        text_lower = user_input.lower()
        
        # Простое определение типа события
        event_type = "unknown"
        if "кофе-брейк" in text_lower or "coffee" in text_lower:
            event_type = "coffee_break"
        elif "фуршет" in text_lower or "buffet" in text_lower:
            event_type = "buffet"
        elif "банкет" in text_lower or "banquet" in text_lower:
            event_type = "banquet"
        
        # Извлечение количества гостей
        import re
        guests_match = re.search(r'(\d+)\s*(?:человек|гост|чел)', text_lower)
        detected_guests = int(guests_match.group(1)) if guests_match else None
        
        # Извлечение бюджета
        budget_match = re.search(r'(?:бюджет|стоимость)[:\s]*(\d+)', text_lower)
        detected_budget = int(budget_match.group(1)) if budget_match else None
        
        # Проверка готовности к созданию сметы
        has_minimum_info = (
            event_type != "unknown" and 
            detected_guests is not None and
            len(user_input) > 30
        )
        
        confidence = 0.8 if has_minimum_info else 0.3
        
        return {
            "analysis": {
                "detected_event_type": event_type,
                "detected_guests": detected_guests,
                "detected_budget": detected_budget,
                "detected_date": None,
                "detected_location": None,
                "needs_service": None,
                "confidence": confidence
            },
            "missing_info": [] if has_minimum_info else [
                "тип мероприятия", "количество гостей", "дата проведения"
            ],
            "questions": [
                "Уточните детали мероприятия для точной сметы"
            ],
            "recommendations": [
                f"Рекомендуем формат: {event_type}" if event_type != "unknown" else "Определите тип мероприятия"
            ],
            "next_step": "create_estimate" if has_minimum_info else "gather_more_info"
        }

    async def generate_response(self, analysis: Dict[str, Any], client_context: Dict[str, Any] = None) -> str:
        """Генерация ответа клиенту на основе анализа"""
        
        user_message = f"""
На основе анализа запроса клиента сформулируй профессиональный ответ.

Анализ: {json.dumps(analysis, ensure_ascii=False, indent=2)}
Контекст клиента: {json.dumps(client_context or {}, ensure_ascii=False, indent=2)}

Создай ответ который:
1. Показывает понимание запроса
2. Задает ключевые уточняющие вопросы
3. Предлагает варианты решений
4. Звучит профессионально и дружелюбно

Ответ должен быть готов для отправки клиенту в Telegram.
"""
        
        try:
            response = await claude_service.send_message(
                system_prompt=self.SYSTEM_PROMPT,
                user_message=user_message
            )
            
            return response.content
            
        except Exception as e:
            logger.error("Failed to generate response", error=str(e))
            return "Спасибо за обращение! Давайте обсудим детали вашего мероприятия. Сколько планируется гостей и какой тип мероприятия вас интересует?"

# Глобальный экземпляр эксперта
conversation_manager = ConversationManager()