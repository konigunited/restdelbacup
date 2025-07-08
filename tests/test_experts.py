"""
Tests for Claude experts system
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from src.experts.conversation_manager import conversation_manager
from src.experts.menu_expert import menu_expert
from src.experts.grammage_controller import grammage_controller
from src.experts.budget_optimizer import budget_optimizer
from src.experts.sheets_formatter import sheets_formatter
from src.services.expert_orchestrator import expert_orchestrator

@pytest.mark.asyncio
class TestConversationManager:
    """Тесты для ConversationManager"""
    
    async def test_analyze_simple_request(self):
        """Тест анализа простого запроса"""
        user_input = "Нужен фуршет на 20 человек на завтра"
        
        with patch('src.services.claude_service.claude_service.send_structured_request') as mock_claude:
            mock_claude.return_value = {
                "analysis": {
                    "detected_event_type": "buffet",
                    "detected_guests": 20,
                    "detected_budget": None,
                    "detected_date": "завтра",
                    "detected_location": None,
                    "needs_service": None,
                    "confidence": 0.9
                },
                "missing_info": ["адрес доставки", "бюджет"],
                "questions": ["Уточните адрес доставки", "Какой у вас бюджет?"],
                "recommendations": ["Рекомендуем фуршет на 20 человек"],
                "next_step": "Уточнить детали доставки и бюджет"
            }
            
            result = await conversation_manager.analyze_request(user_input)
            
            assert result["analysis"]["detected_event_type"] == "buffet"
            assert result["analysis"]["detected_guests"] == 20
            assert result["analysis"]["confidence"] == 0.9
            assert "адрес доставки" in result["missing_info"]
            assert mock_claude.called
    
    async def test_analyze_complex_request(self):
        """Тест анализа сложного запроса"""
        user_input = "Организуем корпоратив на 50 человек, бюджет 100000 рублей, нужны официанты"
        
        with patch('src.services.claude_service.claude_service.send_structured_request') as mock_claude:
            mock_claude.return_value = {
                "analysis": {
                    "detected_event_type": "banquet",
                    "detected_guests": 50,
                    "detected_budget": 100000,
                    "needs_service": True,
                    "confidence": 0.95
                },
                "missing_info": ["дата", "адрес"],
                "questions": ["Когда планируется мероприятие?"],
                "recommendations": ["Банкет с полным обслуживанием"],
                "next_step": "Подобрать меню"
            }
            
            result = await conversation_manager.analyze_request(user_input)
            
            assert result["analysis"]["detected_event_type"] == "banquet"
            assert result["analysis"]["detected_guests"] == 50
            assert result["analysis"]["detected_budget"] == 100000
            assert result["analysis"]["needs_service"] == True
    
    async def test_generate_response(self):
        """Тест генерации ответа клиенту"""
        analysis = {
            "analysis": {
                "detected_event_type": "buffet",
                "detected_guests": 25,
                "confidence": 0.8
            },
            "questions": ["Уточните бюджет"],
            "recommendations": ["Фуршет на 25 человек"]
        }
        
        with patch('src.services.claude_service.claude_service.send_message') as mock_claude:
            mock_claude.return_value = MagicMock(
                content="Отлично! Фуршет на 25 человек - прекрасный выбор. Уточните, пожалуйста, ваш бюджет?"
            )
            
            response = await conversation_manager.generate_response(analysis)
            
            assert "фуршет" in response.lower()
            assert "25" in response
            assert mock_claude.called

@pytest.mark.asyncio
class TestMenuExpert:
    """Тесты для MenuExpert"""
    
    async def test_menu_selection_buffet(self):
        """Тест подбора меню для фуршета"""
        requirements = {
            "event_type": "buffet",
            "guests": 20,
            "budget": 30000
        }
        
        with patch('src.services.claude_service.claude_service.send_structured_request') as mock_claude:
            mock_claude.return_value = {
                "selected_items": [
                    {
                        "id": "1015599",
                        "name": "Антипасти с черри",
                        "weight": 21,
                        "price": 100,
                        "quantity": 20,
                        "total_weight": 420,
                        "total_price": 2000,
                        "reason": "Классические канапе для фуршета"
                    },
                    {
                        "id": "789",
                        "name": "Брускетта с бабаганушом",
                        "weight": 36,
                        "price": 105,
                        "quantity": 15,
                        "total_weight": 540,
                        "total_price": 1575,
                        "reason": "Сытная позиция"
                    }
                ],
                "menu_summary": {
                    "total_weight": 960,
                    "total_price": 3575,
                    "weight_per_guest": 48,
                    "price_per_guest": 178.75
                },
                "balance_analysis": {
                    "appetizers_percent": 45,
                    "main_percent": 40,
                    "desserts_percent": 15,
                    "balance_score": 8.5
                },
                "recommendations": ["Добавить десерты"]
            }
            
            result = await menu_expert.select_menu(requirements)
            
            assert len(result["selected_items"]) == 2
            assert result["menu_summary"]["total_price"] > 0
            assert result["menu_summary"]["weight_per_guest"] > 0
            assert result["balance_analysis"]["balance_score"] > 7
            assert mock_claude.called
    
    async def test_fallback_menu(self):
        """Тест fallback меню при ошибке"""
        requirements = {"guests": 15}
        
        # Симулируем ошибку Claude API
        with patch('src.services.claude_service.claude_service.send_structured_request') as mock_claude:
            mock_claude.side_effect = Exception("API Error")
            
            result = await menu_expert.select_menu(requirements)
            
            # Проверяем что fallback сработал
            assert "selected_items" in result
            assert len(result["selected_items"]) > 0
            assert result["menu_summary"]["total_weight"] == 21 * 15

@pytest.mark.asyncio
class TestGrammageController:
    """Тесты для GrammageController"""
    
    async def test_validate_optimal_portions(self):
        """Тест валидации оптимальной граммовки"""
        menu_data = {
            "menu_summary": {
                "total_weight": 7000,
                "total_price": 25000
            }
        }
        event_context = {
            "event_type": "buffet",
            "guests": 20
        }
        
        with patch('src.services.claude_service.claude_service.send_structured_request') as mock_claude:
            mock_claude.return_value = {
                "validation_result": {
                    "status": "optimal",
                    "weight_per_guest": 350,
                    "standard_range": [250, 423],
                    "compliance_score": 9.5
                },
                "warnings": [],
                "analysis": {
                    "distribution": {
                        "appetizers_weight": 2800,
                        "main_dishes_weight": 2800,
                        "desserts_weight": 1400
                    },
                    "balance_issues": [],
                    "portion_adequacy": "достаточно"
                },
                "recommendations": []
            }
            
            result = await grammage_controller.validate_portions(menu_data, event_context)
            
            assert result["validation_result"]["status"] == "optimal"
            assert result["validation_result"]["weight_per_guest"] == 350
            assert result["validation_result"]["compliance_score"] > 9
            assert len(result["warnings"]) == 0
    
    async def test_validate_insufficient_portions(self):
        """Тест валидации недостаточной граммовки"""
        menu_data = {
            "menu_summary": {
                "total_weight": 3000,  # Недостаточно
                "total_price": 15000
            }
        }
        event_context = {
            "event_type": "buffet",
            "guests": 20
        }
        
        with patch('src.services.claude_service.claude_service.send_structured_request') as mock_claude:
            mock_claude.return_value = {
                "validation_result": {
                    "status": "critical",
                    "weight_per_guest": 150,
                    "standard_range": [250, 423],
                    "compliance_score": 3.0
                },
                "warnings": [
                    {
                        "level": "critical",
                        "message": "⚠️ КРИТИЧНО: Недостаточно еды для гостей",
                        "recommendation": "Добавить больше позиций"
                    }
                ],
                "recommendations": [
                    {
                        "action": "add",
                        "item_type": "канапе",
                        "reason": "Увеличить граммовку",
                        "expected_improvement": "Довести до 250г на гостя"
                    }
                ]
            }
            
            result = await grammage_controller.validate_portions(menu_data, event_context)
            
            assert result["validation_result"]["status"] == "critical"
            assert result["validation_result"]["weight_per_guest"] == 150
            assert len(result["warnings"]) > 0
            assert result["warnings"][0]["level"] == "critical"

@pytest.mark.asyncio
class TestBudgetOptimizer:
    """Тесты для BudgetOptimizer"""
    
    async def test_budget_optimization_achievable(self):
        """Тест успешной оптимизации бюджета"""
        current_menu = {
            "menu_summary": {
                "total_price": 35000,
                "total_weight": 8000
            },
            "selected_items": [
                {"id": "1", "name": "Дорогие канапе", "price": 200, "quantity": 20}
            ]
        }
        target_budget = 30000
        event_context = {"guests": 20, "event_type": "buffet"}
        
        with patch('src.services.claude_service.claude_service.send_structured_request') as mock_claude:
            mock_claude.return_value = {
                "optimization_result": {
                    "achievable": True,
                    "optimized_price": 29500,
                    "savings": 5500,
                    "savings_percent": 15.7
                },
                "changes": [
                    {
                        "type": "replace",
                        "original_item": {"id": "1", "name": "Дорогие канапе", "price": 200},
                        "new_item": {"id": "2", "name": "Стандартные канапе", "price": 150},
                        "savings": 1000,
                        "justification": "Замена на более доступный аналог",
                        "quality_impact": "Минимальное влияние на качество"
                    }
                ],
                "final_menu": {
                    "total_price": 29500,
                    "total_weight": 8000,
                    "weight_per_guest": 400,
                    "price_per_guest": 1475
                },
                "recommendations": ["Оптимизация успешна"]
            }
            
            result = await budget_optimizer.optimize_budget(current_menu, target_budget, event_context)
            
            assert result["optimization_result"]["achievable"] == True
            assert result["optimization_result"]["optimized_price"] <= target_budget
            assert result["optimization_result"]["savings"] > 0
            assert len(result["changes"]) > 0

@pytest.mark.asyncio
class TestSheetsFormatter:
    """Тесты для SheetsFormatter"""
    
    async def test_format_for_sheets(self):
        """Тест форматирования для Google Sheets"""
        menu_data = {
            "selected_items": [
                {
                    "id": "1015599",
                    "name": "Антипасти с черри",
                    "weight": 21,
                    "price": 100,
                    "quantity": 20,
                    "total_weight": 420,
                    "total_price": 2000
                }
            ],
            "menu_summary": {
                "total_weight": 420,
                "total_price": 2000
            }
        }
        event_details = {
            "guests": 20,
            "event_type": "buffet",
            "date": "2025-01-20"
        }
        
        with patch('src.services.claude_service.claude_service.send_structured_request') as mock_claude:
            mock_claude.return_value = {
                "order_info": {
                    "number": "P-12345",
                    "date": "20.01.2025",
                    "time": "14:00",
                    "guests": 20,
                    "event_type": "фуршет"
                },
                "menu_items": [
                    {
                        "name": "Антипасти с черри",
                        "quantity": 20,
                        "weight_per_set": 21,
                        "price_per_set": 100,
                        "total_weight": 420,
                        "total_price": 2000,
                        "category": "канапе"
                    }
                ],
                "services": [],
                "totals": {
                    "menu_cost": 2000,
                    "service_cost": 0,
                    "total_cost": 2000,
                    "total_weight": 420,
                    "weight_per_guest": 21,
                    "price_per_guest": 100
                },
                "metadata": {
                    "created_at": "2025-01-19T12:00:00",
                    "template_version": "1.0"
                }
            }
            
            result = await sheets_formatter.format_for_sheets(menu_data, event_details)
            
            assert "order_info" in result
            assert result["order_info"]["number"].startswith("P-")
            assert result["order_info"]["guests"] == 20
            assert len(result["menu_items"]) > 0
            assert result["totals"]["total_cost"] > 0
            assert "metadata" in result

@pytest.mark.asyncio
class TestExpertOrchestrator:
    """Тесты для ExpertOrchestrator"""
    
    async def test_full_estimate_process_success(self):
        """Тест полного успешного процесса создания сметы"""
        user_input = "Фуршет на 25 человек, бюджет 40000 рублей"
        
        # Мокаем всех экспертов
        with patch('src.experts.conversation_manager.conversation_manager.analyze_request') as mock_conv, \
             patch('src.experts.menu_expert.menu_expert.select_menu') as mock_menu, \
             patch('src.experts.grammage_controller.grammage_controller.validate_portions') as mock_gram, \
             patch('src.experts.budget_optimizer.budget_optimizer.optimize_budget') as mock_budget, \
             patch('src.experts.sheets_formatter.sheets_formatter.format_for_sheets') as mock_sheets:
            
            # Настройка моков
            mock_conv.return_value = {
                "analysis": {
                    "detected_event_type": "buffet",
                    "detected_guests": 25,
                    "detected_budget": 40000,
                    "confidence": 0.9
                }
            }
            
            mock_menu.return_value = {
                "selected_items": [{"id": "1", "name": "Test item"}],
                "menu_summary": {"total_price": 35000, "total_weight": 8750}
            }
            
            mock_gram.return_value = {
                "validation_result": {"status": "optimal"}
            }
            
            mock_budget.return_value = {
                "optimization_result": {"achievable": True},
                "final_menu": {"total_price": 39000}
            }
            
            mock_sheets.return_value = {
                "order_info": {"number": "P-12345"},
                "totals": {"total_cost": 39000}
            }
            
            result = await expert_orchestrator.process_estimate_request(user_input)
            
            assert result["success"] == True
            assert result["stage"] == "completed"
            assert "conversation_analysis" in result
            assert "menu_selection" in result
            assert "grammage_validation" in result
            assert "budget_optimization" in result
            assert "sheets_formatting" in result    
    async def test_full_estimate_process_failure(self):
        """Тест полного процесса создания сметы с ошибкой"""
        user_input = "Фуршет на 25 человек, бюджет 40000 рублей"
        
        # Мокаем экспертов, чтобы вызвать ошибку
        with patch('src.experts.conversation_manager.conversation_manager.analyze_request') as mock_conv, \
             patch('src.experts.menu_expert.menu_expert.select_menu') as mock_menu:
            
            # Настройка моков
            mock_conv.return_value = {
                "analysis": {
                    "detected_event_type": "buffet",
                    "detected_guests": 25,
                    "detected_budget": 40000,
                    "confidence": 0.9
                }
            }
            
            mock_menu.side_effect = Exception("Menu selection failed")
            
            with pytest.raises(Exception) as exc_info:
                await expert_orchestrator.process_estimate_request(user_input)
            
            assert str(exc_info.value) == "Menu selection failed" 