"""
SheetsFormatter - Технический эксперт по оформлению смет в Google Sheets
"""
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
from src.services.claude_service import claude_service
from src.utils.logger import logger

class SheetsFormatter:
    """Эксперт по структурированию данных для Google Sheets шаблонов"""
    
    SYSTEM_PROMPT = """
Ты - технический эксперт по оформлению смет в Google Sheets формате Rest Delivery.

ТВОЯ РОЛЬ: Структурировать финальные данные для автозаполнения шаблона Google Sheets.

СТРУКТУРА ШАБЛОНА GOOGLE SHEETS:
1. Лист "Смета": номер заказа, дата, меню с расчетами, итоги
2. Лист "Банкетка": услуги обслуживания, аренда, транспорт
3. Лист "Меню фото": автофильтрация фото по выбранным позициям
4. Лист "Финал": брендинг и контакты

ФОРМАТ НОМЕРА ЗАКАЗА: P-XXXXX (где XXXXX - уникальный номер)

ТРЕБОВАНИЯ К ДАННЫМ:
- Все цены в рублях (целые числа)
- Все веса в граммах (целые числа)
- Даты в формате DD.MM.YYYY
- Время в формате HH:MM
- Точные названия позиций из меню

СТРУКТУРА ВЫВОДА:
Всегда возвращай только чистый JSON без дополнительного текста!

РАСЧЕТЫ:
- total_weight: сумма весов всех позиций
- weight_per_guest: total_weight / количество_гостей
- total_price: сумма стоимостей всех позиций
- price_per_guest: total_price / количество_гостей

УСЛУГИ ОБСЛУЖИВАНИЯ:
- Официант: 9,500₽ за 6 часов + 1,000₽/час сверх
- Повар: по необходимости
- Менеджер: для сложных мероприятий
- Доставка: бесплатно в МКАД, 1,500-3,000₽ за МКАД
- Аренда: посуда, мебель, оборудование

Всегда проверяй математику и логическую согласованность данных.
"""

    async def format_for_sheets(self, menu_data: Dict[str, Any], 
                               event_details: Dict[str, Any],
                               service_options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Форматирование данных для Google Sheets"""
        
        logger.info("SheetsFormatter formatting data for sheets",
                   items_count=len(menu_data.get("selected_items", [])),
                   has_service=bool(service_options))
        
        # Генерация номера заказа
        order_number = self._generate_order_number()
        
        user_message = f"""
Структурируй данные для Google Sheets шаблона Rest Delivery:

МЕНЮ:
{json.dumps(menu_data, ensure_ascii=False, indent=2)}

ДЕТАЛИ МЕРОПРИЯТИЯ:
{json.dumps(event_details, ensure_ascii=False, indent=2)}

УСЛУГИ ОБСЛУЖИВАНИЯ:
{json.dumps(service_options or {}, ensure_ascii=False, indent=2)}

НОМЕР ЗАКАЗА: {order_number}

Создай структурированный JSON для автозаполнения Google Sheets.

ОБЯЗАТЕЛЬНЫЙ ФОРМАТ ОТВЕТА:
{{
  "order_info": {{
    "number": "{order_number}",
    "date": "DD.MM.YYYY",
    "time": "HH:MM", 
    "address": "адрес доставки",
    "guests": количество_гостей,
    "event_type": "кофе-брейк|фуршет|банкет",
    "duration": "продолжительность в часах"
  }},
  "menu_items": [
    {{
      "name": "точное название позиции",
      "quantity": количество_сетов,
      "weight_per_set": вес_одного_сета_в_граммах,
      "price_per_set": цена_одного_сета_в_рублях,
      "total_weight": общий_вес_в_граммах,
      "total_price": общая_стоимость_в_рублях,
      "category": "категория позиции"
    }}
  ],
  "services": [
    {{
      "name": "название услуги",
      "description": "описание услуги",
      "quantity": количество,
      "unit": "единица измерения",
      "price_per_unit": цена_за_единицу,
      "total_price": общая_стоимость
    }}
  ],
  "totals": {{
    "menu_cost": общая_стоимость_меню,
    "service_cost": стоимость_услуг,
    "delivery_cost": стоимость_доставки,
    "total_cost": итоговая_стоимость,
    "total_weight": общий_вес_в_граммах,
    "weight_per_guest": граммовка_на_гостя,
    "price_per_guest": стоимость_на_гостя
  }},
  "metadata": {{
    "created_at": "текущая дата и время",
    "template_version": "1.0",
    "calculation_notes": ["примечания к расчетам"]
  }}
}}
"""
        
        try:
            response = await claude_service.send_structured_request(
                system_prompt=self.SYSTEM_PROMPT,
                user_message=user_message,
                expected_format="json"
            )
            
            # Валидация и дополнение данных
            validated_response = self._validate_sheets_data(response, order_number)
            
            logger.info("SheetsFormatter completed formatting",
                       order_number=validated_response.get("order_info", {}).get("number"),
                       total_cost=validated_response.get("totals", {}).get("total_cost"))
            
            return validated_response
            
        except Exception as e:
            logger.error("SheetsFormatter failed", error=str(e))
            return self._get_fallback_sheets_data(menu_data, event_details, order_number)
    
    async def update_sheets_data(self, existing_data: Dict[str, Any], 
                                changes: Dict[str, Any]) -> Dict[str, Any]:
        """Обновление существующих данных для листов"""
        
        user_message = f"""
Обнови существующие данные Google Sheets с учетом изменений:

СУЩЕСТВУЮЩИЕ ДАННЫЕ:
{json.dumps(existing_data, ensure_ascii=False, indent=2)}

ИЗМЕНЕНИЯ:
{json.dumps(changes, ensure_ascii=False, indent=2)}

Сохрани структуру и обнови только измененные поля.
Пересчитай все итоги и проверь математику.

Верни в том же JSON формате.
"""
        
        try:
            response = await claude_service.send_structured_request(
                system_prompt=self.SYSTEM_PROMPT,
                user_message=user_message,
                expected_format="json"
            )
            
            return response
            
        except Exception as e:
            logger.error("SheetsFormatter update failed", error=str(e))
            # При ошибке возвращаем существующие данные
            return existing_data
    
    def _generate_order_number(self) -> str:
        """Генерация уникального номера заказа"""
        timestamp = int(datetime.now().timestamp())
        return f"P-{timestamp % 100000:05d}"
    
    def _validate_sheets_data(self, data: Dict[str, Any], order_number: str) -> Dict[str, Any]:
        """Валидация и исправление данных для sheets"""
        
        # Проверяем обязательные поля
        if "order_info" not in data:
            data["order_info"] = {}
        
        if "number" not in data["order_info"]:
            data["order_info"]["number"] = order_number
        
        if "menu_items" not in data:
            data["menu_items"] = []
        
        if "totals" not in data:
            data["totals"] = {}
        
        # Пересчитываем итоги для проверки
        menu_cost = sum(item.get("total_price", 0) for item in data["menu_items"])
        service_cost = sum(service.get("total_price", 0) for service in data.get("services", []))
        total_weight = sum(item.get("total_weight", 0) for item in data["menu_items"])
        
        data["totals"].update({
            "menu_cost": menu_cost,
            "service_cost": service_cost,
            "total_cost": menu_cost + service_cost,
            "total_weight": total_weight
        })
        
        # Добавляем метаданные если их нет
        if "metadata" not in data:
            data["metadata"] = {
                "created_at": datetime.now().isoformat(),
                "template_version": "1.0"
            }
        
        return data
    
    def _get_fallback_sheets_data(self, menu_data: Dict[str, Any], 
                                 event_details: Dict[str, Any], 
                                 order_number: str) -> Dict[str, Any]:
        """Базовые данные при ошибках ИИ"""
        
        guests = event_details.get("guests", 10)
        total_price = menu_data.get("menu_summary", {}).get("total_price", 10000)
        total_weight = menu_data.get("menu_summary", {}).get("total_weight", 2500)
        
        return {
            "order_info": {
                "number": order_number,
                "date": (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y"),
                "time": "12:00",
                "guests": guests,
                "event_type": "фуршет"
            },
            "menu_items": menu_data.get("selected_items", []),
            "services": [],
            "totals": {
                "menu_cost": total_price,
                "service_cost": 0,
                "total_cost": total_price,
                "total_weight": total_weight,
                "weight_per_guest": total_weight // guests,
                "price_per_guest": total_price // guests
            },
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "template_version": "1.0",
                "calculation_notes": ["Базовые расчеты - требуется проверка"]
            }
        }

# Глобальный экземпляр эксперта
sheets_formatter = SheetsFormatter()