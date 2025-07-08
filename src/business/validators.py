from typing import List, Dict, Any
from datetime import datetime, timedelta
from .standards import BusinessStandards, ValidationResult, ValidationLevel

class PortionValidator:
    """Валидатор граммовки"""
    
    @staticmethod
    def validate(order_data: Dict[str, Any]) -> List[ValidationResult]:
        results = []
        
        guests = order_data.get('order_info', {}).get('guests', 0)
        event_type = order_data.get('order_info', {}).get('event_type', 'buffet')
        total_weight = order_data.get('totals', {}).get('total_weight', 0)
        
        if guests <= 0:
            results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                message="❌ Количество гостей должно быть больше 0",
                field="guests",
                recommendation="Укажите корректное количество гостей"
            ))
            return results
        
        grams_per_guest = total_weight / guests
        standards = BusinessStandards.PORTION_STANDARDS.get(event_type, 
                                                           BusinessStandards.PORTION_STANDARDS['buffet'])
        
        if grams_per_guest < 250:
            results.append(ValidationResult(
                level=ValidationLevel.CRITICAL,
                message=f"🚨 КРИТИЧНО: Недостаточно еды! {grams_per_guest:.0f}г < 250г на гостя",
                field="portion_size",
                recommendation="Увеличьте количество блюд минимум до 250г на гостя"
            ))
        elif grams_per_guest > 750:
            results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                message=f"⚠️ Много еды: {grams_per_guest:.0f}г > 750г на гостя",
                field="portion_size",
                recommendation="Рассмотрите возможность уменьшения порций"
            ))
        elif standards['min'] <= grams_per_guest <= standards['max']:
            results.append(ValidationResult(
                level=ValidationLevel.INFO,
                message=f"✅ Оптимальная граммовка: {grams_per_guest:.0f}г для {event_type}",
                field="portion_size",
                recommendation="Граммовка соответствует стандартам",
                reference_case="P-39454"
            ))
        else:
            results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                message=f"⚠️ Граммовка вне стандартов: {grams_per_guest:.0f}г для {event_type}",
                field="portion_size",
                recommendation=f"Оптимальный диапазон: {standards['min']}-{standards['max']}г"
            ))
        
        return results

class CostValidator:
    """Валидатор стоимости"""
    
    @staticmethod
    def validate(order_data: Dict[str, Any]) -> List[ValidationResult]:
        results = []
        
        guests = order_data.get('order_info', {}).get('guests', 0)
        event_type = order_data.get('order_info', {}).get('event_type', 'buffet')
        total_cost = order_data.get('totals', {}).get('total_cost', 0)
        
        # Проверка минимального заказа
        if total_cost < BusinessStandards.MIN_ORDER_AMOUNT:
            results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                message=f"❌ Сумма заказа {total_cost:,}₽ меньше минимальной {BusinessStandards.MIN_ORDER_AMOUNT:,}₽",
                field="total_cost",
                recommendation=f"Увеличьте заказ до {BusinessStandards.MIN_ORDER_AMOUNT:,}₽"
            ))
            return results
        
        # Проверка стоимости на гостя
        if guests > 0:
            cost_per_guest = total_cost / guests
            cost_range = BusinessStandards.COST_PER_GUEST_RANGES.get(event_type, 
                                                                   BusinessStandards.COST_PER_GUEST_RANGES['buffet'])
            
            if cost_per_guest < cost_range['min'] * 0.7:
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    message=f"⚠️ Низкая стоимость на гостя: {cost_per_guest:,.0f}₽",
                    field="cost_per_guest",
                    recommendation=f"Ожидаемый диапазон: {cost_range['min']:,}-{cost_range['max']:,}₽"
                ))
            elif cost_per_guest > cost_range['max'] * 1.5:
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    message=f"⚠️ Высокая стоимость на гостя: {cost_per_guest:,.0f}₽",
                    field="cost_per_guest",
                    recommendation=f"Проверьте корректность расчета"
                ))
            else:
                results.append(ValidationResult(
                    level=ValidationLevel.INFO,
                    message=f"✅ Сумма заказа {total_cost:,}₽ соответствует требованиям",
                    field="total_cost",
                    recommendation="Стоимость в пределах нормы"
                ))
        
        return results

