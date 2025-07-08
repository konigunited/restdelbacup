"""
Tests for Google Sheets integration
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from pathlib import Path

from src.services.sheets_service import sheets_service
from src.services.estimate_service import estimate_service
from src.services.pdf_service import pdf_service

@pytest.mark.asyncio
class TestSheetsService:
    
    async def test_sheets_initialization(self):
        """Тест инициализации Google Sheets сервиса"""
        
        with patch('src.services.sheets_service.Credentials') as mock_creds, \
             patch('src.services.sheets_service.build') as mock_build, \
             patch('src.services.sheets_service.gspread_asyncio.AsyncioGspreadClientManager') as mock_agcm:
            
            mock_creds.from_service_account_file.return_value = MagicMock()
            mock_build.return_value = MagicMock()
            
            # Мокаем проверку доступа к шаблону
            mock_agc = AsyncMock()
            mock_template = AsyncMock()
            mock_template.worksheets.return_value = [
                MagicMock(title="Смета"),
                MagicMock(title="Банкетка"),
                MagicMock(title="Меню фото"),
                MagicMock(title="Финал")
            ]
            mock_agc.open_by_key.return_value = mock_template
            mock_agcm.return_value.authorize.return_value = mock_agc
            
            # Reset initialization status
            sheets_service._initialized = False
            
            await sheets_service.initialize()
            
            assert sheets_service._initialized == True
            assert mock_creds.from_service_account_file.called
            assert mock_build.called

    async def test_create_estimate_sheet(self):
        """Тест создания сметы в Google Sheets"""
        
        estimate_data = {
            "order_info": {
                "number": "P-12345",
                "date": "20.01.2025",
                "guests": 25,
                "event_type": "фуршет"
            },
            "menu_items": [
                {
                    "name": "Канапе с семгой",
                    "quantity": 25,
                    "weight_per_set": 100,
                    "price_per_set": 120,
                    "total_weight": 2500,
                    "total_price": 3000
                },
                {
                    "name": "Мини-сэндвичи",
                    "quantity": 25,
                    "weight_per_set": 80,
                    "price_per_set": 100,
                    "total_weight": 2000,
                    "total_price": 2500
                }
            ],
            "services": [
                {
                    "name": "Официант",
                    "description": "Обслуживание мероприятия",
                    "quantity": 2,
                    "unit": "чел",
                    "price_per_unit": 2000,
                    "total_price": 4000
                }
            ],
            "totals": {
                "total_cost": 9500,
                "total_weight": 4500,
                "weight_per_guest": 180
            }
        }
        
        with patch.object(sheets_service, '_initialized', True), \
             patch.object(sheets_service, 'agcm') as mock_agcm:
            
            # Мокаем создание копии шаблона
            mock_agc = AsyncMock()
            mock_template = AsyncMock()
            mock_new_sheet = AsyncMock()
            mock_new_sheet.id = "new_sheet_id_123"
            
            mock_agc.open_by_key.return_value = mock_template
            mock_agc.copy.return_value = mock_new_sheet
            mock_agcm.authorize.return_value = mock_agc
            
            # Мокаем заполнение данных
            with patch.object(sheets_service, '_fill_estimate_data') as mock_fill, \
                 patch.object(sheets_service, '_create_public_link') as mock_link:
                
                mock_fill.return_value = None
                mock_link.return_value = "https://docs.google.com/spreadsheets/d/new_sheet_id_123/edit"
                
                sheet_id, share_url = await sheets_service.create_estimate_sheet(estimate_data)
                
                assert sheet_id == "new_sheet_id_123"
                assert "new_sheet_id_123" in share_url
                mock_fill.assert_called_once_with(mock_new_sheet, estimate_data)
                mock_link.assert_called_once_with("new_sheet_id_123")

    async def test_fill_main_estimate(self):
        """Тест заполнения основного листа сметы"""
        
        mock_worksheet = AsyncMock()
        
        estimate_data = {
            "order_info": {
                "number": "P-12345",
                "date": "20.01.2025",
                "guests": 25
            },
            "menu_items": [
                {
                    "name": "Канапе тест",
                    "quantity": 25,
                    "weight_per_set": 100,
                    "price_per_set": 120,
                    "total_weight": 2500,
                    "total_price": 3000
                }
            ],
            "totals": {
                "total_cost": 3000,
                "total_weight": 2500
            }
        }
        
        with patch.object(sheets_service, '_batch_update_worksheet') as mock_batch:
            await sheets_service._fill_main_estimate(mock_worksheet, estimate_data)
            
            # Проверяем, что batch_update был вызван
            mock_batch.assert_called_once()
            
            # Проверяем структуру обновлений
            call_args = mock_batch.call_args[0]
            updates = call_args[1]
            
            # Должны быть обновления для заказа, меню и итогов
            assert len(updates) >= 3
            
            # Проверяем наличие номера заказа
            order_updates = [u for u in updates if u['range'] == 'B2']
            assert len(order_updates) == 1
            assert order_updates[0]['values'][0][0] == "P-12345"

@pytest.mark.asyncio 
class TestEstimateService:
    
    async def test_complete_estimate_creation(self):
        """Тест полного процесса создания сметы"""
        
        user_input = "Фуршет на 20 человек, бюджет 30000"
        context = {"session_id": "test_session_123"}
        
        with patch('src.services.expert_orchestrator.expert_orchestrator') as mock_orchestrator, \
             patch.object(sheets_service, 'create_estimate_sheet') as mock_sheets, \
             patch.object(pdf_service, 'generate_pdf_from_sheet') as mock_pdf:
            
            # Мокаем результат экспертов
            mock_orchestrator.process_estimate_request.return_value = {
                "success": True,
                "sheets_data": {
                    "order_info": {
                        "number": "P-54321",
                        "guests": 20,
                        "event_type": "фуршет"
                    },
                    "menu_items": [
                        {
                            "name": "Канапе микс",
                            "quantity": 20,
                            "total_price": 25000
                        }
                    ],
                    "totals": {
                        "total_cost": 28000,
                        "total_weight": 3000,
                        "weight_per_guest": 150
                    },
                    "services": []
                },
                "conversation_analysis": {"confidence": 0.9},
                "grammage_validation": {"status": "valid"},
                "budget_optimization": {"optimized": True}
            }
            
            # Мокаем создание Google Sheets
            mock_sheets.return_value = ("sheet_123", "https://docs.google.com/spreadsheets/d/sheet_123/edit")
            
            # Мокаем генерацию PDF
            mock_pdf.return_value = "/path/to/estimate_P-54321.pdf"
            
            # Инициализируем сервис
            estimate_service._stats = {
                "total_created": 0,
                "total_failed": 0,
                "average_processing_time": 0
            }
            
            result = await estimate_service.create_complete_estimate(user_input, context)
            
            assert result["success"] == True
            assert result["order_number"] == "P-54321"
            assert result["session_id"] == "test_session_123"
            assert "google_sheets" in result
            assert result["google_sheets"]["sheet_id"] == "sheet_123"
            assert result["pdf"]["generated"] == True
            assert result["estimate_summary"]["total_cost"] == 28000
            assert result["estimate_summary"]["guests"] == 20

    async def test_estimate_service_error_handling(self):
        """Тест обработки ошибок в EstimateService"""
        
        user_input = "Невалидный запрос"
        
        with patch('src.services.expert_orchestrator.expert_orchestrator') as mock_orchestrator:
            
            # Мокаем ошибку от экспертов
            mock_orchestrator.process_estimate_request.return_value = {
                "success": False,
                "error": "Не удалось понять запрос"
            }
            
            result = await estimate_service.create_complete_estimate(user_input)
            
            assert result["success"] == False
            assert "error" in result
            assert "Не удалось понять запрос" in result["error"]

    async def test_needs_more_info_scenario(self):
        """Тест сценария когда нужна дополнительная информация"""
        
        user_input = "Нужен фуршет"
        
        with patch('src.services.expert_orchestrator.expert_orchestrator') as mock_orchestrator:
            
            # Мокаем ответ, что нужна дополнительная информация
            mock_orchestrator.process_estimate_request.return_value = {
                "success": False,
                "needs_more_info": True,
                "response": "Сколько будет гостей? Какой бюджет?"
            }
            
            result = await estimate_service.create_complete_estimate(user_input)
            
            assert result["success"] == False
            assert result["needs_more_info"] == True
            assert "Сколько будет гостей" in result["response"]

class TestPDFService:
    
    def test_pdf_service_initialization(self):
        """Тест инициализации PDF сервиса"""
        assert pdf_service.output_dir.exists()
        assert pdf_service.output_dir.name == "pdfs"
        assert isinstance(pdf_service._pdf_cache, dict)

    @pytest.mark.asyncio
    async def test_generate_pdf_from_sheet(self):
        """Тест генерации PDF из Google Sheets"""
        
        sheet_id = "test_sheet_123"
        order_number = "P-12345"
        
        with patch.object(sheets_service, 'export_to_pdf') as mock_export, \
             patch('aiofiles.open', create=True) as mock_aiofiles:
            
            # Мокаем получение PDF контента
            mock_pdf_content = b"PDF content here"
            mock_export.return_value = mock_pdf_content
            
            # Мокаем запись файла
            mock_file = AsyncMock()
            mock_aiofiles.return_value.__aenter__.return_value = mock_file
            
            pdf_path = await pdf_service.generate_pdf_from_sheet(sheet_id, order_number)
            
            assert pdf_path is not None
            assert "estimate_P-12345" in pdf_path
            assert pdf_path.endswith(".pdf")
            mock_export.assert_called_once_with(sheet_id)
            mock_file.write.assert_called_once_with(mock_pdf_content)

    @pytest.mark.asyncio
    async def test_get_pdf_content(self):
        """Тест получения содержимого PDF файла"""
        
        # Создаем временный PDF файл
        test_content = b"Test PDF content"
        test_path = pdf_service.output_dir / "test.pdf"
        
        with patch('aiofiles.open', create=True) as mock_aiofiles:
            mock_file = AsyncMock()
            mock_file.read.return_value = test_content
            mock_aiofiles.return_value.__aenter__.return_value = mock_file
            
            with patch('pathlib.Path.exists', return_value=True):
                content = await pdf_service.get_pdf_content(str(test_path))
                
                assert content == test_content
                mock_file.read.assert_called_once()

@pytest.mark.asyncio
class TestIntegrationAPI:
    
    async def test_create_estimate_endpoint(self):
        """Тест API endpoint создания сметы"""
        
        from src.api.routes.estimates import create_estimate, EstimateRequest
        
        request = EstimateRequest(
            user_input="Фуршет на 25 человек",
            context={"session_id": "api_test_session"}
        )
        
        with patch.object(estimate_service, 'create_complete_estimate') as mock_create:
            
            mock_create.return_value = {
                "success": True,
                "order_number": "P-API-123",
                "session_id": "api_test_session",
                "google_sheets": {
                    "sheet_id": "api_sheet_123",
                    "url": "https://docs.google.com/spreadsheets/d/api_sheet_123/edit"
                },
                "pdf": {
                    "generated": True,
                    "path": "/path/to/api_estimate.pdf"
                }
            }
            
            result = await create_estimate(request)
            
            assert result["success"] == True
            assert result["order_number"] == "P-API-123"
            mock_create.assert_called_once_with(
                "Фуршет на 25 человек",
                {"session_id": "api_test_session"}
            )

    async def test_health_check_endpoint(self):
        """Тест health check endpoint"""
        
        from src.api.routes.estimates import estimates_health_check
        
        with patch.object(sheets_service, '_initialized', True), \
             patch.object(sheets_service, '_verify_template_access') as mock_verify, \
             patch.object(estimate_service, 'get_stats') as mock_stats, \
             patch.object(pdf_service, 'get_stats') as mock_pdf_stats:
            
            mock_verify.return_value = True
            mock_stats.return_value = {
                "initialized": True,
                "active_processing": 0
            }
            mock_pdf_stats.return_value = {
                "output_directory": "/path/to/pdfs",
                "total_files": 5
            }
            
            result = await estimates_health_check()
            
            assert result["status"] == "healthy"
            assert result["components"]["google_sheets"]["status"] == "healthy"
            assert result["components"]["estimate_service"]["status"] == "healthy"
            assert result["components"]["pdf_service"]["status"] == "healthy"

# Фикстуры для тестов
@pytest.fixture
def sample_estimate_data():
    """Пример данных сметы для тестов"""
    return {
        "order_info": {
            "number": "P-TEST-001",
            "date": "25.01.2025",
            "guests": 30,
            "event_type": "корпоратив"
        },
        "menu_items": [
            {
                "name": "Канапе ассорти",
                "quantity": 30,
                "weight_per_set": 120,
                "price_per_set": 150,
                "total_weight": 3600,
                "total_price": 4500
            }
        ],
        "services": [],
        "totals": {
            "total_cost": 4500,
            "total_weight": 3600,
            "weight_per_guest": 120
        }
    }

@pytest.fixture
def mock_google_sheets():
    """Мок для Google Sheets сервиса"""
    with patch.object(sheets_service, '_initialized', True):
        yield sheets_service

# Интеграционные тесты
@pytest.mark.integration
class TestFullIntegration:
    """Полные интеграционные тесты (требуют реальных credentials)"""
    
    @pytest.mark.skip(reason="Requires real Google credentials")
    async def test_real_sheets_integration(self):
        """Тест с реальным Google Sheets (только для локальной разработки)"""
        
        # Этот тест можно запускать только с реальными credentials
        # pytest tests/test_sheets_integration.py::TestFullIntegration::test_real_sheets_integration -m integration
        
        test_data = {
            "order_info": {
                "number": "P-INTEGRATION-TEST",
                "date": datetime.now().strftime("%d.%m.%Y"),
                "guests": 10
            },
            "menu_items": [
                {
                    "name": "Тестовое блюдо",
                    "quantity": 10,
                    "price_per_set": 100,
                    "total_price": 1000
                }
            ],
            "totals": {
                "total_cost": 1000
            }
        }
        
        sheet_id, sheet_url = await sheets_service.create_estimate_sheet(test_data)
        
        assert sheet_id is not None
        assert "docs.google.com" in sheet_url
        
        # Проверяем, что можем получить данные обратно
        retrieved_data = await sheets_service.get_estimate_data(sheet_id)
        assert retrieved_data is not None
        assert sheet_id in retrieved_data.get("sheet_id", "")