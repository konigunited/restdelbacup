"""
Business calculations utilities
"""
from typing import Dict, Any
from src.models.menu import EventType

class BusinessCalculator:
    """Калькулятор бизнес-логики"""
    
    PORTION_STANDARDS = {
        EventType.COFFEE_BREAK: {
            "min_grams": 250,
            "max_grams": 300,
            "optimal_grams": 275
        },
        EventType.BUFFET: {
            "min_grams": 300,
            "max_grams": 450,
            "optimal_grams": 375
        },
        EventType.BANQUET: {
            "min_grams": 600,
            "max_grams": 1000,
            "optimal_grams": 800
        }
    }
    
    @classmethod
    def validate_portion_size(cls, event_type: EventType, grams_per_guest: float) -> Dict[str, Any]:
        """Валидация граммовки"""
        standards = cls.PORTION_STANDARDS.get(event_type)
        if not standards:
            return {"valid": False, "message": "Неизвестный тип мероприятия"}
        
        if grams_per_guest < standards["min_grams"]:
            return {
                "valid": False,
                "status": "warning",
                "message": f"Недостаточно еды: {grams_per_guest}г",
                "recommendation": f"Добавьте еще {standards['min_grams'] - grams_per_guest:.1f}г"
            }
        elif grams_per_guest > standards["max_grams"]:
            return {
                "valid": True,
                "status": "warning",
                "message": f"Много еды: {grams_per_guest}г",
                "recommendation": "Можно уменьшить количество"
            }
        else:
            return {
                "valid": True,
                "status": "optimal",
                "message": f"Оптимальная граммовка: {grams_per_guest}г",
                "recommendation": "Идеально!"
            }
    
    @classmethod
    def calculate_service_cost(cls, guests: int, duration_hours: float, **kwargs) -> Dict[str, Any]:
        """Расчет стоимости обслуживания"""
        base_cost = 9500  # Базовая стоимость
        waiters_count = max(1, guests // 30)
        total_cost = base_cost * waiters_count
        
        return {
            "waiters_count": waiters_count,
            "base_cost": base_cost,
            "total_cost": total_cost,
            "description": f"{waiters_count} официант(ов)"
        }
