#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프로덕션 하드닝된 검색 API 서버
"""
import os
import json
import numpy as np
import time
import psutil
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from sentence_transformers import SentenceTransformer
import torch
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from functools import lru_cache
from collections import deque
import statistics
import threading
from datetime import datetime, timedelta

# ===== 환경 가드 설정 =====
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# SLO 정의
SLO_P95_LATENCY_MS = 200
SLO_ERROR_RATE = 0.005  # 0.5%
SLO_COLD_START_MS = 2000  # 2초
SLO_CACHE_HIT_RATE = 0.6  # 60%

# FastAPI 앱 초기화
app = FastAPI(
    title="Legal Blog Search API - Production",
    description="프로덕션 하드닝된 법률 블로그 검색 API",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 변수
embeddings = None
metadata = None
model = None
system_ready = False
startup_time = None

# 메트릭 수집
class MetricsCollector:
    def __init__(self):
        self.latency_history = deque(maxlen=1000)
        self.error_count = 0
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.embedding_requests = 0
        self.memmap_faults = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
    
    def record_request(self, latency_ms: float, cache_hit: bool, error: bool = False):
        with self.lock:
            self.latency_history.append(latency_ms)
            self.total_requests += 1
            if cache_hit:
                self.cache_hits += 1
            else:
                self.cache_misses += 1
            if error:
                self.error_count += 1
    
    def record_embedding_request(self):
        with self.lock:
            self.embedding_requests += 1
    
    def record_memmap_fault(self):
        with self.lock:
            self.memmap_faults += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        with self.lock:
            uptime = time.time() - self.start_time
            qps = self.total_requests / uptime if uptime > 0 else 0
            
            latencies = list(self.latency_history)
            latency_stats = {}
            if latencies:
                latency_stats = {
                    "p50": np.percentile(latencies, 50),
                    "p95": np.percentile(latencies, 95),
                    "p99": np.percentile(latencies, 99),
                    "mean": statistics.mean(latencies),
                    "min": min(latencies),
                    "max": max(latencies)
                }
            
            cache_hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
            error_rate = self.error_count / self.total_requests if self.total_requests > 0 else 0
            
            return {
                "uptime_seconds": uptime,
                "qps": qps,
                "total_requests": self.total_requests,
                "error_rate": error_rate,
                "cache_hit_rate": cache_hit_rate,
                "embedding_requests": self.embedding_requests,
                "memmap_faults": self.memmap_faults,
                "latency": latency_stats,
                "slo_status": {
                    "p95_latency_ok": latency_stats.get("p95", 0) <= SLO_P95_LATENCY_MS,
                    "error_rate_ok": error_rate <= SLO_ERROR_RATE,
                    "cache_hit_rate_ok": cache_hit_rate >= SLO_CACHE_HIT_RATE
                }
            }

metrics = MetricsCollector()

def cosine_similarity(a, b):
    """코사인 유사도 계산"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

@lru_cache(maxsize=200)  # 캐시 크기 증가
def encode_query_cached(query: str) -> tuple:
    """쿼리 임베딩 캐시 (확장)"""
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    metrics.record_embedding_request()
    
    # e5 프리픽스 적용
    prefixed_query = f"query: {query}"
    embedding = model.encode([prefixed_query], normalize_embeddings=True)[0]
    return tuple(embedding)

