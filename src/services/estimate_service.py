"""
Complete estimate generation service integrating all components
"""
import asyncio
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from src.services.expert_orchestrator import expert_orchestrator
from src.services.sheets_service import sheets_service
from src.services.pdf_service import pdf_service
from src.utils.logger import logger

class EstimateService:
    """Полный сервис создания смет от запроса до готового документа"""
    
    def __init__(self):
        self.processing_estimates = {}  # Для отслеживания процесса
        self.completed_estimates = {}   # История завершенных смет
        self._stats = {
            "total_created": 0,
            "total_failed": 0,
            "average_processing_time": 0
        }
    
    async def initialize(self):
        """Инициализация всех зависимых сервисов"""
        logger.info("Initializing EstimateService")
        
        try:
            # Инициализируем Google Sheets Service
            await sheets_service.initialize()
            
            # Проверяем expert_orchestrator (если нужно)
            # await expert_orchestrator.initialize()
            
            logger.info("EstimateService initialized successfully")
            
        except Exception as e:
            logger.error("EstimateService initialization failed", error=str(e))
            raise
    
    async def create_complete_estimate(self, user_input: str, 
                                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Полный процесс создания сметы от запроса до готового документа"""
        
        session_id = context.get("session_id") if context else f"session_{int(datetime.now().timestamp())}"
        
        logger.info("Starting complete estimate creation", 
                   session_id=session_id,
                   input_length=len(user_input))
        
        start_time = datetime.now()
        
        try:
            # Отмечаем начало обработки
            self.processing_estimates[session_id] = {
                "status": "processing",
                "stage": "analysis",
                "started_at": start_time,
                "user_input": user_input[:100] + "..." if len(user_input) > 100 else user_input
            }
            
            # Этап 1: Генерация данных сметы через экспертов
            logger.info("Stage 1: Expert analysis and menu generation", session_id=session_id)
            self.processing_estimates[session_id]["stage"] = "experts"
            
            expert_result = await expert_orchestrator.process_estimate_request(user_input, context)
            
            if not expert_result.get("success"):
                if expert_result.get("needs_more_info"):
                    return {
                        "success": False,
                        "needs_more_info": True,
                        "response": expert_result.get("response"),
                        "session_id": session_id,
                        "stage": "needs_clarification"
                    }
                else:
                    raise Exception(f"Expert analysis failed: {expert_result.get('error')}")
            
            sheets_data = expert_result["sheets_data"]
            order_number = sheets_data.get("order_info", {}).get("number", f"P-{int(datetime.now().timestamp())}")
            
            # Этап 2: Создание Google Sheets документа
            logger.info("Stage 2: Creating Google Sheets document", 
                       session_id=session_id,
                       order_number=order_number)
            self.processing_estimates[session_id]["stage"] = "sheets"
            self.processing_estimates[session_id]["order_number"] = order_number
            
            sheet_id, sheet_url = await sheets_service.create_estimate_sheet(sheets_data)
            
            # Этап 3: Генерация PDF (опционально)
            logger.info("Stage 3: Generating PDF", session_id=session_id)
            self.processing_estimates[session_id]["stage"] = "pdf"
            
            pdf_path = await pdf_service.generate_pdf_from_sheet(sheet_id, order_number)
            
            # Финализация
            completion_time = datetime.now()
            processing_duration = (completion_time - start_time).total_seconds()
            
            # Создаем результат
            result = {
                "success": True,
                "order_number": order_number,
                "session_id": session_id,
                "processing_duration": processing_duration,
                "google_sheets": {
                    "sheet_id": sheet_id,
                    "url": sheet_url,
                    "edit_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
                },
                "pdf": {
                    "generated": pdf_path is not None,
                    "path": pdf_path,
                    "download_url": f"/api/estimates/pdf/{sheet_id}" if pdf_path else None
                },
                "estimate_summary": {
                    "total_cost": sheets_data.get("totals", {}).get("total_cost", 0),
                    "guests": sheets_data.get("order_info", {}).get("guests", 0),
                    "event_type": sheets_data.get("order_info", {}).get("event_type", ""),
                    "menu_items_count": len(sheets_data.get("menu_items", [])),
                    "weight_per_guest": sheets_data.get("totals", {}).get("weight_per_guest", 0),
                    "services_count": len(sheets_data.get("services", []))
                },
                "expert_analysis": {
                    "conversation_analysis": expert_result.get("conversation_analysis", {}),
                    "grammage_validation": expert_result.get("grammage_validation", {}),
                    "budget_optimization": expert_result.get("budget_optimization", {})
                },
                "created_at": completion_time.isoformat(),
                "stage": "completed"
            }
            
            # Сохраняем в историю завершенных
            self.completed_estimates[session_id] = result
            
            # Обновляем статистику
            self._update_stats(processing_duration, success=True)
            
            logger.info("Complete estimate created successfully",
                       session_id=session_id,
                       order_number=order_number,
                       processing_duration=processing_duration,
                       total_cost=result["estimate_summary"]["total_cost"])
            
            # Убираем из обработки
            if session_id in self.processing_estimates:
                del self.processing_estimates[session_id]
            
            return result
            
        except Exception as e:
            logger.error("Complete estimate creation failed",
                        session_id=session_id,
                        error=str(e),
                        stage=self.processing_estimates.get(session_id, {}).get("stage"))
            
            # Обновляем статистику
            processing_duration = (datetime.now() - start_time).total_seconds()
            self._update_stats(processing_duration, success=False)
            
            # Убираем из обработки
            if session_id in self.processing_estimates:
                del self.processing_estimates[session_id]
            
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id,
                "processing_duration": processing_duration,
                "stage": self.processing_estimates.get(session_id, {}).get("stage", "unknown")
            }
    
    async def update_estimate(self, sheet_id: str, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Обновление существующей сметы"""
        
        try:
            logger.info("Updating estimate", sheet_id=sheet_id)
            
            # Обновляем данные через SheetsFormatter
            from src.experts.sheets_formatter import sheets_formatter
            updated_data = await sheets_formatter.update_sheets_data({}, changes)
            
            # Применяем изменения в Google Sheets
            success = await sheets_service.update_estimate_sheet(sheet_id, updated_data)
            
            if success:
                return {
                    "success": True,
                    "sheet_id": sheet_id,
                    "updated_at": datetime.now().isoformat(),
                    "changes_applied": len(changes)
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to update Google Sheets"
                }
                
        except Exception as e:
            logger.error("Estimate update failed", sheet_id=sheet_id, error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_estimate_details(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Получение деталей сметы по session_id или sheet_id"""
        
        try:
            # Проверяем в завершенных сметах
            if identifier in self.completed_estimates:
                return self.completed_estimates[identifier]
            
            # Проверяем в обрабатываемых
            if identifier in self.processing_estimates:
                return self.processing_estimates[identifier]
            
            # Пытаемся получить данные из Google Sheets
            sheet_data = await sheets_service.get_estimate_data(identifier)
            if sheet_data:
                return {
                    "source": "google_sheets",
                    "sheet_data": sheet_data,
                    "retrieved_at": datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error("Failed to get estimate details", identifier=identifier, error=str(e))
            return None
    
    async def create_estimate_variations(self, base_estimate: Dict[str, Any], 
                                       variations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Создание вариаций сметы (разные бюджеты/количества гостей)"""
        
        results = []
        
        for i, variation in enumerate(variations):
            try:
                logger.info("Creating estimate variation", variation_index=i)
                
                # Модифицируем базовую смету
                modified_input = self._apply_variation_to_input(
                    base_estimate.get("user_input", ""),
                    variation
                )
                
                # Создаем новую смету
                variation_context = {
                    "session_id": f"{base_estimate.get('session_id', 'base')}_var_{i}",
                    "variation_of": base_estimate.get("session_id"),
                    "variation_params": variation
                }
                
                result = await self.create_complete_estimate(modified_input, variation_context)
                results.append(result)
                
            except Exception as e:
                logger.error("Variation creation failed", variation_index=i, error=str(e))
                results.append({
                    "success": False,
                    "variation_index": i,
                    "error": str(e)
                })
        
        return results
    
    def _apply_variation_to_input(self, base_input: str, variation: Dict[str, Any]) -> str:
        """Применение вариации к исходному запросу"""
        
        modified_input = base_input
        
        if "budget" in variation:
            modified_input += f" Бюджет: {variation['budget']} рублей"
        
        if "guests" in variation:
            modified_input += f" Количество гостей: {variation['guests']}"
        
        if "event_type" in variation:
            modified_input += f" Тип мероприятия: {variation['event_type']}"
        
        return modified_input
    
    def _update_stats(self, processing_time: float, success: bool):
        """Обновление статистики сервиса"""
        
        if success:
            self._stats["total_created"] += 1
        else:
            self._stats["total_failed"] += 1
        
        # Обновляем среднее время обработки
        total_estimates = self._stats["total_created"] + self._stats["total_failed"]
        if total_estimates > 0:
            current_avg = self._stats["average_processing_time"]
            self._stats["average_processing_time"] = (
                (current_avg * (total_estimates - 1) + processing_time) / total_estimates
            )
    
    def get_processing_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Получение статуса обработки сметы"""
        
        if session_id in self.processing_estimates:
            status = self.processing_estimates[session_id].copy()
            # Добавляем время обработки
            if "started_at" in status:
                elapsed = (datetime.now() - status["started_at"]).total_seconds()
                status["elapsed_seconds"] = elapsed
            return status
        
        return None
    
    def get_completed_estimates(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение списка завершенных смет"""
        
        completed = list(self.completed_estimates.values())
        # Сортируем по времени создания (новые первые)
        completed.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return completed[:limit]
    
    async def cleanup_old_data(self, days_old: int = 7):
        """Очистка старых данных"""
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            # Очищаем завершенные сметы
            keys_to_remove = []
            for session_id, estimate in self.completed_estimates.items():
                created_at = datetime.fromisoformat(estimate.get("created_at", ""))
                if created_at < cutoff_date:
                    keys_to_remove.append(session_id)
            
            for key in keys_to_remove:
                del self.completed_estimates[key]
            
            # Очищаем PDF файлы
            pdf_service.cleanup_old_pdfs(days_old)
            
            logger.info("Cleanup completed", 
                       removed_estimates=len(keys_to_remove),
                       cutoff_date=cutoff_date.isoformat())
            
        except Exception as e:
            logger.error("Cleanup failed", error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика сервиса"""
        
        return {
            "service_stats": self._stats.copy(),
            "active_processing": len(self.processing_estimates),
            "completed_estimates": len(self.completed_estimates),
            "processing_sessions": list(self.processing_estimates.keys()),
            "sheets_service": sheets_service.get_stats(),
            "pdf_service": pdf_service.get_stats(),
            "initialized": True,
            "last_updated": datetime.now().isoformat()
        }

# Глобальный экземпляр сервиса
estimate_service = EstimateService()