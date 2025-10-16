#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 기반 검색 API 서버
"""
import os
import json
import numpy as np
from pathlib import Path
import logging
from typing import List, Optional, Dict, Any
from sentence_transformers import SentenceTransformer
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time
from functools import lru_cache

# ===== 환경 가드 설정 =====
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(
    title="Legal Blog Search API",
    description="법률 블로그 검색 API",
    version="1.0.0"
)

# 전역 변수
embeddings = None
metadata = None
model = None

def cosine_similarity(a, b):
    """코사인 유사도 계산"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

@lru_cache(maxsize=100)
def encode_query_cached(query: str) -> tuple:
    """쿼리 임베딩 캐시"""
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    # e5 프리픽스 적용
    prefixed_query = f"query: {query}"
    embedding = model.encode([prefixed_query], normalize_embeddings=True)[0]
    return tuple(embedding)

def load_artifacts():
    """벡터 인덱스와 메타데이터 로드"""
    global embeddings, metadata, model
    
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
    logger.info(f"Loading model on device: {device}")
    model = SentenceTransformer("intfloat/multilingual-e5-base", device=device)
    model.max_seq_length = 512
    
    logger.info(f"Loaded {len(metadata['ids'])} chunks, embeddings shape: {embeddings.shape}")

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

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 아티팩트 로드"""
    try:
        load_artifacts()
        logger.info("✅ Search API ready!")
    except Exception as e:
        logger.error(f"❌ Failed to load artifacts: {e}")
        raise

@app.get("/")
async def root():
    """헬스 체크"""
    return {
        "status": "healthy",
        "total_chunks": len(metadata["ids"]) if metadata else 0,
        "embedding_dimension": embeddings.shape[1] if embeddings is not None else 0
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
    """검색 API"""
    if not embeddings or not metadata or not model:
        raise HTTPException(status_code=500, detail="System not ready")
    
    start_time = time.time()
    
    try:
        # 쿼리 임베딩 생성 (캐시 사용)
        query_embedding = np.array(encode_query_cached(request.q))
        
        # 검색 실행
        similarities = []
        for i, embedding in enumerate(embeddings):
            sim = cosine_similarity(query_embedding, embedding)
            similarities.append((sim, i))
        
        # 유사도 순 정렬
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
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        "model": "intfloat/multilingual-e5-base"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)




