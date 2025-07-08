"""
Демонстрационный скрипт полной интеграции EventBot 5.0
Google Sheets Integration Demo
"""
import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию в path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Импорты с обработкой ошибок
try:
    from src.services.estimate_service import estimate_service
    from src.services.sheets_service import sheets_service
    from src.services.pdf_service import pdf_service
    from src.utils.logger import logger
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Создаем заглушки для демонстрации...")
    
    # Создаем простые заглушки
    class MockLogger:
        def info(self, msg, **kwargs): print(f"INFO: {msg}")
        def error(self, msg, **kwargs): print(f"ERROR: {msg}")
        def warning(self, msg, **kwargs): print(f"WARNING: {msg}")
    
    logger = MockLogger()

# Эмуляция expert_orchestrator для демо
class MockExpertOrchestrator:
    """Мок оркестратора экспертов для демонстрации"""
    
    async def process_estimate_request(self, user_input: str, context=None):
        """Эмуляция обработки запроса экспертами"""
        
        # Простая логика для демо
        if "кофе-брейк" in user_input.lower():
            return self._create_coffee_break_estimate(user_input)
        elif "фуршет" in user_input.lower():
            return self._create_buffet_estimate(user_input)
        elif "банкет" in user_input.lower():
            return self._create_banquet_estimate(user_input)
        else:
            return self._create_default_estimate(user_input)
    
    def _create_coffee_break_estimate(self, user_input):
        """Создание сметы для кофе-брейка"""
        guests = self._extract_guests(user_input)
        order_number = f"P-CB-{int(datetime.now().timestamp())}"
        
        return {
            "success": True,
            "sheets_data": {
                "order_info": {
                    "number": order_number,
                    "date": datetime.now().strftime("%d.%m.%Y"),
                    "guests": guests,
                    "event_type": "кофе-брейк"
                },
                "menu_items": [
                    {
                        "name": "Кофе американо",
                        "quantity": guests,
                        "weight_per_set": 200,
                        "price_per_set": 150,
                        "total_weight": guests * 200,
                        "total_price": guests * 150
                    },
                    {
                        "name": "Круассаны мини",
                        "quantity": guests * 2,
                        "weight_per_set": 40,
                        "price_per_set": 80,
                        "total_weight": guests * 2 * 40,
                        "total_price": guests * 2 * 80
                    },
                    {
                        "name": "Печенье ассорти",
                        "quantity": guests,
                        "weight_per_set": 50,
                        "price_per_set": 60,
                        "total_weight": guests * 50,
                        "total_price": guests * 60
                    }
                ],
                "services": [],
                "totals": {
                    "total_cost": guests * (150 + 160 + 60),
                    "total_weight": guests * (200 + 80 + 50),
                    "weight_per_guest": 330
                }
            },
            "conversation_analysis": {
                "event_type": "кофе-брейк",
                "confidence": 0.95,
                "extracted_guests": guests
            },
            "grammage_validation": {
                "status": "valid",
                "weight_per_guest": 330,
                "recommendation": "Оптимальный вес для кофе-брейка"
            },
            "budget_optimization": {
                "total_cost": guests * 370,
                "cost_per_guest": 370,
                "optimization_applied": False
            }
        }
    
    def _create_buffet_estimate(self, user_input):
        """Создание сметы для фуршета"""
        guests = self._extract_guests(user_input)
        budget = self._extract_budget(user_input)
        order_number = f"P-BF-{int(datetime.now().timestamp())}"
        
        base_cost_per_guest = 2000 if not budget else min(budget // guests, 3000)
        
        return {
            "success": True,
            "sheets_data": {
                "order_info": {
                    "number": order_number,
                    "date": datetime.now().strftime("%d.%m.%Y"),
                    "guests": guests,
                    "event_type": "фуршет"
                },
                "menu_items": [
                    {
                        "name": "Канапе с семгой",
                        "quantity": guests * 3,
                        "weight_per_set": 25,
                        "price_per_set": 120,
                        "total_weight": guests * 3 * 25,
                        "total_price": guests * 3 * 120
                    },
                    {
                        "name": "Мини-сэндвичи",
                        "quantity": guests * 2,
                        "weight_per_set": 40,
                        "price_per_set": 100,
                        "total_weight": guests * 2 * 40,
                        "total_price": guests * 2 * 100
                    },
                    {
                        "name": "Овощная нарезка",
                        "quantity": guests,
                        "weight_per_set": 80,
                        "price_per_set": 150,
                        "total_weight": guests * 80,
                        "total_price": guests * 150
                    },
                    {
                        "name": "Фруктовая нарезка",
                        "quantity": guests,
                        "weight_per_set": 70,
                        "price_per_set": 200,
                        "total_weight": guests * 70,
                        "total_price": guests * 200
                    }
                ],
                "services": [
                    {
                        "name": "Официант",
                        "description": "Обслуживание фуршета",
                        "quantity": 1 if guests <= 20 else 2,
                        "unit": "чел",
                        "price_per_unit": 3000,
                        "total_price": (1 if guests <= 20 else 2) * 3000
                    }
                ],
                "totals": {
                    "total_cost": guests * (360 + 200 + 150 + 200) + (1 if guests <= 20 else 2) * 3000,
                    "total_weight": guests * (75 + 80 + 80 + 70),
                    "weight_per_guest": 305
                }
            },
            "conversation_analysis": {
                "event_type": "фуршет",
                "confidence": 0.92,
                "extracted_guests": guests,
                "extracted_budget": budget
            },
            "grammage_validation": {
                "status": "valid",
                "weight_per_guest": 305,
                "recommendation": "Стандартная граммовка для фуршета"
            },
            "budget_optimization": {
                "total_cost": guests * 910 + (1 if guests <= 20 else 2) * 3000,
                "cost_per_guest": base_cost_per_guest,
                "optimization_applied": budget is not None
            }
        }
    
    def _create_banquet_estimate(self, user_input):
        """Создание сметы для банкета"""
        guests = self._extract_guests(user_input)
        order_number = f"P-BQ-{int(datetime.now().timestamp())}"
        
        return {
            "success": True,
            "sheets_data": {
                "order_info": {
                    "number": order_number,
                    "date": datetime.now().strftime("%d.%m.%Y"),
                    "guests": guests,
                    "event_type": "банкет"
                },
                "menu_items": [
                    {
                        "name": "Салат Цезарь",
                        "quantity": guests,
                        "weight_per_set": 150,
                        "price_per_set": 350,
                        "total_weight": guests * 150,
                        "total_price": guests * 350
                    },
                    {
                        "name": "Стейк из семги",
                        "quantity": guests,
                        "weight_per_set": 200,
                        "price_per_set": 800,
                        "total_weight": guests * 200,
                        "total_price": guests * 800
                    },
                    {
                        "name": "Гарнир овощной",
                        "quantity": guests,
                        "weight_per_set": 120,
                        "price_per_set": 200,
                        "total_weight": guests * 120,
                        "total_price": guests * 200
                    },
                    {
                        "name": "Десерт тирамису",
                        "quantity": guests,
                        "weight_per_set": 100,
                        "price_per_set": 300,
                        "total_weight": guests * 100,
                        "total_price": guests * 300
                    }
                ],
                "services": [
                    {
                        "name": "Официант",
                        "description": "Полное банкетное обслуживание",
                        "quantity": max(2, guests // 15),
                        "unit": "чел",
                        "price_per_unit": 4000,
                        "total_price": max(2, guests // 15) * 4000
                    },
                    {
                        "name": "Аренда посуды",
                        "description": "Банкетная посуда и приборы",
                        "quantity": guests,
                        "unit": "комплект",
                        "price_per_unit": 200,
                        "total_price": guests * 200
                    }
                ],
                "totals": {
                    "total_cost": guests * (350 + 800 + 200 + 300 + 200) + max(2, guests // 15) * 4000,
                    "total_weight": guests * (150 + 200 + 120 + 100),
                    "weight_per_guest": 570
                }
            },
            "conversation_analysis": {
                "event_type": "банкет",
                "confidence": 0.88,
                "extracted_guests": guests
            },
            "grammage_validation": {
                "status": "valid",
                "weight_per_guest": 570,
                "recommendation": "Полноценное банкетное меню"
            },
            "budget_optimization": {
                "total_cost": guests * 1850 + max(2, guests // 15) * 4000,
                "cost_per_guest": 1850,
                "optimization_applied": False
            }
        }
    
    def _create_default_estimate(self, user_input):
        """Создание базовой сметы"""
        guests = self._extract_guests(user_input) or 20
        order_number = f"P-DEF-{int(datetime.now().timestamp())}"
        
        return {
            "success": True,
            "sheets_data": {
                "order_info": {
                    "number": order_number,
                    "date": datetime.now().strftime("%d.%m.%Y"),
                    "guests": guests,
                    "event_type": "мероприятие"
                },
                "menu_items": [
                    {
                        "name": "Универсальный сет",
                        "quantity": guests,
                        "weight_per_set": 250,
                        "price_per_set": 500,
                        "total_weight": guests * 250,
                        "total_price": guests * 500
                    }
                ],
                "services": [],
                "totals": {
                    "total_cost": guests * 500,
                    "total_weight": guests * 250,
                    "weight_per_guest": 250
                }
            },
            "conversation_analysis": {
                "event_type": "мероприятие",
                "confidence": 0.5,
                "extracted_guests": guests
            },
            "grammage_validation": {
                "status": "basic",
                "weight_per_guest": 250
            },
            "budget_optimization": {
                "total_cost": guests * 500,
                "cost_per_guest": 500
            }
        }
    
    def _extract_guests(self, text):
        """Извлечение количества гостей из текста"""
        import re
        match = re.search(r'(\d+)\s*(?:человек|гост|чел)', text.lower())
        return int(match.group(1)) if match else 25
    
    def _extract_budget(self, text):
        """Извлечение бюджета из текста"""
        import re
        match = re.search(r'бюджет[:\s]*(\d+)', text.lower())
        return int(match.group(1)) if match else None

# Инициализация mock orchestrator
mock_orchestrator = MockExpertOrchestrator()

# Monkey patch для демо - только если модуль существует
try:
    import src.services.expert_orchestrator
    src.services.expert_orchestrator.expert_orchestrator = mock_orchestrator
except ImportError:
    pass

async def run_demo():
    """Запуск демонстрации полной интеграции"""
    
    print("🚀 EventBot 5.0 - Google Sheets Integration Demo")
    print("=" * 60)
    print(f"Время запуска: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print()
    
    try:
        # Проверяем доступность сервисов
        services_available = True
        
        try:
            # Инициализация
            print("📊 Инициализация сервисов...")
            await estimate_service.initialize()
            print("✅ Сервисы инициализированы")
        except Exception as e:
            print(f"❌ Ошибка инициализации: {e}")
            services_available = False
        
        print()
        
        # Тестовые запросы
        test_requests = [
            {
                "description": "Кофе-брейк для небольшой команды",
                "input": "Нужен кофе-брейк на 15 человек завтра в 14:00",
                "expected": "кофе-брейк"
            },
            {
                "description": "Фуршет с ограниченным бюджетом",
                "input": "Фуршет на 25 человек, бюджет 40000 рублей",
                "expected": "фуршет"
            },
            {
                "description": "Банкет с полным обслуживанием",
                "input": "Банкет на 50 человек с обслуживанием",
                "expected": "банкет"
            }
        ]
        
        results = []
        
        for i, request in enumerate(test_requests, 1):
            print(f"🎯 Тест {i}: {request['description']}")
            print(f"📝 Запрос: {request['input']}")
            print("-" * 50)
            
            start_time = datetime.now()
            
            if services_available:
                try:
                    # Создание сметы
                    result = await estimate_service.create_complete_estimate(
                        request['input'],
                        {"session_id": f"demo_session_{i}", "demo": True}
                    )
                    
                    end_time = datetime.now()
                    processing_time = (end_time - start_time).total_seconds()
                    
                    if result["success"]:
                        print(f"✅ Смета создана: {result['order_number']}")
                        print(f"💰 Стоимость: {result['estimate_summary']['total_cost']:,}₽")
                        print(f"👥 Гостей: {result['estimate_summary']['guests']}")
                        print(f"🍽️ Позиций меню: {result['estimate_summary']['menu_items_count']}")
                        print(f"⚖️ Граммовка: {result['estimate_summary']['weight_per_guest']}г/чел")
                        print(f"🔗 Google Sheets: {result['google_sheets']['url']}")
                        print(f"⏱️ Время обработки: {processing_time:.2f}с")
                        
                        if result["pdf"]["generated"]:
                            print(f"📄 PDF создан: {result['pdf']['path']}")
                        
                        results.append({
                            "success": True,
                            "order_number": result['order_number'],
                            "cost": result['estimate_summary']['total_cost'],
                            "processing_time": processing_time,
                            "url": result['google_sheets']['url']
                        })
                        
                    else:
                        if result.get("needs_more_info"):
                            print(f"❓ Нужна дополнительная информация:")
                            print(f"   {result['response']}")
                        else:
                            print(f"❌ Ошибка: {result.get('error')}")
                        
                        results.append({
                            "success": False,
                            "error": result.get('error', 'Unknown error'),
                            "processing_time": processing_time
                        })
                
                except Exception as e:
                    print(f"❌ Ошибка выполнения: {e}")
                    results.append({
                        "success": False,
                        "error": str(e),
                        "processing_time": 0
                    })
            else:
                # Демо без реальных сервисов
                mock_result = await mock_orchestrator.process_estimate_request(request['input'])
                if mock_result["success"]:
                    sheets_data = mock_result["sheets_data"]
                    print(f"✅ Мок смета создана: {sheets_data['order_info']['number']}")
                    print(f"💰 Стоимость: {sheets_data['totals']['total_cost']:,}₽")
                    print(f"👥 Гостей: {sheets_data['order_info']['guests']}")
                    print(f"⚖️ Граммовка: {sheets_data['totals']['weight_per_guest']}г/чел")
                    print(f"🔗 Google Sheets: [DEMO MODE - сервис недоступен]")
                    print(f"⏱️ Время обработки: 0.1с (мок)")
                    
                    results.append({
                        "success": True,
                        "order_number": sheets_data['order_info']['number'],
                        "cost": sheets_data['totals']['total_cost'],
                        "processing_time": 0.1,
                        "url": "[DEMO MODE]"
                    })
            
            print()
        
        # Статистика сервиса
        if services_available:
            try:
                print("📈 Статистика сервиса:")
                stats = estimate_service.get_stats()
                print(f"   Активных обработок: {stats['active_processing']}")
                print(f"   Google Sheets статус: {stats['sheets_service']['status']}")
                print()
            except Exception as e:
                print(f"❌ Ошибка получения статистики: {e}")
                print()
        
        # Итоги демонстрации
        print("📊 Итоги демонстрации:")
        print("-" * 50)
        successful = len([r for r in results if r["success"]])
        total_cost = sum(r.get("cost", 0) for r in results if r["success"])
        avg_time = sum(r["processing_time"] for r in results) / len(results) if results else 0
        
        print(f"✅ Успешно создано смет: {successful}/{len(results)}")
        print(f"💰 Общая стоимость смет: {total_cost:,}₽")
        print(f"⏱️ Среднее время создания: {avg_time:.2f}с")
        print(f"🔗 Google Sheets интеграция: {'Работает' if services_available else 'Недоступна'}")
        print(f"📄 PDF генерация: {'Работает' if services_available else 'Недоступна'}")
        
        print()
        print("🎉 Демонстрация завершена успешно!")
        
        if services_available:
            print()
            print("📋 Доступные URL для проверки:")
            for i, result in enumerate(results, 1):
                if result["success"] and result["url"] != "[DEMO MODE]":
                    print(f"   Смета {i}: {result['url']}")
        
    except Exception as e:
        print(f"❌ Ошибка демонстрации: {e}")
        logger.error("Demo failed", error=str(e))
        import traceback
        print("Детали ошибки:")
        print(traceback.format_exc())

async def run_health_check():
    """Проверка работоспособности всех компонентов"""
    
    print("🏥 EventBot 5.0 - Health Check")
    print("=" * 40)
    
    checks = []
    
    # Проверка EstimateService
    try:
        await estimate_service.initialize()
        stats = estimate_service.get_stats()
        checks.append({
            "component": "EstimateService",
            "status": "✅ OK",
            "details": f"Initialized: {stats['initialized']}"
        })
    except Exception as e:
        checks.append({
            "component": "EstimateService", 
            "status": "❌ FAIL",
            "details": str(e)
        })
    
    # Проверка Google Sheets
    try:
        if not sheets_service._initialized:
            await sheets_service.initialize()
        await sheets_service._verify_template_access()
        checks.append({
            "component": "Google Sheets",
            "status": "✅ OK",
            "details": f"Template ID: {sheets_service.template_id}"
        })
    except Exception as e:
        checks.append({
            "component": "Google Sheets",
            "status": "❌ FAIL", 
            "details": str(e)
        })
    
    # Проверка PDF Service
    try:
        pdf_stats = pdf_service.get_stats()
        checks.append({
            "component": "PDF Service",
            "status": "✅ OK",
            "details": f"Output dir: {pdf_stats['output_directory']}"
        })
    except Exception as e:
        checks.append({
            "component": "PDF Service",
            "status": "❌ FAIL",
            "details": str(e)
        })
    
    # Проверка файла credentials
    creds_path = Path("config/google_credentials.json")
    if creds_path.exists():
        checks.append({
            "component": "Google Credentials",
            "status": "✅ OK",
            "details": f"File exists: {creds_path}"
        })
    else:
        checks.append({
            "component": "Google Credentials",
            "status": "❌ FAIL",
            "details": f"File not found: {creds_path}"
        })
    
    # Вывод результатов
    for check in checks:
        print(f"{check['status']} {check['component']}")
        print(f"   {check['details']}")
    
    all_ok = all("OK" in check["status"] for check in checks)
    print()
    print(f"🎯 Общий статус: {'✅ Все системы работают' if all_ok else '❌ Есть проблемы'}")
    
    return all_ok

async def run_quick_test():
    """Быстрый тест основной функциональности"""
    
    print("⚡ EventBot 5.0 - Quick Test")
    print("=" * 30)
    
    try:
        await estimate_service.initialize()
        
        result = await estimate_service.create_complete_estimate(
            "Тестовый кофе-брейк на 10 человек",
            {"session_id": "quick_test", "test": True}
        )
        
        if result["success"]:
            print("✅ Быстрый тест пройден")
            print(f"   Заказ: {result['order_number']}")
            print(f"   Стоимость: {result['estimate_summary']['total_cost']}₽")
            print(f"   URL: {result['google_sheets']['url']}")
            return True
        else:
            print("❌ Быстрый тест провален")
            print(f"   Ошибка: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка быстрого теста: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="EventBot 5.0 Integration Demo")
    parser.add_argument("--mode", choices=["demo", "health", "quick"], default="demo",
                       help="Режим запуска")
    parser.add_argument("--verbose", action="store_true", help="Подробный вывод")
    
    args = parser.parse_args()
    
    if args.mode == "demo":
        asyncio.run(run_demo())
    elif args.mode == "health":
        asyncio.run(run_health_check())
    elif args.mode == "quick":
        asyncio.run(run_quick_test())