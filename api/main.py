#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 메인 애플리케이션
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트 설정 (sys.path 조작 대신 상대 import 사용)
project_root = Path(__file__).parent.parent

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from contextlib import asynccontextmanager
from .core.config import get_settings, validate_settings
from .core.logging import get_logger, setup_logging
from .core.middleware import setup_middleware
from .routes import crawl, index, search, generate, upload
from .schemas import HealthResponse, ErrorResponse, StatsResponse, ConfigResponse

# 로깅 설정
setup_logging()
logger = get_logger(__name__)

# 설정 검증
config_errors = validate_settings()
if config_errors:
    logger.error("설정 검증 실패", extra={
        "extra_fields": {"errors": config_errors}
    })
    sys.exit(1)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시간 기록 (uvicorn 모듈 실행에서도 정확한 uptime 보장)
    import time
    app.state.start_time = time.time()
    logger.debug(f"Application start_time initialized: {app.state.start_time}")
    
    # 시작 시 실행
    logger.info("애플리케이션 시작", extra={
        "extra_fields": {
            "app_name": settings.app_name,
            "version": settings.app_version,
            "debug": settings.debug
        }
    })
    
    # 초기화 작업
    try:
        # 필요한 디렉토리 생성
        os.makedirs("logs", exist_ok=True)
        os.makedirs("src/data/meta", exist_ok=True)
        os.makedirs("src/data/processed", exist_ok=True)
        os.makedirs("src/data/indexes", exist_ok=True)
        os.makedirs("data", exist_ok=True)
        
        logger.info("초기화 완료")
        
    except Exception as e:
        logger.error(f"초기화 실패: {e}", exc_info=True)
        raise
    
    yield
    
    # 종료 시 실행
    logger.info("애플리케이션 종료")


# FastAPI 앱 생성
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="네이버 블로그 자동화 API - 크롤링, 검색, 생성, 업로드",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# 미들웨어 설정
setup_middleware(app)


# 전역 예외 처리기
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """HTTP 예외 처리"""
    logger.warning(f"HTTP 예외: {exc.status_code} - {exc.detail}")
    
    payload = {
        "error": exc.detail,
        "error_code": f"HTTP_{exc.status_code}",
        "timestamp": datetime.utcnow(),
        "path": str(request.url.path),
        "run_id": getattr(request.state, "run_id", None)
    }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(payload)
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """일반 예외 처리"""
    logger.error(f"예상치 못한 오류: {str(exc)}", exc_info=True)
    
    payload = {
        "error": "내부 서버 오류가 발생했습니다",
        "error_code": "INTERNAL_SERVER_ERROR",
        "timestamp": datetime.utcnow(),
        "path": str(request.url.path),
        "run_id": getattr(request.state, "run_id", None)
    }
    
    return JSONResponse(
        status_code=500,
        content=jsonable_encoder(payload)
    )


# 라우터 등록
app.include_router(crawl.router, prefix="/api/v1", tags=["crawl"])
app.include_router(index.router, prefix="/api/v1", tags=["index"])
app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(generate.router, prefix="/api/v1", tags=["generate"])
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])


