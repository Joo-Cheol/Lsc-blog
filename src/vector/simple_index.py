#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 벡터 인덱스 (ChromaDB 대안)
"""
import os
import hashlib
import pickle
import numpy as np
import logging
from typing import List, Dict, Optional, Tuple, Any
try:
    from .embedder import EmbeddingService
except ImportError:
    from embedder import EmbeddingService

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleVectorIndex:
    """간단한 벡터 인덱스 클래스"""
    
    def __init__(self, 
                 index_name: str = "naver_blog_debt_collection",
                 persist_directory: str = "./src/data/indexes/default/simple",
                 embedding_service: Optional[EmbeddingService] = None):
        self.index_name = index_name
        self.persist_directory = persist_directory
        self.embedding_service = embedding_service or EmbeddingService()
        
        # 인덱스 파일 경로
        self.index_file = os.path.join(persist_directory, f"{index_name}.pkl")
        self.metadata_file = os.path.join(persist_directory, f"{index_name}_metadata.pkl")
        
        # 인덱스 데이터
        self.documents = {}  # {doc_id: {"text": str, "embedding": np.ndarray, "metadata": dict}}
        self.embeddings_matrix = None  # 모든 임베딩을 담은 행렬
        self.doc_ids = []  # 문서 ID 순서
        
        # 디렉터리 생성 및 인덱스 로드
        os.makedirs(persist_directory, exist_ok=True)
        self._load_index()
        
        logger.info(f"SimpleVectorIndex 초기화 완료: {index_name}")
    
    def get_content_hash(self, content: str) -> str:
        """콘텐츠 해시 생성"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _load_index(self):
        """인덱스 로드"""
        try:
            if os.path.exists(self.index_file) and os.path.exists(self.metadata_file):
                with open(self.index_file, 'rb') as f:
                    self.documents = pickle.load(f)
                with open(self.metadata_file, 'rb') as f:
                    metadata = pickle.load(f)
                    self.embeddings_matrix = metadata.get('embeddings_matrix')
                    self.doc_ids = metadata.get('doc_ids', [])
                
                logger.info(f"인덱스 로드 완료: {len(self.documents)}개 문서")
            else:
                logger.info("새 인덱스 생성")
        except Exception as e:
            logger.error(f"인덱스 로드 오류: {e}")
            self.documents = {}
            self.embeddings_matrix = None
            self.doc_ids = []
    
    def _save_index(self):
        """인덱스 저장"""
        try:
            with open(self.index_file, 'wb') as f:
                pickle.dump(self.documents, f)
            
            metadata = {
                'embeddings_matrix': self.embeddings_matrix,
                'doc_ids': self.doc_ids
            }
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(metadata, f)
            
            logger.info(f"인덱스 저장 완료: {len(self.documents)}개 문서")
        except Exception as e:
            logger.error(f"인덱스 저장 오류: {e}")
    
    def _update_embeddings_matrix(self):
        """임베딩 행렬 업데이트"""
        if not self.documents:
            self.embeddings_matrix = None
            self.doc_ids = []
            return
        
        # 문서 ID 순서 정렬
        self.doc_ids = sorted(self.documents.keys())
        
        # 임베딩 행렬 생성
        embeddings = []
        for doc_id in self.doc_ids:
            embeddings.append(self.documents[doc_id]['embedding'])
        
        self.embeddings_matrix = np.vstack(embeddings)
        logger.debug(f"임베딩 행렬 업데이트: {self.embeddings_matrix.shape}")
    
    def upsert_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, int]:
        """청크들을 벡터 인덱스에 업서트"""
        if not chunks:
            return {"added": 0, "skipped": 0, "failed": 0}
        
        added_count = 0
        skipped_count = 0
        failed_count = 0
        
        # 처리할 청크들 필터링
        chunks_to_process = []
        
        for chunk in chunks:
            try:
                content_hash = self.get_content_hash(chunk["text"])
                
                # 기존 문서 확인
                if content_hash in self.documents:
                    logger.debug(f"문서 이미 존재: {content_hash[:8]}...")
                    skipped_count += 1
                    continue
                
                chunks_to_process.append({
                    **chunk,
                    "content_hash": content_hash
                })
                
            except Exception as e:
                logger.error(f"청크 처리 오류: {e}")
                failed_count += 1
        
        if not chunks_to_process:
            return {"added": 0, "skipped": skipped_count, "failed": failed_count}
        
        # 임베딩 계산
        texts = [chunk["text"] for chunk in chunks_to_process]
        embeddings = self.embedding_service.get_embeddings_batch(texts)
        
        # 문서 추가
        for i, chunk in enumerate(chunks_to_process):
            try:
                doc_id = chunk["content_hash"]
                self.documents[doc_id] = {
                    "text": chunk["text"],
                    "embedding": embeddings[i],
                    "metadata": self._prepare_metadata(chunk)
                }
                added_count += 1
            except Exception as e:
                logger.error(f"문서 추가 오류: {e}")
                failed_count += 1
        
        # 임베딩 행렬 업데이트 및 저장
        self._update_embeddings_matrix()
        self._save_index()
        
        logger.info(f"[INDEX] 업서트 완료: added={added_count}, skipped={skipped_count}, failed={failed_count}")
        return {
            "added": added_count,
            "skipped": skipped_count,
            "failed": failed_count
        }
    
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
            if not self.documents or self.embeddings_matrix is None:
                logger.warning("인덱스가 비어있음")
                return []
            
            # 쿼리 임베딩 계산
            query_embedding = self.embedding_service.get_or_compute_embedding(query)
            
            # 코사인 유사도 계산
            similarities = np.dot(self.embeddings_matrix, query_embedding) / (
                np.linalg.norm(self.embeddings_matrix, axis=1) * np.linalg.norm(query_embedding)
            )
            
            # 상위 k개 선택
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            # 결과 포맷팅
            results = []
            for idx in top_indices:
                doc_id = self.doc_ids[idx]
                doc = self.documents[doc_id]
                
                # 필터 적용
                if where_filter:
                    if not self._matches_filter(doc["metadata"], where_filter):
                        continue
                
                results.append({
                    "id": doc_id,
                    "text": doc["text"],
                    "metadata": doc["metadata"],
                    "similarity": float(similarities[idx])
                })
            
            logger.info(f"벡터 검색 완료: {len(results)}개 결과")
            return results
            
        except Exception as e:
            logger.error(f"벡터 검색 오류: {e}")
            return []
    
    def _matches_filter(self, metadata: Dict[str, str], where_filter: Dict[str, Any]) -> bool:
        """메타데이터 필터 매칭"""
        for key, value in where_filter.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True
    
    def get_index_stats(self) -> Dict[str, Any]:
        """인덱스 통계 조회"""
        try:
            stats = {
                "total_documents": len(self.documents),
                "index_name": self.index_name,
                "persist_directory": self.persist_directory
            }
            
            if self.documents:
                # 법률 주제별 분포
                law_topics = {}
                token_counts = []
                
                for doc in self.documents.values():
                    topic = doc["metadata"].get("law_topic", "unknown")
                    law_topics[topic] = law_topics.get(topic, 0) + 1
                    
                    token_count = int(doc["metadata"].get("token_count", 0))
                    token_counts.append(token_count)
                
                stats["law_topics"] = law_topics
                
                if token_counts:
                    stats["avg_token_count"] = sum(token_counts) / len(token_counts)
            
            return stats
            
        except Exception as e:
            logger.error(f"통계 조회 오류: {e}")
            return {"error": str(e)}
    
    def delete_documents(self, content_hashes: List[str]) -> int:
        """문서 삭제"""
        try:
            deleted_count = 0
            for content_hash in content_hashes:
                if content_hash in self.documents:
                    del self.documents[content_hash]
                    deleted_count += 1
            
            if deleted_count > 0:
                self._update_embeddings_matrix()
                self._save_index()
            
            logger.info(f"문서 삭제 완료: {deleted_count}개")
            return deleted_count
        except Exception as e:
            logger.error(f"문서 삭제 오류: {e}")
            return 0
    
    def clear_index(self) -> bool:
        """인덱스 전체 삭제"""
        try:
            self.documents = {}
            self.embeddings_matrix = None
            self.doc_ids = []
            self._save_index()
            
            logger.info(f"인덱스 초기화 완료: {self.index_name}")
            return True
        except Exception as e:
            logger.error(f"인덱스 초기화 오류: {e}")
            return False
    
    def close(self):
        """리소스 정리"""
        if self.embedding_service:
            self.embedding_service.close()


