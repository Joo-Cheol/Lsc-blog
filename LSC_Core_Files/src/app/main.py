#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 메인 애플리케이션
"""
import logging, json, time, uuid
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os
import sys

# Prometheus 지표
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# 구조화된 로깅 설정
from .logging_setup import setup_logging

# 보안 및 레이트 리밋
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from .security import require_api_key, require_api_key_strict, get_cors_origins, get_api_key_hash
from src.infra.cache import cache_get, cache_set, CACHE_SEARCH, PROMPT_VER
from src.infra.kv import push_history, list_history, add_fav, list_fav, is_fav, remove_fav
from src.jobs.scheduler import start_scheduler, get_scheduler_status

# src 경로를 Python 경로에 추가
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from src.llm.services.generator import generate_blog
from src.llm.clients.gemini_client import GeminiClient
from src.config.settings import settings
from src.search.retriever import retrieve
from src.search.fact_snippets import compress_to_facts

# 로깅 설정
logger = logging.getLogger("lsc")
ops_logger = logging.getLogger("ops")

# Prometheus 지표 정의
REQ_COUNT = Counter("http_requests_total", "Total HTTP Requests", ["method", "path", "status"])
REQ_LATENCY = Histogram("http_request_seconds", "Request latency by path", ["path"])
SEARCH_COUNT = Counter("search_requests_total", "Total search requests", ["status"])
GENERATE_COUNT = Counter("generate_requests_total", "Total blog generation requests", ["status"])

# 레이트 리밋 설정 (Redis 사용)
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/1")
limiter = Limiter(key_func=get_remote_address, storage_uri=redis_url)

app = FastAPI(
    title="LSC Blog Generator API",
    description="법무법인 블로그 생성 API",
    version="1.0.0"
)

# 레이트 리밋 미들웨어 추가
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=False,
    allow_methods=["POST","GET","OPTIONS"],
    allow_headers=["*"],
)

# 레이트 리밋 예외 처리
@app.exception_handler(RateLimitExceeded)
def ratelimit_handler(request, exc):
    return JSONResponse(
        {"error": "rate_limited", "detail": "Too many requests"}, 
        status_code=429
    )

# Prometheus 지표 수집 미들웨어
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    elapsed_time = time.perf_counter() - start_time
    
    # Prometheus 지표 수집
    path = request.url.path
    REQ_COUNT.labels(method=request.method, path=path, status=response.status_code).inc()
    REQ_LATENCY.labels(path=path).observe(elapsed_time)
    
    return response

# 요청 로깅 미들웨어
@app.middleware("http")
async def request_logger(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.perf_counter()
    try:
        response = await call_next(request)
        status = response.status_code
        ok = 200 <= status < 400
        elapsed_ms = round((time.perf_counter()-start)*1000, 1)
        logger.info(json.dumps({
            "type": "access", "req_id": req_id, "method": request.method,
            "path": request.url.path, "status": status, "ms": elapsed_ms, "ok": ok
        }, ensure_ascii=False))
        response.headers["X-Request-ID"] = req_id
        return response
    except Exception as e:
        elapsed_ms = round((time.perf_counter()-start)*1000, 1)
        logger.error(json.dumps({
            "type": "error", "req_id": req_id, "path": request.url.path,
            "error": str(e), "ms": elapsed_ms
        }, ensure_ascii=False))
        raise

# 보안 헤더 미들웨어
@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"]="nosniff"
    resp.headers["X-Frame-Options"]="DENY"
    resp.headers["Referrer-Policy"]="no-referrer"
    return resp

class BlogRequest(BaseModel):
    topic: str
    keywords: str

class BlogResponse(BaseModel):
    success: bool
    provider: str
    topic: str
    text: str
    qc: Dict[str, Any]
    error: str = None

class SearchRequest(BaseModel):
    query: str
    where: dict | None = None
    k: int | None = None
    user_id: str | None = None  # 사용자 ID (히스토리/즐겨찾기용)

# 정적 파일 서빙 (방어적)
WEB_DIR = os.path.join(BASE_DIR, "web")
if os.path.isdir(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

@app.get("/")
async def root():
    index = os.path.join(WEB_DIR, "index.html")
    return FileResponse(index) if os.path.exists(index) else {"ok": True, "message": "Web UI not found"}

@app.get("/metrics")
def metrics():
    """Prometheus 지표 엔드포인트"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/api/scheduler/status")
