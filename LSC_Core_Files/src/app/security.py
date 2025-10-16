#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 보안 관련 기능
"""
import os
from fastapi import Header, HTTPException, Depends, Request
from typing import Optional

# API 키 인증
API_KEY = os.getenv("API_KEY")
ENFORCE_API_KEY = os.getenv("ENFORCE_API_KEY", "false").lower() == "true"

async def require_api_key(x_api_key: Optional[str] = Header(None)):
    """API 키 인증 검증 (선택적)"""
    if not API_KEY:
        if ENFORCE_API_KEY:
            raise HTTPException(status_code=500, detail="API_KEY not configured")
        return True  # API 키가 설정되지 않은 경우 인증 생략
    
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(
            status_code=401, 
            detail="Unauthorized: Invalid or missing API key"
        )
    return True

async def require_api_key_strict(x_api_key: Optional[str] = Header(None)):
    """API 키 인증 검증 (무조건 강제)"""
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API_KEY not configured")
    
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(
            status_code=401, 
            detail="Unauthorized: Invalid or missing API key"
        )
    return True

def get_api_key_hash(request: Request) -> str:
    """API 키 해시 기반 레이트리밋 키 함수 (멀티 테넌트 지원)"""
    import hashlib
    
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # API 키 해시로 멀티 테넌트 지원
        return hashlib.md5(api_key.encode()).hexdigest()[:8]
    else:
        # API 키가 없으면 IP 기반
        from slowapi.util import get_remote_address
        return get_remote_address(request)

# CORS 화이트리스트 설정
def get_cors_origins():
    """CORS 허용 오리진 목록"""
    origins_str = os.getenv("CORS_ORIGINS", "https://yourdomain.com")
    return [origin.strip() for origin in origins_str.split(",") if origin.strip()]
