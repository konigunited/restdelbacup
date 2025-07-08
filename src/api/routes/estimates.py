"""
API endpoints for estimate generation and management
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import io

from src.services.estimate_service import estimate_service
from src.services.sheets_service import sheets_service
from src.services.pdf_service import pdf_service
from src.utils.logger import logger

router = APIRouter(prefix="/api/estimates", tags=["Estimates"])

# Pydantic модели
class EstimateRequest(BaseModel):
    user_input: str = Field(..., description="Пользовательский запрос на создание сметы")
    context: Optional[Dict[str, Any]] = Field(None, description="Дополнительный контекст")

class UpdateEstimateRequest(BaseModel):
    sheet_id: str = Field(..., description="ID Google Sheets документа")
    changes: Dict[str, Any] = Field(..., description="Изменения для применения")

class EstimateVariationRequest(BaseModel):
    session_id: str = Field(..., description="ID базовой сметы")
    variations: List[Dict[str, Any]] = Field(..., description="Список вариаций")

# Основные endpoints
@router.post("/create")
async def create_estimate(request: EstimateRequest):
    """Создание полной сметы от запроса до Google Sheets"""
    try:
        logger.info("Creating estimate via API", 
                   input_length=len(request.user_input),
                   has_context=request.context is not None)
        
        result = await estimate_service.create_complete_estimate(
            request.user_input,
            request.context
        )
        
        return result
        
    except Exception as e:
        logger.error("Estimate creation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{session_id}")
async def get_estimate_status(session_id: str):
    """Получение статуса обработки сметы"""
    try:
        status = estimate_service.get_processing_status(session_id)
        if status:
            return {
                "found": True,
                "status": status
            }
        else:
            # Проверяем в завершенных
            completed = await estimate_service.get_estimate_details(session_id)
            if completed:
                return {
                    "found": True,
                    "status": "completed",
                    "details": completed
                }
            else:
                raise HTTPException(status_code=404, detail="Session not found")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Status check failed", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update")
async def update_estimate(request: UpdateEstimateRequest):
    """Обновление существующей сметы"""
    try:
        result = await estimate_service.update_estimate(
            request.sheet_id,
            request.changes
        )
        return result
        
    except Exception as e:
        logger.error("Estimate update failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/details/{identifier}")
async def get_estimate_details(identifier: str):
    """Получение детальной информации о смете"""
    try:
        details = await estimate_service.get_estimate_details(identifier)
        if details:
            return details
        else:
            raise HTTPException(status_code=404, detail="Estimate not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get estimate details", identifier=identifier, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Google Sheets операции
@router.get("/sheet/{sheet_id}")
async def get_estimate_data(sheet_id: str):
    """Получение данных сметы из Google Sheets"""
    try:
        data = await sheets_service.get_estimate_data(sheet_id)
        if data:
            return data
        else:
            raise HTTPException(status_code=404, detail="Sheet not found or empty")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get estimate data", sheet_id=sheet_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sheet/{sheet_id}/url")
async def get_sheet_url(sheet_id: str):
    """Получение ссылки на Google Sheets документ"""
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit?usp=sharing"
        return {
            "sheet_id": sheet_id,
            "url": url,
            "edit_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
        }
        
    except Exception as e:
        logger.error("Failed to generate sheet URL", sheet_id=sheet_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# PDF операции
@router.get("/pdf/{sheet_id}")
async def download_estimate_pdf(sheet_id: str, background_tasks: BackgroundTasks):
    """Скачивание PDF сметы"""
    try:
        # Получаем информацию о смете для имени файла
        estimate_data = await sheets_service.get_estimate_data(sheet_id)
        order_number = "estimate"
        
        # Пытаемся извлечь номер заказа из данных
        if estimate_data and "data" in estimate_data:
            for row in estimate_data["data"]:
                if row and len(row) > 1 and "P-" in str(row[1]):
                    order_number = str(row[1])
                    break
        
        # Генерируем PDF
        pdf_path = await pdf_service.generate_pdf_from_sheet(sheet_id, order_number)
        
        if not pdf_path:
            raise HTTPException(status_code=500, detail="Failed to generate PDF")
        
        path = Path(pdf_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="PDF file not found")
        
        # Планируем удаление временного файла через 1 час
        background_tasks.add_task(
            lambda: Path(pdf_path).unlink(missing_ok=True)
        )
        
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"estimate_{order_number}.pdf",
            headers={
                "Content-Disposition": f"attachment; filename=estimate_{order_number}.pdf"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("PDF download failed", sheet_id=sheet_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pdf/{sheet_id}/metadata")
async def get_pdf_metadata(sheet_id: str):
    """Получение метаданных PDF файла"""
    try:
        # Сначала найдем PDF файл для этого sheet_id
        pdf_files = list(pdf_service.output_dir.glob(f"*{sheet_id}*.pdf"))
        
        if not pdf_files:
            return {"exists": False, "message": "PDF not found for this sheet"}
        
        # Берем самый новый файл
        latest_pdf = max(pdf_files, key=lambda p: p.stat().st_mtime)
        metadata = await pdf_service.get_pdf_metadata(str(latest_pdf))
        
        return metadata
        
    except Exception as e:
        logger.error("PDF metadata failed", sheet_id=sheet_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Вариации смет
@router.post("/variations")
async def create_estimate_variations(request: EstimateVariationRequest):
    """Создание вариаций сметы"""
    try:
        base_estimate = await estimate_service.get_estimate_details(request.session_id)
        
        if not base_estimate:
            raise HTTPException(status_code=404, detail="Base estimate not found")
        
        variations = await estimate_service.create_estimate_variations(
            base_estimate,
            request.variations
        )
        
        return {
            "base_session_id": request.session_id,
            "variations_count": len(variations),
            "variations": variations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Variations creation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Списки и история
@router.get("/completed")
async def get_completed_estimates(limit: int = Query(10, ge=1, le=100)):
    """Получение списка завершенных смет"""
    try:
        estimates = estimate_service.get_completed_estimates(limit)
        return {
            "count": len(estimates),
            "estimates": estimates
        }
        
    except Exception as e:
        logger.error("Failed to get completed estimates", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active")
async def get_active_processing():
    """Получение списка активных обработок"""
    try:
        stats = estimate_service.get_stats()
        return {
            "active_count": stats["active_processing"],
            "active_sessions": stats["processing_sessions"]
        }
        
    except Exception as e:
        logger.error("Failed to get active processing", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Демо и тестирование
@router.get("/demo")
async def demo_estimate_generation():
    """Демонстрация полного процесса создания сметы"""
    try:
        demo_input = "Нужен фуршет на 25 человек, бюджет 50000 рублей, завтра в 18:00"
        demo_context = {
            "session_id": f"demo_session_{int(datetime.now().timestamp())}",
            "client_type": "demo",
            "demo": True
        }
        
        result = await estimate_service.create_complete_estimate(demo_input, demo_context)
        
        return {
            "demo": True,
            "input": demo_input,
            "context": demo_context,
            "result": result
        }
        
    except Exception as e:
        logger.error("Demo estimate failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/demo/batch")
async def demo_batch_estimates():
    """Демо создания нескольких смет подряд"""
    try:
        demo_requests = [
            "Кофе-брейк на 15 человек",
            "Фуршет на 30 человек, бюджет 60000",
            "Банкет на 50 человек с полным обслуживанием"
        ]
        
        results = []
        for i, request in enumerate(demo_requests):
            context = {
                "session_id": f"batch_demo_{i}_{int(datetime.now().timestamp())}",
                "batch_demo": True,
                "batch_index": i
            }
            
            result = await estimate_service.create_complete_estimate(request, context)
            results.append({
                "input": request,
                "result": result
            })
        
        return {
            "batch_demo": True,
            "total_estimates": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error("Batch demo failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Статистика и мониторинг
@router.get("/stats")
async def get_estimates_stats():
    """Статистика сервиса смет"""
    try:
        return estimate_service.get_stats()
        
    except Exception as e:
        logger.error("Failed to get estimates stats", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def estimates_health_check():
    """Проверка работоспособности Google Sheets интеграции"""
    try:
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "service": "estimates",
            "components": {}
        }
        
        # Проверяем EstimateService
        try:
            stats = estimate_service.get_stats()
            health_data["components"]["estimate_service"] = {
                "status": "healthy",
                "initialized": stats["initialized"],
                "active_processing": stats["active_processing"]
            }
        except Exception as e:
            health_data["components"]["estimate_service"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Проверяем Google Sheets Service
        try:
            if not sheets_service._initialized:
                await sheets_service.initialize()
            
            await sheets_service._verify_template_access()
            
            health_data["components"]["google_sheets"] = {
                "status": "healthy",
                "initialized": sheets_service._initialized,
                "template_accessible": True
            }
        except Exception as e:
            health_data["components"]["google_sheets"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Проверяем PDF Service
        try:
            pdf_stats = pdf_service.get_stats()
            health_data["components"]["pdf_service"] = {
                "status": "healthy",
                "output_directory": pdf_stats["output_directory"],
                "total_files": pdf_stats["total_files"]
            }
        except Exception as e:
            health_data["components"]["pdf_service"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Определяем общий статус
        all_healthy = all(
            comp.get("status") == "healthy" 
            for comp in health_data["components"].values()
        )
        
        health_data["status"] = "healthy" if all_healthy else "degraded"
        
        return health_data
        
    except Exception as e:
        logger.error("Estimates health check failed", error=str(e))
        return {
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Административные функции
@router.post("/admin/cleanup")
async def cleanup_old_data(days_old: int = Query(7, ge=1, le=30)):
    """Очистка старых данных (только для администраторов)"""
    try:
        await estimate_service.cleanup_old_data(days_old)
        
        return {
            "success": True,
            "message": f"Cleanup completed for data older than {days_old} days",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Cleanup failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))