def scheduler_status():
    """스케줄러 상태 조회"""
    try:
        return get_scheduler_status()
    except Exception as e:
        logger.error(f"Scheduler status error: {e}")
        return {"error": str(e)}

@app.get("/api")
async def api_info():
    return {"message": "LSC Blog Generator API", "version": "1.0.0"}

@app.get("/health/ready")
async def health_ready():
    """레디니스 체크 - 검색 샘플 1건 시도"""
    try:
        # 검색 샘플 1건 시도
        from src.search.retriever import retrieve
        sample_hits = retrieve("ping", k=1)
        
        # 벡터 스토어 상태 확인
        from simple_vector_store import get_store
        store = get_store()
        store_status = "ok" if store and len(store.documents) > 0 else "empty"
        
        return {
            "status": "ready",
            "search_test": "ok",
            "vector_store": store_status,
            "doc_count": len(store.documents) if store else 0,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "not_ready",
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/health/live")
def liveness():
    return {"ok": True}

@app.get("/health/ready")
def readiness():
    ok = bool(settings.GEMINI_API_KEY and settings.GEMINI_MODEL)
    detail = []
    if not settings.GEMINI_API_KEY: detail.append("GEMINI_API_KEY missing")
    if not settings.GEMINI_MODEL: detail.append("GEMINI_MODEL missing")
    # 가벼운 모델 핑(실패해도 서비스 자체는 살려 둠)
    model_ping = "skip"
    try:
        if ok:
            client = GeminiClient()
            model_ping = "ok"
    except Exception as e:
        model_ping = f"fail: {e}"
        ok = False
    
    # Chroma 스토어 핑 (간단한 벡터 스토어 사용 시 건너뛰기)
    chroma_ping = "skip"
    try:
        # 간단한 벡터 스토어 사용 중인지 확인
        from simple_vector_store import get_store
        _ = get_store()  # ping
        chroma_ping = "ok (simple store)"
    except ImportError:
        # ChromaDB 사용 시도
        try:
            from src.search.store import get_collection
            _ = get_collection()  # ping
            chroma_ping = "ok (chromadb)"
        except Exception as e:
            chroma_ping = f"fail: {e}"
            ok = False
            detail.append(f"chroma_fail: {e}")
    except Exception as e:
        chroma_ping = f"fail: {e}"
        ok = False
        detail.append(f"store_fail: {e}")
    
    return {
        "ok": ok, 
        "model_ping": model_ping, 
        "chroma_ping": chroma_ping,
        "detail": detail or "ok"
    }

@app.post("/api/search")
@limiter.limit("5/second")  # 검색은 조금 여유
def api_search(req: SearchRequest, request: Request):
    """검색 API"""
    try:
        # 캐시 키 생성
        cache_payload = {
            "q": req.query, 
            "where": req.where, 
            "k": req.k,
            "pv": PROMPT_VER
        }
        
        # 캐시에서 조회
        cached = cache_get(CACHE_SEARCH, cache_payload)
        if cached:
            hits = cached["hits"]
            ops_logger.info("search_cache_hit", extra={"query": req.query})
        else:
            # 실제 검색 수행
            hits = retrieve(req.query, req.where, req.k)
            
            # 캐시에 저장 (15분)
            cache_set(CACHE_SEARCH, cache_payload, {"hits": hits}, ttl=900)
        
        # 사용자 히스토리에 추가
        if req.user_id:
            push_history(req.user_id, req.query)
        
        # Prometheus 지표 수집
        SEARCH_COUNT.labels(status="success").inc()
        
        # 검색 품질 로그 남기기
        ops_logger.info("search_result", extra={
            "type": "search",
            "q": req.query,
            "k": len(hits),
            "cached": cached is not None,
            "results": [
                {
                    "id": h["id"],
                    "sim": round(h["sim"], 4),
                    "bm25": round(h.get("bm25", 0), 4),
                    "combo": round(h.get("combo", 0), 4)
                } for h in hits
            ]
        })
        
        return {
            "query": req.query,
            "k": len(hits),
            "results": [
                {
                    "id": h["id"], 
                    "title": h["meta"].get("title"), 
                    "url": h["meta"].get("url"),
                    "sim": h["sim"], 
                    "snippet": compress_to_facts(h["text"], 2)
                }
                for h in hits
            ]
        }
    except Exception as e:
        SEARCH_COUNT.labels(status="error").inc()
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate")
@limiter.limit("1/second", key_func=get_api_key_hash)  # API Key 기반 레이트리밋
def api_generate(req: BlogRequest, request: Request, _: bool = Depends(require_api_key_strict)):
    """블로그 생성 API"""
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    
    try:
        out = generate_blog(req.model_dump())
        success = out.get("success", bool(out.get("qc", {}).get("passed")))
        
        # Prometheus 지표 수집
        GENERATE_COUNT.labels(status="success" if success else "qc_failed").inc()
        
        # 생성 품질 로그 남기기
        ops_logger.info("generate_result", extra={
            "req_id": req_id,
            "type": "generate",
            "topic": req.topic,
            "success": success,
            "length": len(out.get("text", "")),
            "qc_passed": out.get("qc", {}).get("passed", False),
            "plag_score": out.get("plag_score", 0.0)
        })
        
        return {**out, "success": success, "req_id": req_id}
    except Exception as e:
        GENERATE_COUNT.labels(status="error").inc()
        
        # 오류 카테고리 분류
        error_category = "unknown"
        if "quota" in str(e).lower() or "limit" in str(e).lower():
            error_category = "quota"
        elif "network" in str(e).lower() or "timeout" in str(e).lower():
            error_category = "network"
        elif "qc" in str(e).lower() or "quality" in str(e).lower():
            error_category = "qc_fail"
        elif "auth" in str(e).lower() or "unauthorized" in str(e).lower():
            error_category = "auth"
        
        logger.error(f"Generate error: {e}", extra={
            "req_id": req_id,
            "error_category": error_category,
            "topic": req.topic
        })
        
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "req_id": req_id,
                "category": error_category,
                "topic": req.topic
            }
        )

