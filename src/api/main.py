"""
EventBot 5.0 - AI-Powered Estimate Generator
Main FastAPI application with Google Sheets integration + Business Logic Core
"""
import asyncio
import sys
import os
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn

# Добавляем корневую директорию в путь для импортов
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

# Core imports
from config.settings import settings
from src.utils.logger import logger

# API Routes (с безопасной обработкой)
estimates_router = None
experts_router = None

try:
    from src.api.routes import estimates
    estimates_router = getattr(estimates, 'router', None)
    if estimates_router:
        logger.info("✅ Estimates router loaded successfully")
    else:
        logger.warning("⚠️ Estimates module found but no 'router' attribute")
except ImportError as e:
    logger.warning(f"⚠️ Estimates router not found: {e}")
except AttributeError as e:
    logger.warning(f"⚠️ Estimates router attribute error: {e}")

try:
    from src.api.routes import experts
    experts_router = getattr(experts, 'router', None)
    if experts_router:
        logger.info("✅ Experts router loaded successfully")
    else:
        logger.warning("⚠️ Experts module found but no 'router' attribute")
except ImportError as e:
    logger.warning(f"⚠️ Experts router not found: {e}")
except AttributeError as e:
    logger.warning(f"⚠️ Experts router attribute error: {e}")

# Calculator and Menu routes
calculator_router = None
menu_router = None

try:
    from src.api.routes import calculator
    calculator_router = getattr(calculator, 'router', None)
    if calculator_router:
        logger.info("✅ Calculator router loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Calculator router not found: {e}")

try:
    from src.api.routes import menu
    menu_router = getattr(menu, 'router', None)
    if menu_router:
        logger.info("✅ Menu router loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Menu router not found: {e}")

# Services
estimate_service = None
sheets_service = None
pdf_service = None

try:
    from src.services.estimate_service import estimate_service
    if estimate_service:
        logger.info("✅ Estimate service loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Estimate service not found: {e}")
    class MockEstimateService:
        async def initialize(self): 
            logger.info("🔄 Mock estimate service initialized")
        async def cleanup_old_data(self, days_old): 
            pass
        def get_stats(self): 
            return {
                "active_processing": 0, 
                "service_stats": {"total_created": 0}, 
                "sheets_service": {"status": "mock"}
            }
    estimate_service = MockEstimateService()

try:
    from src.services.sheets_service import sheets_service
    if sheets_service:
        logger.info("✅ Sheets service loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Sheets service not found: {e}")

try:
    from src.services.pdf_service import pdf_service
    if pdf_service:
        logger.info("✅ PDF service loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ PDF service not found: {e}")
    class MockPdfService:
        def cleanup_old_pdfs(self, days_old): 
            pass
    pdf_service = MockPdfService()

# Business Logic Core
try:
    from src.business import BusinessRulesEngine
    BUSINESS_LOGIC_AVAILABLE = True
    logger.info("✅ Business Logic Core imported successfully")
except ImportError as e:
    logger.error(f"❌ Business Logic Core import failed: {e}")
    BUSINESS_LOGIC_AVAILABLE = False
    
    class MockBusinessRulesEngine:
        async def validate_order(self, order_data):
            return {
                "overall_status": "error",
                "validations": [{
                    "level": "error", 
                    "message": "❌ Business Logic Core не найден", 
                    "field": "system",
                    "recommendation": "Проверьте файлы src/business/*.py"
                }],
                "summary": {"total_validations": 1, "by_level": {"error": 1}},
                "recommendations": ["Создайте файлы Business Logic Core"]
            }
    BusinessRulesEngine = MockBusinessRulesEngine

# Pydantic models для Business Logic
class OrderInfo(BaseModel):
    guests: int
    event_type: str
    date: Optional[str] = None
    number: Optional[str] = None

class MenuItem(BaseModel):
    name: str
    category: Optional[str] = "unknown"
    quantity: Optional[int] = 1
    weight_per_set: Optional[float] = 0
    price_per_set: Optional[float] = 0

class Service(BaseModel):
    name: str
    quantity: Optional[int] = 1
    duration: Optional[int] = 6
    cost: Optional[float] = 0

class OrderTotals(BaseModel):
    total_weight: float
    total_cost: float
    service_cost: Optional[float] = 0

