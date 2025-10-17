"""
ChromaDB 인덱스 관리 모듈
- chunk_hash 기반 업서트
- added/skipped 로그
- 메타데이터 필터링 지원
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional, Tuple
import logging
from pathlib import Path
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class ChromaIndexer:
    """ChromaDB 인덱스 관리"""
    
    def __init__(self, persist_directory: str = "data/chroma", collection_name: str = "legal_documents"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self._init_client()
    
    def _init_client(self):
        """ChromaDB 클라이언트 초기화"""
        try:
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # 컬렉션 생성 또는 가져오기
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
                logger.info(f"Loaded existing collection: {self.collection_name}")
            except Exception:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Legal documents for RAG system"}
                )
                logger.info(f"Created new collection: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise
    
    def upsert_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]], chunk_hashes: List[str]) -> Dict[str, int]:
        """
        청크들을 ChromaDB에 업서트
        Returns: {"added": count, "skipped": count}
        """
        if not chunks or not embeddings or not chunk_hashes:
            return {"added": 0, "skipped": 0}
        
        if len(chunks) != len(embeddings) or len(chunks) != len(chunk_hashes):
            raise ValueError("chunks, embeddings, and chunk_hashes must have the same length")
        
        added_count = 0
        skipped_count = 0
        
        # 배치 처리 (ChromaDB 권장 크기: 100개씩)
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            batch_hashes = chunk_hashes[i:i + batch_size]
            
            # 기존 문서 ID 확인
            existing_ids = set()
            try:
                existing_docs = self.collection.get(ids=batch_hashes)
                existing_ids = set(existing_docs['ids'])
            except Exception as e:
                logger.debug(f"No existing documents found for batch: {e}")
            
            # 새로운 문서만 필터링
            new_chunks = []
            new_embeddings = []
            new_ids = []
            new_metadatas = []
            
            for chunk, embedding, chunk_hash in zip(batch_chunks, batch_embeddings, batch_hashes):
                if chunk_hash not in existing_ids:
                    new_chunks.append(chunk['text'])
                    new_embeddings.append(embedding)
                    new_ids.append(chunk_hash)
                    
                    # 메타데이터 구성
                    metadata = {
                        "source_url": chunk.get('source_url', ''),
                        "logno": chunk.get('logno', 0),
                        "content_hash": chunk_hash,
                        "published_at": chunk.get('published_at', ''),
                        "law_topic": chunk.get('law_topic', ''),
                        "title": chunk.get('title', ''),
                        "chunk_index": chunk.get('chunk_index', 0),
                        "total_chunks": chunk.get('total_chunks', 1),
                        "created_at": datetime.now().isoformat()
                    }
                    new_metadatas.append(metadata)
                else:
                    skipped_count += 1
            
            # 새로운 문서들만 업서트
            if new_chunks:
                try:
                    self.collection.upsert(
                        ids=new_ids,
                        documents=new_chunks,
                        embeddings=new_embeddings,
                        metadatas=new_metadatas
                    )
                    added_count += len(new_chunks)
                    logger.info(f"Upserted {len(new_chunks)} new documents (batch {i//batch_size + 1})")
                except Exception as e:
                    logger.error(f"Failed to upsert batch {i//batch_size + 1}: {e}")
                    raise
        
        logger.info(f"Upsert complete: {added_count} added, {skipped_count} skipped")
        return {"added": added_count, "skipped": skipped_count}
    
    def search(self, query_embedding: List[float], top_k: int = 20, 
               where_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        임베딩 기반 검색
        Returns: 검색 결과 리스트
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,
                include=['documents', 'metadatas', 'distances']
            )
            
            # 결과 포맷팅
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    formatted_results.append({
                        'document': doc,
                        'metadata': metadata,
                        'distance': distance,
                        'score': 1 - distance,  # ChromaDB distance를 score로 변환
                        'rank': i + 1
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계 반환"""
        try:
            # 전체 문서 수
            count = self.collection.count()
            
            # 샘플 메타데이터로 통계 생성
            sample_docs = self.collection.get(limit=1000, include=['metadatas'])
            
            stats = {
                "total_documents": count,
                "collection_name": self.collection_name,
                "last_updated": datetime.now().isoformat()
            }
            
            if sample_docs['metadatas']:
                # 소스별 통계
                sources = {}
                topics = {}
                lognos = []
                
                for metadata in sample_docs['metadatas']:
                    source = metadata.get('source_url', 'unknown')
                    topic = metadata.get('law_topic', 'unknown')
                    logno = metadata.get('logno', 0)
                    
                    sources[source] = sources.get(source, 0) + 1
                    topics[topic] = topics.get(topic, 0) + 1
                    if logno > 0:
                        lognos.append(logno)
                
                stats.update({
                    "sources": sources,
                    "topics": topics,
                    "logno_range": {
                        "min": min(lognos) if lognos else 0,
                        "max": max(lognos) if lognos else 0
                    }
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}
    
    def delete_by_filter(self, where_filter: Dict[str, Any]) -> int:
        """필터 조건에 맞는 문서 삭제"""
        try:
            # 삭제할 문서 ID 조회
            results = self.collection.get(where=where_filter, include=['metadatas'])
            ids_to_delete = results['ids']
            
            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)
                logger.info(f"Deleted {len(ids_to_delete)} documents")
                return len(ids_to_delete)
            else:
                logger.info("No documents found matching filter")
                return 0
                
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return 0
    
    def reset_collection(self):
        """컬렉션 초기화"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Legal documents for RAG system"}
            )
            logger.info(f"Reset collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            raise


# 전역 인스턴스
chroma_indexer = ChromaIndexer()