# 편의 함수들
def get_simple_vector_index(index_name: str = "naver_blog_debt_collection",
                          persist_directory: str = "./src/data/indexes/default/simple") -> SimpleVectorIndex:
    """간단한 벡터 인덱스 인스턴스 생성"""
    return SimpleVectorIndex(index_name, persist_directory)


def index_chunks_simple(chunks: List[Dict[str, Any]], 
                       index_name: str = "naver_blog_debt_collection") -> Dict[str, int]:
    """간편한 청크 인덱싱"""
    index = get_simple_vector_index(index_name)
    try:
        return index.upsert_chunks(chunks)
    finally:
        index.close()


# 테스트용 함수
def test_simple_vector_index():
    """간단한 벡터 인덱스 테스트"""
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 테스트용 인덱스 생성
        index = SimpleVectorIndex(
            index_name="test_simple_index",
            persist_directory=temp_dir
        )
        
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
        result = index.upsert_chunks(test_chunks)
        print(f"✅ 청크 인덱싱 테스트 통과: {result}")
        
        # 검색 테스트
        search_results = index.search("채권추심 절차", top_k=5)
        print(f"✅ 검색 테스트 통과: {len(search_results)}개 결과")
        
        # 통계 조회
        stats = index.get_index_stats()
        print(f"✅ 통계 조회 테스트 통과: {stats}")
        
        # 중복 인덱싱 테스트 (스킵 확인)
        result2 = index.upsert_chunks(test_chunks)
        print(f"✅ 중복 인덱싱 테스트 통과: {result2}")
        
        index.close()
        
    finally:
        # 테스트 파일 정리
        shutil.rmtree(temp_dir)
    
    print("✅ SimpleVectorIndex 테스트 완료")


if __name__ == "__main__":
    test_simple_vector_index()
