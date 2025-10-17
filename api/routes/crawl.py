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
from src.crawler.extractors import parse_blog_id

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


@router.post("/crawl", response_model=CrawlResponse)
async def crawl_blog(request: CrawlRequest):
    """네이버 블로그 크롤링"""
    start_time = time.time()
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # blog_id 결정 (호환성: blog_url 또는 blog_id)
        blog_id = request.blog_id
        if not blog_id and request.blog_url:
            blog_id = parse_blog_id(str(request.blog_url))
        
        if not blog_id:
            raise HTTPException(status_code=400, detail="blog_url 또는 blog_id를 제공하세요.")
        
        logger.info(f"크롤링 시작: {blog_id}, 카테고리 {request.category_no}")
        
        # 크롤러 초기화
        from src.crawler.naver_crawler import NaverBlogCrawler
        
        # 데이터베이스 경로 설정
        db_path = settings.seen_db
        
        # 크롤러 생성
        crawler = NaverBlogCrawler(
            blog_id=blog_id,
            category_no=request.category_no,
            seen_db_path=db_path,
            delay_min_ms=settings.crawl_delay_min,
            delay_max_ms=settings.crawl_delay_max
        )
        
        # 크롤링 실행 (crawl → crawl_incremental)
        results = crawler.crawl_incremental(
            max_pages=request.max_pages or 5, 
            run_id=run_id
        )
        
        # 실행 시간 계산
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 새 키셋으로 변환
        crawled = results.get("new_posts", 0) + results.get("duplicate_content", 0)
        skipped = results.get("duplicate_content", 0)
        failed = results.get("failed", 0)
        
        # 비즈니스 이벤트 로깅 (변환된 값으로)
        log_business_event(
            "crawl_completed",
            run_id=run_id,
            blog_id=blog_id,
            category_no=request.category_no,
            max_pages=request.max_pages,
            crawled_count=crawled,
            skipped_count=skipped,
            failed_count=failed,
            duration_ms=duration_ms
        )
        
        logger.info(f"크롤링 완료: {results}")
        
        # results dict를 라우트의 응답 스키마에 맞게 맵핑 (이미 위에서 계산됨)
        
        return CrawlResponse(
            success=True,
            run_id=run_id,
            crawled_count=crawled,
            skipped_count=skipped,
            failed_count=failed,
            last_logno_updated=results.get("last_logno_updated"),
            duration_ms=duration_ms,
            message=f"크롤링이 성공적으로 완료되었습니다. {crawled}개 포스트를 수집했습니다.",
            blog_id=blog_id
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
