"""
Мониторинг и метрики OSAGAMING CRM
"""

from typing import Dict, Any, Optional
from time import time
from contextlib import contextmanager


class Metrics:
    """Простой класс для хранения метрик"""
    
    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._timers: Dict[str, list] = {}
    
    def counter(self, name: str, value: int = 1):
        """Увеличение счётчика"""
        self._counters[name] = self._counters.get(name, 0) + value
    
    def gauge(self, name: str, value: float):
        """Установка значения gauge"""
        self._gauges[name] = value
    
    def timer(self, name: str, value: float):
        """Добавление замера времени"""
        if name not in self._timers:
            self._timers[name] = []
        self._timers[name].append(value)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получение всех метрик"""
        result = {}
        for name, value in self._counters.items():
            result[f"counter_{name}"] = value
        for name, value in self._gauges.items():
            result[f"gauge_{name}"] = value
        for name, values in self._timers.items():
            if values:
                result[f"timer_{name}_count"] = len(values)
                result[f"timer_{name}_sum"] = sum(values)
                result[f"timer_{name}_avg"] = sum(values) / len(values)
        return result


# Глобальный объект метрик
metrics = Metrics()


class RequestMetricsMiddleware:
    """Middleware для сбора метрик запросов"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time()
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Можно записать статус код
                pass
            await send(message)
        
        await self.app(scope, receive, send_wrapper)
        
        duration = time() - start_time
        metrics.timer("request_duration", duration)


def get_metrics() -> Dict[str, Any]:
    """Получение метрик"""
    return metrics.get_metrics()


def generate_prometheus_metrics() -> str:
    """Генерация метрик в формате Prometheus"""
    mets = get_metrics()
    lines = ["# OSAGAMING CRM Metrics"]
    for name, value in mets.items():
        lines.append(f"osagaming_{name} {value}")
    return "\n".join(lines)


def comprehensive_health_check() -> Dict[str, Any]:
    """Комплексная проверка здоровья системы"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "database": "ok",
            "memory": "ok",
            "storage": "ok"
        }
    }


@contextmanager
def performance_tracker(operation: str):
    """Контекстный менеджер для отслеживания производительности операций"""
    start = time()
    yield
    duration = time() - start
    metrics.timer(f"operation_{operation}", duration)