"""
리랭커 모듈
- 1차 e5 검색 (top-20) → 2차 Cross-Encoder 리랭크 (top-6)
- ms-marco-MiniLM-L-6-v2 모델 사용
"""

import logging
from typing import List, Dict, Any, Tuple
import numpy as np
from sentence_transformers import CrossEncoder
import time

logger = logging.getLogger(__name__)


class Reranker:
    """Cross-Encoder 기반 리랭커"""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """리랭커 모델 로드"""
        try:
            logger.info(f"Loading reranker model: {self.model_name}")
            self.model = CrossEncoder(self.model_name)
            logger.info("Reranker model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load reranker model: {e}")
            raise
    
    def rerank(self, query: str, documents: List[Dict[str, Any]], 
               top_k: int = 6) -> List[Dict[str, Any]]:
        """
        문서들을 쿼리 기준으로 리랭크
        
        Args:
            query: 검색 쿼리
            documents: 1차 검색 결과 (document, metadata, score 포함)
            top_k: 최종 반환할 문서 수
            
        Returns:
            리랭크된 문서 리스트
        """
        if not documents or not query:
            return []
        
        if len(documents) <= top_k:
            # 문서 수가 top_k 이하면 그대로 반환
            return documents
        
        try:
            # 쿼리-문서 쌍 생성
            query_doc_pairs = []
            for doc in documents:
                doc_text = doc.get('document', '')
                query_doc_pairs.append([query, doc_text])
            
            # Cross-Encoder 점수 계산
            start_time = time.time()
            rerank_scores = self.model.predict(query_doc_pairs)
            compute_time = time.time() - start_time
            
            # 점수와 함께 문서 정보 결합
            scored_docs = []
            for doc, score in zip(documents, rerank_scores):
                doc_copy = doc.copy()
                doc_copy['rerank_score'] = float(score)
                doc_copy['original_score'] = doc.get('score', 0.0)
                scored_docs.append(doc_copy)
            
            # 리랭크 점수 기준으로 정렬
            scored_docs.sort(key=lambda x: x['rerank_score'], reverse=True)
            
            # top_k만 반환
            top_docs = scored_docs[:top_k]
            
            logger.info(f"Reranked {len(documents)} documents to top-{top_k} in {compute_time:.3f}s")
            
            # 점수 분포 로깅
            if top_docs:
                scores = [doc['rerank_score'] for doc in top_docs]
                logger.debug(f"Rerank score range: {min(scores):.3f} - {max(scores):.3f}")
            
            return top_docs
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            # 실패 시 원본 문서 반환
            return documents[:top_k]
    
    def batch_rerank(self, queries_docs: List[Tuple[str, List[Dict[str, Any]]]], 
                     top_k: int = 6) -> List[List[Dict[str, Any]]]:
        """
        여러 쿼리에 대해 배치 리랭크
        
        Args:
            queries_docs: [(query, documents), ...] 리스트
            top_k: 각 쿼리당 반환할 문서 수
            
        Returns:
            각 쿼리별 리랭크된 문서 리스트
        """
        results = []
        
        for query, documents in queries_docs:
            reranked = self.rerank(query, documents, top_k)
            results.append(reranked)
        
        return results
    
    def get_rerank_stats(self, original_docs: List[Dict[str, Any]], 
                        reranked_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """리랭크 통계 반환"""
        if not original_docs or not reranked_docs:
            return {}
        
        # 점수 개선 통계
        original_scores = [doc.get('score', 0.0) for doc in original_docs]
        rerank_scores = [doc.get('rerank_score', 0.0) for doc in reranked_docs]
        
        # 순위 변화 분석
        original_ranks = {i: doc for i, doc in enumerate(original_docs)}
        rerank_ranks = {i: doc for i, doc in enumerate(reranked_docs)}
        
        rank_changes = []
        for i, rerank_doc in enumerate(reranked_docs):
            # 원본에서의 순위 찾기
            original_rank = None
            for j, orig_doc in enumerate(original_docs):
                if orig_doc.get('document') == rerank_doc.get('document'):
                    original_rank = j
                    break
            
            if original_rank is not None:
                rank_change = original_rank - i  # 양수면 상승
                rank_changes.append(rank_change)
        
        stats = {
            "total_documents": len(original_docs),
            "returned_documents": len(reranked_docs),
            "score_improvement": {
                "original_avg": np.mean(original_scores) if original_scores else 0.0,
                "rerank_avg": np.mean(rerank_scores) if rerank_scores else 0.0,
                "original_max": max(original_scores) if original_scores else 0.0,
                "rerank_max": max(rerank_scores) if rerank_scores else 0.0
            },
            "rank_changes": {
                "avg_change": np.mean(rank_changes) if rank_changes else 0.0,
                "max_improvement": max(rank_changes) if rank_changes else 0,
                "max_degradation": min(rank_changes) if rank_changes else 0
            }
        }
        
        return stats


# 전역 인스턴스
reranker = Reranker()
