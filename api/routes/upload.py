#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
업로드 API 라우터
"""
import sys
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.schemas import UploadRequest, UploadResponse
from api.core.logging import get_logger, log_business_event
from api.core.config import get_settings

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


@router.post("/upload", response_model=UploadResponse)
async def upload_content(request: UploadRequest):
    """콘텐츠 업로드"""
    start_time = time.time()
    
    try:
        # 업로드 기능 활성화 확인
        if not settings.upload_enabled:
            raise HTTPException(
                status_code=403,
                detail="업로드 기능이 비활성화되어 있습니다. UPLOAD_ENABLED=true로 설정하세요."
            )
        
        logger.info(f"업로드 시작: {request.title}")
        
        # 업로드 서비스 초기화
        from src.upload.naver_post import NaverPostUploader
        
        uploader = NaverPostUploader(
            rate_limit_sec=settings.upload_rate_limit_sec
        )
        
        # 업로드 실행
        if request.auto_upload:
            # 자동 업로드 (실제 네이버 블로그에 업로드)
            result = await uploader.upload_post(
                title=request.title,
                content=request.content,
                tags=request.tags
            )
            
            post_url = result.get("post_url")
            upload_id = result.get("upload_id")
        else:
            # 시뮬레이션 모드 (실제 업로드 없이 검증만)
            result = await uploader.validate_post(
                title=request.title,
                content=request.content,
                tags=request.tags
            )
            
            post_url = None
            upload_id = f"sim_{int(time.time())}"
        
        # 실행 시간 계산
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 비즈니스 이벤트 로깅
        log_business_event(
            "upload_completed",
            title=request.title,
            auto_upload=request.auto_upload,
            tags=request.tags,
            upload_id=upload_id,
            duration_ms=duration_ms
        )
        
        logger.info(f"업로드 완료: {upload_id}")
        
        return UploadResponse(
            success=True,
            post_url=post_url,
            upload_id=upload_id,
            duration_ms=duration_ms,
            message="업로드가 성공적으로 완료되었습니다." if request.auto_upload else "업로드 검증이 완료되었습니다."
        )
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"업로드 실패: {e}", exc_info=True)
        
        # 비즈니스 이벤트 로깅
        log_business_event(
            "upload_failed",
            title=request.title,
            error=str(e),
            duration_ms=duration_ms
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"업로드 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/upload/status/{upload_id}")
async def get_upload_status(upload_id: str):
    """업로드 상태 조회"""
    try:
        # 실제 구현에서는 데이터베이스에서 상태 조회
        # 여기서는 기본 응답 반환
        return {
            "success": True,
            "upload_id": upload_id,
            "status": "completed",
            "message": "업로드 상태 조회 기능은 추후 구현 예정입니다"
        }
        
    except Exception as e:
        logger.error(f"업로드 상태 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"업로드 상태 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/upload/history")
async def get_upload_history(limit: int = 10):
    """업로드 히스토리 조회"""
    try:
        # 실제 구현에서는 데이터베이스에서 히스토리 조회
        # 여기서는 기본 응답 반환
        return {
            "success": True,
            "history": [],
            "message": "업로드 히스토리 조회 기능은 추후 구현 예정입니다"
        }
        
    except Exception as e:
        logger.error(f"업로드 히스토리 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"업로드 히스토리 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/upload/validate")
async def validate_upload_content(request: UploadRequest):
    """업로드 콘텐츠 검증"""
    try:
        logger.info(f"업로드 콘텐츠 검증: {request.title}")
        
        # 업로드 서비스 초기화
        from src.upload.naver_post import NaverPostUploader
        
        uploader = NaverPostUploader(
            rate_limit_sec=settings.upload_rate_limit_sec
        )
        
        # 콘텐츠 검증
        validation_result = await uploader.validate_post(
            title=request.title,
            content=request.content,
            tags=request.tags
        )
        
        return {
            "success": True,
            "validation_result": validation_result,
            "message": "업로드 콘텐츠 검증이 완료되었습니다"
        }
        
    except Exception as e:
        logger.error(f"업로드 콘텐츠 검증 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"업로드 콘텐츠 검증 중 오류가 발생했습니다: {str(e)}"
        )
