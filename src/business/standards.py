from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any

class ValidationLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationResult:
    level: ValidationLevel
    message: str
    field: str
    recommendation: str = None
    reference_case: str = None

class BusinessStandards:
    """Бизнес-стандарты Rest Delivery"""
    
    # Минимальный заказ
    MIN_ORDER_AMOUNT = 10000
    
    # Стандарты граммовки (мин, макс)
    PORTION_STANDARDS = {
        'coffee_break': {'min': 250, 'max': 300, 'optimal': 275},
        'buffet': {'min': 250, 'max': 423, 'optimal': 335},
        'banquet': {'min': 600, 'max': 1000, 'optimal': 800}
    }
    
    # Стоимость обслуживания
    WAITER_BASE_COST = 9500  # 6 часов
    WAITER_EXTRA_HOUR = 1000
    TAXI_SURCHARGE = 1500
    
    # Расчет персонала
    WAITER_RATIO_SIMPLE = 30  # 1 официант на 30 гостей
    WAITER_RATIO_COMPLEX = 15  # 1 официант на 15 гостей
    
    # Временные ограничения (часы)
    TIMING_REQUIREMENTS = {
        'no_service': 24,
        'service_standard': 48,
        'service_premium': 72
    }
    
    # Ценовые ориентиры по типам мероприятий
    COST_PER_GUEST_RANGES = {
        'coffee_break': {'min': 1150, 'max': 1700},
        'buffet': {'min': 2300, 'max': 3300},
        'banquet': {'min': 4700, 'max': 8600}
    }