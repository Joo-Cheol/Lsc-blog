#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
하이브리드 검색 (BM25 + 벡터) 구현
"""
import numpy as np
from typing import List, Dict, Any, Optional
from .bm25 import create_bm25_index
from .retriever import retrieve, mmr_select

def hybrid_search(
    query: str, 
    where: Optional[Dict] = None, 
    k: int = 8,
    alpha: Optional[float] = None,
    use_mmr: bool = True
) -> List[Dict[str, Any]]:
    """
    하이브리드 검색: BM25 + 벡터 검색
    
    Args:
        query: 검색 쿼리
        where: 필터 조건
        k: 반환할 결과 수
        alpha: BM25 가중치 (None이면 settings에서 가져옴)
        use_mmr: MMR 다양화 사용 여부
    
    Returns:
        검색 결과 리스트
    """
    
    # 설정에서 alpha 가져오기
    if alpha is None:
        from src.config.settings import settings
        alpha = settings.RETRIEVAL_ALPHA
    
    # 1. 벡터 검색 (기존)
    vector_hits = retrieve(query, where, k * 3)  # 더 많은 후보 수집
    
    if not vector_hits:
        return []
    
    # 2. BM25 검색을 위한 문서 준비
    docs_for_bm25 = []
    for hit in vector_hits:
        docs_for_bm25.append({
            "id": hit["id"],
            "text": hit["text"],
            "meta": hit["meta"]
        })
    
    # 3. BM25 인덱스 생성 및 검색
    bm25_index = create_bm25_index(docs_for_bm25)
    bm25_hits = bm25_index.search(query, topk=k * 3)
    
    # 4. BM25 점수 정규화
    if bm25_hits:
        bm25_scores = [hit["bm25"] for hit in bm25_hits]
        min_bm25 = min(bm25_scores)
        max_bm25 = max(bm25_scores)
        bm25_range = max_bm25 - min_bm25 + 1e-9
        
        for hit in bm25_hits:
            hit["bm25_norm"] = (hit["bm25"] - min_bm25) / bm25_range
    else:
        bm25_hits = []
    
    # 5. 벡터와 BM25 결과 병합
    vector_dict = {hit["id"]: hit for hit in vector_hits}
    bm25_dict = {hit["id"]: hit for hit in bm25_hits}
    
    # 모든 ID 수집
    all_ids = set(vector_dict.keys()) | set(bm25_dict.keys())
    
    # 병합된 결과 생성
    merged_hits = []
    for doc_id in all_ids:
        merged_hit = {
            "id": doc_id,
            "sim": 0.0,
            "bm25": 0.0,
            "bm25_norm": 0.0,
            "combo": 0.0,
            "text": "",
            "meta": {}
        }
        
        # 벡터 점수
        if doc_id in vector_dict:
            vec_hit = vector_dict[doc_id]
            merged_hit.update({
                "sim": vec_hit["sim"],
                "text": vec_hit["text"],
                "meta": vec_hit["meta"]
            })
        
        # BM25 점수
        if doc_id in bm25_dict:
            bm25_hit = bm25_dict[doc_id]
            merged_hit.update({
                "bm25": bm25_hit["bm25"],
                "bm25_norm": bm25_hit.get("bm25_norm", 0.0)
            })
        
        # 조합 점수 계산
        merged_hit["combo"] = (1 - alpha) * merged_hit["sim"] + alpha * merged_hit["bm25_norm"]
        merged_hits.append(merged_hit)
    
    # 6. 조합 점수로 정렬
    merged_hits.sort(key=lambda x: x["combo"], reverse=True)
    
    # 7. MMR 다양화 적용 (선택사항)
    if use_mmr and len(merged_hits) > k:
        # 상위 후보들에 대해 MMR 적용
        top_candidates = merged_hits[:k * 2]
        
        # 실제 벡터 임베딩 추출
        candidate_vectors = []
        query_vector = None
        
        try:
            from simple_vector_store import get_store
            store = get_store()
            
            # 쿼리 벡터 생성
            query_vector = store.embedder.encode_query([query])[0]
            
            # 후보 벡터들 추출
            for hit in top_candidates:
                # 실제 임베딩을 가져오거나 새로 생성
                try:
                    # 벡터 스토어에서 임베딩 조회 시도
                    if hasattr(store, 'get_embedding'):
                        embedding = store.get_embedding(hit["id"])
                    else:
                        # 임베딩이 없으면 새로 생성
                        embedding = store.embedder.encode_docs([hit["text"]])[0]
                    candidate_vectors.append(embedding)
                except Exception as e:
                    # 임베딩 추출 실패 시 sim 점수로 대체
                    candidate_vectors.append([hit["sim"]])
            
            if candidate_vectors and query_vector is not None:
                # 설정에서 MMR lambda 가져오기
                from src.config.settings import settings
                lambda_div = settings.MMR_LAMBDA
                
                selected_indices = mmr_select(
                    query_vector, 
                    candidate_vectors, 
                    lambda_div=lambda_div, 
                    topk=k
                )
                final_hits = [top_candidates[i] for i in selected_indices]
            else:
                final_hits = merged_hits[:k]
                
        except Exception as e:
            # MMR 실패 시 상위 k개 반환
            final_hits = merged_hits[:k]
    else:
        final_hits = merged_hits[:k]
    
    return final_hits

def get_hybrid_search_stats() -> Dict[str, Any]:
    """하이브리드 검색 통계"""
    from src.config.settings import settings
    return {
        "enabled": True,
        "alpha": settings.RETRIEVAL_ALPHA,
        "mmr_lambda": settings.MMR_LAMBDA,
        "mmr_enabled": True,
        "description": "BM25 + 벡터 검색 조합"
    }