class ServiceValidator:
    """Валидатор услуг обслуживания"""
    
    @staticmethod
    def validate(order_data: Dict[str, Any]) -> List[ValidationResult]:
        results = []
        
        guests = order_data.get('order_info', {}).get('guests', 0)
        services = order_data.get('services', [])
        
        # Подсчет официантов
        waiter_count = 0
        for service in services:
            if 'официант' in service.get('name', '').lower():
                waiter_count += service.get('quantity', 0)
        
        if waiter_count > 0:
            min_waiters = max(1, guests // BusinessStandards.WAITER_RATIO_SIMPLE)
            max_waiters = max(2, guests // BusinessStandards.WAITER_RATIO_COMPLEX)
            
            if waiter_count < min_waiters:
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    message=f"⚠️ Мало официантов: {waiter_count} для {guests} гостей",
                    field="waiter_count",
                    recommendation=f"Рекомендуем минимум {min_waiters} официант(ов)"
                ))
            elif waiter_count > max_waiters:
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    message=f"⚠️ Много официантов: {waiter_count} для {guests} гостей",
                    field="waiter_count",
                    recommendation=f"Оптимальное количество: {min_waiters}-{max_waiters}"
                ))
            else:
                results.append(ValidationResult(
                    level=ValidationLevel.INFO,
                    message=f"✅ Количество официантов оптимально: {waiter_count}",
                    field="waiter_count",
                    recommendation="Персонал соответствует требованиям"
                ))
        
        return results

class TimingValidator:
    """Валидатор временных ограничений"""
    
    @staticmethod
    def validate(order_data: Dict[str, Any]) -> List[ValidationResult]:
        results = []
        
        event_date = order_data.get('order_info', {}).get('date')
        services = order_data.get('services', [])
        total_cost = order_data.get('totals', {}).get('total_cost', 0)
        
        if not event_date:
            return results
        
        try:
            event_datetime = datetime.strptime(event_date, '%Y-%m-%d')
            now = datetime.now()
            hours_until_event = (event_datetime - now).total_seconds() / 3600
            
            # Определение требований по времени
            has_service = len(services) > 0
            required_hours = BusinessStandards.TIMING_REQUIREMENTS['no_service']
            
            if has_service:
                if total_cost > 60000:
                    required_hours = BusinessStandards.TIMING_REQUIREMENTS['service_premium']
                else:
                    required_hours = BusinessStandards.TIMING_REQUIREMENTS['service_standard']
            
            if hours_until_event < required_hours:
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    message=f"⚠️ Мало времени до мероприятия: {hours_until_event:.0f}ч < {required_hours}ч",
                    field="timing",
                    recommendation=f"Рекомендуем заказывать за {required_hours} часов"
                ))
            else:
                results.append(ValidationResult(
                    level=ValidationLevel.INFO,
                    message=f"✅ Время до мероприятия достаточно: {hours_until_event:.0f}ч",
                    field="timing",
                    recommendation="Временные требования соблюдены"
                ))
                
        except ValueError:
            results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                message="❌ Некорректный формат даты",
                field="event_date",
                recommendation="Используйте формат YYYY-MM-DD"
            ))
        
        return results

class MenuValidator:
    """Валидатор состава меню"""
    
    @staticmethod
    def validate(order_data: Dict[str, Any]) -> List[ValidationResult]:
        results = []
        
        menu_items = order_data.get('menu_items', [])
        
        if not menu_items:
            results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                message="❌ Меню не может быть пустым",
                field="menu_items",
                recommendation="Добавьте блюда в заказ"
            ))
            return results
        
        # Проверка разнообразия меню
        categories = set()
        for item in menu_items:
            category = item.get('category', 'unknown')
            categories.add(category)
        
        if len(categories) < 2:
            results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                message="⚠️ Мало разнообразия в меню",
                field="menu_composition",
                recommendation="Добавьте блюда из разных категорий"
            ))
        else:
            results.append(ValidationResult(
                level=ValidationLevel.INFO,
                message=f"✅ Разнообразное меню: {len(categories)} категорий",
                field="menu_composition",
                recommendation="Хорошее разнообразие блюд"
            ))
        
        return results