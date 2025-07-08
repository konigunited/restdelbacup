"""
Menu management service
"""
import json
from typing import List, Optional
from pathlib import Path
from src.models.menu import Menu, MenuItem, MenuSet, MenuCategory, EventType
from src.utils.logger import logger
from config.settings import settings

class MenuService:
    """Сервис управления меню"""
    
    def __init__(self):
        self._menu: Optional[Menu] = None
        
    async def initialize(self):
        """Инициализация сервиса"""
        logger.info("Initializing MenuService")
        await self.load_menu()
        logger.info("MenuService initialized")
    
    async def load_menu(self):
        """Загрузка меню из файла"""
        menu_path = Path(settings.MENU_DATA_PATH)
        
        if not menu_path.exists():
            logger.warning("Menu data file not found, creating sample data")
            await self._create_sample_menu()
        
        try:
            with open(menu_path, 'r', encoding='utf-8') as f:
                menu_data = json.load(f)
            
            items = []
            sets = []
            
            for category, category_items in menu_data.items():
                for item_data in category_items:
                    if item_data.get("is_set"):
                        sets.append(MenuSet(**item_data))
                    else:
                        items.append(MenuItem(**item_data))
            
            self._menu = Menu(items=items, sets=sets)
            logger.info(f"Menu loaded successfully. Items: {len(items)}, Sets: {len(sets)}")
            
        except Exception as e:
            logger.error(f"Failed to load menu: {e}")
            raise
    
    async def _create_sample_menu(self):
        """Создание образца меню"""
        sample_data = {
            "canapes": [
                {
                    "id": "1",
                    "name": "Канапе с лососем",
                    "weight": 25,
                    "price": 150,
                    "category": "канапе",
                    "nutrition": {"fats": 8.2, "proteins": 6.3, "carbs": 5.1, "calories": 120}
                },
                {
                    "id": "2",
                    "name": "Канапе с икрой",
                    "weight": 18,
                    "price": 250,
                    "category": "канапе",
                    "nutrition": {"fats": 12.1, "proteins": 8.9, "carbs": 3.2, "calories": 180}
                }
            ],
            "sets": [
                {
                    "id": "set1",
                    "name": "Сет Деловой на 20 персон",
                    "weight": 5000,
                    "price": 25000,
                    "category": "наборы",
                    "is_set": True,
                    "guests_range": "20-25",
                    "includes": ["Канапе ассорти", "Брускетты", "Десерты"],
                    "nutrition": {"fats": 10.5, "proteins": 7.8, "carbs": 12.3, "calories": 165}
                }
            ]
        }
        
        menu_path = Path(settings.MENU_DATA_PATH)
        menu_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(menu_path, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, ensure_ascii=False, indent=2)
        
        logger.info("Sample menu created")
    
    def get_item_by_id(self, item_id: str) -> Optional[MenuItem]:
        """Получить позицию по ID"""
        if not self._menu:
            return None
        return self._menu.get_by_id(item_id)
    
    def get_items_by_category(self, category: MenuCategory) -> List[MenuItem]:
        """Получить позиции по категории"""
        if not self._menu:
            return []
        return self._menu.get_by_category(category)
    
    def search_items(self, query: str, category: Optional[MenuCategory] = None, limit: int = 50) -> List[MenuItem]:
        """Поиск позиций"""
        if not self._menu:
            return []
        
        results = self._menu.search(query, limit)
        
        if category:
            results = [item for item in results if item.category == category]
        
        return results
    
    def get_popular_items(self, limit: int = 10) -> List[MenuItem]:
        """Получить популярные позиции"""
        if not self._menu:
            return []
        return self._menu.items[:limit]

# Глобальный экземпляр
menu_service = MenuService()
