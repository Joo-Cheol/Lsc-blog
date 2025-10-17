#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
캐싱 시스템
"""
import hashlib
import json
import time
from typing import Any, Dict, Optional
from .kv import r

def _key(ns: str, payload: Dict[str, Any]) -> str:
    """캐시 키 생성"""
    payload_str = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return f"{ns}:{hashlib.md5(payload_str.encode()).hexdigest()}"

def cache_get(ns: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """캐시에서 데이터 조회"""
    try:
        v = r.get(_key(ns, payload))
        return json.loads(v) if v else None
    except Exception:
        return None

def cache_set(ns: str, payload: Dict[str, Any], data: Dict[str, Any], ttl: int = 3600):
    """캐시에 데이터 저장"""
    try:
        r.setex(_key(ns, payload), ttl, json.dumps(data, ensure_ascii=False))
    except Exception:
        pass  # 캐시 실패해도 서비스는 계속

def cache_invalidate(ns: str, pattern: str = "*"):
    """캐시 무효화 (패턴 매칭)"""
    try:
        keys = r.keys(f"{ns}:{pattern}")
        if keys:
            r.delete(*keys)
    except Exception:
        pass

# 캐시 네임스페이스 상수
CACHE_SEARCH = "search"
CACHE_GENERATE = "generate"
CACHE_EMBED = "embed"

# 프롬프트 버전 (변경 시 자동 무효화)
PROMPT_VER = "v4.2"






