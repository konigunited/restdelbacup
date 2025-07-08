"""
Calculator API endpoints
"""
from fastapi import APIRouter
from pydantic import BaseModel
from src.models.menu import EventType
from src.utils.calculations import BusinessCalculator

router = APIRouter(prefix="/api/calculator", tags=["calculator"])

class PortionRequest(BaseModel):
    event_type: EventType
    grams_per_guest: float

@router.post("/validate-portions")
async def validate_portions(request: PortionRequest):
    """Валидация граммовки"""
    return BusinessCalculator.validate_portion_size(
        request.event_type, 
        request.grams_per_guest
    )

@router.get("/portion-standards")
async def get_portion_standards():
    """Получить стандарты граммовки"""
    return BusinessCalculator.PORTION_STANDARDS
