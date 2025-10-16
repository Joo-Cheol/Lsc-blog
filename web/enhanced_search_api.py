#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AB 플래그 기반 하이브리드/리랭커 확장 API
"""
import os
import json
import numpy as np
import time
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

# AB 플래그 설정
USE_HYBRID_SEARCH = os.getenv("USE_HYBRID_SEARCH", "false").lower() == "true"
USE_RERANKER = os.getenv("USE_RERANKER", "false").lower() == "true"
RERANKER_CACHE_SIZE = int(os.getenv("RERANKER_CACHE_SIZE", "50"))

# FastAPI 앱 초기화
app = FastAPI(
    title="Enhanced Legal Blog Search API",
    description="AB 플래그 기반 하이브리드/리랭커 확장 API",
    version="2.1.0"
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
reranker_model = None
bm25_index = None
system_ready = False

# 메트릭 수집
class EnhancedMetricsCollector:
    def __init__(self):
        self.latency_history = deque(maxlen=1000)
        self.error_count = 0
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.hybrid_requests = 0
        self.reranker_requests = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
    
    def record_request(self, latency_ms: float, cache_hit: bool, hybrid: bool = False, reranker: bool = False, error: bool = False):
        with self.lock:
            self.latency_history.append(latency_ms)
            self.total_requests += 1
            if cache_hit:
                self.cache_hits += 1
            else:
                self.cache_misses += 1
            if hybrid:
                self.hybrid_requests += 1
            if reranker:
                self.reranker_requests += 1
            if error:
                self.error_count += 1
    
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
            hybrid_rate = self.hybrid_requests / self.total_requests if self.total_requests > 0 else 0
            reranker_rate = self.reranker_requests / self.total_requests if self.total_requests > 0 else 0
            
            return {
                "uptime_seconds": uptime,
                "qps": qps,
                "total_requests": self.total_requests,
                "error_rate": error_rate,
                "cache_hit_rate": cache_hit_rate,
                "hybrid_rate": hybrid_rate,
                "reranker_rate": reranker_rate,
                "latency": latency_stats,
                "ab_flags": {
                    "hybrid_enabled": USE_HYBRID_SEARCH,
                    "reranker_enabled": USE_RERANKER
                }
            }

metrics = EnhancedMetricsCollector()

def cosine_similarity(a, b):
    """코사인 유사도 계산"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

@lru_cache(maxsize=200)
def encode_query_cached(query: str) -> tuple:
    """쿼리 임베딩 캐시"""
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    # e5 프리픽스 적용
    prefixed_query = f"query: {query}"
    embedding = model.encode([prefixed_query], normalize_embeddings=True)[0]
    return tuple(embedding)

def build_bm25_index():
    """BM25 인덱스 구축"""
    try:
        from rank_bm25 import BM25Okapi
        
        # 한국어 bi-gram 토큰화
        def ko_tokenize(text):
            # 간단한 bi-gram 토큰화
            words = text.split()
            tokens = []
            for word in words:
                if len(word) >= 2:
                    for i in range(len(word) - 1):
                        tokens.append(word[i:i+2])
                tokens.append(word)
            return tokens
        
        # 문서 토큰화
        tokenized_docs = []
        for doc in metadata["documents"]:
            tokens = ko_tokenize(doc)
            tokenized_docs.append(tokens)
        
        # BM25 인덱스 구축
        bm25 = BM25Okapi(tokenized_docs)
        
        logger.info(f"Built BM25 index with {len(tokenized_docs)} documents")
        return bm25, ko_tokenize
        
    except ImportError:
        logger.warning("rank_bm25 not installed, BM25 disabled")
        return None, None

def hybrid_search(query: str, top_k: int = 50) -> List[tuple]:
    """하이브리드 검색 (벡터 + BM25)"""
    if bm25_index is None:
        # BM25 없으면 벡터 검색만
        return vector_search(query, top_k)
    
    # 벡터 검색
    vector_results = vector_search(query, top_k * 2)  # 더 많이 가져와서 BM25와 머지
    
    # BM25 검색
    query_tokens = bm25_index[1](query)  # 토큰화 함수 사용
    bm25_scores = bm25_index[0].get_scores(query_tokens)
    
    # BM25 상위 결과
    bm25_indices = np.argsort(bm25_scores)[::-1][:top_k]
    bm25_results = [(bm25_scores[i], i) for i in bm25_indices if bm25_scores[i] > 0]
    
    # ID 기반 머지 (가중합)
    merged_scores = {}
    
    # 벡터 결과 (가중치 0.7)
    for sim, idx in vector_results:
        merged_scores[idx] = merged_scores.get(idx, 0) + sim * 0.7
    
    # BM25 결과 (가중치 0.3)
    for score, idx in bm25_results:
        # BM25 점수를 0-1 범위로 정규화
        normalized_score = min(score / 10.0, 1.0)  # 경험적 정규화
        merged_scores[idx] = merged_scores.get(idx, 0) + normalized_score * 0.3
    
    # 최종 결과 정렬
    final_results = [(score, idx) for idx, score in merged_scores.items()]
    final_results.sort(reverse=True)
    
    return final_results[:top_k]

