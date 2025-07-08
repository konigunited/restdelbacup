"""
Menu API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from src.models.menu import MenuItem, MenuCategory
from src.services.menu_service import menu_service

router = APIRouter(prefix="/api/menu", tags=["menu"])

@router.get("/categories")
async def get_categories():
    """Получить список категорий"""
    return [category.value for category in MenuCategory]

@router.get("/items", response_model=List[MenuItem])
async def get_menu_items(
    category: Optional[MenuCategory] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=100)
):
    """Получить позиции меню"""
    if not menu_service._menu:
        await menu_service.initialize()
    
    if search:
        return menu_service.search_items(search, category, limit)
    elif category:
        items = menu_service.get_items_by_category(category)
        return items[:limit]
    else:
        return menu_service.get_popular_items(limit=limit)

@router.get("/items/{item_id}", response_model=MenuItem)
async def get_menu_item(item_id: str):
    """Получить позицию по ID"""
    if not menu_service._menu:
        await menu_service.initialize()
    
    item = menu_service.get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Позиция не найдена")
    
    return item
