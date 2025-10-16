#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
인덱싱 API 라우터
"""
import sys
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.schemas import IndexRequest, IndexResponse
from api.core.logging import get_logger, log_business_event
from api.core.config import get_settings

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


@router.post("/index", response_model=IndexResponse)
async def index_data(request: IndexRequest):
    """데이터 인덱싱"""
    start_time = time.time()
    
    try:
        logger.info(f"인덱싱 시작: {request.run_id}")
        
        # 인덱싱 서비스 초기화
        from src.vector.simple_index import SimpleVectorIndex
        from src.vector.embedder import EmbeddingService
        from src.preprocess.normalize import TextNormalizer
        from src.preprocess.chunking import SemanticChunker
        
        # 임베딩 서비스 초기화
        embedder = EmbeddingService(
            model_name=settings.embed_model,
            device=settings.embed_device
        )
        
        # 벡터 인덱스 초기화
        index = SimpleVectorIndex(
            index_path=settings.chroma_dir,
            embedder=embedder
        )
        
        # 텍스트 정규화 및 청킹 초기화
        normalizer = TextNormalizer()
        chunker = SemanticChunker(
            max_tokens=384,
            overlap_tokens=40
        )
        
        # 실제 인덱싱 로직 (여기서는 시뮬레이션)
        # TODO: 실제 크롤링된 데이터를 읽어서 인덱싱
        
        # 시뮬레이션 결과
        added_count = 0
        skipped_count = 0
        total_chunks = 0
        
        # 실행 시간 계산
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 비즈니스 이벤트 로깅
        log_business_event(
            "index_completed",
            run_id=request.run_id,
            added_count=added_count,
            skipped_count=skipped_count,
            total_chunks=total_chunks,
            duration_ms=duration_ms
        )
        
        logger.info(f"인덱싱 완료: added={added_count}, skipped={skipped_count}")
        
        return IndexResponse(
            success=True,
            run_id=request.run_id,
            added_count=added_count,
            skipped_count=skipped_count,
            total_chunks=total_chunks,
            duration_ms=duration_ms,
            message=f"인덱싱이 성공적으로 완료되었습니다. {added_count}개 청크가 추가되었습니다."
        )
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"인덱싱 실패: {e}", exc_info=True)
        
        # 비즈니스 이벤트 로깅
        log_business_event(
            "index_failed",
            run_id=request.run_id,
            error=str(e),
            duration_ms=duration_ms
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"인덱싱 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/index/stats")
async def get_index_stats():
    """인덱스 통계 조회"""
    try:
        # 벡터 인덱스 통계 조회
        from src.vector.simple_index import SimpleVectorIndex
        from src.vector.embedder import EmbeddingService
        
        embedder = EmbeddingService(
            model_name=settings.embed_model,
            device=settings.embed_device
        )
        
        index = SimpleVectorIndex(
            index_path=settings.chroma_dir,
            embedder=embedder
        )
        
        stats = index.get_index_stats()
        
        return {
            "success": True,
            "stats": stats,
            "message": "인덱스 통계를 성공적으로 조회했습니다"
        }
        
    except Exception as e:
        logger.error(f"인덱스 통계 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"인덱스 통계 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.delete("/index")
async def clear_index():
    """인덱스 초기화"""
    try:
        logger.info("인덱스 초기화 시작")
        
        # 인덱스 파일 삭제
        import shutil
        import os
        
        if os.path.exists(settings.chroma_dir):
            shutil.rmtree(settings.chroma_dir)
            os.makedirs(settings.chroma_dir, exist_ok=True)
        
        # 비즈니스 이벤트 로깅
        log_business_event("index_cleared")
        
        logger.info("인덱스 초기화 완료")
        
        return {
            "success": True,
            "message": "인덱스가 성공적으로 초기화되었습니다"
        }
        
    except Exception as e:
        logger.error(f"인덱스 초기화 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"인덱스 초기화 중 오류가 발생했습니다: {str(e)}"
        )
