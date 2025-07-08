"""
Enhanced logging configuration for expert system
"""
import logging
import json
import sys
from typing import Any, Dict, Optional
from datetime import datetime
from config.settings import settings

class ExpertLogger:
    """Специализированный логгер для системы экспертов"""
    
    def __init__(self, name: str = "expert_system"):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Настройка логгера"""
        if not self.logger.handlers:
            # Консольный обработчик
            console_handler = logging.StreamHandler(sys.stdout)
            
            # Форматтер
            formatter = logging.Formatter(
                fmt=settings.LOG_FORMAT,
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            
            # Добавляем обработчик
            self.logger.addHandler(console_handler)
            
            # Устанавливаем уровень логирования
            log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
            self.logger.setLevel(log_level)
            
            # Предотвращаем дублирование логов
            self.logger.propagate = False
    
    def info(self, message: str, **kwargs):
        """Логирование информации с контекстом"""
        if settings.DETAILED_LOGGING:
            context = self._format_context(**kwargs)
            self.logger.info(f"{message} {context}")
        else:
            self.logger.info(message)
    
    def error(self, message: str, **kwargs):
        """Логирование ошибок с контекстом"""
        context = self._format_context(**kwargs)
        self.logger.error(f"{message} {context}")
    
    def warning(self, message: str, **kwargs):
        """Логирование предупреждений с контекстом"""
        context = self._format_context(**kwargs)
        self.logger.warning(f"{message} {context}")
    
    def debug(self, message: str, **kwargs):
        """Логирование отладочной информации"""
        if settings.DEBUG:
            context = self._format_context(**kwargs)
            self.logger.debug(f"{message} {context}")
    
    def expert_start(self, expert_name: str, operation: str, **kwargs):
        """Логирование начала работы эксперта"""
        self.info(
            f"🤖 {expert_name} starting {operation}",
            expert=expert_name,
            operation=operation,
            timestamp=datetime.now().isoformat(),
            **kwargs
        )
    
    def expert_complete(self, expert_name: str, operation: str, duration_ms: int = None, **kwargs):
        """Логирование завершения работы эксперта"""
        duration_info = f" in {duration_ms}ms" if duration_ms else ""
        self.info(
            f"✅ {expert_name} completed {operation}{duration_info}",
            expert=expert_name,
            operation=operation,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def expert_error(self, expert_name: str, operation: str, error: str, **kwargs):
        """Логирование ошибки эксперта"""
        self.error(
            f"❌ {expert_name} failed {operation}: {error}",
            expert=expert_name,
            operation=operation,
            error=error,
            **kwargs
        )
    
    def claude_request(self, expert_name: str, request_id: int, **kwargs):
        """Логирование запроса к Claude API"""
        self.debug(
            f"📡 {expert_name} → Claude API request #{request_id}",
            expert=expert_name,
            request_id=request_id,
            **kwargs
        )
    
    def claude_response(self, expert_name: str, request_id: int, **kwargs):
        """Логирование ответа от Claude API"""
        self.debug(
            f"📡 {expert_name} ← Claude API response #{request_id}",
            expert=expert_name,
            request_id=request_id,
            **kwargs
        )
    
    def workflow_stage(self, stage: str, session_id: str, **kwargs):
        """Логирование этапов workflow"""
        self.info(
            f"🔄 Workflow stage: {stage}",
            stage=stage,
            session_id=session_id,
            **kwargs
        )
    
    def performance_metric(self, metric_name: str, value: Any, unit: str = "", **kwargs):
        """Логирование метрик производительности"""
        self.info(
            f"📊 Performance: {metric_name} = {value}{unit}",
            metric=metric_name,
            value=value,
            unit=unit,
            **kwargs
        )
    
    def business_event(self, event: str, **kwargs):
        """Логирование бизнес-событий"""
        self.info(
            f"💼 Business event: {event}",
            event=event,
            **kwargs
        )
    
    def _format_context(self, **kwargs) -> str:
        """Форматирование контекста для логов"""
        if not kwargs:
            return ""
        
        # Удаляем None значения и большие объекты
        clean_context = {}
        for key, value in kwargs.items():
            if value is not None:
                if isinstance(value, (dict, list)):
                    # Ограничиваем размер больших объектов
                    str_value = str(value)
                    if len(str_value) > 500:
                        clean_context[key] = f"<{type(value).__name__} size={len(str_value)}>"
                    else:
                        clean_context[key] = value
                elif isinstance(value, str) and len(value) > 200:
                    clean_context[key] = f"{value[:200]}..."
                else:
                    clean_context[key] = value
        
        try:
            return f"| {json.dumps(clean_context, ensure_ascii=False, default=str)}"
        except (TypeError, ValueError):
            # Fallback для не-сериализуемых объектов
            return f"| {str(clean_context)}"

class ExpertPerformanceLogger:
    """Логгер для отслеживания производительности экспертов"""
    
    def __init__(self, logger: ExpertLogger):
        self.logger = logger
        self.metrics = {}
    
    def start_timer(self, operation: str) -> str:
        """Запуск таймера для операции"""
        timer_id = f"{operation}_{datetime.now().timestamp()}"
        self.metrics[timer_id] = {
            "operation": operation,
            "start_time": datetime.now(),
            "status": "running"
        }
        return timer_id
    
    def end_timer(self, timer_id: str, success: bool = True, **kwargs):
        """Завершение таймера"""
        if timer_id in self.metrics:
            metric = self.metrics[timer_id]
            duration = datetime.now() - metric["start_time"]
            duration_ms = int(duration.total_seconds() * 1000)
            
            metric.update({
                "end_time": datetime.now(),
                "duration_ms": duration_ms,
                "status": "success" if success else "error"
            })
            
            self.logger.performance_metric(
                f"{metric['operation']}_duration",
                duration_ms,
                "ms",
                success=success,
                **kwargs
            )
            
            return duration_ms
        return 0
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Получить сводку метрик"""
        completed_metrics = [m for m in self.metrics.values() if m.get("duration_ms")]
        
        if not completed_metrics:
            return {"total_operations": 0}
        
        durations = [m["duration_ms"] for m in completed_metrics]
        successes = [m for m in completed_metrics if m["status"] == "success"]
        
        return {
            "total_operations": len(completed_metrics),
            "successful_operations": len(successes),
            "success_rate": len(successes) / len(completed_metrics) * 100,
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations)
        }

# Глобальные экземпляры логгеров
logger = ExpertLogger("eventbot_experts")
performance_logger = ExpertPerformanceLogger(logger)

# Логирование старта системы
logger.info("EventBot 5.0 Expert System Logger initialized", 
           log_level=settings.LOG_LEVEL,
           detailed_logging=settings.DETAILED_LOGGING,
           debug_mode=settings.DEBUG)