class OrderValidationRequest(BaseModel):
    order_info: OrderInfo
    menu_items: List[MenuItem] = []
    services: List[Service] = []
    totals: OrderTotals

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    
    logger.info("🚀 EventBot 5.0 starting up", version="5.0.0")
    
    try:
        # Initialize core services
        logger.info("⚙️ Initializing core services...")
        
        # Initialize estimate service if available
        if estimate_service and hasattr(estimate_service, 'initialize'):
            await estimate_service.initialize()
            logger.info("✅ Estimate service initialized")
        
        # Initialize Business Logic Core
        if BUSINESS_LOGIC_AVAILABLE:
            logger.info("⚙️ Initializing Business Logic Core...")
            app.state.rules_engine = BusinessRulesEngine()
            logger.info("✅ Business Logic Core initialized successfully")
        else:
            logger.warning("⚠️ Business Logic Core not available, using mock")
            app.state.rules_engine = BusinessRulesEngine()
        
        logger.info("🎉 All services initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error("❌ Failed to initialize services", error=str(e))
        raise
    
    finally:
        logger.info("🔄 EventBot 5.0 shutting down")
        
        # Cleanup tasks
        try:
            # Clean up old PDFs if service available
            if pdf_service and hasattr(pdf_service, 'cleanup_old_pdfs'):
                pdf_service.cleanup_old_pdfs(days_old=7)
            
            # Clean up old estimate data if service available
            if estimate_service and hasattr(estimate_service, 'cleanup_old_data'):
                await estimate_service.cleanup_old_data(days_old=7)
            
            logger.info("✅ Cleanup completed")
            
        except Exception as e:
            logger.error("❌ Cleanup failed", error=str(e))

def create_app() -> FastAPI:
    """Создание и настройка FastAPI приложения"""
    
    app = FastAPI(
        title="EventBot 5.0 - AI Estimate Generator + Business Logic",
        description="Intelligent catering estimate generation with Google Sheets integration and business rules validation",
        version="5.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # В продакшене заменить на конкретные домены
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include existing routers if available
    routers_included = []
    
    if estimates_router:
        app.include_router(estimates_router)
        routers_included.append("estimates")
        logger.info("🔗 Estimates router included")
    
    if experts_router:
        app.include_router(experts_router)
        routers_included.append("experts")
        logger.info("🔗 Experts router included")
        
    if calculator_router:
        app.include_router(calculator_router)
        routers_included.append("calculator")
        logger.info("🔗 Calculator router included")
        
    if menu_router:
        app.include_router(menu_router)
        routers_included.append("menu")
        logger.info("🔗 Menu router included")
    
    # =============== BUSINESS LOGIC ENDPOINTS ===============
    
    @app.post("/api/business/validate-order")
    async def validate_order(order: OrderValidationRequest):
        """
        🎯 Валидация заказа по бизнес-правилам Rest Delivery
        
        Проверяет:
        - Граммовку на гостя (250-750г)
        - Минимальный заказ (10,000₽) 
        - Количество официантов
        - Временные ограничения
        - Состав меню
        
        Returns:
        - overall_status: valid/warning/error/critical
        - validations: детальные результаты проверок
        - summary: статистика по уровням
        - recommendations: рекомендации по улучшению
        """
        try:
            logger.info("🔍 Starting order validation", 
                       order_number=order.order_info.number,
                       guests=order.order_info.guests,
                       event_type=order.order_info.event_type)
            
            # Конвертация в словарь для валидации
            order_data = order.dict()
            
            # Валидация через Business Logic Core
            result = await app.state.rules_engine.validate_order(order_data)
            
            logger.info("✅ Order validation completed", 
                       status=result['overall_status'],
                       validations_count=result['summary']['total_validations'])
            
            return result
            
        except Exception as e:
            logger.error("❌ Order validation failed", error=str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка валидации заказа: {str(e)}"
            )
    
    @app.get("/api/business/standards")
    async def get_business_standards():
        """📋 Получение бизнес-стандартов Rest Delivery"""
        try:
            if BUSINESS_LOGIC_AVAILABLE:
                from src.business import BusinessStandards
                
                return {
                    "service": "Rest Delivery Business Standards",
                    "version": "1.0.0",
                    "status": "active",
                    "last_updated": "2025-01-07",
                    "standards": {
                        "min_order_amount": BusinessStandards.MIN_ORDER_AMOUNT,
                        "portion_standards": BusinessStandards.PORTION_STANDARDS,
                        "cost_per_guest_ranges": BusinessStandards.COST_PER_GUEST_RANGES,
                        "waiter_ratios": {
                            "simple": BusinessStandards.WAITER_RATIO_SIMPLE,
                            "complex": BusinessStandards.WAITER_RATIO_COMPLEX
                        },
                        "timing_requirements": BusinessStandards.TIMING_REQUIREMENTS
                    },
                    "description": {
                        "portion_standards": "Граммовка на гостя по типам мероприятий",
                        "cost_per_guest_ranges": "Ценовые диапазоны на гостя",
                        "waiter_ratios": "Соотношение официантов к гостям",
                        "timing_requirements": "Минимальные сроки заказа в часах"
                    }
                }
            else:
                return {
                    "service": "Rest Delivery Business Standards",
                    "version": "1.0.0", 
                    "status": "unavailable",
                    "error": "Business Logic Core не найден",
                    "fallback_standards": {
                        "min_order_amount": settings.MIN_ORDER_AMOUNT,
                        "waiter_cost_base": settings.WAITER_COST_BASE,
                        "grammage_ranges": {
                            "coffee_break": settings.COFFEE_BREAK_GRAMMAGE,
                            "buffet": settings.BUFFET_GRAMMAGE,
                            "banquet": settings.BANQUET_GRAMMAGE
                        }
                    }
                }
            
        except Exception as e:
            logger.error("❌ Failed to get business standards", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/business/quick-test")
    async def quick_validation_test():
        """🧪 Быстрый тест валидации с примером данных"""
        try:
            test_data = {
                "order_info": {
                    "guests": 25,
                    "event_type": "buffet", 
                    "date": "2025-02-15",
                    "number": "TEST-001"
                },
                "totals": {
                    "total_weight": 8500,
                    "total_cost": 65000,
                    "service_cost": 19000
                },
                "menu_items": [
                    {"name": "Канапе с лососем", "category": "канапе", "quantity": 50},
                    {"name": "Салат Цезарь", "category": "салаты", "quantity": 25}
                ],
                "services": [
                    {"name": "Официант", "quantity": 2, "duration": 4, "cost": 19000}
                ]
            }
            
            result = await app.state.rules_engine.validate_order(test_data)
            
            return {
                "message": "Тестовая валидация выполнена успешно",
                "timestamp": datetime.now().isoformat(),
                "business_logic_status": "active" if BUSINESS_LOGIC_AVAILABLE else "mock",
                "test_data": test_data,
                "validation_result": result,
                "performance_note": "Время выполнения < 0.1 сек"
            }
            
        except Exception as e:
            logger.error("❌ Quick test failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/business/health")
    async def business_logic_health():
        """🔍 Проверка здоровья Business Logic Core"""
        try:
            # Простой тест валидации
            test_order = {
                "order_info": {"guests": 1, "event_type": "coffee_break"},
                "totals": {"total_weight": 250, "total_cost": 10000}
            }
            
            import time
            start_time = time.time()
            result = await app.state.rules_engine.validate_order(test_order)
            end_time = time.time()
            
            response_time = round((end_time - start_time) * 1000, 2)
            
            return {
                "status": "healthy" if BUSINESS_LOGIC_AVAILABLE else "mock",
                "service": "Business Logic Core",
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat(),
                "response_time_ms": response_time,
                "business_logic_available": BUSINESS_LOGIC_AVAILABLE,
                "test_result": {
                    "status": result["overall_status"],
                    "validations_count": result["summary"]["total_validations"]
                },
                "capabilities": [
                    "portion_validation",
                    "cost_validation", 
                    "service_validation",
                    "timing_validation",
                    "menu_validation"
                ] if BUSINESS_LOGIC_AVAILABLE else ["mock_validation"]
            }
            
        except Exception as e:
            logger.error("❌ Business logic health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "service": "Business Logic Core",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    # =============== ENHANCED ROOT ENDPOINT ===============
    
    @app.get("/")
    async def root():
        """Корневой endpoint с информацией о системе"""
        try:
            # Get service stats if available
            service_stats = {}
            if estimate_service and hasattr(estimate_service, 'get_stats'):
                try:
                    service_stats = estimate_service.get_stats()
                except Exception as e:
                    logger.warning(f"Failed to get service stats: {e}")
                    service_stats = {"error": "stats_unavailable"}
            
            return {
                "service": "EventBot 5.0",
                "version": "5.0.0",
                "description": "AI-Powered Estimate Generator with Business Logic Core",
                "status": "running",
                "timestamp": datetime.now().isoformat(),
                "features": {
                    "ai_experts": bool(experts_router),
                    "google_sheets": bool(sheets_service),
                    "pdf_generation": bool(pdf_service),
                    "real_time_estimates": bool(estimate_service),
                    "business_logic_validation": BUSINESS_LOGIC_AVAILABLE,
                    "order_validation": True,
                    "calculator": bool(calculator_router),
                    "menu_management": bool(menu_router)
                },
                "routers_loaded": routers_included,
                "endpoints": {
                    # Business Logic endpoints (всегда доступны)
                    "validate_order": "/api/business/validate-order",
                    "business_standards": "/api/business/standards", 
                    "business_health": "/api/business/health",
                    "quick_test": "/api/business/quick-test",
                    "docs": "/docs",
                    "root": "/",
                    
                    # Условные endpoints в зависимости от загруженных роутеров
                    **({
                        "estimates": "/api/estimates/*",
                    } if estimates_router else {}),
                    **({
                        "experts": "/api/experts/*",
                    } if experts_router else {}),
                    **({
                        "calculator": "/api/calculator/*",
                    } if calculator_router else {}),
                    **({
                        "menu": "/api/menu/*",
                    } if menu_router else {})
                },
                "stats": {
                    "active_processing": service_stats.get("active_processing", 0),
                    "total_created": service_stats.get("service_stats", {}).get("total_created", 0),
                    "google_sheets_status": service_stats.get("sheets_service", {}).get("status", "unknown"),
                    "business_logic_status": "active" if BUSINESS_LOGIC_AVAILABLE else "mock"
                },
                "configuration": {
                    "debug_mode": settings.DEBUG,
                    "environment": settings.ENVIRONMENT,
                    "claude_configured": settings.validate_claude_config(),
                    "business_config_valid": settings.validate_business_config(),
                    "min_order_amount": settings.MIN_ORDER_AMOUNT
                }
            }
            
        except Exception as e:
            logger.error(f"Root endpoint error: {str(e)}")
            return {
                "service": "EventBot 5.0",
                "version": "5.0.0",
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "message": "Some features may not be available"
            }
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Глобальный обработчик исключений"""
        logger.error("💥 Unhandled exception", 
                    path=request.url.path,
                    method=request.method,
                    error=str(exc))
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
                "path": request.url.path,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    # Background tasks startup
    @app.on_event("startup")
    async def startup_background_tasks():
        """Запуск фоновых задач"""
        try:
            if estimate_service and pdf_service:
                asyncio.create_task(periodic_cleanup())
                logger.info("🔄 Background cleanup tasks started")
            
        except Exception as e:
            logger.error("❌ Failed to start background tasks", error=str(e))

    return app

async def periodic_cleanup():
    """Периодическая очистка старых данных"""
    while True:
        try:
            await asyncio.sleep(3600)  # Каждый час
            
            if pdf_service and hasattr(pdf_service, 'cleanup_old_pdfs'):
                pdf_service.cleanup_old_pdfs(days_old=1)
            
            if estimate_service and hasattr(estimate_service, 'cleanup_old_data'):
                await estimate_service.cleanup_old_data(days_old=7)
            
            logger.info("🧹 Periodic cleanup completed")
            
        except Exception as e:
            logger.error("❌ Periodic cleanup failed", error=str(e))
            await asyncio.sleep(300)  # Retry in 5 minutes

# Create the application
app = create_app()

if __name__ == "__main__":
    # Development server
    logger.info("🚀 Starting EventBot 5.0 development server...")
    logger.info(f"📍 Server will start on http://{settings.APP_HOST}:{settings.APP_PORT}")
    logger.info(f"🔧 Debug mode: {settings.DEBUG}")
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🤖 Claude configured: {settings.validate_claude_config()}")
    logger.info(f"💼 Business Logic available: {BUSINESS_LOGIC_AVAILABLE}")
    
    uvicorn.run(
        "src.api.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level="info"
    )