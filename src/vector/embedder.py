#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
임베딩 캐시 및 벡터화 모듈
"""
import os
import sqlite3
import hashlib
import pickle
import numpy as np
from typing import List, Dict, Optional, Tuple
from sentence_transformers import SentenceTransformer
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingCache:
    """임베딩 캐시 관리 클래스"""
    
    def __init__(self, cache_db_path: str):
        self.cache_db_path = cache_db_path
        self.conn = self._get_connection()
        self._init_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결 생성"""
        # 디렉터리 생성
        os.makedirs(os.path.dirname(self.cache_db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.cache_db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn
    
    def _init_schema(self):
        """캐시 스키마 초기화"""
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS embedding_cache (
            text_hash TEXT PRIMARY KEY,
            text_content TEXT NOT NULL,
            embedding BLOB NOT NULL,
            model_name TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            access_count INTEGER DEFAULT 0,
            last_accessed INTEGER NOT NULL
        );
        
        CREATE INDEX IF NOT EXISTS idx_model_name ON embedding_cache(model_name);
        CREATE INDEX IF NOT EXISTS idx_created_at ON embedding_cache(created_at);
        CREATE INDEX IF NOT EXISTS idx_access_count ON embedding_cache(access_count);
        """)
        self.conn.commit()
    
    def get_text_hash(self, text: str) -> str:
        """텍스트 해시 생성"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def get_cached_embedding(self, text: str, model_name: str) -> Optional[np.ndarray]:
        """캐시된 임베딩 조회"""
        text_hash = self.get_text_hash(text)
        
        cursor = self.conn.execute("""
            SELECT embedding, access_count FROM embedding_cache 
            WHERE text_hash = ? AND model_name = ?
        """, (text_hash, model_name))
        
        row = cursor.fetchone()
        if row:
            embedding_blob, access_count = row
            embedding = pickle.loads(embedding_blob)
            
            # 접근 횟수 업데이트
            import time
            self.conn.execute("""
                UPDATE embedding_cache 
                SET access_count = ?, last_accessed = ?
                WHERE text_hash = ? AND model_name = ?
            """, (access_count + 1, int(time.time()), text_hash, model_name))
            self.conn.commit()
            
            logger.debug(f"캐시 히트: {text_hash[:8]}... (접근 횟수: {access_count + 1})")
            return embedding
        
        logger.debug(f"캐시 미스: {text_hash[:8]}...")
        return None
    
    def cache_embedding(self, text: str, embedding: np.ndarray, model_name: str):
        """임베딩 캐시 저장"""
        text_hash = self.get_text_hash(text)
        embedding_blob = pickle.dumps(embedding)
        
        import time
        now = int(time.time())
        
        self.conn.execute("""
            INSERT OR REPLACE INTO embedding_cache 
            (text_hash, text_content, embedding, model_name, created_at, last_accessed)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (text_hash, text, embedding_blob, model_name, now, now))
        self.conn.commit()
        
        logger.debug(f"임베딩 캐시 저장: {text_hash[:8]}...")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """캐시 통계 조회"""
        cursor = self.conn.execute("""
            SELECT 
                COUNT(*) as total_entries,
                COUNT(DISTINCT model_name) as unique_models,
                SUM(access_count) as total_accesses,
                AVG(access_count) as avg_accesses
            FROM embedding_cache
        """)
        
        row = cursor.fetchone()
        return {
            'total_entries': row[0] or 0,
            'unique_models': row[1] or 0,
            'total_accesses': row[2] or 0,
            'avg_accesses': int(row[3] or 0)
        }
    
    def cleanup_old_entries(self, days_old: int = 30):
        """오래된 캐시 항목 정리"""
        import time
        cutoff_time = int(time.time()) - (days_old * 24 * 60 * 60)
        
        cursor = self.conn.execute("""
            DELETE FROM embedding_cache 
            WHERE created_at < ? AND access_count < 2
        """, (cutoff_time,))
        
        deleted_count = cursor.rowcount
        self.conn.commit()
        
        logger.info(f"오래된 캐시 항목 {deleted_count}개 정리 완료")
        return deleted_count
    
    def close(self):
        """연결 종료"""
        self.conn.close()


class EmbeddingService:
    """임베딩 서비스 클래스"""
    
    def __init__(self, model_name: str = "intfloat/multilingual-e5-base", 
                 device: str = "cuda", cache_db_path: str = "./src/data/cache/embeddings.sqlite"):
        self.model_name = model_name
        self.device = device
        self.cache = EmbeddingCache(cache_db_path)
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """모델 로드"""
        try:
            logger.info(f"임베딩 모델 로딩: {self.model_name} (device: {self.device})")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info("임베딩 모델 로딩 완료")
        except Exception as e:
            logger.error(f"모델 로딩 실패: {e}")
            # CPU로 폴백
            if self.device == "cuda":
                logger.info("CPU로 폴백 시도...")
                self.device = "cpu"
                self.model = SentenceTransformer(self.model_name, device=self.device)
                logger.info("CPU 모델 로딩 완료")
            else:
                raise e
    
    def get_or_compute_embedding(self, text: str) -> np.ndarray:
        """임베딩 조회 또는 계산"""
        if not text or not text.strip():
            # 빈 텍스트에 대한 기본 임베딩 반환
            return np.zeros(768, dtype=np.float32)
        
        # 캐시에서 조회
        cached_embedding = self.cache.get_cached_embedding(text, self.model_name)
        if cached_embedding is not None:
            return cached_embedding
        
        # 임베딩 계산
        logger.debug(f"임베딩 계산: {text[:50]}...")
        embedding = self.model.encode(text, convert_to_numpy=True)
        
        # 캐시에 저장
        self.cache.cache_embedding(text, embedding, self.model_name)
        
        return embedding
    
    def get_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """배치 임베딩 계산"""
        if not texts:
            return []
        
        embeddings = []
        cache_hits = 0
        texts_to_compute = []
        indices_to_compute = []
        
        # 캐시 확인
        for i, text in enumerate(texts):
            if not text or not text.strip():
                embeddings.append(np.zeros(768, dtype=np.float32))
                continue
                
            cached_embedding = self.cache.get_cached_embedding(text, self.model_name)
            if cached_embedding is not None:
                embeddings.append(cached_embedding)
                cache_hits += 1
            else:
                embeddings.append(None)  # 플레이스홀더
                texts_to_compute.append(text)
                indices_to_compute.append(i)
        
        # 캐시되지 않은 텍스트들 배치 계산
        if texts_to_compute:
            logger.info(f"배치 임베딩 계산: {len(texts_to_compute)}개 (캐시 히트: {cache_hits}개)")
            
            computed_embeddings = self.model.encode(
                texts_to_compute, 
                batch_size=batch_size,
                convert_to_numpy=True
            )
            
            # 결과 배치 저장
            for i, embedding in enumerate(computed_embeddings):
                original_index = indices_to_compute[i]
                text = texts_to_compute[i]
                
                embeddings[original_index] = embedding
                self.cache.cache_embedding(text, embedding, self.model_name)
        
        logger.info(f"배치 임베딩 완료: 총 {len(texts)}개, 캐시 히트 {cache_hits}개")
        return embeddings
    
    def get_similarity(self, text1: str, text2: str) -> float:
        """두 텍스트 간 유사도 계산"""
        emb1 = self.get_or_compute_embedding(text1)
        emb2 = self.get_or_compute_embedding(text2)
        
        # 코사인 유사도 계산
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)
    
    def get_cache_stats(self) -> Dict[str, int]:
        """캐시 통계 조회"""
        return self.cache.get_cache_stats()
    
    def cleanup_cache(self, days_old: int = 30) -> int:
        """캐시 정리"""
        return self.cache.cleanup_old_entries(days_old)
    
    def close(self):
        """리소스 정리"""
        self.cache.close()


# 편의 함수들
def get_embedding_service(model_name: str = "intfloat/multilingual-e5-base", 
                         device: str = "cuda") -> EmbeddingService:
    """임베딩 서비스 인스턴스 생성"""
    return EmbeddingService(model_name, device)


def compute_text_embedding(text: str, model_name: str = "intfloat/multilingual-e5-base") -> np.ndarray:
    """간편한 텍스트 임베딩 계산"""
    service = get_embedding_service(model_name)
    try:
        return service.get_or_compute_embedding(text)
    finally:
        service.close()


# 테스트용 함수
def test_embedding_service():
    """임베딩 서비스 테스트"""
    # 테스트용 임베딩 서비스 생성
    service = EmbeddingService(
        model_name="intfloat/multilingual-e5-base",
        device="cpu",  # 테스트용으로 CPU 사용
        cache_db_path="./test_embeddings.sqlite"
    )
    
    try:
        # 단일 텍스트 임베딩 테스트
        text1 = "채권추심 절차에 대한 설명입니다."
        embedding1 = service.get_or_compute_embedding(text1)
        print(f"✅ 단일 임베딩 테스트 통과: {embedding1.shape}")
        
        # 캐시 테스트
        embedding1_cached = service.get_or_compute_embedding(text1)
        assert np.array_equal(embedding1, embedding1_cached)
        print("✅ 캐시 테스트 통과")
        
        # 배치 임베딩 테스트
        texts = [
            "채권추심 절차",
            "지급명령 신청 방법",
            "강제집행 절차",
            "내용증명 발송"
        ]
        embeddings = service.get_embeddings_batch(texts)
        print(f"✅ 배치 임베딩 테스트 통과: {len(embeddings)}개")
        
        # 유사도 테스트
        similarity = service.get_similarity("채권추심", "채권 회수")
        print(f"✅ 유사도 테스트 통과: {similarity:.4f}")
        
        # 캐시 통계
        stats = service.get_cache_stats()
        print(f"✅ 캐시 통계: {stats}")
        
    finally:
        service.close()
        # 테스트 파일 정리
        if os.path.exists("./test_embeddings.sqlite"):
            os.remove("./test_embeddings.sqlite")
    
    print("✅ EmbeddingService 테스트 완료")


if __name__ == "__main__":
    test_embedding_service()