@app.get("/api/history/{user_id}")
def get_search_history(user_id: str):
    """검색 히스토리 조회"""
    try:
        history = list_history(user_id)
        return {"user_id": user_id, "history": history}
    except Exception as e:
        logger.error(f"History error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/favorites/{user_id}")
def get_favorites(user_id: str):
    """즐겨찾기 조회"""
    try:
        favorites = list_fav(user_id)
        return {"user_id": user_id, "favorites": list(favorites)}
    except Exception as e:
        logger.error(f"Favorites error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/favorites/{user_id}")
def toggle_favorite(user_id: str, query: str):
    """즐겨찾기 토글"""
    try:
        if is_fav(user_id, query):
            remove_fav(user_id, query)
            action = "removed"
        else:
            add_fav(user_id, query)
            action = "added"
        
        return {"user_id": user_id, "query": query, "action": action}
    except Exception as e:
        logger.error(f"Toggle favorite error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    try:
        start_scheduler()
        logger.info("백그라운드 스케줄러 시작됨")
    except Exception as e:
        logger.error(f"스케줄러 시작 실패: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행"""
    try:
        from src.jobs.scheduler import stop_scheduler
        stop_scheduler()
        logger.info("백그라운드 스케줄러 중지됨")
    except Exception as e:
        logger.error(f"스케줄러 중지 실패: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
