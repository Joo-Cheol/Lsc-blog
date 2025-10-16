#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cross-Encoder 리랭커 모듈
"""
import os
import logging
from typing import List, Dict, Tuple, Optional
import numpy as np
from sentence_transformers import CrossEncoder

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Cross-Encoder 기반 리랭커"""
    
    def __init__(self, 
                 model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
                 device: str = "cuda"):
        self.model_name = model_name
        self.device = device
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """모델 로드"""
        try:
            logger.info(f"Cross-Encoder 모델 로딩: {self.model_name} (device: {self.device})")
            self.model = CrossEncoder(self.model_name, device=self.device)
            logger.info("Cross-Encoder 모델 로딩 완료")
        except Exception as e:
            logger.error(f"모델 로딩 실패: {e}")
            # CPU로 폴백
            if self.device == "cuda":
                logger.info("CPU로 폴백 시도...")
                self.device = "cpu"
                self.model = CrossEncoder(self.model_name, device=self.device)
                logger.info("CPU 모델 로딩 완료")
            else:
                raise e
    
    def rerank(self, query: str, documents: List[str], 
               top_k: Optional[int] = None) -> List[Tuple[str, float]]:
        """문서 리랭킹"""
        if not documents:
            return []
        
        try:
            # 쿼리-문서 쌍 생성
            pairs = [(query, doc) for doc in documents]
            
            # Cross-Encoder로 점수 계산
            scores = self.model.predict(pairs)
            
            # 점수와 문서를 함께 정렬
            scored_docs = list(zip(documents, scores))
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            # 상위 k개 반환
            if top_k is not None:
                scored_docs = scored_docs[:top_k]
            
            logger.info(f"리랭킹 완료: {len(scored_docs)}개 문서")
            return scored_docs
            
        except Exception as e:
            logger.error(f"리랭킹 오류: {e}")
            # 오류 시 원본 순서로 반환
            return [(doc, 0.0) for doc in documents]
    
    def rerank_with_metadata(self, query: str, 
                           documents: List[Dict[str, any]], 
                           top_k: Optional[int] = None) -> List[Dict[str, any]]:
        """메타데이터가 포함된 문서 리랭킹"""
        if not documents:
            return []
        
        try:
            # 문서 텍스트 추출
            doc_texts = []
            for doc in documents:
                if isinstance(doc, dict):
                    text = doc.get("text", "")
                else:
                    text = str(doc)
                doc_texts.append(text)
            
            # 리랭킹 실행
            reranked_results = self.rerank(query, doc_texts, top_k)
            
            # 메타데이터와 함께 결과 구성
            result_docs = []
            for text, score in reranked_results:
                # 원본 문서에서 메타데이터 찾기
                original_doc = None
                for doc in documents:
                    if isinstance(doc, dict):
                        if doc.get("text", "") == text:
                            original_doc = doc
                            break
                    elif str(doc) == text:
                        original_doc = {"text": text}
                        break
                
                if original_doc:
                    result_doc = original_doc.copy()
                    result_doc["rerank_score"] = float(score)
                    result_docs.append(result_doc)
                else:
                    # 메타데이터를 찾을 수 없는 경우
                    result_docs.append({
                        "text": text,
                        "rerank_score": float(score)
                    })
            
            logger.info(f"메타데이터 리랭킹 완료: {len(result_docs)}개 문서")
            return result_docs
            
        except Exception as e:
            logger.error(f"메타데이터 리랭킹 오류: {e}")
            return documents


