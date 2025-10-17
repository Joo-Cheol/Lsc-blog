#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
크롤링 API 라우터
"""
import sys
import time
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.schemas import CrawlRequest, CrawlResponse
from api.core.logging import get_logger, log_business_event
from api.core.config import get_settings
from api.core.jobs import JOBS
from src.crawler.extractors import parse_blog_id

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


@router.post("/crawl")
async def crawl_blog(request: CrawlRequest, bg: BackgroundTasks):
    """네이버 블로그 크롤링 (Job 기반)"""
    # Job 생성
    job = JOBS.create("crawl")
    
    def run():
        from src.crawler.naver_crawler import NaverBlogCrawler
        
        st = job
        st.status = "running"
        st.started_at = datetime.utcnow().isoformat()
        
        try:
            # blog_id 결정
            blog_id = request.blog_id
            if not blog_id and request.blog_url:
                blog_id = parse_blog_id(str(request.blog_url))
            
            if not blog_id:
                st.status = "failed"
                st.errors.append("blog_url 또는 blog_id를 제공하세요.")
                st.finished_at = datetime.utcnow().isoformat()
                return
            
            st.push("info", "크롤링 시작", blog_id=blog_id)
            
            # 크롤러 초기화
            crawler = NaverBlogCrawler(
                blog_id=blog_id,
                category_no=request.category_no,
                seen_db_path=settings.seen_db,
                delay_min_ms=settings.crawl_delay_min,
                delay_max_ms=settings.crawl_delay_max
            )
            
            added_posts = []
            
            def on_page(category, page):
                st.counters["pages"] += 1
                st.push("progress", f"{category} 카테고리 {page}페이지 처리중", category=category, page=page)
            
            def on_new_post(post):
                added_posts.append({
                    "title": post["title"], 
                    "url": post["url"], 
                    "logno": post.get("logno")
                })
                st.counters["new"] += 1
                st.counters["found"] += 1
                st.push("info", f"새 글: {post['title']}", url=post["url"])
            
            def on_skip(post):
                st.counters["skipped"] += 1
                st.counters["found"] += 1
                st.push("info", f"스킵: {post['title']}", url=post["url"])
            
            # 크롤링 실행
            stats = crawler.crawl_incremental(
                max_pages=request.max_pages or 5,
                run_id=st.id,
                on_page=on_page,
                on_new=on_new_post,
                on_skip=on_skip
            )
            
            # 결과 저장
            st.results["posts"] = added_posts
            st.counters["failed"] = stats.get("failed", 0)
            st.progress = 1.0
            st.status = "succeeded"
            st.finished_at = datetime.utcnow().isoformat()
            st.push("done", "크롤링 완료", summary=stats)
            
            # 비즈니스 이벤트 로깅
            log_business_event(
                "crawl_completed",
                run_id=st.id,
                blog_id=blog_id,
                category_no=request.category_no,
                max_pages=request.max_pages,
                crawled_count=len(added_posts),
                skipped_count=st.counters["skipped"],
                failed_count=st.counters["failed"],
                duration_ms=int((datetime.utcnow() - datetime.fromisoformat(st.started_at)).total_seconds() * 1000)
            )
            
        except Exception as e:
            logger.error(f"크롤링 실패: {e}", exc_info=True)
            st.status = "failed"
            st.errors.append(str(e))
            st.finished_at = datetime.utcnow().isoformat()
            st.push("error", f"크롤링 실패: {str(e)}")
    
    bg.add_task(run)
    return {"ok": True, "job_id": job.id}


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
