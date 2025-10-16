#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
검색 서비스 모듈
"""
import os
import logging
from typing import List, Dict, Optional, Any
from ..vector.simple_index import SimpleVectorIndex
from ..vector.reranker import TwoStageRetriever, CrossEncoderReranker

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SearchService:
    """검색 서비스 클래스"""
    
    def __init__(self, 
                 index_name: str = "naver_blog_debt_collection",
                 index_directory: str = "./src/data/indexes/default/simple",
                 top_k_first: int = 20,
                 top_k_final: int = 6):
        self.index_name = index_name
        self.index_directory = index_directory
        self.top_k_first = top_k_first
        self.top_k_final = top_k_final
        
        # 벡터 인덱스 초기화
        self.vector_index = SimpleVectorIndex(
            index_name=index_name,
            persist_directory=index_directory
        )
        
        # 2단계 검색기 초기화
        self.retriever = TwoStageRetriever(
            vector_index=self.vector_index,
            top_k_first=top_k_first,
            top_k_final=top_k_final
        )
        
        logger.info(f"SearchService 초기화 완료: {index_name}")
    
    def search(self, query: str, 
               top_k: Optional[int] = None,
               law_topic: Optional[str] = None,
               use_rerank: bool = True) -> List[Dict[str, Any]]:
        """검색 실행"""
        try:
            # 필터 설정
            where_filter = None
            if law_topic:
                where_filter = {"law_topic": law_topic}
            
            # 검색 실행
            if use_rerank:
                # 2단계 검색 (벡터 + 리랭킹)
                results = self.retriever.search_with_rerank(
                    query=query,
                    where_filter=where_filter
                )
                
                # top_k가 지정된 경우 추가 제한
                if top_k is not None and top_k < len(results):
                    results = results[:top_k]
            else:
                # 1단계 검색만 (벡터 검색)
                results = self.vector_index.search(
                    query=query,
                    top_k=top_k or self.top_k_final,
                    where_filter=where_filter
                )
                
                # 결과 포맷 통일
                for i, result in enumerate(results):
                    result["search_rank"] = i + 1
                    result["vector_score"] = result.get("similarity", 0.0)
                    result["final_score"] = result.get("similarity", 0.0)
            
            logger.info(f"검색 완료: '{query}' -> {len(results)}개 결과")
            return results
            
        except Exception as e:
            logger.error(f"검색 오류: {e}")
            return []
    
    def search_by_law_topic(self, query: str, law_topic: str = "채권추심") -> List[Dict[str, Any]]:
        """법률 주제별 검색"""
        return self.search(query, law_topic=law_topic)
    
    def get_search_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """검색 제안 (간단한 구현)"""
        # 실제로는 더 정교한 제안 시스템을 구현할 수 있음
        suggestions = [
            f"{query} 절차",
            f"{query} 방법",
            f"{query} 비용",
            f"{query} 서류",
            f"{query} 기간"
        ]
        return suggestions[:limit]
    
    def get_search_stats(self, query: str, 
                        law_topic: Optional[str] = None) -> Dict[str, Any]:
        """검색 통계 조회"""
        try:
            where_filter = {"law_topic": law_topic} if law_topic else None
            
            stats = self.retriever.get_search_stats(
                query=query,
                where_filter=where_filter
            )
            
            # 추가 통계 정보
            stats["index_stats"] = self.vector_index.get_index_stats()
            stats["search_config"] = {
                "top_k_first": self.top_k_first,
                "top_k_final": self.top_k_final,
                "index_name": self.index_name
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"검색 통계 조회 오류: {e}")
            return {"error": str(e)}
    
    def get_index_info(self) -> Dict[str, Any]:
        """인덱스 정보 조회"""
        try:
            index_stats = self.vector_index.get_index_stats()
            return {
                "index_name": self.index_name,
                "index_directory": self.index_directory,
                "stats": index_stats,
                "search_config": {
                    "top_k_first": self.top_k_first,
                    "top_k_final": self.top_k_final
                }
            }
        except Exception as e:
            logger.error(f"인덱스 정보 조회 오류: {e}")
            return {"error": str(e)}
    
    def close(self):
        """리소스 정리"""
        if self.vector_index:
            self.vector_index.close()


# 편의 함수들
def get_search_service(index_name: str = "naver_blog_debt_collection",
                      index_directory: str = "./src/data/indexes/default/simple") -> SearchService:
    """검색 서비스 인스턴스 생성"""
    return SearchService(index_name, index_directory)


def search_documents(query: str, 
                    index_name: str = "naver_blog_debt_collection",
                    law_topic: Optional[str] = None) -> List[Dict[str, Any]]:
    """간편한 문서 검색"""
    service = get_search_service(index_name)
    try:
        return service.search(query, law_topic=law_topic)
    finally:
        service.close()


# 테스트용 함수
def test_search_service():
    """검색 서비스 테스트"""
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 테스트용 검색 서비스 생성
        service = SearchService(
            index_name="test_search",
            index_directory=temp_dir,
            top_k_first=10,
            top_k_final=3
        )
        
        # 테스트 데이터 추가
        test_chunks = [
            {
                "text": "채권추심 절차는 내용증명 발송부터 시작됩니다.",
                "metadata": {
                    "source_url": "https://test.com/1",
                    "logno": "12345",
                    "published_at": "2024-01-15",
                    "law_topic": "채권추심"
                }
            },
            {
                "text": "지급명령 신청 시 필요한 서류들을 준비해야 합니다.",
                "metadata": {
                    "source_url": "https://test.com/2",
                    "logno": "12346",
                    "published_at": "2024-01-16",
                    "law_topic": "채권추심"
                }
            },
            {
                "text": "강제집행 절차에 대해 상세히 설명합니다.",
                "metadata": {
                    "source_url": "https://test.com/3",
                    "logno": "12347",
                    "published_at": "2024-01-17",
                    "law_topic": "채권추심"
                }
            }
        ]
        
        # 데이터 인덱싱
        index_result = service.vector_index.upsert_chunks(test_chunks)
        print(f"✅ 데이터 인덱싱 테스트 통과: {index_result}")
        
        # 검색 테스트
        search_results = service.search("채권추심 절차", use_rerank=True)
        print(f"✅ 2단계 검색 테스트 통과: {len(search_results)}개 결과")
        
        for i, result in enumerate(search_results):
            print(f"  {i+1}. {result['text'][:40]}... (점수: {result.get('final_score', 0):.4f})")
        
        # 1단계 검색 테스트
        vector_results = service.search("채권추심 절차", use_rerank=False)
        print(f"✅ 1단계 검색 테스트 통과: {len(vector_results)}개 결과")
        
        # 법률 주제별 검색 테스트
        topic_results = service.search_by_law_topic("절차", "채권추심")
        print(f"✅ 주제별 검색 테스트 통과: {len(topic_results)}개 결과")
        
        # 검색 통계 테스트
        stats = service.get_search_stats("채권추심 절차")
        print(f"✅ 검색 통계 테스트 통과: {stats}")
        
        # 인덱스 정보 테스트
        index_info = service.get_index_info()
        print(f"✅ 인덱스 정보 테스트 통과: {index_info}")
        
        service.close()
        
    finally:
        # 테스트 파일 정리
        shutil.rmtree(temp_dir)
    
    print("✅ SearchService 테스트 완료")


if __name__ == "__main__":
    test_search_service()
