"""
임베딩 캐시 & 계산 모듈
- chunk_hash 기반 캐시 시스템
- get_or_compute() 패턴으로 중복 계산 방지
"""

import hashlib
import sqlite3
import json
import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import logging
from sentence_transformers import SentenceTransformer
import time

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """임베딩 캐시 시스템"""
    
    def __init__(self, cache_path: str = None, model_name: str = None, batch_size: int = None):
        # 환경변수에서 설정 가져오기
        import os
        self.cache_path = Path(cache_path or os.getenv("EMBEDDING_CACHE_DB", "data/embedding_cache.db"))
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.model_name = model_name or os.getenv("EMBED_MODEL", "jhgan/ko-sroberta-multitask")
        self.batch_size = batch_size or int(os.getenv("EMBED_BATCH_SIZE", "32"))
        self.model = None
        self._init_cache()
    
    def _init_cache(self):
        """캐시 데이터베이스 초기화"""
        with sqlite3.connect(self.cache_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embedding_cache (
                    chunk_hash TEXT PRIMARY KEY,
                    chunk_text TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    model_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 인덱스 생성
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_model ON embedding_cache(model_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_created ON embedding_cache(created_at)")
            
            conn.commit()
    
    def get_chunk_hash(self, chunk_text: str) -> str:
        """청크 텍스트의 해시 생성"""
        return hashlib.sha256(chunk_text.encode('utf-8')).hexdigest()
    
    def _load_model(self):
        """모델 로드 (지연 로딩)"""
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Model loaded successfully")
    
    def _embed_text(self, text: str) -> np.ndarray:
        """텍스트 임베딩 계산"""
        self._load_model()
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.astype(np.float32)  # 메모리 절약
    
    def get_cached_embedding(self, chunk_hash: str) -> Optional[np.ndarray]:
        """캐시에서 임베딩 조회"""
        with sqlite3.connect(self.cache_path) as conn:
            cursor = conn.execute("""
                SELECT embedding, access_count FROM embedding_cache 
                WHERE chunk_hash = ? AND model_name = ?
            """, (chunk_hash, self.model_name))
            
            result = cursor.fetchone()
            if result:
                embedding_bytes, access_count = result
                embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                
                # 접근 통계 업데이트
                conn.execute("""
                    UPDATE embedding_cache 
                    SET access_count = ?, last_accessed = CURRENT_TIMESTAMP
                    WHERE chunk_hash = ?
                """, (access_count + 1, chunk_hash))
                conn.commit()
                
                return embedding
            return None
    
    def cache_embedding(self, chunk_hash: str, chunk_text: str, embedding: np.ndarray):
        """임베딩을 캐시에 저장"""
        embedding_bytes = embedding.astype(np.float32).tobytes()
        
        with sqlite3.connect(self.cache_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO embedding_cache 
                (chunk_hash, chunk_text, embedding, model_name, created_at, access_count, last_accessed)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP)
            """, (chunk_hash, chunk_text, embedding_bytes, self.model_name))
            conn.commit()
    
    def get_or_compute(self, chunk_text: str) -> Tuple[np.ndarray, str]:
        """
        임베딩을 가져오거나 계산
        Returns: (embedding, chunk_hash)
        """
        chunk_hash = self.get_chunk_hash(chunk_text)
        
        # 캐시에서 조회
        cached_embedding = self.get_cached_embedding(chunk_hash)
        if cached_embedding is not None:
            logger.debug(f"Cache hit for chunk_hash: {chunk_hash[:8]}...")
            return cached_embedding, chunk_hash
        
        # 캐시 미스 - 새로 계산
        logger.debug(f"Cache miss for chunk_hash: {chunk_hash[:8]}...")
        start_time = time.time()
        embedding = self._embed_text(chunk_text)
        compute_time = time.time() - start_time
        
        # 캐시에 저장
        self.cache_embedding(chunk_hash, chunk_text, embedding)
        
        logger.info(f"Computed and cached embedding in {compute_time:.2f}s")
        return embedding, chunk_hash
    
    def batch_get_or_compute(self, chunk_texts: List[str]) -> Tuple[List[np.ndarray], List[str]]:
        """배치 임베딩 계산"""
        embeddings = []
        chunk_hashes = []
        
        # 캐시 히트/미스 분리
        cache_hits = []
        cache_misses = []
        
        for i, text in enumerate(chunk_texts):
            chunk_hash = self.get_chunk_hash(text)
            cached_embedding = self.get_cached_embedding(chunk_hash)
            
            if cached_embedding is not None:
                cache_hits.append((i, cached_embedding, chunk_hash))
            else:
                cache_misses.append((i, text, chunk_hash))
        
        # 캐시 히트 결과 배치
        for i, embedding, chunk_hash in cache_hits:
            embeddings.append(embedding)
            chunk_hashes.append(chunk_hash)
        
        # 캐시 미스 배치 계산
        if cache_misses:
            self._load_model()
            miss_texts = [item[1] for item in cache_misses]
            miss_hashes = [item[2] for item in cache_misses]
            
            start_time = time.time()
            batch_embeddings = self.model.encode(miss_texts, convert_to_numpy=True, batch_size=self.batch_size)
            compute_time = time.time() - start_time
            
            # 결과 정렬 및 캐시 저장
            for (i, _, chunk_hash), embedding in zip(cache_misses, batch_embeddings):
                embedding = embedding.astype(np.float32)
                embeddings.append(embedding)
                chunk_hashes.append(chunk_hash)
                
                # 캐시에 저장
                self.cache_embedding(chunk_hash, miss_texts[i - len(cache_hits)], embedding)
            
            logger.info(f"Batch computed {len(cache_misses)} embeddings in {compute_time:.2f}s")
        
        # 원래 순서대로 정렬
        sorted_results = sorted(zip(range(len(chunk_texts)), embeddings, chunk_hashes))
        final_embeddings = [emb for _, emb, _ in sorted_results]
        final_hashes = [hash_val for _, _, hash_val in sorted_results]
        
        hit_rate = len(cache_hits) / len(chunk_texts) * 100
        logger.info(f"Batch embedding complete: {len(cache_hits)} hits, {len(cache_misses)} misses (hit rate: {hit_rate:.1f}%)")
        
        return final_embeddings, final_hashes
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        with sqlite3.connect(self.cache_path) as conn:
            # 전체 통계
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_embeddings,
                    COUNT(DISTINCT model_name) as models,
                    SUM(access_count) as total_accesses,
                    AVG(access_count) as avg_accesses,
                    MIN(created_at) as oldest_entry,
                    MAX(last_accessed) as last_access
                FROM embedding_cache
            """)
            stats = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))
            
            # 모델별 통계
            cursor = conn.execute("""
                SELECT model_name, COUNT(*) as count, SUM(access_count) as accesses
                FROM embedding_cache 
                GROUP BY model_name
            """)
            stats['by_model'] = [dict(zip(['model_name', 'count', 'accesses'], row)) for row in cursor.fetchall()]
            
            # 최근 접근 통계
            cursor = conn.execute("""
                SELECT 
                    COUNT(CASE WHEN last_accessed > datetime('now', '-1 day') THEN 1 END) as accessed_today,
                    COUNT(CASE WHEN last_accessed > datetime('now', '-7 days') THEN 1 END) as accessed_week
                FROM embedding_cache
            """)
            recent_stats = cursor.fetchone()
            stats['accessed_today'] = recent_stats[0]
            stats['accessed_week'] = recent_stats[1]
            
            return stats
    
    def cleanup_old_cache(self, days: int = 30, min_access_count: int = 2):
        """오래되고 사용되지 않는 캐시 정리"""
        with sqlite3.connect(self.cache_path) as conn:
            cursor = conn.execute("""
                DELETE FROM embedding_cache 
                WHERE created_at < datetime('now', '-? days')
                AND access_count < ?
            """, (days, min_access_count))
            deleted_count = cursor.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted_count} old cache entries")
            return deleted_count


# 전역 인스턴스
embedding_cache = EmbeddingCache()