def load_artifacts_with_memmap():
    """메모리 매핑으로 아티팩트 로드"""
    global embeddings, metadata, model, system_ready, startup_time
    
    startup_time = time.time()
    logger.info("Starting artifact loading...")
    
    try:
        # 최신 버전 찾기
        artifacts_dir = Path("artifacts")
        if not artifacts_dir.exists():
            # 기본 경로에서 로드
            index_path = "simple_vector_index.npy"
            metadata_path = "simple_metadata.json"
        else:
            # 최신 버전 디렉토리 찾기
            versions = [d for d in artifacts_dir.iterdir() if d.is_dir()]
            if not versions:
                raise FileNotFoundError("No artifact versions found")
            
            latest_version = max(versions, key=lambda x: x.name)
            index_path = latest_version / "simple_vector_index.npy"
            metadata_path = latest_version / "simple_metadata.json"
        
        logger.info(f"Loading artifacts from: {index_path}")
        
        # 벡터 인덱스 로드 (메모리 매핑)
        embeddings = np.load(index_path, mmap_mode='r')
        logger.info(f"Loaded embeddings: {embeddings.shape}")
        
        # 메타데이터 로드
        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            metadata = {
                "ids": data["ids"],
                "metadatas": data["metadatas"],
                "documents": data["documents"]
            }
        
        logger.info(f"Loaded metadata: {len(metadata['ids'])} chunks")
        
        # 모델 로드
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading model on device: {device}")
        model = SentenceTransformer("intfloat/multilingual-e5-base", device=device)
        model.max_seq_length = 512
        
        # 워밍업 (상위 다빈도 쿼리)
        warmup_queries = [
            "채권추심", "지급명령", "압류", "제3채무자", "채권회수",
            "강제집행", "가압류", "경매", "소송", "법원"
        ]
        
        logger.info("Warming up with frequent queries...")
        for query in warmup_queries[:5]:  # 상위 5개만 워밍업
            try:
                encode_query_cached(query)
            except Exception as e:
                logger.warning(f"Warmup failed for '{query}': {e}")
        
        system_ready = True
        cold_start_time = (time.time() - startup_time) * 1000
        
        logger.info(f"✅ System ready! Cold start: {cold_start_time:.2f}ms")
        
        if cold_start_time > SLO_COLD_START_MS:
            logger.warning(f"⚠️ Cold start exceeded SLO: {cold_start_time:.2f}ms > {SLO_COLD_START_MS}ms")
        
    except Exception as e:
        logger.error(f"❌ Failed to load artifacts: {e}")
        system_ready = False
        raise

# Pydantic 모델
class SearchRequest(BaseModel):
    q: str
    top_k: int = 20
    filters: Optional[Dict[str, List[str]]] = None
    offset: int = 0
    min_similarity: float = 0.0

class SearchResult(BaseModel):
    id: str
    score: float
    title: str
    url: str
    snippet: str
    category: str
    date: str

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    query: str
    processing_time_ms: float

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    uptime_seconds: float
    cold_start_ms: float
    system_ready: bool

class MetricsResponse(BaseModel):
    metrics: Dict[str, Any]
    timestamp: str

# 미들웨어
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    latency_ms = (time.time() - start_time) * 1000
    
    # 메트릭 기록 (검색 요청만)
    if request.url.path == "/search" and request.method == "POST":
        cache_hit = False  # 실제로는 쿼리 기반으로 판단
        error = response.status_code >= 400
        metrics.record_request(latency_ms, cache_hit, error)
    
    return response

