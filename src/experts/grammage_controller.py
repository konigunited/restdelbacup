"""
GrammageController - Технический эксперт по контролю стандартов граммовки
"""
import json
from typing import Dict, Any, List
from src.services.claude_service import claude_service
from src.utils.logger import logger

class GrammageController:
    """Эксперт по валидации граммовки и соответствию стандартам Rest Delivery"""
    
    SYSTEM_PROMPT = """
Ты - технический эксперт Rest Delivery по контролю стандартов граммовки.

ТВОЯ РОЛЬ: Валидировать соответствие граммовки стандартам и предупреждать об отклонениях.

СТАНДАРТЫ ГРАММОВКИ:
- Кофе-брейк: 250-300г стандарт (реально зафиксировано: 246-347г)
- Фуршет: 250-423г (реально до 423г в кейсе P-39454)
- Банкет: 600-1000г для длительных мероприятий (943г в кейсе P-38906)

СИСТЕМА ПРЕДУПРЕЖДЕНИЙ:
- <250г: "⚠️ НЕДОСТАТОЧНО ЕДЫ - обязательно предупредите клиента"
- 250-750г: "✅ В ПРЕДЕЛАХ НОРМЫ"
- >750г: "⚠️ ИЗБЫТОЧНО МНОГО - еда может остаться"

ОСОБЫЕ СЛУЧАИ:
- Welcome-зона: достаточно 100-120г на гостя
- Детские мероприятия: 150-200г на ребенка
- Длительные банкеты (8+ часов): до 1000г нормально
- Простые перекусы: от 50г (но предупреждать клиента)

УЧИТЫВАЙ КОНТЕКСТ:
- Время мероприятия (длительность)
- Возраст участников
- Характер мероприятия (деловое/праздничное)
- Наличие дополнительного питания

СТИЛЬ ОТВЕТОВ:
- Четкие предупреждения с эмодзи
- Конкретные рекомендации по корректировке
- Ссылки на реальные кейсы Rest Delivery
- Практические советы для менеджера
"""

    async def validate_portions(self, menu_data: Dict[str, Any], event_context: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация граммовки меню"""
        
        logger.info("GrammageController validating portions", 
                   total_weight=menu_data.get("menu_summary", {}).get("total_weight"),
                   guests=event_context.get("guests"))
        
        user_message = f"""
Проанализируй граммовку меню на соответствие стандартам:

МЕНЮ:
{json.dumps(menu_data, ensure_ascii=False, indent=2)}

КОНТЕКСТ МЕРОПРИЯТИЯ:
{json.dumps(event_context, ensure_ascii=False, indent=2)}

Проведи полный анализ и дай заключение:

Ответь в формате JSON:
{{
  "validation_result": {{
    "status": "optimal|acceptable|warning|critical",
    "weight_per_guest": граммовка_на_гостя,
    "standard_range": [мин_граммы, макс_граммы],
    "compliance_score": оценка_0_10
  }},
  "warnings": [
    {{
      "level": "info|warning|critical",
      "message": "текст предупреждения с эмодзи",
      "recommendation": "конкретная рекомендация"
    }}
  ],
  "analysis": {{
    "distribution": {{
      "appetizers_weight": вес_закусок,
      "main_dishes_weight": вес_основных,
      "desserts_weight": вес_десертов
    }},
    "balance_issues": [
      "проблемы баланса если есть"
    ],
    "portion_adequacy": "недостаточно|достаточно|избыточно"
  }},
  "recommendations": [
    {{
      "action": "add|remove|replace",
      "item_type": "тип позиции",
      "reason": "обоснование",
      "expected_improvement": "ожидаемое улучшение"
    }}
  ]
}}
"""
        
        try:
            response = await claude_service.send_structured_request(
                system_prompt=self.SYSTEM_PROMPT,
                user_message=user_message,
                expected_format="json"
            )
            
            logger.info("GrammageController validation completed",
                       status=response.get("validation_result", {}).get("status"),
                       warnings_count=len(response.get("warnings", [])))
            
            return response
            
        except Exception as e:
            logger.error("GrammageController validation failed", error=str(e))
            return self._get_fallback_validation(menu_data, event_context)
    
    async def suggest_corrections(self, validation_result: Dict[str, Any], current_menu: Dict[str, Any]) -> Dict[str, Any]:
        """Предложение корректировок для исправления проблем с граммовкой"""
        
        user_message = f"""
На основе результатов валидации предложи конкретные корректировки меню:

РЕЗУЛЬТАТ ВАЛИДАЦИИ:
{json.dumps(validation_result, ensure_ascii=False, indent=2)}

ТЕКУЩЕЕ МЕНЮ:
{json.dumps(current_menu, ensure_ascii=False, indent=2)}

Предложи минимальные изменения для исправления выявленных проблем.

Ответь в формате JSON:
{{
  "corrections": [
    {{
      "type": "add|remove|increase|decrease",
      "item_id": "ID позиции или null для новой",
      "item_name": "название позиции",
      "quantity_change": изменение_количества,
      "weight_impact": влияние_на_вес,
      "price_impact": влияние_на_стоимость,
      "justification": "обоснование изменения"
    }}
  ],
  "expected_result": {{
    "new_weight_per_guest": новая_граммовка,
    "new_total_price": новая_стоимость,
    "improvement_score": оценка_улучшения_0_10
  }},
  "priority": "low|medium|high|critical"
}}
"""
        
        try:
            response = await claude_service.send_structured_request(
                system_prompt=self.SYSTEM_PROMPT,
                user_message=user_message,
                expected_format="json"
            )
            
            return response
            
        except Exception as e:
            logger.error("GrammageController corrections failed", error=str(e))
            return {"corrections": [], "priority": "low"}
    
    def _get_fallback_validation(self, menu_data: Dict[str, Any], event_context: Dict[str, Any]) -> Dict[str, Any]:
        """Базовая валидация при ошибках ИИ"""
        total_weight = menu_data.get("menu_summary", {}).get("total_weight", 0)
        guests = event_context.get("guests", 1)
        weight_per_guest = total_weight / guests if guests > 0 else 0
        
        if weight_per_guest < 250:
            status = "critical"
            message = "⚠️ КРИТИЧНО: Недостаточно еды для гостей"
        elif weight_per_guest > 750:
            status = "warning"
            message = "⚠️ Много еды, может остаться"
        else:
            status = "acceptable"
            message = "✅ Граммовка в приемлемых пределах"
        
        return {
            "validation_result": {
                "status": status,
                "weight_per_guest": weight_per_guest,
                "compliance_score": 7.0
            },
            "warnings": [{
                "level": "info" if status == "acceptable" else "warning",
                "message": message,
                "recommendation": "Проверьте расчеты"
            }],
            "recommendations": []
        }

# Глобальный экземпляр эксперта
grammage_controller = GrammageController()