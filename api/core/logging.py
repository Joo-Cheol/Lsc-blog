#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
구조화된 로깅 설정
"""
import logging
import json
import sys
import time
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
from .config import get_settings

# 컨텍스트 변수
run_id_var: ContextVar[Optional[str]] = ContextVar('run_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


class JSONFormatter(logging.Formatter):
    """JSON 형태의 로그 포맷터"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 컨텍스트 정보 추가
        if run_id := run_id_var.get():
            log_entry["run_id"] = run_id
        
        if user_id := user_id_var.get():
            log_entry["user_id"] = user_id
        
        # 예외 정보 추가
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # 추가 필드 추가
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry, ensure_ascii=False)


class StandardFormatter(logging.Formatter):
    """표준 형태의 로그 포맷터"""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def format(self, record: logging.LogRecord) -> str:
        # 컨텍스트 정보 추가
        context_info = []
        if run_id := run_id_var.get():
            context_info.append(f"run_id={run_id}")
        if user_id := user_id_var.get():
            context_info.append(f"user_id={user_id}")
        
        if context_info:
            record.msg = f"[{' '.join(context_info)}] {record.msg}"
        
        return super().format(record)


def setup_logging():
    """로깅 설정 초기화"""
    settings = get_settings()
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler(sys.stdout)
    
    if settings.log_format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = StandardFormatter()
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 파일 핸들러 추가 (프로덕션 환경)
    if not settings.debug:
        try:
            # logs 디렉토리 생성
            import os
            os.makedirs("logs", exist_ok=True)
            file_handler = logging.FileHandler("logs/api.log", encoding="utf-8")
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            # 파일 핸들러 생성 실패 시 콘솔 핸들러만 사용
            pass
    
    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """로거 인스턴스 조회"""
    return logging.getLogger(name)


def set_run_id(run_id: str):
    """실행 ID 설정"""
    run_id_var.set(run_id)


def set_user_id(user_id: str):
    """사용자 ID 설정"""
    user_id_var.set(user_id)


def clear_context():
    """컨텍스트 변수 초기화"""
    run_id_var.set(None)
    user_id_var.set(None)


class LoggerMixin:
    """로깅 믹스인 클래스"""
    
    @property
    def logger(self) -> logging.Logger:
        return get_logger(self.__class__.__name__)


def log_function_call(func_name: str, **kwargs):
    """함수 호출 로깅"""
    logger = get_logger("function_call")
    logger.info(f"함수 호출: {func_name}", extra={
        "extra_fields": {
            "function": func_name,
            "parameters": kwargs
        }
    })


def log_performance(operation: str, duration_ms: int, **metadata):
    """성능 로깅"""
    logger = get_logger("performance")
    logger.info(f"성능 측정: {operation}", extra={
        "extra_fields": {
            "operation": operation,
            "duration_ms": duration_ms,
            **metadata
        }
    })


def log_api_request(method: str, path: str, status_code: int, duration_ms: int, **metadata):
    """API 요청 로깅"""
    logger = get_logger("api_request")
    logger.info(f"API 요청: {method} {path}", extra={
        "extra_fields": {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            **metadata
        }
    })


def log_error(error: Exception, context: Optional[Dict[str, Any]] = None):
    """오류 로깅"""
    logger = get_logger("error")
    logger.error(f"오류 발생: {str(error)}", exc_info=True, extra={
        "extra_fields": {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }
    })


def log_business_event(event: str, **data):
    """비즈니스 이벤트 로깅"""
    logger = get_logger("business")
    logger.info(f"비즈니스 이벤트: {event}", extra={
        "extra_fields": {
            "event": event,
            **data
        }
    })


# 로깅 설정 초기화
setup_logging()
