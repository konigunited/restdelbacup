"""
High-performance menu data models with validation
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from decimal import Decimal
from src.models.base import RestDelBotBaseModel

class NutritionInfo(BaseModel):
    """Пищевая ценность на 100г"""
    fats: float = Field(..., ge=0, description="Жиры на 100г")
    proteins: float = Field(..., ge=0, description="Белки на 100г") 
    carbs: float = Field(..., ge=0, description="Углеводы на 100г")
    calories: float = Field(..., ge=0, description="Калории на 100г")

class MenuCategory(str, Enum):
    """Категории меню"""
    CANAPES = "канапе"
    BRUSCHETTAS = "брускетты"
    SANDWICHES = "сэндвичи"
    SALADS = "салаты"
    DESSERTS = "десерты"
    HOT_DISHES = "горячие закуски"
    SETS = "наборы"

class EventType(str, Enum):
    """Типы мероприятий"""
    COFFEE_BREAK = "coffee_break"
    BUFFET = "buffet"
    BANQUET = "banquet"

class MenuItem(RestDelBotBaseModel):
    """Позиция меню с оптимизацией для поиска"""
    
    id: str = Field(..., description="Уникальный ID позиции")
    name: str = Field(..., min_length=1, max_length=200, description="Название")
    weight: int = Field(..., gt=0, description="Вес в граммах")
    price: int = Field(..., gt=0, description="Цена в рублях")
    category: MenuCategory = Field(..., description="Категория")
    nutrition: NutritionInfo = Field(..., description="Пищевая ценность")
    
    # Дополнительные поля
    search_terms: List[str] = Field(default_factory=list, description="Термины для поиска")
    
    @validator("search_terms", always=True)
    def generate_search_terms(cls, v, values):
        """Автогенерация поисковых терминов"""
        if not v and "name" in values:
            name = values["name"].lower()
            terms = name.split()
            return list(set(terms))
        return v

class MenuSet(MenuItem):
    """Готовый набор блюд"""
    is_set: bool = Field(default=True, description="Это набор")
    guests_range: Optional[str] = Field(None, description="Диапазон гостей")
    includes: Optional[List[str]] = Field(None, description="Состав набора")

class Menu(RestDelBotBaseModel):
    """Полное меню с индексами для оптимизации"""
    
    items: List[MenuItem] = Field(..., description="Все позиции меню")
    sets: List[MenuSet] = Field(..., description="Готовые наборы")
    
    def __init__(self, **data):
        super().__init__(**data)
        self._by_id = {}
        self._by_category = {}
        self._build_indexes()
    
    def _build_indexes(self):
        """Построение индексов для быстрого поиска"""
        all_items = self.items + self.sets
        
        for item in all_items:
            self._by_id[item.id] = item
            
            if item.category not in self._by_category:
                self._by_category[item.category] = []
            self._by_category[item.category].append(item)
    
    def get_by_id(self, item_id: str) -> Optional[MenuItem]:
        """Получить позицию по ID"""
        return self._by_id.get(item_id)
    
    def get_by_category(self, category: MenuCategory) -> List[MenuItem]:
        """Получить позиции по категории"""
        return self._by_category.get(category, [])
    
    def search(self, query: str, limit: int = 50) -> List[MenuItem]:
        """Простой поиск по названию"""
        query = query.lower()
        results = []
        
        for item in self.items + self.sets:
            if query in item.name.lower():
                results.append(item)
                if len(results) >= limit:
                    break
        
        return results
