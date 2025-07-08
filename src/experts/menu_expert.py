"""
MenuExpert - Шеф-менеджер по подбору меню Rest Delivery
"""
import json
from typing import Dict, Any, Optional, List
from src.services.claude_service import claude_service
from src.utils.logger import logger

class MenuExpert:
    """Эксперт по подбору оптимального меню из ассортимента Rest Delivery"""
    
    SYSTEM_PROMPT = """
Ты - шеф-менеджер Rest Delivery с глубоким знанием всей продукции.

ТВОЯ РОЛЬ: Подобрать идеальное меню из реального ассортимента Rest Delivery для конкретного мероприятия.

ПРИНЦИПЫ ПОДБОРА МЕНЮ:

ДЛЯ КОФЕ-БРЕЙКА (250-300г на гостя):
- Обязательно: канапе (2-3 вида) + сэндвичи + круассаны + десерты
- Дополнительно: морсы, фрукты
- Избегать: горячие закуски, салаты, банкетные блюда

ДЛЯ ФУРШЕТА (250-423г на гостя):
- Обязательно: много канапе (4-6 видов) + брускетты + сытные позиции + салаты + десерты
- Сытные позиции: мини-бургеры, сэндвичи, хот-доги
- Дополнительно: круассаны, горячие закуски, морсы

ДЛЯ БАНКЕТА (600-1000г на гостя):
- Обязательно: нарезки + брускетты + горячие блюда + десерты
- Дополнительно: канапе, салаты, напитки
- Избегать: простые сэндвичи, хот-доги

ПРАВИЛА РАСЧЕТА КОЛИЧЕСТВА:
- Учитывай точный вес каждой позиции
- Соблюдай стандарты граммовки для типа мероприятия
- Минимум 1 позиция каждого ключевого типа на гостя
- Разнообразие важнее количества одной позиции

ГОТОВЫЕ НАБОРЫ:
В меню есть готовые авторские наборы (сеты) которые оптимально подходят:
- "Деловой" на 21-25 персон (6023г, 27,290₽)
- "Праздничный" на 21-25 персон (5740г, 30,190₽)
- VIP кофе-брейк на 16-20 персон (4668г, 28,190₽)
Рассматривай их как готовое решение, если подходят по количеству гостей.

ПРИНЦИПЫ БАЛАНСА:
- 40% канапе и закуски
- 25% сытные позиции  
- 20% салаты/гарниры (для фуршета/банкета)
- 15% десерты

Всегда используй ТОЛЬКО реальные позиции из меню Rest Delivery с точными весами и ценами.
"""

    async def select_menu(self, requirements: Dict[str, Any], available_items: List[Dict] = None) -> Dict[str, Any]:
        """Подбор меню на основе требований"""
        
        logger.info("MenuExpert selecting menu", requirements=requirements)
        
        # Получаем доступные позиции если не переданы
        if not available_items:
            available_items = await self._get_available_items()
        
        user_message = f"""
Подбери оптимальное меню для мероприятия:

ТРЕБОВАНИЯ:
{json.dumps(requirements, ensure_ascii=False, indent=2)}

ДОСТУПНЫЕ ПОЗИЦИИ МЕНЮ:
{json.dumps(available_items[:100], ensure_ascii=False, indent=2)}

Создай сбалансированное меню учитывая:
1. Тип мероприятия и стандарты граммовки
2. Количество гостей
3. Бюджетные ограничения (если указаны)
4. Разнообразие и баланс позиций

Ответь в формате JSON:
{{
  "selected_items": [
    {{
      "id": "ID позиции",
      "name": "название",
      "category": "категория",
      "weight": вес_грамм,
      "price": цена_рублей,
      "quantity": количество_сетов,
      "total_weight": общий_вес,
      "total_price": общая_стоимость,
      "reason": "почему выбрана эта позиция"
    }}
  ],
  "menu_summary": {{
    "total_weight": общий_вес_граммов,
    "total_price": общая_стоимость_рублей,
    "weight_per_guest": граммовка_на_гостя,
    "price_per_guest": стоимость_на_гостя,
    "categories_coverage": {{
      "канапе": количество_видов,
      "брускетты": количество_видов,
      "десерты": количество_видов
    }}
  }},
  "balance_analysis": {{
    "appetizers_percent": процент_закусок,
    "main_percent": процент_основных_блюд,
    "desserts_percent": процент_десертов,
    "balance_score": оценка_баланса_0_10
  }},
  "recommendations": [
    "рекомендации по улучшению меню"
  ]
}}
"""
        
        try:
            response = await claude_service.send_structured_request(
                system_prompt=self.SYSTEM_PROMPT,
                user_message=user_message,
                expected_format="json"
            )
            
            logger.info("MenuExpert selection completed", 
                       items_count=len(response.get("selected_items", [])),
                       total_price=response.get("menu_summary", {}).get("total_price"))
            
            return response
            
        except Exception as e:
            logger.error("MenuExpert selection failed", error=str(e))
            return self._get_fallback_menu(requirements)
    
    async def _get_available_items(self) -> List[Dict]:
        """Получение доступных позиций меню"""
        # Тестовые данные для демонстрации
        return [
            {
                "id": "1015599",
                "name": "Антипасти с черри, дайконом и оливкой на бородинском тосте",
                "weight": 21,
                "price": 100,
                "category": "канапе"
            },
            {
                "id": "789",
                "name": "Брускетта с бабаганушом и кедром",
                "weight": 36,
                "price": 105,
                "category": "брускетты"
            },
            {
                "id": "456",
                "name": "Мини-эклер с лососем",
                "weight": 18,
                "price": 95,
                "category": "канапе"
            },
            {
                "id": "321",
                "name": "Круассан с индейкой и сыром",
                "weight": 45,
                "price": 120,
                "category": "сэндвичи"
            },
            {
                "id": "654",
                "name": "Тарталетка с муссом из лосося",
                "weight": 22,
                "price": 110,
                "category": "канапе"
            }
        ]
    
    def _get_fallback_menu(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Запасное меню при ошибках ИИ"""
        guests = requirements.get("guests", 10)
        
        return {
            "selected_items": [
                {
                    "id": "1015599",
                    "name": "Антипасти с черри",
                    "weight": 21,
                    "price": 100,
                    "quantity": guests,
                    "total_weight": 21 * guests,
                    "total_price": 100 * guests,
                    "reason": "Базовые канапе для мероприятия"
                }
            ],
            "menu_summary": {
                "total_weight": 21 * guests,
                "total_price": 100 * guests,
                "weight_per_guest": 21,
                "price_per_guest": 100
            },
            "recommendations": ["Нужно больше позиций для полноценного меню"]
        }

# Глобальный экземпляр эксперта
menu_expert = MenuExpert()