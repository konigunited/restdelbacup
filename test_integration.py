import asyncio
import json
import sys
import os

# Добавляем src в путь для импорта
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from business import BusinessRulesEngine

async def test_integration():
    """Тест интеграции Business Logic Core"""
    
    engine = BusinessRulesEngine()
    
    # Тестовые данные
    test_orders = [
        {
            "name": "Нормальный фуршет",
            "data": {
                "order_info": {"guests": 30, "event_type": "buffet", "date": "2025-02-15"},  # Дата через месяц
                "totals": {"total_weight": 10500, "total_cost": 75000},
                "menu_items": [
                    {"name": "Канапе", "quantity": 50, "category": "канапе"},
                    {"name": "Салат", "quantity": 50, "category": "салаты"}  # Добавили вторую категорию
                ],
                "services": [{"name": "Официант", "quantity": 2}]
            },
            "expected_status": "valid"
        },
        {
            "name": "Критическая недостача",
            "data": {
                "order_info": {"guests": 50, "event_type": "buffet"},
                "totals": {"total_weight": 8000, "total_cost": 45000},
                "menu_items": [{"name": "Канапе", "quantity": 50}],
                "services": []
            },
            "expected_status": "critical"
        },
        {
            "name": "Малый заказ",
            "data": {
                "order_info": {"guests": 5, "event_type": "coffee_break"},
                "totals": {"total_weight": 1500, "total_cost": 8000},
                "menu_items": [{"name": "Кофе", "quantity": 5}],
                "services": []
            },
            "expected_status": "error"
        }
    ]
    
    print("🧪 ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ BUSINESS LOGIC CORE")
    print("=" * 60)
    
    passed_tests = 0
    total_tests = len(test_orders)
    
    for i, test_case in enumerate(test_orders, 1):
        print(f"\n📋 Тест {i}/{total_tests}: {test_case['name']}")
        print("-" * 40)
        
        try:
            result = await engine.validate_order(test_case['data'])
            
            # Основная информация
            print(f"✅ Статус: {result['overall_status']}")
            print(f"📊 Валидаций: {result['summary']['total_validations']}")
            print(f"🎯 Ожидался: {test_case['expected_status']}")
            
            # Проверка результата
            if result['overall_status'] == test_case['expected_status']:
                print("✅ ТЕСТ ПРОЙДЕН")
                passed_tests += 1
            else:
                print("❌ ТЕСТ НЕ ПРОЙДЕН")
            
            # Показ валидаций по уровням
            level_counts = result['summary']['by_level']
            print(f"📈 По уровням: INFO({level_counts.get('info', 0)}) "
                  f"WARNING({level_counts.get('warning', 0)}) "
                  f"ERROR({level_counts.get('error', 0)}) "
                  f"CRITICAL({level_counts.get('critical', 0)})")
            
            # Показ первых 3 валидаций
            print("📝 Основные сообщения:")
            for j, validation in enumerate(result['validations'][:3], 1):
                print(f"  {j}. {validation['message']}")
            
            # Рекомендации
            if result['recommendations']:
                print("💡 Рекомендации:")
                for rec in result['recommendations'][:2]:
                    print(f"  • {rec}")
                
        except Exception as e:
            print(f"❌ ОШИБКА: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО: {passed_tests}/{total_tests} тестов пройдено")
    
    if passed_tests == total_tests:
        print("✅ ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!")
        print("🚀 Business Logic Core готов к интеграции!")
    else:
        print("⚠️ Есть проблемы в тестах. Проверьте логику валидации.")
    
    return passed_tests == total_tests

async def test_performance():
    """Тест производительности"""
    print("\n🚀 ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ")
    print("-" * 30)
    
    engine = BusinessRulesEngine()
    
    test_data = {
        "order_info": {"guests": 100, "event_type": "banquet"},
        "totals": {"total_weight": 80000, "total_cost": 450000},
        "menu_items": [{"name": "Блюдо", "category": "основное"}],
        "services": [{"name": "Официант", "quantity": 5}]
    }
    
    import time
    
    # Тест скорости
    start_time = time.time()
    for i in range(10):
        await engine.validate_order(test_data)
    end_time = time.time()
    
    avg_time = (end_time - start_time) / 10
    print(f"⏱️ Среднее время валидации: {avg_time:.3f} сек")
    
    if avg_time < 0.1:
        print("✅ Производительность отличная!")
    elif avg_time < 0.5:
        print("✅ Производительность хорошая!")
    else:
        print("⚠️ Производительность требует оптимизации")

if __name__ == "__main__":
    async def main():
        # Основные тесты
        success = await test_integration()
        
        # Тест производительности
        await test_performance()
        
        return success
    
    result = asyncio.run(main())