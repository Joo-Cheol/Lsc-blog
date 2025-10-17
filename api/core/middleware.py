#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 미들웨어
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .logging import get_logger, set_run_id, clear_context, log_api_request
from .config import get_settings

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """요청 로깅 미들웨어"""
    
    # 클래스 변수로 변경 (메인에서 클래스 속성으로 읽기 위해)
    _op_metrics = {"search": 0, "generate": 0, "crawl": 0, "upload": 0}
    _lock = threading.Lock()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 요청 시작 시간
        start_time = time.time()
        
        # 실행 ID 생성
        run_id = str(uuid.uuid4())[:8]
        set_run_id(run_id)
        
        # 요청 정보 로깅
        logger.info(
            f"요청 시작: {request.method} {request.url.path}",
            extra={
                "extra_fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": dict(request.query_params),
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                    "run_id": run_id
                }
            }
        )
        
        try:
            # 요청 처리
            response = await call_next(request)
            
            # 응답 시간 계산
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 운영 메트릭 카운터 증가 (성공한 요청만)
            self._increment_operation_counter(request.url.path)
            
            # 응답 로깅
            log_api_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                run_id=run_id
            )
            
            # 응답 헤더에 실행 정보 추가
            response.headers["X-Run-ID"] = run_id
            response.headers["X-Response-Time"] = str(duration_ms)
            
            return response
            
        except Exception as e:
            # 오류 발생 시 로깅 (카운터는 증가하지 않음 - 실패한 요청)
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"요청 처리 중 오류: {str(e)}",
                exc_info=True,
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": duration_ms,
                        "run_id": run_id,
                        "error": str(e)
                    }
                }
            )
            
            # 오류 응답 반환
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "내부 서버 오류가 발생했습니다",
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "run_id": run_id
                },
                headers={
                    "X-Run-ID": run_id,
                    "X-Response-Time": str(duration_ms)
                }
            )
        
        finally:
            # 컨텍스트 정리
            clear_context()
    
    def _increment_operation_counter(self, path: str):
        """운영 메트릭 카운터 증가"""
        try:
            with self._lock:
                # 경로별 카운터 증가 (클래스 변수 사용)
                if "/search" in path:
                    type(self)._op_metrics["search"] += 1
                elif "/generate" in path:
                    type(self)._op_metrics["generate"] += 1
                elif "/crawl" in path:
                    type(self)._op_metrics["crawl"] += 1
                elif "/upload" in path:
                    type(self)._op_metrics["upload"] += 1
        except Exception:
            # 메트릭 수집 실패 시 무시
            pass


class RateLimitMiddleware(BaseHTTPMiddleware):
    """속도 제한 미들웨어"""
    
    def __init__(self, app, calls_per_minute: int = 60):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.requests = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # 클라이언트별 요청 기록 정리 (1분 이상 된 기록 제거)
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if current_time - req_time < 60
            ]
        else:
            self.requests[client_ip] = []
        
        # 요청 수 확인
        if len(self.requests[client_ip]) >= self.calls_per_minute:
            logger.warning(
                f"속도 제한 초과: {client_ip}",
                extra={
                    "extra_fields": {
                        "client_ip": client_ip,
                        "requests_count": len(self.requests[client_ip]),
                        "limit": self.calls_per_minute
                    }
                }
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": "요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
                    "error_code": "RATE_LIMIT_EXCEEDED"
                }
            )
        
        # 요청 기록 추가
        self.requests[client_ip].append(current_time)
        
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """보안 헤더 미들웨어"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # 보안 헤더 추가
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # 개발 환경이 아닌 경우 HTTPS 강제
        settings = get_settings()
        if not settings.debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


def setup_cors(app):
    """CORS 설정"""
    settings = get_settings()
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )


def setup_middleware(app):
    """미들웨어 설정"""
    settings = get_settings()
    
    # 보안 헤더 미들웨어 (가장 먼저)
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 속도 제한 미들웨어
    app.add_middleware(RateLimitMiddleware, calls_per_minute=100)
    
    # 요청 로깅 미들웨어 (가장 나중에)
    app.add_middleware(RequestLoggingMiddleware)
    
    # CORS 설정
    setup_cors(app)
    
    logger.info("미들웨어 설정 완료")
