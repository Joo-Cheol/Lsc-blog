#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
크롤링 API 라우터
"""
import sys
import time
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.schemas import CrawlRequest, CrawlResponse
from api.core.logging import get_logger, log_business_event
from api.core.config import get_settings

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


@router.post("/crawl", response_model=CrawlResponse)
async def crawl_blog(request: CrawlRequest):
    """네이버 블로그 크롤링"""
    start_time = time.time()
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        logger.info(f"크롤링 시작: {request.blog_id}, 카테고리 {request.category_no}")
        
        # 크롤러 초기화
        from src.crawler.naver_crawler import NaverBlogCrawler
        
        # 데이터베이스 경로 설정
        db_path = settings.seen_db
        
        # 크롤러 생성
        crawler = NaverBlogCrawler(
            blog_id=request.blog_id,
            category_no=request.category_no,
            db_path=db_path,
            headless=True,
            crawl_delay_min=settings.crawl_delay_min,
            crawl_delay_max=settings.crawl_delay_max
        )
        
        # 크롤링 실행
        results = crawler.crawl(max_pages=request.max_pages)
        
        # 실행 시간 계산
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 비즈니스 이벤트 로깅
        log_business_event(
            "crawl_completed",
            run_id=run_id,
            blog_id=request.blog_id,
            category_no=request.category_no,
            max_pages=request.max_pages,
            crawled_count=results["crawled_count"],
            skipped_count=results["skipped_count"],
            failed_count=results["failed_count"],
            duration_ms=duration_ms
        )
        
        logger.info(f"크롤링 완료: {results}")
        
        return CrawlResponse(
            success=True,
            run_id=run_id,
            crawled_count=results["crawled_count"],
            skipped_count=results["skipped_count"],
            failed_count=results["failed_count"],
            last_logno_updated=results.get("last_logno_updated"),
            duration_ms=duration_ms,
            message=f"크롤링이 성공적으로 완료되었습니다. {results['crawled_count']}개 포스트를 수집했습니다."
        )
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"크롤링 실패: {e}", exc_info=True)
        
        # 비즈니스 이벤트 로깅
        log_business_event(
            "crawl_failed",
            run_id=run_id,
            blog_id=request.blog_id,
            category_no=request.category_no,
            error=str(e),
            duration_ms=duration_ms
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"크롤링 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/crawl/status/{run_id}")
async def get_crawl_status(run_id: str):
    """크롤링 상태 조회"""
    try:
        # 실제 구현에서는 데이터베이스에서 상태 조회
        # 여기서는 기본 응답 반환
        return {
            "success": True,
            "run_id": run_id,
            "status": "completed",
            "message": "크롤링 상태 조회 기능은 추후 구현 예정입니다"
        }
        
    except Exception as e:
        logger.error(f"크롤링 상태 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"크롤링 상태 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/crawl/history")
async def get_crawl_history(limit: int = 10):
    """크롤링 히스토리 조회"""
    try:
        # 실제 구현에서는 데이터베이스에서 히스토리 조회
        # 여기서는 기본 응답 반환
        return {
            "success": True,
            "history": [],
            "message": "크롤링 히스토리 조회 기능은 추후 구현 예정입니다"
        }
        
    except Exception as e:
        logger.error(f"크롤링 히스토리 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"크롤링 히스토리 조회 중 오류가 발생했습니다: {str(e)}"
        )
