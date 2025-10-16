#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChromaDB 벡터 인덱스 관리
"""
import os
import hashlib
import logging
from typing import List, Dict, Optional, Tuple, Any
import chromadb
from chromadb.config import Settings as ChromaSettings
from .embedder import EmbeddingService

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChromaIndexManager:
    """ChromaDB 인덱스 관리 클래스"""
    
    def __init__(self, 
                 collection_name: str = "naver_blog_debt_collection",
                 persist_directory: str = "./src/data/indexes/default/chroma",
                 embedding_service: Optional[EmbeddingService] = None):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embedding_service = embedding_service or EmbeddingService()
        
        # ChromaDB 클라이언트 초기화
        self.client = self._init_client()
        self.collection = self._get_or_create_collection()
        
        logger.info(f"ChromaDB 인덱스 초기화 완료: {collection_name}")
    
    def _init_client(self):
        """ChromaDB 클라이언트 초기화"""
        # 디렉터리 생성
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # ChromaDB 설정
        settings = ChromaSettings(
            persist_directory=self.persist_directory,
            anonymized_telemetry=False
        )
        
        client = chromadb.PersistentClient(settings=settings)
        logger.info(f"ChromaDB 클라이언트 초기화: {self.persist_directory}")
        return client
    
    def _get_or_create_collection(self):
        """컬렉션 조회 또는 생성"""
        try:
            collection = self.client.get_collection(self.collection_name)
            logger.info(f"기존 컬렉션 로드: {self.collection_name}")
        except Exception:
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "네이버 블로그 채권추심 관련 문서 벡터 인덱스"}
            )
            logger.info(f"새 컬렉션 생성: {self.collection_name}")
        
        return collection
    
    def get_content_hash(self, content: str) -> str:
        """콘텐츠 해시 생성"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def upsert_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, int]:
        """청크들을 벡터 인덱스에 업서트"""
        if not chunks:
            return {"added": 0, "skipped": 0, "failed": 0}
        
        added_count = 0
        skipped_count = 0
        failed_count = 0
        
        # 배치 처리
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_result = self._upsert_batch(batch)
            
            added_count += batch_result["added"]
            skipped_count += batch_result["skipped"]
            failed_count += batch_result["failed"]
        
        logger.info(f"[INDEX] 배치 업서트 완료: added={added_count}, skipped={skipped_count}, failed={failed_count}")
        return {
            "added": added_count,
            "skipped": skipped_count,
            "failed": failed_count
        }
    
    def _upsert_batch(self, chunks: List[Dict[str, Any]]) -> Dict[str, int]:
        """배치 단위로 청크 업서트"""
        added_count = 0
        skipped_count = 0
        failed_count = 0
        
        # 처리할 청크들 필터링
        chunks_to_process = []
        existing_hashes = set()
        
        for chunk in chunks:
            try:
                content_hash = self.get_content_hash(chunk["text"])
                
                # 기존 문서 확인
                if self._document_exists(content_hash):
                    logger.debug(f"문서 이미 존재: {content_hash[:8]}...")
                    skipped_count += 1
                    continue
                
                chunks_to_process.append({
                    **chunk,
                    "content_hash": content_hash
                })
                existing_hashes.add(content_hash)
                
            except Exception as e:
                logger.error(f"청크 처리 오류: {e}")
                failed_count += 1
        
        if not chunks_to_process:
            return {"added": 0, "skipped": skipped_count, "failed": failed_count}
        
        # 임베딩 계산
        texts = [chunk["text"] for chunk in chunks_to_process]
        embeddings = self.embedding_service.get_embeddings_batch(texts)
        
        # ChromaDB에 업서트
        try:
            ids = [chunk["content_hash"] for chunk in chunks_to_process]
            metadatas = [self._prepare_metadata(chunk) for chunk in chunks_to_process]
            
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=texts
            )
            
            added_count = len(chunks_to_process)
            logger.info(f"[INDEX] 배치 추가: {added_count}개 문서")
            
        except Exception as e:
            logger.error(f"ChromaDB 업서트 오류: {e}")
            failed_count += len(chunks_to_process)
        
        return {
            "added": added_count,
            "skipped": skipped_count,
            "failed": failed_count
        }
    
    def _document_exists(self, content_hash: str) -> bool:
        """문서 존재 여부 확인"""
        try:
            result = self.collection.get(ids=[content_hash])
            return len(result["ids"]) > 0
        except Exception:
            return False
    
    def _prepare_metadata(self, chunk: Dict[str, Any]) -> Dict[str, str]:
        """메타데이터 준비"""
        metadata = {
            "content_hash": chunk["content_hash"],
            "law_topic": chunk.get("metadata", {}).get("law_topic", "채권추심"),
            "source_url": chunk.get("metadata", {}).get("source_url", ""),
            "logno": chunk.get("metadata", {}).get("logno", ""),
            "published_at": chunk.get("metadata", {}).get("published_at", ""),
            "chunk_id": chunk.get("metadata", {}).get("chunk_id", ""),
            "chunk_type": chunk.get("metadata", {}).get("chunk_type", "semantic"),
            "token_count": chunk.get("metadata", {}).get("token_count", "0"),
            "char_count": chunk.get("metadata", {}).get("char_count", "0")
        }
        
        # 키워드가 있으면 추가
        if "keywords" in chunk.get("metadata", {}):
            metadata["keywords"] = chunk["metadata"]["keywords"]
        
        return metadata
    
    def search(self, query: str, top_k: int = 20, 
               where_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """벡터 검색"""
        try:
            # 쿼리 임베딩 계산
            query_embedding = self.embedding_service.get_or_compute_embedding(query)
            
            # 검색 실행
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=top_k,
                where=where_filter
            )
            
            # 결과 포맷팅
            formatted_results = []
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    formatted_results.append({
                        "id": doc_id,
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if "distances" in results else None
                    })
            
            logger.info(f"벡터 검색 완료: {len(formatted_results)}개 결과")
            return formatted_results
            
        except Exception as e:
            logger.error(f"벡터 검색 오류: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계 조회"""
        try:
            count = self.collection.count()
            
            # 샘플 메타데이터 조회
            sample_results = self.collection.get(limit=10)
            sample_metadata = sample_results.get("metadatas", [])
            
            # 통계 계산
            stats = {
                "total_documents": count,
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory
            }
            
            if sample_metadata:
                # 법률 주제별 분포
                law_topics = {}
                for meta in sample_metadata:
                    topic = meta.get("law_topic", "unknown")
                    law_topics[topic] = law_topics.get(topic, 0) + 1
                
                stats["law_topics"] = law_topics
                
                # 평균 토큰 수
                token_counts = [int(meta.get("token_count", 0)) for meta in sample_metadata]
                if token_counts:
                    stats["avg_token_count"] = sum(token_counts) / len(token_counts)
            
            return stats
            
        except Exception as e:
            logger.error(f"통계 조회 오류: {e}")
            return {"error": str(e)}
    
    def delete_documents(self, content_hashes: List[str]) -> int:
        """문서 삭제"""
        try:
            self.collection.delete(ids=content_hashes)
            deleted_count = len(content_hashes)
            logger.info(f"문서 삭제 완료: {deleted_count}개")
            return deleted_count
        except Exception as e:
            logger.error(f"문서 삭제 오류: {e}")
            return 0
    
    def clear_collection(self) -> bool:
        """컬렉션 전체 삭제"""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self._get_or_create_collection()
            logger.info(f"컬렉션 초기화 완료: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"컬렉션 초기화 오류: {e}")
            return False
    
    def close(self):
        """리소스 정리"""
        if self.embedding_service:
            self.embedding_service.close()


# 편의 함수들
def get_chroma_index_manager(collection_name: str = "naver_blog_debt_collection",
                           persist_directory: str = "./src/data/indexes/default/chroma") -> ChromaIndexManager:
    """ChromaDB 인덱스 매니저 인스턴스 생성"""
    return ChromaIndexManager(collection_name, persist_directory)


def index_chunks(chunks: List[Dict[str, Any]], 
                collection_name: str = "naver_blog_debt_collection") -> Dict[str, int]:
    """간편한 청크 인덱싱"""
    manager = get_chroma_index_manager(collection_name)
    try:
        return manager.upsert_chunks(chunks)
    finally:
        manager.close()


# 테스트용 함수
def test_chroma_index():
    """ChromaDB 인덱스 테스트"""
    # 테스트용 인덱스 매니저 생성
    manager = ChromaIndexManager(
        collection_name="test_collection",
        persist_directory="./test_chroma"
    )
    
    try:
        # 테스트 청크 생성
        test_chunks = [
            {
                "text": "채권추심 절차는 다음과 같습니다.",
                "metadata": {
                    "source_url": "https://test.com/1",
                    "logno": "12345",
                    "published_at": "2024-01-15",
                    "law_topic": "채권추심"
                }
            },
            {
                "text": "지급명령 신청 방법을 설명합니다.",
                "metadata": {
                    "source_url": "https://test.com/2",
                    "logno": "12346",
                    "published_at": "2024-01-16",
                    "law_topic": "채권추심"
                }
            }
        ]
        
        # 청크 인덱싱
        result = manager.upsert_chunks(test_chunks)
        print(f"✅ 청크 인덱싱 테스트 통과: {result}")
        
        # 검색 테스트
        search_results = manager.search("채권추심 절차", top_k=5)
        print(f"✅ 검색 테스트 통과: {len(search_results)}개 결과")
        
        # 통계 조회
        stats = manager.get_collection_stats()
        print(f"✅ 통계 조회 테스트 통과: {stats}")
        
        # 중복 인덱싱 테스트 (스킵 확인)
        result2 = manager.upsert_chunks(test_chunks)
        print(f"✅ 중복 인덱싱 테스트 통과: {result2}")
        
    finally:
        manager.close()
        # 테스트 파일 정리
        import shutil
        if os.path.exists("./test_chroma"):
            shutil.rmtree("./test_chroma")
    
    print("✅ ChromaIndexManager 테스트 완료")


if __name__ == "__main__":
    test_chroma_index()
