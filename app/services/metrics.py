import time
import statistics
from collections import deque
from typing import Deque
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta


class MetricsService:
    def __init__(self, window_size: int = 3600):  # Default 1 hour window
        self.window_size = window_size
        self.errors: Deque[dict] = deque(maxlen=window_size)
        self.requests: Deque[datetime] = deque(maxlen=window_size)
        self.start_time = datetime.utcnow()

    def record_error(self, status_code: int, path: str):
        """Record an error occurrence"""
        self.errors.append({
            'timestamp': datetime.utcnow(),
            'status_code': status_code,
            'path': path
        })

    def record_request(self):
        """Record a request occurrence"""
        self.requests.append(datetime.utcnow())

    def get_metrics(self) -> dict:
        """Get current metrics"""
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)

        recent_errors = [e for e in self.errors if e['timestamp'] > hour_ago]
        recent_requests = [r for r in self.requests if r > minute_ago]

        error_rate = (len(recent_errors) / len(recent_requests)
                      * 100) if recent_requests else 0
        requests_per_minute = len(recent_requests)  # Requests in last minute

        # Calculate uptime
        uptime_seconds = (now - self.start_time).total_seconds()

        return {
            "errors": {
                "rate": round(error_rate, 2),
                "count": len(recent_errors)
            },
            "throughput": {
                "requests_per_minute": round(requests_per_minute, 2),
                "total_requests": len(self.requests)
            },
            "uptime": {
                "seconds": int(uptime_seconds),
                "formatted": str(timedelta(seconds=int(uptime_seconds)))
            }
        }


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, metrics_service: MetricsService):
        super().__init__(app)
        self.metrics_service = metrics_service

    async def dispatch(self, request: Request, call_next):
        self.metrics_service.record_request()

        response = await call_next(request)

        # Record errors (status code >= 400)
        if response.status_code >= 400:
            self.metrics_service.record_error(
                response.status_code, request.url.path)

        return response
