#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
구조화된 JSON 로깅 설정
"""
import json
import logging
import sys
from typing import Any, Dict

class JsonFormatter(logging.Formatter):
    """JSON 형태로 로그를 포맷하는 클래스"""
    
    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드를 JSON 형태로 변환"""
        base = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # 추가 필드가 있으면 포함
        if hasattr(record, 'args') and record.args and isinstance(record.args, dict):
            base.update(record.args)
        
        # 예외 정보가 있으면 포함
        if record.exc_info:
            base["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(base, ensure_ascii=False)

def setup_logging():
    """구조화된 로깅 설정"""
    # 기존 핸들러 제거
    root = logging.getLogger()
    root.handlers.clear()
    
    # JSON 포맷터로 스트림 핸들러 설정
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    
    # 루트 로거에 핸들러 추가
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    
    # 특정 로거들 설정
    logging.getLogger("ops").setLevel(logging.INFO)
    logging.getLogger("job").setLevel(logging.INFO)
    logging.getLogger("lsc").setLevel(logging.INFO)

# 로깅 설정 자동 실행
setup_logging()






