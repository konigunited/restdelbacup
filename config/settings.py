"""
Settings for Claude API integration and Expert System
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

class Settings:
    """Конфигурация системы экспертов EventBot 5.0"""
    
    # ===== CLAUDE API SETTINGS =====
    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-4-sonnet-20250514")
    CLAUDE_TIMEOUT: int = int(os.getenv("CLAUDE_TIMEOUT", "60"))
    CLAUDE_TEMPERATURE: float = float(os.getenv("CLAUDE_TEMPERATURE", "0.7"))
    CLAUDE_MAX_TOKENS: int = int(os.getenv("CLAUDE_MAX_TOKENS", "4000"))
    
    # ===== EXPERT SYSTEM SETTINGS =====
    EXPERT_RETRY_COUNT: int = int(os.getenv("EXPERT_RETRY_COUNT", "3"))
    EXPERT_TIMEOUT: int = int(os.getenv("EXPERT_TIMEOUT", "30"))
    ORCHESTRATOR_MAX_ITERATIONS: int = int(os.getenv("ORCHESTRATOR_MAX_ITERATIONS", "5"))
    
    # ===== LOGGING SETTINGS =====
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # ===== APPLICATION SETTINGS =====
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # ===== REST DELIVERY BUSINESS SETTINGS =====
    MIN_ORDER_AMOUNT: int = int(os.getenv("MIN_ORDER_AMOUNT", "10000"))
    MIN_GRAMMAGE_PER_GUEST: int = int(os.getenv("MIN_GRAMMAGE_PER_GUEST", "250"))
    MAX_GRAMMAGE_PER_GUEST: int = int(os.getenv("MAX_GRAMMAGE_PER_GUEST", "1000"))
    
    # Стандарты граммовки по типам мероприятий
    COFFEE_BREAK_GRAMMAGE: tuple = (250, 300)
    BUFFET_GRAMMAGE: tuple = (250, 423)
    BANQUET_GRAMMAGE: tuple = (600, 1000)
    
    # Стоимость услуг
    WAITER_COST_BASE: int = int(os.getenv("WAITER_COST_BASE", "9500"))  # За 6 часов
    WAITER_COST_HOURLY: int = int(os.getenv("WAITER_COST_HOURLY", "1000"))  # За каждый час сверх
    DELIVERY_COST_MKAD: int = int(os.getenv("DELIVERY_COST_MKAD", "0"))  # Бесплатно в МКАД
    DELIVERY_COST_OUTSIDE: tuple = (1500, 3000)  # За МКАД
    
    # ===== VALIDATION METHODS =====
    
    @classmethod
    def validate_claude_config(cls) -> bool:
        """Проверка конфигурации Claude API"""
        return bool(cls.CLAUDE_API_KEY and len(cls.CLAUDE_API_KEY) > 10)
    
    @classmethod
    def validate_business_config(cls) -> bool:
        """Проверка бизнес-конфигурации"""
        return all([
            cls.MIN_ORDER_AMOUNT > 0,
            cls.MIN_GRAMMAGE_PER_GUEST > 0,
            cls.MAX_GRAMMAGE_PER_GUEST > cls.MIN_GRAMMAGE_PER_GUEST,
            cls.WAITER_COST_BASE > 0
        ])
    
    @classmethod
    def get_grammage_range(cls, event_type: str) -> tuple:
        """Получить диапазон граммовки для типа мероприятия"""
        grammage_map = {
            "coffee_break": cls.COFFEE_BREAK_GRAMMAGE,
            "buffet": cls.BUFFET_GRAMMAGE,
            "banquet": cls.BANQUET_GRAMMAGE
        }
        return grammage_map.get(event_type, cls.BUFFET_GRAMMAGE)
    
    @classmethod
    def calculate_waiter_cost(cls, hours: int) -> int:
        """Расчет стоимости официанта"""
        if hours <= 6:
            return cls.WAITER_COST_BASE
        else:
            extra_hours = hours - 6
            return cls.WAITER_COST_BASE + (extra_hours * cls.WAITER_COST_HOURLY)
    
    @classmethod
    def get_delivery_cost(cls, outside_mkad: bool = False) -> int:
        """Получить стоимость доставки"""
        if outside_mkad:
            return cls.DELIVERY_COST_OUTSIDE[0]  # Минимальная стоимость за МКАД
        return cls.DELIVERY_COST_MKAD
    
    # ===== EXPERT PROMPTS CONFIGURATION =====
    
    # Оптимизированные температуры для Claude 4
    CONVERSATION_MANAGER_TEMPERATURE: float = 0.7  # Более консервативный
    MENU_EXPERT_TEMPERATURE: float = 0.5          # Более точный
    GRAMMAGE_CONTROLLER_TEMPERATURE: float = 0.2  # Максимальная точность
    BUDGET_OPTIMIZER_TEMPERATURE: float = 0.4     # Точная оптимизация
    SHEETS_FORMATTER_TEMPERATURE: float = 0.1     # Структурированность
    
    @classmethod
    def get_expert_temperature(cls, expert_type: str) -> float:
        """Получить температуру для конкретного эксперта"""
        temp_map = {
            "conversation": cls.CONVERSATION_MANAGER_TEMPERATURE,
            "menu": cls.MENU_EXPERT_TEMPERATURE,
            "grammage": cls.GRAMMAGE_CONTROLLER_TEMPERATURE,
            "budget": cls.BUDGET_OPTIMIZER_TEMPERATURE,
            "sheets": cls.SHEETS_FORMATTER_TEMPERATURE
        }
        return temp_map.get(expert_type, cls.CLAUDE_TEMPERATURE)
    
    # ===== DEVELOPMENT & DEBUG SETTINGS =====
    
    ENABLE_EXPERT_FALLBACKS: bool = os.getenv("ENABLE_EXPERT_FALLBACKS", "true").lower() == "true"
    # ===== MOCK CLAUDE SETTINGS =====
    MOCK_CLAUDE_RESPONSES: bool = os.getenv("MOCK_CLAUDE_RESPONSES", "false").lower() == "true"
    MOCK_RESPONSE_DELAY: int = int(os.getenv("MOCK_RESPONSE_DELAY", "2"))  # секунды
    MOCK_SUCCESS_RATE: float = float(os.getenv("MOCK_SUCCESS_RATE", "0.9"))  # 90% успеха
    DETAILED_LOGGING: bool = os.getenv("DETAILED_LOGGING", "true").lower() == "true"
    
    # ===== PERFORMANCE SETTINGS =====
    
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "120"))
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))  # 5 минут
    
    @classmethod
    def to_dict(cls) -> dict:
        """Конвертация настроек в словарь для логирования (без секретов)"""
        return {
            "claude_model": cls.CLAUDE_MODEL,
            "claude_temperature": cls.CLAUDE_TEMPERATURE,
            "claude_max_tokens": cls.CLAUDE_MAX_TOKENS,
            "expert_retry_count": cls.EXPERT_RETRY_COUNT,
            "environment": cls.ENVIRONMENT,
            "debug": cls.DEBUG,
            "min_order_amount": cls.MIN_ORDER_AMOUNT,
            "grammage_ranges": {
                "coffee_break": cls.COFFEE_BREAK_GRAMMAGE,
                "buffet": cls.BUFFET_GRAMMAGE,
                "banquet": cls.BANQUET_GRAMMAGE
            },
            "claude_configured": cls.validate_claude_config(),
            "business_config_valid": cls.validate_business_config()
        }

# Глобальный экземпляр настроек
settings = Settings()

# Валидация критически важных настроек при импорте
if not settings.validate_claude_config() and not settings.MOCK_CLAUDE_RESPONSES:
    import warnings
    warnings.warn(
        "Claude API key not configured! Set CLAUDE_API_KEY environment variable.",
        UserWarning
    )

if not settings.validate_business_config():
    raise ValueError("Invalid business configuration. Check your environment variables.")