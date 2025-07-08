"""
Expert Orchestrator - Координатор работы всех Claude экспертов
"""
import asyncio
from typing import Dict, Any, Optional, List
from src.experts.conversation_manager import conversation_manager
from src.experts.menu_expert import menu_expert
from src.experts.grammage_controller import grammage_controller
from src.experts.budget_optimizer import budget_optimizer
from src.experts.sheets_formatter import sheets_formatter
from src.utils.logger import logger

class ExpertOrchestrator:
    """Координатор всех экспертов для создания сметы"""
    
    def __init__(self):
        self.conversation_manager = conversation_manager
        self.menu_expert = menu_expert
        self.grammage_controller = grammage_controller
        self.budget_optimizer = budget_optimizer
        self.sheets_formatter = sheets_formatter
    
    async def process_estimate_request(self, user_input: str, 
                                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Полный процесс создания сметы через всех экспертов"""
        
        session_id = context.get("session_id", "unknown") if context else "unknown"
        
        logger.info("Starting estimate generation process", 
                   session_id=session_id,
                   input_length=len(user_input))
        
        try:
            # Этап 1: Анализ запроса (ConversationManager)
            logger.info("Stage 1: Conversation analysis", session_id=session_id)
            
            # Правильно передаем контекст
            conversation_context = None
            if context and "conversation_history" in context:
                conversation_context = context["conversation_history"]
            
            conversation_analysis = await self.conversation_manager.analyze_request(
                user_input, 
                conversation_context
            )
            
            # Улучшенная проверка достаточности информации
            if not self._has_sufficient_info(conversation_analysis, user_input):
                response = await self.conversation_manager.generate_response(conversation_analysis, context)
                return {
                    "stage": "conversation",
                    "success": False,
                    "needs_more_info": True,
                    "response": response,
                    "analysis": conversation_analysis
                }
            
            # Этап 2: Подбор меню (MenuExpert)
            logger.info("Stage 2: Menu selection", session_id=session_id)
            requirements = self._extract_requirements(conversation_analysis, context)
            menu_selection = await self.menu_expert.select_menu(requirements)
            
            # Этап 3: Валидация граммовки (GrammageController)
            logger.info("Stage 3: Portion validation", session_id=session_id)
            event_context = self._extract_event_context(conversation_analysis, context)
            grammage_validation = await self.grammage_controller.validate_portions(menu_selection, event_context)
            
            # Этап 4: Оптимизация бюджета (BudgetOptimizer)
            budget_optimization = None
            target_budget = self._extract_budget(conversation_analysis, context)
            
            if target_budget:
                logger.info("Stage 4: Budget optimization", session_id=session_id, target_budget=target_budget)
                budget_optimization = await self.budget_optimizer.optimize_budget(
                    menu_selection, target_budget, event_context
                )
                
                # Используем оптимизированное меню если бюджет достижим
                if budget_optimization.get("optimization_result", {}).get("achievable"):
                    menu_selection = budget_optimization.get("final_menu", menu_selection)
            
            # Этап 5: Форматирование для Google Sheets (SheetsFormatter)
            logger.info("Stage 5: Sheets formatting", session_id=session_id)
            
            # Подготавливаем данные об обслуживании если нужно
            service_options = self._prepare_service_options(conversation_analysis, context)
            
            sheets_data = await self.sheets_formatter.format_for_sheets(
                menu_selection, 
                event_context,
                service_options
            )
            
            logger.info("Estimate generation completed successfully", 
                       session_id=session_id,
                       total_cost=sheets_data.get("totals", {}).get("total_cost"))
            
            return {
                "stage": "completed",
                "success": True,
                "conversation_analysis": conversation_analysis,
                "menu_selection": menu_selection,
                "grammage_validation": grammage_validation,
                "budget_optimization": budget_optimization,
                "sheets_data": sheets_data,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error("Estimate generation failed", 
                        session_id=session_id,
                        error=str(e),
                        stage="orchestrator")
            
            return {
                "stage": "error",
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
    
    async def process_iterative_refinement(self, 
                                         initial_result: Dict[str, Any],
                                         refinement_request: str) -> Dict[str, Any]:
        """Итеративное улучшение сметы на основе запросов клиента"""
        
        session_id = initial_result.get("session_id", "unknown")
        
        logger.info("Starting iterative refinement", 
                   session_id=session_id,
                   refinement=refinement_request)
        
        try:
            # Анализируем запрос на изменения
            refinement_analysis = await self.conversation_manager.analyze_request(
                refinement_request, 
                context={"existing_estimate": initial_result}
            )
            
            # Определяем какие эксперты нужно привлечь
            current_menu = initial_result.get("menu_selection", {})
            event_context = initial_result.get("conversation_analysis", {}).get("analysis", {})
            
            # Если нужны изменения в меню
            if "меню" in refinement_request.lower() or "позиции" in refinement_request.lower():
                logger.info("Refining menu selection", session_id=session_id)
                
                # Обновляем требования на основе запроса
                updated_requirements = self._update_requirements_from_refinement(
                    refinement_analysis, 
                    self._extract_requirements(initial_result.get("conversation_analysis", {}))
                )
                
                current_menu = await self.menu_expert.select_menu(updated_requirements)
                
                # Переваlidируем граммовку
                grammage_validation = await self.grammage_controller.validate_portions(
                    current_menu, event_context
                )
            
            # Если нужна оптимизация бюджета
            budget_optimization = None
            if "бюджет" in refinement_request.lower() or "цена" in refinement_request.lower():
                logger.info("Refining budget optimization", session_id=session_id)
                
                # Извлекаем новый целевой бюджет из запроса
                new_budget = self._extract_budget_from_refinement(refinement_request)
                if new_budget:
                    budget_optimization = await self.budget_optimizer.optimize_budget(
                        current_menu, new_budget, event_context
                    )
                    
                    if budget_optimization.get("optimization_result", {}).get("achievable"):
                        current_menu = budget_optimization.get("final_menu", current_menu)
            
            # Обновляем форматирование для Google Sheets
            logger.info("Updating sheets formatting", session_id=session_id)
            service_options = self._prepare_service_options(
                initial_result.get("conversation_analysis", {}), 
                {"refinement": refinement_request}
            )
            
            updated_sheets_data = await self.sheets_formatter.format_for_sheets(
                current_menu,
                event_context,
                service_options
            )
            
            logger.info("Iterative refinement completed", session_id=session_id)
            
            return {
                "stage": "refined",
                "success": True,
                "refinement_analysis": refinement_analysis,
                "updated_menu": current_menu,
                "updated_grammage_validation": grammage_validation if 'grammage_validation' in locals() else None,
                "updated_budget_optimization": budget_optimization,
                "updated_sheets_data": updated_sheets_data,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error("Iterative refinement failed", 
                        session_id=session_id,
                        error=str(e))
            
            return {
                "stage": "refinement_error",
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
    
    def _has_sufficient_info(self, analysis: Dict[str, Any], user_input: str) -> bool:
        """Улучшенная проверка достаточности информации для создания сметы"""
        detected = analysis.get("analysis", {})
        
        # Базовые требования
        has_event_type = detected.get("detected_event_type") not in [None, "unknown"]
        has_guests = detected.get("detected_guests") is not None
        has_confidence = detected.get("confidence", 0) > 0.6
        
        # Дополнительные критерии готовности
        has_details = len(user_input) > 50  # Достаточно детальный запрос
        has_budget_or_menu = (
            detected.get("detected_budget") is not None or
            any(word in user_input.lower() for word in ['канапе', 'сэндвич', 'меню', 'блюда'])
        )
        
        # Принудительное создание если есть ключевые слова детализации
        force_create_keywords = [
            'хотим', 'нужен', 'планируем', 'заказать', 'подготовить',
            'конкретно', 'именно', 'точно', 'создать смету'
        ]
        has_intent = any(keyword in user_input.lower() for keyword in force_create_keywords)
        
        # Основная логика: если есть тип, гости и уверенность > 60%
        basic_ready = has_event_type and has_guests and has_confidence
        
        # Расширенная логика: если есть намерение и минимальные детали
        enhanced_ready = has_intent and has_guests and (has_budget_or_menu or has_details)
        
        logger.info("Sufficiency check", 
                   basic_ready=basic_ready,
                   enhanced_ready=enhanced_ready,
                   has_event_type=has_event_type,
                   has_guests=has_guests,
                   confidence=detected.get("confidence", 0))
        
        return basic_ready or enhanced_ready
    
    def _extract_requirements(self, analysis: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Извлечение требований для MenuExpert"""
        detected = analysis.get("analysis", {})
        
        # Маппинг типов событий
        event_type_mapping = {
            "coffee_break": "кофе-брейк",
            "buffet": "фуршет", 
            "banquet": "банкет"
        }
        
        event_type = event_type_mapping.get(
            detected.get("detected_event_type", "buffet"), 
            "фуршет"
        )
        
        return {
            "event_type": event_type,
            "guests": detected.get("detected_guests", 20),
            "budget": detected.get("detected_budget"),
            "preferences": context.get("preferences", []) if context else [],
            "restrictions": context.get("restrictions", []) if context else []
        }
    
    def _extract_event_context(self, analysis: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Извлечение контекста мероприятия"""
        detected = analysis.get("analysis", {})
        
        event_type_mapping = {
            "coffee_break": "кофе-брейк",
            "buffet": "фуршет",
            "banquet": "банкет"
        }
        
        event_type = event_type_mapping.get(
            detected.get("detected_event_type", "buffet"),
            "фуршет"
        )
        
        return {
            "event_type": event_type,
            "guests": detected.get("detected_guests", 20),
            "date": detected.get("detected_date"),
            "location": detected.get("detected_location"),
            "needs_service": detected.get("needs_service", False),
            "duration": context.get("duration") if context else None
        }
    
    def _extract_budget(self, analysis: Dict[str, Any], context: Dict[str, Any] = None) -> Optional[int]:
        """Извлечение бюджета"""
        detected = analysis.get("analysis", {})
        return detected.get("detected_budget") or (context.get("budget") if context else None)
    
    def _prepare_service_options(self, analysis: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Подготовка опций обслуживания"""
        detected = analysis.get("analysis", {})
        needs_service = detected.get("needs_service", False)
        guests = detected.get("detected_guests", 20)
        
        if not needs_service:
            return {}
        
        # Базовый расчет обслуживания
        waiters_needed = max(1, guests // 20)  # Упрощенный расчет
        
        return {
            "waiters": {
                "count": waiters_needed,
                "hours": 6,
                "cost_per_waiter": 9500
            },
            "delivery": {
                "needed": True,
                "cost": 0  # В пределах МКАД
            }
        }
    
    def _update_requirements_from_refinement(self, refinement_analysis: Dict[str, Any], 
                                           current_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Обновление требований на основе запроса на уточнение"""
        detected = refinement_analysis.get("analysis", {})
        
        # Обновляем только те поля, которые были изменены
        updated_requirements = current_requirements.copy()
        
        if detected.get("detected_event_type") and detected.get("detected_event_type") != "unknown":
            updated_requirements["event_type"] = detected.get("detected_event_type")
        
        if detected.get("detected_guests"):
            updated_requirements["guests"] = detected.get("detected_guests")
        
        if detected.get("detected_budget"):
            updated_requirements["budget"] = detected.get("detected_budget")
        
        return updated_requirements
    
    def _extract_budget_from_refinement(self, refinement_request: str) -> Optional[int]:
        """Извлечение нового бюджета из запроса на уточнение"""
        import re
        
        # Простое извлечение числа из текста (можно улучшить)
        budget_match = re.search(r'(\d{2,6})', refinement_request)
        if budget_match:
            return int(budget_match.group(1))
        
        return None

# Глобальный экземпляр оркестратора
expert_orchestrator = ExpertOrchestrator()