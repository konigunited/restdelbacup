from typing import Dict, Any, List
from .validators import (
    PortionValidator, CostValidator, ServiceValidator, 
    TimingValidator, MenuValidator
)
from .standards import ValidationResult, ValidationLevel

class BusinessRulesEngine:
    """Движок валидации бизнес-правил Rest Delivery"""
    
    def __init__(self):
        self.validators = [
            PortionValidator(),
            CostValidator(),
            ServiceValidator(),
            TimingValidator(),
            MenuValidator()
        ]
    
    async def validate_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Основной метод валидации заказа
        
        Args:
            order_data: Данные заказа
            
        Returns:
            Результат валидации в формате JSON
        """
        try:
            all_validations = []
            
            # Запуск всех валидаторов
            for validator in self.validators:
                validations = validator.validate(order_data)
                all_validations.extend(validations)
            
            # Определение общего статуса
            overall_status = self._determine_overall_status(all_validations)
            
            # Подсчет по уровням
            level_counts = self._count_by_level(all_validations)
            
            # Формирование рекомендаций
            recommendations = self._generate_recommendations(all_validations)
            
            return {
                "overall_status": overall_status,
                "validations": [
                    {
                        "level": v.level,
                        "message": v.message,
                        "field": v.field,
                        "recommendation": v.recommendation,
                        "reference_case": v.reference_case
                    }
                    for v in all_validations
                ],
                "summary": {
                    "total_validations": len(all_validations),
                    "by_level": level_counts
                },
                "recommendations": recommendations
            }
            
        except Exception as e:
            return {
                "overall_status": "error",
                "validations": [{
                    "level": "error",
                    "message": f"❌ Ошибка валидации: {str(e)}",
                    "field": "system",
                    "recommendation": "Проверьте корректность данных"
                }],
                "summary": {
                    "total_validations": 1,
                    "by_level": {"error": 1}
                },
                "recommendations": ["Исправьте ошибки в данных заказа"]
            }
    
    def _determine_overall_status(self, validations: List[ValidationResult]) -> str:
        """Определение общего статуса заказа"""
        if any(v.level == ValidationLevel.CRITICAL for v in validations):
            return "critical"
        elif any(v.level == ValidationLevel.ERROR for v in validations):
            return "error"
        elif any(v.level == ValidationLevel.WARNING for v in validations):
            # Если есть только предупреждения о времени и разнообразии меню - считаем valid
            warning_fields = [v.field for v in validations if v.level == ValidationLevel.WARNING]
            critical_warnings = {'portion_size', 'total_cost', 'waiter_count'}  # Критичные поля
            
            if any(field in critical_warnings for field in warning_fields):
                return "warning"
            else:
                return "valid"  # Некритичные предупреждения не влияют на общий статус
        else:
            return "valid"
    
    def _count_by_level(self, validations: List[ValidationResult]) -> Dict[str, int]:
        """Подсчет валидаций по уровням"""
        counts = {"info": 0, "warning": 0, "error": 0, "critical": 0}
        
        for validation in validations:
            counts[validation.level] += 1
        
        return counts
    
    def _generate_recommendations(self, validations: List[ValidationResult]) -> List[str]:
        """Генерация списка рекомендаций"""
        recommendations = []
        
        # Приоритетные рекомендации для критичных и ошибочных валидаций
        for validation in validations:
            if validation.level in [ValidationLevel.CRITICAL, ValidationLevel.ERROR]:
                if validation.recommendation:
                    recommendations.append(validation.recommendation)
        
        # Рекомендации для предупреждений
        for validation in validations:
            if validation.level == ValidationLevel.WARNING:
                if validation.recommendation and validation.recommendation not in recommendations:
                    recommendations.append(validation.recommendation)
        
        return recommendations[:5]  # Ограничиваем до 5 рекомендаций