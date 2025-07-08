"""
API endpoints for testing Claude experts
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from src.services.expert_orchestrator import expert_orchestrator
from src.experts.conversation_manager import conversation_manager
from src.experts.menu_expert import menu_expert
from src.experts.grammage_controller import grammage_controller
from src.experts.budget_optimizer import budget_optimizer
from src.experts.sheets_formatter import sheets_formatter
from src.services.claude_service import claude_service
from src.utils.logger import logger

router = APIRouter(prefix="/api/experts", tags=["Claude Experts"])

class EstimateRequest(BaseModel):
    user_input: str
    context: Optional[Dict[str, Any]] = None

class RefinementRequest(BaseModel):
    initial_result: Dict[str, Any]
    refinement_request: str

class ConversationRequest(BaseModel):
    user_input: str
    context: Optional[List[Dict[str, str]]] = None

class MenuRequest(BaseModel):
    requirements: Dict[str, Any]

class ValidationRequest(BaseModel):
    menu_data: Dict[str, Any]
    event_context: Dict[str, Any]

class BudgetRequest(BaseModel):
    current_menu: Dict[str, Any]
    target_budget: int
    event_context: Dict[str, Any]

class SheetsRequest(BaseModel):
    menu_data: Dict[str, Any]
    event_details: Dict[str, Any]
    service_options: Optional[Dict[str, Any]] = None

@router.post("/estimate/generate")
async def generate_estimate(request: EstimateRequest):
    """Полная генерация сметы через всех экспертов"""
    try:
        result = await expert_orchestrator.process_estimate_request(
            request.user_input, 
            request.context
        )
        return result
    except Exception as e:
        logger.error("Estimate generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/estimate/refine")
async def refine_estimate(request: RefinementRequest):
    """Итеративное улучшение существующей сметы"""
    try:
        result = await expert_orchestrator.process_iterative_refinement(
            request.initial_result,
            request.refinement_request
        )
        return result
    except Exception as e:
        logger.error("Estimate refinement failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conversation/analyze")
async def analyze_conversation(request: ConversationRequest):
    """Тестирование ConversationManager"""
    try:
        # Преобразуем context в нужный формат если нужно
        context = None
        if request.context:
            from src.services.claude_service import ClaudeMessage
            context = [ClaudeMessage(role=msg["role"], content=msg["content"]) 
                      for msg in request.context]
        
        result = await conversation_manager.analyze_request(request.user_input, context)
        return result
    except Exception as e:
        logger.error("Conversation analysis failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conversation/response")
async def generate_conversation_response(request: ConversationRequest):
    """Генерация ответа клиенту"""
    try:
        # Сначала анализируем запрос
        context = None
        if request.context:
            from src.services.claude_service import ClaudeMessage
            context = [ClaudeMessage(role=msg["role"], content=msg["content"]) 
                      for msg in request.context]
        
        analysis = await conversation_manager.analyze_request(request.user_input, context)
        
        # Генерируем ответ
        response = await conversation_manager.generate_response(analysis)
        
        return {
            "analysis": analysis,
            "response": response
        }
    except Exception as e:
        logger.error("Response generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/menu/select")
async def select_menu(request: MenuRequest):
    """Тестирование MenuExpert"""
    try:
        result = await menu_expert.select_menu(request.requirements)
        return result
    except Exception as e:
        logger.error("Menu selection failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/grammage/validate")
async def validate_grammage(request: ValidationRequest):
    """Тестирование GrammageController"""
    try:
        result = await grammage_controller.validate_portions(
            request.menu_data, 
            request.event_context
        )
        return result
    except Exception as e:
        logger.error("Grammage validation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/grammage/suggest-corrections")
async def suggest_grammage_corrections(request: ValidationRequest):
    """Предложение корректировок граммовки"""
    try:
        # Сначала валидируем
        validation_result = await grammage_controller.validate_portions(
            request.menu_data, 
            request.event_context
        )
        
        # Если есть проблемы, предлагаем корректировки
        if validation_result.get("validation_result", {}).get("status") in ["warning", "critical"]:
            corrections = await grammage_controller.suggest_corrections(
                validation_result,
                request.menu_data
            )
            return {
                "validation": validation_result,
                "corrections": corrections
            }
        
        return {
            "validation": validation_result,
            "corrections": {"corrections": [], "priority": "none"}
        }
        
    except Exception as e:
        logger.error("Grammage corrections failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/budget/optimize")
async def optimize_budget(request: BudgetRequest):
    """Тестирование BudgetOptimizer"""
    try:
        result = await budget_optimizer.optimize_budget(
            request.current_menu,
            request.target_budget,
            request.event_context
        )
        return result
    except Exception as e:
        logger.error("Budget optimization failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/budget/alternatives")
async def suggest_budget_alternatives(request: BudgetRequest):
    """Предложение альтернативных вариантов бюджета"""
    try:
        current_price = request.current_menu.get("menu_summary", {}).get("total_price", 0)
        
        # Создаем диапазон ±20% от целевого бюджета
        min_budget = int(request.target_budget * 0.8)
        max_budget = int(request.target_budget * 1.2)
        
        result = await budget_optimizer.suggest_alternatives(
            request.current_menu,
            (min_budget, max_budget)
        )
        return result
    except Exception as e:
        logger.error("Budget alternatives failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sheets/format")
async def format_sheets(request: SheetsRequest):
    """Тестирование SheetsFormatter"""
    try:
        result = await sheets_formatter.format_for_sheets(
            request.menu_data,
            request.event_details,
            request.service_options
        )
        return result
    except Exception as e:
        logger.error("Sheets formatting failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sheets/update")
async def update_sheets_data(existing_data: Dict[str, Any], changes: Dict[str, Any]):
    """Обновление данных для Google Sheets"""
    try:
        result = await sheets_formatter.update_sheets_data(existing_data, changes)
        return result
    except Exception as e:
        logger.error("Sheets update failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_experts_stats():
    """Статистика использования экспертов"""
    try:
        claude_stats = claude_service.get_stats()
        return {
            "claude_api": claude_stats,
            "experts": {
                "conversation_manager": "active",
                "menu_expert": "active", 
                "grammage_controller": "active",
                "budget_optimizer": "active",
                "sheets_formatter": "active"
            },
            "orchestrator": "active"
        }
    except Exception as e:
        logger.error("Failed to get stats", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def experts_health_check():
    """Проверка работоспособности всех экспертов"""
    try:
        # Простой тест Claude API
        test_response = await claude_service.send_message(
            system_prompt="Ты - тестовая система. Ответь одним словом: 'работает'",
            user_message="Тест связи"
        )
        
        claude_working = "работает" in test_response.content.lower()
        
        return {
            "status": "healthy" if claude_working else "degraded",
            "claude_api": "working" if claude_working else "error",
            "experts_loaded": True,
            "orchestrator_ready": True,
            "timestamp": "2025-01-19T12:00:00Z"
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "claude_api": "error",
            "experts_loaded": False,
            "error": str(e),
            "timestamp": "2025-01-19T12:00:00Z"
        }

@router.get("/demo")
async def demo_full_workflow():
    """Демонстрация полного workflow экспертной системы"""
    try:
        demo_request = "Нужен фуршет на 25 человек, бюджет 35000 рублей, завтра в офисе"
        
        result = await expert_orchestrator.process_estimate_request(
            demo_request,
            {"session_id": "demo", "demo_mode": True}
        )
        
        return {
            "demo_request": demo_request,
            "result": result,
            "explanation": {
                "stage_1": "ConversationManager проанализировал запрос",
                "stage_2": "MenuExpert подобрал меню",
                "stage_3": "GrammageController проверил граммовку", 
                "stage_4": "BudgetOptimizer оптимизировал под бюджет",
                "stage_5": "SheetsFormatter подготовил данные для Google Sheets"
            }
        }
    except Exception as e:
        logger.error("Demo workflow failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))