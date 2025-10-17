"""
향상된 검색 모듈
- 1차 임베딩 검색 (top-20) → 2차 리랭크 (top-6)
- 통합된 검색 파이프라인
"""

import logging
from typing import List, Dict, Any, Optional
import time

from ..vector.reranker import CrossEncoderReranker
from ..vector.embedder import embedding_cache
from ..vector.chroma_index import chroma_indexer

logger = logging.getLogger(__name__)


class EnhancedSearch:
    """향상된 검색 시스템"""
    
    def __init__(self, 
                 first_stage_k: int = 20,
                 final_k: int = 6,
                 enable_rerank: bool = True):
        self.first_stage_k = first_stage_k
        self.final_k = final_k
        self.enable_rerank = enable_rerank
        self.reranker = CrossEncoderReranker() if enable_rerank else None
    
    def search(self, query: str, 
               where_filter: Optional[Dict[str, Any]] = None,
               return_metadata: bool = True) -> Dict[str, Any]:
        """
        통합 검색 실행
        
        Args:
            query: 검색 쿼리
            where_filter: ChromaDB 메타데이터 필터
            return_metadata: 메타데이터 포함 여부
            
        Returns:
            검색 결과와 통계
        """
        start_time = time.time()
        
        try:
            # 1단계: 쿼리 임베딩 생성
            query_embedding, _ = embedding_cache.get_or_compute(query)
            
            # 2단계: ChromaDB에서 1차 검색
            first_stage_results = chroma_indexer.search(
                query_embedding=query_embedding.tolist(),
                top_k=self.first_stage_k,
                where_filter=where_filter
            )
            
            if not first_stage_results:
                return {
                    "documents": [],
                    "stats": {
                        "total_found": 0,
                        "first_stage_k": self.first_stage_k,
                        "final_k": self.final_k,
                        "rerank_enabled": self.enable_rerank,
                        "search_time": time.time() - start_time
                    }
                }
            
            # 3단계: 리랭크 (옵션)
            if self.enable_rerank and self.reranker and len(first_stage_results) > self.final_k:
                # 문서 텍스트 추출
                doc_texts = [doc["document"] for doc in first_stage_results]
                
                # 리랭킹 실행
                reranked_results = self.reranker.rerank_with_metadata(
                    query=query,
                    documents=first_stage_results,
                    top_k=self.final_k
                )
                
                final_results = reranked_results
                rerank_stats = {"rerank_enabled": True}
            else:
                final_results = first_stage_results[:self.final_k]
                rerank_stats = {"rerank_enabled": False}
            
            # 4단계: 결과 포맷팅
            formatted_results = []
            for i, doc in enumerate(final_results):
                result_item = {
                    "rank": i + 1,
                    "document": doc.get("document", doc.get("text", "")),
                    "score": doc.get("rerank_score", doc.get("score", 0.0)),
                    "original_score": doc.get("score", 0.0)
                }
                
                if return_metadata and "metadata" in doc:
                    result_item["metadata"] = doc["metadata"]
                
                formatted_results.append(result_item)
            
            # 통계 수집
            search_time = time.time() - start_time
            stats = {
                "total_found": len(first_stage_results),
                "returned": len(final_results),
                "first_stage_k": self.first_stage_k,
                "final_k": self.final_k,
                "rerank_enabled": self.enable_rerank,
                "search_time": search_time,
                "rerank_stats": rerank_stats
            }
            
            logger.info(f"Enhanced search completed: {len(final_results)} results in {search_time:.3f}s")
            
            return {
                "documents": formatted_results,
                "stats": stats
            }
            
        except Exception as e:
            logger.error(f"Enhanced search failed: {e}")
            return {
                "documents": [],
                "stats": {
                    "error": str(e),
                    "search_time": time.time() - start_time
                }
            }
    
    def search_with_filters(self, query: str, 
                           law_topic: Optional[str] = None,
                           source_url: Optional[str] = None,
                           min_logno: Optional[int] = None,
                           max_logno: Optional[int] = None) -> Dict[str, Any]:
        """
        필터 조건이 있는 검색
        
        Args:
            query: 검색 쿼리
            law_topic: 법률 주제 필터
            source_url: 소스 URL 필터
            min_logno: 최소 logno
            max_logno: 최대 logno
            
        Returns:
            필터링된 검색 결과
        """
        # 필터 구성
        where_filter = {}
        
        if law_topic:
            where_filter["law_topic"] = law_topic
        
        if source_url:
            where_filter["source_url"] = source_url
        
        if min_logno is not None or max_logno is not None:
            logno_filter = {}
            if min_logno is not None:
                logno_filter["$gte"] = min_logno
            if max_logno is not None:
                logno_filter["$lte"] = max_logno
            where_filter["logno"] = logno_filter
        
        return self.search(query, where_filter=where_filter if where_filter else None)
    
    def get_search_stats(self) -> Dict[str, Any]:
        """검색 시스템 통계"""
        try:
            # 임베딩 캐시 통계
            cache_stats = embedding_cache.get_cache_stats()
            
            # ChromaDB 통계
            chroma_stats = chroma_indexer.get_collection_stats()
            
            return {
                "embedding_cache": cache_stats,
                "chroma_collection": chroma_stats,
                "search_config": {
                    "first_stage_k": self.first_stage_k,
                    "final_k": self.final_k,
                    "rerank_enabled": self.enable_rerank
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get search stats: {e}")
            return {"error": str(e)}


# 전역 인스턴스
enhanced_search = EnhancedSearch()