# 이벤트 핸들러
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 아티팩트 로드"""
    load_artifacts_with_memmap()

# 엔드포인트
@app.get("/healthz", response_model=HealthResponse)
async def health_check():
    """프로세스·메모리 헬스 체크"""
    process = psutil.Process()
    memory_info = process.memory_info()
    
    uptime = time.time() - metrics.start_time
    cold_start_ms = (startup_time - metrics.start_time) * 1000 if startup_time else 0
    
    return HealthResponse(
        status="healthy" if system_ready else "unhealthy",
        timestamp=datetime.now().isoformat(),
        uptime_seconds=uptime,
        cold_start_ms=cold_start_ms,
        system_ready=system_ready
    )

@app.get("/readyz")
async def readiness_check():
    """인덱스 로드 완료 체크"""
    if not system_ready:
        raise HTTPException(status_code=503, detail="System not ready")
    
    return {"status": "ready", "timestamp": datetime.now().isoformat()}

@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """메트릭 정보"""
    return MetricsResponse(
        metrics=metrics.get_metrics(),
        timestamp=datetime.now().isoformat()
    )

@app.get("/")
async def root():
    """기본 정보"""
    return {
        "service": "Legal Blog Search API",
        "version": "2.0.0",
        "status": "operational",
        "total_chunks": len(metadata["ids"]) if metadata else 0,
        "embedding_dimension": embeddings.shape[1] if embeddings is not None else 0,
        "system_ready": system_ready
    }

@app.get("/categories")
async def get_categories():
    """사용 가능한 카테고리 목록"""
    if not metadata:
        raise HTTPException(status_code=500, detail="Metadata not loaded")
    
    categories = set()
    for meta in metadata["metadatas"]:
        category = meta.get("category", "N/A")
        categories.add(category)
    
    return {"categories": sorted(list(categories))}

@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """검색 API (하드닝됨)"""
    if not system_ready:
        raise HTTPException(status_code=503, detail="System not ready")
    
    if not embeddings or not metadata or not model:
        raise HTTPException(status_code=500, detail="System not ready")
    
    start_time = time.time()
    
    try:
        # 입력 검증
        if not request.q.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        if request.top_k > 100:
            raise HTTPException(status_code=400, detail="top_k cannot exceed 100")
        
        # 쿼리 임베딩 생성 (캐시 사용)
        query_embedding = np.array(encode_query_cached(request.q))
        
        # 검색 실행
        similarities = []
        for i, embedding in enumerate(embeddings):
            sim = cosine_similarity(query_embedding, embedding)
            similarities.append((sim, i))
        
        similarities.sort(reverse=True)
        
        # 필터 적용
        filtered_results = []
        for sim, idx in similarities:
            if sim < request.min_similarity:
                continue
                
            meta = metadata["metadatas"][idx]
            
            # 카테고리 필터 적용
            if request.filters and "category" in request.filters:
                category = meta.get("category", "N/A")
                if category not in request.filters["category"]:
                    continue
            
            filtered_results.append((sim, idx))
        
        # 페이징 적용
        total = len(filtered_results)
        start_idx = request.offset
        end_idx = start_idx + request.top_k
        page_results = filtered_results[start_idx:end_idx]
        
        # 결과 포맷팅
        results = []
        for sim, idx in page_results:
            meta = metadata["metadatas"][idx]
            doc = metadata["documents"][idx]
            
            # 스니펫 생성 (첫 200자)
            snippet = doc[:200] + "..." if len(doc) > 200 else doc
            
            result = SearchResult(
                id=metadata["ids"][idx],
                score=float(sim),
                title=meta.get("title", "N/A"),
                url=meta.get("url", "N/A"),
                snippet=snippet,
                category=meta.get("category", "N/A"),
                date=meta.get("date", "N/A")
            )
            results.append(result)
        
        processing_time = (time.time() - start_time) * 1000
        
        return SearchResponse(
            results=results,
            total=total,
            query=request.q,
            processing_time_ms=round(processing_time, 2)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/stats")
async def get_stats():
    """통계 정보"""
    if not metadata:
        raise HTTPException(status_code=500, detail="Metadata not loaded")
    
    # 카테고리별 통계
    category_counts = {}
    for meta in metadata["metadatas"]:
        category = meta.get("category", "N/A")
        category_counts[category] = category_counts.get(category, 0) + 1
    
    return {
        "total_chunks": len(metadata["ids"]),
        "embedding_dimension": embeddings.shape[1] if embeddings is not None else 0,
        "categories": category_counts,
        "model": "intfloat/multilingual-e5-base",
        "system_ready": system_ready,
        "slo": {
            "p95_latency_ms": SLO_P95_LATENCY_MS,
            "error_rate": SLO_ERROR_RATE,
            "cold_start_ms": SLO_COLD_START_MS,
            "cache_hit_rate": SLO_CACHE_HIT_RATE
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1)