def vector_search(query: str, top_k: int = 50) -> List[tuple]:
    """벡터 검색"""
    query_embedding = np.array(encode_query_cached(query))
    
    similarities = []
    for i, embedding in enumerate(embeddings):
        sim = cosine_similarity(query_embedding, embedding)
        similarities.append((sim, i))
    
    similarities.sort(reverse=True)
    return similarities[:top_k]

@lru_cache(maxsize=RERANKER_CACHE_SIZE)
def rerank_cached(query: str, candidate_texts: tuple) -> tuple:
    """리랭커 캐시"""
    if reranker_model is None:
        return candidate_texts  # 리랭커 없으면 원본 반환
    
    try:
        # Cross-Encoder 리랭킹
        pairs = [(query, text) for text in candidate_texts]
        scores = reranker_model.predict(pairs)
        
        # 점수 순으로 정렬
        scored_pairs = list(zip(scores, candidate_texts))
        scored_pairs.sort(reverse=True)
        
        return tuple([text for _, text in scored_pairs])
        
    except Exception as e:
        logger.warning(f"Reranking failed: {e}")
        return candidate_texts

def load_artifacts_with_enhancements():
    """확장 기능과 함께 아티팩트 로드"""
    global embeddings, metadata, model, reranker_model, bm25_index, system_ready
    
    logger.info("Loading artifacts with enhancements...")
    
    # 기본 아티팩트 로드
    artifacts_dir = Path("artifacts")
    if not artifacts_dir.exists():
        index_path = "simple_vector_index.npy"
        metadata_path = "simple_metadata.json"
    else:
        versions = [d for d in artifacts_dir.iterdir() if d.is_dir()]
        if not versions:
            raise FileNotFoundError("No artifact versions found")
        
        latest_version = max(versions, key=lambda x: x.name)
        index_path = latest_version / "simple_vector_index.npy"
        metadata_path = latest_version / "simple_metadata.json"
    
    # 벡터 인덱스 로드
    embeddings = np.load(index_path, mmap_mode='r')
    
    # 메타데이터 로드
    with open(metadata_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        metadata = {
            "ids": data["ids"],
            "metadatas": data["metadatas"],
            "documents": data["documents"]
        }
    
    # 모델 로드
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer("intfloat/multilingual-e5-base", device=device)
    model.max_seq_length = 512
    
    # 리랭커 모델 로드 (선택적)
    if USE_RERANKER:
        try:
            from sentence_transformers import CrossEncoder
            reranker_model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            logger.info("Reranker model loaded")
        except Exception as e:
            logger.warning(f"Failed to load reranker: {e}")
            reranker_model = None
    
    # BM25 인덱스 구축 (선택적)
    if USE_HYBRID_SEARCH:
        bm25_index, _ = build_bm25_index()
    
    system_ready = True
    logger.info(f"✅ Enhanced system ready! Hybrid: {USE_HYBRID_SEARCH}, Reranker: {USE_RERANKER}")

# Pydantic 모델
class EnhancedSearchRequest(BaseModel):
    q: str
    top_k: int = 20
    filters: Optional[Dict[str, List[str]]] = None
    offset: int = 0
    min_similarity: float = 0.0
    # AB 플래그
    hybrid: Optional[bool] = None  # None이면 환경변수 사용
    reranker: Optional[bool] = None  # None이면 환경변수 사용

class SearchResult(BaseModel):
    id: str
    score: float
    title: str
    url: str
    snippet: str
    category: str
    date: str
    # 메타데이터
    search_method: str  # "vector", "hybrid", "reranked"
    rerank_score: Optional[float] = None

class EnhancedSearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    query: str
    processing_time_ms: float
    search_method: str
    ab_flags: Dict[str, bool]

# 미들웨어
@app.middleware("http")
async def enhanced_metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    latency_ms = (time.time() - start_time) * 1000
    
    # 메트릭 기록
    if request.url.path == "/search" and request.method == "POST":
        # 요청 본문에서 AB 플래그 추출 (간단한 방법)
        hybrid = "hybrid" in str(request.url)
        reranker = "reranker" in str(request.url)
        cache_hit = False  # 실제로는 쿼리 기반으로 판단
        error = response.status_code >= 400
        metrics.record_request(latency_ms, cache_hit, hybrid, reranker, error)
    
    return response

# 이벤트 핸들러
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 아티팩트 로드"""
    load_artifacts_with_enhancements()

# 엔드포인트
@app.get("/")
async def root():
    """기본 정보"""
    return {
        "service": "Enhanced Legal Blog Search API",
        "version": "2.1.0",
        "status": "operational",
        "total_chunks": len(metadata["ids"]) if metadata else 0,
        "embedding_dimension": embeddings.shape[1] if embeddings is not None else 0,
        "system_ready": system_ready,
        "ab_flags": {
            "hybrid_enabled": USE_HYBRID_SEARCH,
            "reranker_enabled": USE_RERANKER
        }
    }

@app.get("/metrics")
async def get_metrics():
    """확장 메트릭 정보"""
    return {
        "metrics": metrics.get_metrics(),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/metrics/quality")
async def get_quality_metrics():
    """품질 메트릭 엔드포인트"""
    try:
        from quality_monitor import QualityMonitor
        
        monitor = QualityMonitor()
        monitor.load_artifacts()
        
        # 빠른 품질 평가 (샘플 쿼리만)
        recall_10 = monitor.evaluate_recall_at_k(10)
        ndcg_10 = monitor.evaluate_ndcg_at_k(10)
        mrr = monitor.evaluate_mrr()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "quality_metrics": {
                "recall@10": recall_10,
                "ndcg@10": ndcg_10,
                "mrr": mrr
            },
            "slo_status": {
                "recall@10_ok": recall_10["recall@10"] >= 0.7,
                "ndcg@10_ok": ndcg_10["ndcg@10"] >= 0.6,
                "mrr_ok": mrr["mrr"] >= 0.5
            }
        }
        
    except Exception as e:
        logger.error(f"Quality metrics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search", response_model=EnhancedSearchResponse)
async def enhanced_search(request: EnhancedSearchRequest):
    """확장 검색 API"""
    if not system_ready:
        raise HTTPException(status_code=503, detail="System not ready")
    
    start_time = time.time()
    
    try:
        # AB 플래그 결정
        use_hybrid = request.hybrid if request.hybrid is not None else USE_HYBRID_SEARCH
        use_reranker = request.reranker if request.reranker is not None else USE_RERANKER
        
        # 검색 실행
        if use_hybrid:
            search_results = hybrid_search(request.q, request.top_k * 2)  # 리랭킹을 위해 더 많이
            search_method = "hybrid"
        else:
            search_results = vector_search(request.q, request.top_k * 2)
            search_method = "vector"
        
        # 리랭킹 적용
        if use_reranker and reranker_model is not None:
            # 상위 후보들만 리랭킹
            top_candidates = search_results[:50]  # 상위 50개만 리랭킹
            
            candidate_texts = []
            candidate_indices = []
            for score, idx in top_candidates:
                candidate_texts.append(metadata["documents"][idx])
                candidate_indices.append(idx)
            
            # 리랭킹 실행
            reranked_texts = rerank_cached(request.q, tuple(candidate_texts))
            
            # 리랭킹된 순서로 결과 재정렬
            reranked_results = []
            for text in reranked_texts:
                text_idx = candidate_texts.index(text)
                original_idx = candidate_indices[text_idx]
                original_score = next(score for score, idx in top_candidates if idx == original_idx)
                reranked_results.append((original_score, original_idx))
            
            # 나머지 결과 추가
            remaining_results = search_results[50:]
            search_results = reranked_results + remaining_results
            search_method += "+reranked"
        
        # 필터 적용
        filtered_results = []
        for sim, idx in search_results:
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
            
            # 스니펫 생성
            snippet = doc[:200] + "..." if len(doc) > 200 else doc
            
            result = SearchResult(
                id=metadata["ids"][idx],
                score=float(sim),
                title=meta.get("title", "N/A"),
                url=meta.get("url", "N/A"),
                snippet=snippet,
                category=meta.get("category", "N/A"),
                date=meta.get("date", "N/A"),
                search_method=search_method
            )
            results.append(result)
        
        processing_time = (time.time() - start_time) * 1000
        
        return EnhancedSearchResponse(
            results=results,
            total=total,
            query=request.q,
            processing_time_ms=round(processing_time, 2),
            search_method=search_method,
            ab_flags={
                "hybrid": use_hybrid,
                "reranker": use_reranker
            }
        )
        
    except Exception as e:
        logger.error(f"Enhanced search error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1)




