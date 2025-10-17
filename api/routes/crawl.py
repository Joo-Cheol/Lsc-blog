#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
크롤링 API 라우터
"""
import sys
import time
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from typing import Dict, Any
from datetime import datetime
import re
from collections import defaultdict
import time

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.schemas import CrawlRequest, CrawlResponse
from api.core.logging import get_logger, log_business_event
from api.core.config import get_settings
from api.core.jobs import JOBS
from src.crawler.extractors import parse_blog_id
from monitoring.job_metrics import job_metrics

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()

# Rate limiting storage
_rate_limits = defaultdict(list)  # {client_ip: [timestamps]}
RATE_LIMIT_REQUESTS = 5  # 5 requests per minute
RATE_LIMIT_WINDOW = 60   # 1 minute

def _cleanup_rate_limits():
    """오래된 rate limit 기록 정리"""
    current_time = time.time()
    for client_ip in list(_rate_limits.keys()):
        _rate_limits[client_ip] = [
            ts for ts in _rate_limits[client_ip] 
            if current_time - ts < RATE_LIMIT_WINDOW
        ]
        if not _rate_limits[client_ip]:
            del _rate_limits[client_ip]

def _check_rate_limit(client_ip: str) -> bool:
    """Rate limit 체크"""
    _cleanup_rate_limits()
    current_time = time.time()
    
    # 현재 윈도우 내 요청 수 체크
    recent_requests = [
        ts for ts in _rate_limits[client_ip] 
        if current_time - ts < RATE_LIMIT_WINDOW
    ]
    
    if len(recent_requests) >= RATE_LIMIT_REQUESTS:
        return False
    
    # 새 요청 기록
    _rate_limits[client_ip].append(current_time)
    return True

def _validate_naver_blog_url(blog_url: str) -> bool:
    """네이버 블로그 URL 검증"""
    if not blog_url:
        return False
    
    # 네이버 블로그 URL 패턴
    naver_patterns = [
        r'https?://blog\.naver\.com/[^/]+/?$',
        r'https?://blog\.naver\.com/[^/]+/PostList\.naver.*',
        r'https?://blog\.naver\.com/[^/]+/PostView\.naver.*'
    ]
    
    return any(re.match(pattern, blog_url) for pattern in naver_patterns)


@router.post("/crawl")
async def crawl_blog(request: CrawlRequest, bg: BackgroundTasks, http_request: Request):
    """네이버 블로그 크롤링 (Job 기반)"""
    # Rate limiting 체크
    client_ip = http_request.client.host
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="요청이 너무 많습니다. 1분에 5회까지만 요청할 수 있습니다."
        )
    
    # URL 검증
    if request.blog_url and not _validate_naver_blog_url(str(request.blog_url)):
        raise HTTPException(
            status_code=400,
            detail="올바른 네이버 블로그 주소를 입력해주세요. (예: https://blog.naver.com/블로그ID)"
        )
    
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
                st.add_error("INVALID_INPUT", "blog_url 또는 blog_id를 제공하세요.", "올바른 네이버 블로그 주소를 입력해주세요.")
                st.finished_at = datetime.utcnow().isoformat()
                return
            
            st.push("info", "크롤링 시작", blog_id=blog_id)
            logger.info(f"크롤링 시작 - blog_id: {blog_id}, category_no: {request.category_no}")
            
            # 크롤러 초기화
            crawler = NaverBlogCrawler(
                blog_id=blog_id,
                category_no=request.category_no,
                seen_db_path=settings.seen_db,
                delay_min_ms=settings.crawl_delay_min,
                delay_max_ms=settings.crawl_delay_max
            )
            logger.info(f"크롤러 초기화 완료 - blog_id: {blog_id}")
            
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
            
            def on_event(event_type, data):
                """크롤러 이벤트 핸들러"""
                if event_type == "crawl_started":
                    st.push("info", f"크롤링 시작: {data['blog_id']}", categories=data["categories"])
                elif event_type == "category_started":
                    st.push("info", f"카테고리 {data['category_no']} 처리 시작", 
                           category_no=data["category_no"], total_categories=data["total_categories"])
                elif event_type == "page_completed":
                    st.push("info", f"페이지 {data['page']} 완료", 
                           category_no=data["category_no"], page=data["page"], posts_found=data["posts_found"])
                elif event_type == "request_error":
                    st.counters["failed"] += 1
                    st.push("warning", f"요청 실패: {data['error']}", url=data.get("url"))
            
            # 크롤링 실행
            logger.info(f"크롤링 실행 시작 - max_pages: {request.max_pages or 5}")
            stats = crawler.crawl_incremental(
                max_pages=request.max_pages or 5,
                run_id=st.id,
                on_page=on_page,
                on_new=on_new_post,
                on_skip=on_skip,
                on_event=on_event
            )
            logger.info(f"크롤링 실행 완료 - stats: {stats}")
            
            # 결과 저장
            st.results["posts"] = added_posts
            st.counters["failed"] = stats.get("failed", 0)
            st.progress = 1.0
            st.status = "succeeded"
            st.finished_at = datetime.utcnow().isoformat()
            st.push("done", "크롤링 완료", summary=stats)
            
            logger.info(f"크롤링 결과 저장 - added_posts: {len(added_posts)}, stats: {stats}")
            
            # 비즈니스 이벤트 로깅
            duration_ms = int((datetime.utcnow() - datetime.fromisoformat(st.started_at)).total_seconds() * 1000)
            log_business_event(
                "crawl_completed",
                run_id=st.id,
                blog_id=blog_id,
                category_no=request.category_no,
                max_pages=request.max_pages,
                crawled_count=len(added_posts),
                skipped_count=st.counters["skipped"],
                failed_count=st.counters["failed"],
                duration_ms=duration_ms
            )
            
            # 메트릭 기록
            job_metrics.record_operation("crawl", duration_ms, success=True)
            job_metrics.record_job_completion("crawl", duration_ms, success=True)
            
        except Exception as e:
            logger.error(f"크롤링 실패: {e}", exc_info=True)
            st.status = "failed"
            st.add_error("CRAWL_FAILED", str(e), "잠시 후 다시 시도해주세요. 문제가 지속되면 다른 블로그 주소를 시도해보세요.")
            st.finished_at = datetime.utcnow().isoformat()
            st.push("error", f"크롤링 실패: {str(e)}")
            
            logger.info(f"크롤링 실패 처리 완료 - error: {str(e)}")
            
            # 실패 메트릭 기록
            if st.started_at:
                duration_ms = int((datetime.utcnow() - datetime.fromisoformat(st.started_at)).total_seconds() * 1000)
                job_metrics.record_operation("crawl", duration_ms, success=False)
                job_metrics.record_job_completion("crawl", duration_ms, success=False)
    
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