class TwoStageRetriever:
    """2단계 검색 시스템 (1차: 벡터 검색, 2차: Cross-Encoder 리랭킹)"""
    
    def __init__(self, 
                 vector_index,
                 reranker: Optional[CrossEncoderReranker] = None,
                 top_k_first: int = 20,
                 top_k_final: int = 6):
        self.vector_index = vector_index
        self.reranker = reranker or CrossEncoderReranker()
        self.top_k_first = top_k_first
        self.top_k_final = top_k_final
    
    def search_with_rerank(self, query: str, 
                          where_filter: Optional[Dict[str, any]] = None) -> List[Dict[str, any]]:
        """2단계 검색 실행"""
        try:
            # 1단계: 벡터 검색으로 상위 문서들 검색
            logger.info(f"1단계 벡터 검색: top_k={self.top_k_first}")
            vector_results = self.vector_index.search(
                query=query,
                top_k=self.top_k_first,
                where_filter=where_filter
            )
            
            if not vector_results:
                logger.warning("벡터 검색 결과가 없음")
                return []
            
            logger.info(f"1단계 검색 완료: {len(vector_results)}개 문서")
            
            # 2단계: Cross-Encoder로 리랭킹
            logger.info(f"2단계 리랭킹: top_k={self.top_k_final}")
            reranked_results = self.reranker.rerank_with_metadata(
                query=query,
                documents=vector_results,
                top_k=self.top_k_final
            )
            
            logger.info(f"2단계 리랭킹 완료: {len(reranked_results)}개 문서")
            
            # 결과에 검색 단계 정보 추가
            for i, result in enumerate(reranked_results):
                result["search_rank"] = i + 1
                result["vector_score"] = result.get("similarity", 0.0)
                result["final_score"] = result.get("rerank_score", 0.0)
            
            return reranked_results
            
        except Exception as e:
            logger.error(f"2단계 검색 오류: {e}")
            # 오류 시 1단계 결과만 반환
            return vector_results[:self.top_k_final] if vector_results else []
    
    def get_search_stats(self, query: str, 
                        where_filter: Optional[Dict[str, any]] = None) -> Dict[str, any]:
        """검색 통계 조회"""
        try:
            # 1단계 검색
            vector_results = self.vector_index.search(
                query=query,
                top_k=self.top_k_first,
                where_filter=where_filter
            )
            
            # 2단계 리랭킹
            reranked_results = self.reranker.rerank_with_metadata(
                query=query,
                documents=vector_results,
                top_k=self.top_k_final
            )
            
            # 통계 계산
            stats = {
                "query": query,
                "vector_search_count": len(vector_results),
                "reranked_count": len(reranked_results),
                "top_k_first": self.top_k_first,
                "top_k_final": self.top_k_final
            }
            
            if vector_results:
                # 벡터 점수 통계
                vector_scores = [r.get("similarity", 0.0) for r in vector_results]
                stats["vector_score_stats"] = {
                    "min": min(vector_scores),
                    "max": max(vector_scores),
                    "avg": sum(vector_scores) / len(vector_scores)
                }
            
            if reranked_results:
                # 리랭킹 점수 통계
                rerank_scores = [r.get("rerank_score", 0.0) for r in reranked_results]
                stats["rerank_score_stats"] = {
                    "min": min(rerank_scores),
                    "max": max(rerank_scores),
                    "avg": sum(rerank_scores) / len(rerank_scores)
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"검색 통계 조회 오류: {e}")
            return {"error": str(e)}


# 편의 함수들
def get_reranker(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
                device: str = "cuda") -> CrossEncoderReranker:
    """리랭커 인스턴스 생성"""
    return CrossEncoderReranker(model_name, device)


def get_two_stage_retriever(vector_index, 
                          top_k_first: int = 20,
                          top_k_final: int = 6) -> TwoStageRetriever:
    """2단계 검색기 인스턴스 생성"""
    return TwoStageRetriever(vector_index, top_k_first=top_k_first, top_k_final=top_k_final)


# 테스트용 함수
def test_reranker():
    """리랭커 테스트"""
    # 테스트용 리랭커 생성
    reranker = CrossEncoderReranker(device="cpu")  # 테스트용으로 CPU 사용
    
    try:
        # 테스트 쿼리와 문서
        query = "채권추심 절차"
        documents = [
            "채권추심은 내용증명 발송부터 시작됩니다.",
            "지급명령 신청 시 필요한 서류들을 준비해야 합니다.",
            "오늘 날씨가 좋습니다.",
            "강제집행 절차에 대해 설명합니다."
        ]
        
        # 리랭킹 테스트
        reranked_results = reranker.rerank(query, documents, top_k=3)
        print(f"✅ 리랭킹 테스트 통과: {len(reranked_results)}개 결과")
        
        # 점수 확인
        for i, (doc, score) in enumerate(reranked_results):
            print(f"  {i+1}. {doc[:30]}... (점수: {score:.4f})")
        
        # 메타데이터 리랭킹 테스트
        documents_with_meta = [
            {"text": "채권추심은 내용증명 발송부터 시작됩니다.", "source": "doc1"},
            {"text": "지급명령 신청 시 필요한 서류들을 준비해야 합니다.", "source": "doc2"},
            {"text": "오늘 날씨가 좋습니다.", "source": "doc3"},
            {"text": "강제집행 절차에 대해 설명합니다.", "source": "doc4"}
        ]
        
        reranked_with_meta = reranker.rerank_with_metadata(query, documents_with_meta, top_k=3)
        print(f"✅ 메타데이터 리랭킹 테스트 통과: {len(reranked_with_meta)}개 결과")
        
        for i, doc in enumerate(reranked_with_meta):
            print(f"  {i+1}. {doc['text'][:30]}... (점수: {doc['rerank_score']:.4f}, 소스: {doc['source']})")
        
    finally:
        pass  # 리랭커는 별도 리소스 정리가 필요하지 않음
    
    print("✅ CrossEncoderReranker 테스트 완료")


if __name__ == "__main__":
    test_reranker()
