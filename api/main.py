#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 메인 애플리케이션
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
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
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            error_code=f"HTTP_{exc.status_code}"
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """일반 예외 처리"""
    logger.error(f"예상치 못한 오류: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="내부 서버 오류가 발생했습니다",
            error_code="INTERNAL_SERVER_ERROR"
        ).dict()
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
async def health_check():
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
    
    return HealthResponse(
        status="healthy" if provider_health["overall_status"] == "healthy" else "degraded",
        timestamp=datetime.now(),
        version=settings.app_version,
        providers=provider_health["providers"],
        database=db_status,
        uptime_seconds=int(time.time() - app.state.start_time) if hasattr(app.state, 'start_time') else 0
    )


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """통계 정보 조회"""
    try:
        # 기본 통계 (실제 구현에서는 데이터베이스에서 조회)
        stats = {
            "total_posts": 0,
            "total_chunks": 0,
            "total_searches": 0,
            "total_generations": 0,
            "last_crawl": None,
            "last_index": None,
            "provider_stats": {}
        }
        
        # Provider 통계
        try:
            from src.llm.provider_manager import get_provider_manager
            manager = get_provider_manager()
            providers = manager.list_providers()
            stats["provider_stats"] = providers
        except Exception as e:
            logger.error(f"Provider 통계 조회 실패: {e}")
        
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
    
    # 시작 시간 기록
    import time
    app.state.start_time = time.time()
    
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )