"""
BudgetOptimizer - Финансовый эксперт по оптимизации бюджета
"""
import json
from typing import Dict, Any, Optional, List
from src.services.claude_service import claude_service
from src.utils.logger import logger

class BudgetOptimizer:
    """Эксперт по оптимизации сметы под бюджет клиента"""
    
    SYSTEM_PROMPT = """
Ты - финансовый эксперт Rest Delivery по оптимизации бюджета.

ТВОЯ РОЛЬ: Подогнать смету под бюджет клиента, сохранив качество и стандарты.

ОГРАНИЧЕНИЯ Rest Delivery:
- Минимальный заказ: 10,000₽
- Минимальная граммовка: 250г на гостя (критично!)
- Нельзя нарушать баланс меню
- Качество продукции - приоритет над ценой

СТРАТЕГИИ ОПТИМИЗАЦИИ:
1. ЗАМЕНА ПОЗИЦИЙ: дорогие аналоги → более доступные с тем же качеством
2. КОРРЕКТИРОВКА КОЛИЧЕСТВА: уменьшение порций в пределах стандартов
3. ИЗМЕНЕНИЕ ФОРМАТА: банкет → фуршет → кофе-брейк (если уместно)
4. УБИРАНИЕ ОПЦИЙ: удаление дополнительных, но не критичных позиций
5. ГОТОВЫЕ НАБОРЫ: использование авторских сетов (часто выгоднее)

ГОТОВЫЕ НАБОРЫ (ВЫГОДНЫЕ РЕШЕНИЯ):
- "Деловой" 21-25 персон: 27,290₽ (1,310₽ за гостя)
- "Праздничный" 21-25 персон: 30,190₽ (1,437₽ за гостя) 
- VIP кофе-брейк 16-20 персон: 28,190₽ (1,573₽ за гостя)
- "Стрит-фуд" 16-20 персон: 16,790₽ (934₽ за гостя)

ПРИНЦИПЫ ЗАМЕН:
- Канапе 385₽ → канапе 100₽ (но того же уровня)
- Банкетные блюда → фуршетные позиции
- Премиум десерты → стандартные десерты
- Индивидуальные позиции → наборы

НЕ ДОПУСКАЙ:
- Падение ниже 10,000₽ общей суммы
- Граммовка менее 250г на гостя
- Полное убирание ключевых категорий
- Снижение качества ниже стандартов Rest Delivery

ВСЕГДА ОБЪЯСНЯЙ:
- Почему предлагаешь конкретную замену
- Как это повлияет на впечатление гостей
- Альтернативные варианты экономии
"""

    async def optimize_budget(self, current_menu: Dict[str, Any], target_budget: int, 
                             event_context: Dict[str, Any]) -> Dict[str, Any]:
        """Оптимизация меню под целевой бюджет"""
        
        logger.info("BudgetOptimizer optimizing budget",
                   current_price=current_menu.get("menu_summary", {}).get("total_price"),
                   target_budget=target_budget)
        
        user_message = f"""
Оптимизируй меню под бюджет клиента:

ТЕКУЩЕЕ МЕНЮ:
{json.dumps(current_menu, ensure_ascii=False, indent=2)}

ЦЕЛЕВОЙ БЮДЖЕТ: {target_budget:,}₽

КОНТЕКСТ МЕРОПРИЯТИЯ:
{json.dumps(event_context, ensure_ascii=False, indent=2)}

Предложи оптимизацию с сохранением качества и стандартов.

Ответь в формате JSON:
{{
  "optimization_result": {{
    "achievable": true/false,
    "optimized_price": финальная_стоимость,
    "savings": размер_экономии,
    "savings_percent": процент_экономии
  }},
  "changes": [
    {{
      "type": "replace|remove|reduce|add_set",
      "original_item": {{
        "id": "ID_оригинала",
        "name": "название",
        "price": стоимость,
        "quantity": количество
      }},
      "new_item": {{
        "id": "ID_замены", 
        "name": "название",
        "price": стоимость,
        "quantity": количество
      }},
      "savings": экономия_по_позиции,
      "justification": "обоснование замены",
      "quality_impact": "как повлияет на качество"
    }}
  ],
  "final_menu": {{
    "items": [список_финальных_позиций],
    "total_price": итоговая_стоимость,
    "total_weight": итоговый_вес,
    "weight_per_guest": граммовка_на_гостя,
    "price_per_guest": стоимость_на_гостя
  }},
  "alternatives": [
    {{
      "description": "альтернативный подход",
      "price": стоимость,
      "pros": ["плюсы"],
      "cons": ["минусы"]
    }}
  ],
  "recommendations": [
    "дополнительные рекомендации по экономии"
  ]
}}
"""
        
        try:
            response = await claude_service.send_structured_request(
                system_prompt=self.SYSTEM_PROMPT,
                user_message=user_message,
                expected_format="json"
            )
            
            logger.info("BudgetOptimizer completed optimization",
                       achievable=response.get("optimization_result", {}).get("achievable"),
                       savings=response.get("optimization_result", {}).get("savings"))
            
            return response
            
        except Exception as e:
            logger.error("BudgetOptimizer failed", error=str(e))
            return self._get_fallback_optimization(current_menu, target_budget)
    
    async def suggest_alternatives(self, current_menu: Dict[str, Any], 
                                  budget_range: tuple) -> Dict[str, Any]:
        """Предложение альтернативных вариантов в диапазоне бюджета"""
        
        min_budget, max_budget = budget_range
        
        user_message = f"""
Предложи несколько альтернативных вариантов меню в диапазоне {min_budget:,}-{max_budget:,}₽:

БАЗОВОЕ МЕНЮ:
{json.dumps(current_menu, ensure_ascii=False, indent=2)}

Создай 3-4 варианта с разными подходами к экономии.

Ответь в формате JSON:
{{
  "alternatives": [
    {{
      "name": "название варианта",
      "description": "описание подхода",
      "price": стоимость,
      "weight_per_guest": граммовка,
      "key_changes": ["основные изменения"],
      "target_audience": "для кого подойдет",
      "menu_items": [список_позиций]
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
            
            return response
            
        except Exception as e:
            logger.error("BudgetOptimizer alternatives failed", error=str(e))
            return {"alternatives": []}
    
    def _get_fallback_optimization(self, current_menu: Dict[str, Any], target_budget: int) -> Dict[str, Any]:
        """Базовая оптимизация при ошибках ИИ"""
        current_price = current_menu.get("menu_summary", {}).get("total_price", 0)
        
        if current_price <= target_budget:
            return {
                "optimization_result": {
                    "achievable": True,
                    "optimized_price": current_price,
                    "savings": 0
                },
                "changes": [],
                "final_menu": current_menu.get("menu_summary", {})
            }
        
        # Простая пропорциональная редукция
        reduction_factor = target_budget / current_price if current_price > 0 else 1
        
        return {
            "optimization_result": {
                "achievable": reduction_factor >= 0.5,  # Не более 50% сокращения
                "optimized_price": int(current_price * reduction_factor),
                "savings": current_price - int(current_price * reduction_factor)
            },
            "changes": [{
                "type": "reduce",
                "justification": "Пропорциональное сокращение количества",
                "savings": current_price - int(current_price * reduction_factor)
            }],
            "recommendations": ["Требуется детальный анализ для точной оптимизации"]
        }

# Глобальный экземпляр эксперта
budget_optimizer = BudgetOptimizer()