# 기본 엔드포인트
@app.get("/", response_model=dict)
async def root():
    """루트 엔드포인트"""
    return {
        "message": "LSC Blog Automation API",
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "문서는 개발 환경에서만 제공됩니다"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check(return_503_on_degraded: bool = False):
    """헬스 체크"""
    from datetime import datetime
    import time
    
    # Provider 상태 확인
    try:
        from src.llm.provider_manager import get_provider_manager
        manager = get_provider_manager()
        provider_health = manager.health_check()
    except Exception as e:
        logger.error(f"Provider 상태 확인 실패: {e}")
        provider_health = {"overall_status": "unhealthy", "providers": {}}
    
    # 데이터베이스 상태 확인
    db_status = {"status": "unknown"}
    try:
        import sqlite3
        if os.path.exists(settings.seen_db):
            conn = sqlite3.connect(settings.seen_db)
            conn.execute("SELECT 1")
            conn.close()
            db_status = {"status": "healthy"}
        else:
            db_status = {"status": "not_initialized"}
    except Exception as e:
        db_status = {"status": "error", "error": str(e)}
    
    # ChromaDB 상태 확인
    chroma_status = {"status": "unknown"}
    try:
        from src.vector.chroma_index import chroma_indexer
        stats = chroma_indexer.get_collection_stats()
        if "error" not in stats:
            chroma_status = {
                "status": "healthy",
                "total_documents": stats.get("total_documents", 0),
                "collection_name": stats.get("collection_name", "unknown")
            }
        else:
            chroma_status = {"status": "error", "error": stats["error"]}
    except Exception as e:
        chroma_status = {"status": "error", "error": str(e)}
    
    # 임베딩 캐시 상태 확인
    cache_status = {"status": "unknown"}
    try:
        from src.vector.embedder import embedding_cache
        cache_stats = embedding_cache.get_cache_stats()
        
        # hit_rate 계산
        total_accesses = cache_stats.get("total_accesses", 0)
        total_embeddings = cache_stats.get("total_embeddings", 0)
        if total_accesses > 0:
            hits = total_accesses - total_embeddings
            hit_rate = (hits / total_accesses) * 100
        else:
            hit_rate = 0.0
        
        cache_status = {
            "status": "healthy",
            "total_embeddings": total_embeddings,
            "total_accesses": total_accesses,
            "hit_rate": f"{hit_rate:.1f}%"
        }
    except Exception as e:
        cache_status = {"status": "error", "error": str(e)}
    
    # 전체 상태 결정
    overall_status = "healthy"
    if (provider_health["overall_status"] != "healthy" or 
        db_status["status"] not in ["healthy", "not_initialized"] or
        chroma_status["status"] == "error"):
        overall_status = "degraded"
    
    health_response = HealthResponse(
        status=overall_status,
        timestamp=datetime.now(),
        version=settings.app_version,
        providers=provider_health["providers"],
        database=db_status,
        chroma=chroma_status,
        embedding_cache=cache_status,
        uptime_seconds=int(time.time() - app.state.start_time) if hasattr(app.state, 'start_time') else 0
    )
    
    # degraded 상태에서 503 반환 옵션
    if return_503_on_degraded and overall_status == "degraded":
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=health_response.dict())
    
    return health_response


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """통계 정보 조회"""
    try:
        # 크롤러 통계
        crawler_stats = {"total_posts": 0, "last_crawl": None}
        try:
            from src.crawler.storage import crawler_storage
            crawler_stats = crawler_storage.get_crawl_stats()
        except Exception as e:
            logger.error(f"크롤러 통계 조회 실패: {e}")
        
        # ChromaDB 통계
        chroma_stats = {"total_documents": 0, "last_index": None}
        try:
            from src.vector.chroma_index import chroma_indexer
            chroma_data = chroma_indexer.get_collection_stats()
            chroma_stats = {
                "total_documents": chroma_data.get("total_documents", 0),
                "last_updated": chroma_data.get("last_updated", None),
                "sources": chroma_data.get("sources", {}),
                "topics": chroma_data.get("topics", {})
            }
        except Exception as e:
            logger.error(f"ChromaDB 통계 조회 실패: {e}")
        
        # 임베딩 캐시 통계
        cache_stats = {"total_embeddings": 0, "hit_rate": "N/A"}
        try:
            from src.vector.embedder import embedding_cache
            cache_data = embedding_cache.get_cache_stats()
            cache_stats = {
                "total_embeddings": cache_data.get("total_embeddings", 0),
                "total_accesses": cache_data.get("total_accesses", 0),
                "avg_accesses": cache_data.get("avg_accesses", 0),
                "accessed_today": cache_data.get("accessed_today", 0),
                "accessed_week": cache_data.get("accessed_week", 0)
            }
        except Exception as e:
            logger.error(f"임베딩 캐시 통계 조회 실패: {e}")
        
        # Provider 통계
        provider_stats = {}
        try:
            from src.llm.provider_manager import get_provider_manager
            manager = get_provider_manager()
            providers = manager.list_providers()
            provider_stats = providers
        except Exception as e:
            logger.error(f"Provider 통계 조회 실패: {e}")
        
        # 운영 메트릭 카운터 가져오기
        op_metrics = {"search": 0, "generate": 0, "crawl": 0, "upload": 0}
        try:
            from api.core.middleware import RequestLoggingMiddleware
            # 미들웨어 인스턴스에서 카운터 가져오기
            for middleware in app.user_middleware:
                if middleware.cls is RequestLoggingMiddleware:
                    if hasattr(middleware.cls, '_op_metrics'):
                        op_metrics = middleware.cls._op_metrics
                    break
        except Exception as e:
            logger.error(f"운영 메트릭 조회 실패: {e}")
        
        # 통합 통계
        stats = {
            "total_posts": crawler_stats.get("total_posts", 0),
            "total_chunks": chroma_stats.get("total_documents", 0),
            "total_searches": op_metrics.get("search", 0),
            "total_generations": op_metrics.get("generate", 0),
            "total_crawls": op_metrics.get("crawl", 0),
            "total_uploads": op_metrics.get("upload", 0),
            "last_crawl": crawler_stats.get("last_crawl", None),
            "last_index": chroma_stats.get("last_updated", None),
            "provider_stats": provider_stats,
            "crawler_stats": crawler_stats,
            "chroma_stats": chroma_stats,
            "cache_stats": cache_stats,
            "operation_metrics": op_metrics
        }
        
        return StatsResponse(success=True, **stats)
        
    except Exception as e:
        logger.error(f"통계 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="통계 조회에 실패했습니다")


@app.get("/config", response_model=ConfigResponse)
async def get_config():
    """설정 정보 조회"""
    try:
        from src.llm.provider_manager import get_provider_manager
        manager = get_provider_manager()
        providers = manager.list_providers()
        available_providers = [name for name, info in providers.items() if info.get("available", False)]
        
        return ConfigResponse(
            success=True,
            llm_provider=settings.llm_provider,
            available_providers=available_providers,
            embed_model=settings.embed_model,
            rerank_model=settings.rerank_model,
            upload_enabled=settings.upload_enabled,
            max_pages_per_crawl=settings.max_pages_per_crawl,
            quality_guard_enabled=True
        )
        
    except Exception as e:
        logger.error(f"설정 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="설정 조회에 실패했습니다")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )