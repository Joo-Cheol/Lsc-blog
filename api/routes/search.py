#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
검색 API 라우터
"""
import sys
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.schemas import SearchRequest, SearchResponse, SearchResult
from api.core.logging import get_logger, log_business_event
from api.core.config import get_settings

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """문서 검색"""
    start_time = time.time()
    
    try:
        logger.info(f"검색 시작: {request.query}")
        
        # 검색 서비스 초기화
        from src.search.search_service import SearchService
        from src.vector.simple_index import SimpleVectorIndex
        from src.vector.embedder import EmbeddingService
        from src.vector.reranker import CrossEncoderReranker
        
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
        
        # 리랭커 초기화
        reranker = CrossEncoderReranker(
            model_name=settings.rerank_model
        )
        
        # 검색 서비스 초기화
        search_service = SearchService(
            vector_index=index,
            reranker=reranker,
            top_k_first=settings.topk_first,
            top_k_final=settings.topk_final
        )
        
        # 검색 실행
        if request.with_rerank:
            results = search_service.search_with_rerank(
                query=request.query,
                top_k=request.top_k,
                law_topic=request.law_topic
            )
        else:
            results = search_service.search(
                query=request.query,
                top_k=request.top_k,
                law_topic=request.law_topic
            )
        
        # 검색 결과 변환
        search_results = []
        for result in results:
            search_results.append(SearchResult(
                text=result["text"],
                score=result["score"],
                metadata=result["metadata"],
                source_url=result["metadata"].get("source_url"),
                published_at=result["metadata"].get("published_at")
            ))
        
        # 검색 제안 생성
        suggestions = search_service.get_search_suggestions(request.query)
        
        # 실행 시간 계산
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 비즈니스 이벤트 로깅
        log_business_event(
            "search_completed",
            query=request.query,
            results_count=len(search_results),
            with_rerank=request.with_rerank,
            law_topic=request.law_topic,
            duration_ms=duration_ms
        )
        
        logger.info(f"검색 완료: {len(search_results)}개 결과")
        
        return SearchResponse(
            success=True,
            query=request.query,
            results=search_results,
            total_results=len(search_results),
            with_rerank=request.with_rerank,
            duration_ms=duration_ms,
            suggestions=suggestions
        )
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"검색 실패: {e}", exc_info=True)
        
        # 비즈니스 이벤트 로깅
        log_business_event(
            "search_failed",
            query=request.query,
            error=str(e),
            duration_ms=duration_ms
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"검색 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/search/suggestions")
async def get_search_suggestions(q: str = ""):
    """검색 제안 조회"""
    try:
        # 검색 서비스 초기화
        from src.search.search_service import SearchService
        from src.vector.simple_index import SimpleVectorIndex
        from src.vector.embedder import EmbeddingService
        from src.vector.reranker import CrossEncoderReranker
        
        embedder = EmbeddingService(
            model_name=settings.embed_model,
            device=settings.embed_device
        )
        
        index = SimpleVectorIndex(
            index_path=settings.chroma_dir,
            embedder=embedder
        )
        
        reranker = CrossEncoderReranker(
            model_name=settings.rerank_model
        )
        
        search_service = SearchService(
            vector_index=index,
            reranker=reranker,
            top_k_first=settings.topk_first,
            top_k_final=settings.topk_final
        )
        
        # 검색 제안 생성
        suggestions = search_service.get_search_suggestions(q)
        
        return {
            "success": True,
            "query": q,
            "suggestions": suggestions,
            "message": "검색 제안을 성공적으로 조회했습니다"
        }
        
    except Exception as e:
        logger.error(f"검색 제안 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"검색 제안 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/search/popular")
async def get_popular_searches(limit: int = 10):
    """인기 검색어 조회"""
    try:
        # 실제 구현에서는 데이터베이스에서 인기 검색어 조회
        # 여기서는 기본 응답 반환
        popular_searches = [
            "채권추심 절차",
            "지급명령 신청",
            "채권 회수 방법",
            "소액사건 절차",
            "내용증명 발송"
        ]
        
        return {
            "success": True,
            "popular_searches": popular_searches[:limit],
            "message": "인기 검색어를 성공적으로 조회했습니다"
        }
        
    except Exception as e:
        logger.error(f"인기 검색어 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"인기 검색어 조회 중 오류가 발생했습니다: {str(e)}"
        )
