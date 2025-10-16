#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
벡터 모듈 단위 테스트
"""
import unittest
import os
import sys
import tempfile
import shutil
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.vector.embedder import EmbeddingCache, EmbeddingService
from src.vector.simple_index import SimpleVectorIndex


class TestEmbeddingCache(unittest.TestCase):
    """EmbeddingCache 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_db_path = os.path.join(self.temp_dir, "test_cache.sqlite")
        self.cache = EmbeddingCache(self.cache_db_path)
    
    def tearDown(self):
        """테스트 정리"""
        self.cache.close()
        shutil.rmtree(self.temp_dir)
    
    def test_cache_initialization(self):
        """캐시 초기화 테스트"""
        # 스키마 확인
        cursor = self.cache.conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        self.assertIn('embedding_cache', tables)
    
    def test_text_hash_generation(self):
        """텍스트 해시 생성 테스트"""
        text1 = "채권추심 절차"
        text2 = "채권추심 절차"
        text3 = "지급명령 신청"
        
        hash1 = self.cache.get_text_hash(text1)
        hash2 = self.cache.get_text_hash(text2)
        hash3 = self.cache.get_text_hash(text3)
        
        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)
        self.assertEqual(len(hash1), 64)  # SHA-256 해시 길이
    
    def test_cache_operations(self):
        """캐시 저장/조회 테스트"""
        import numpy as np
        
        text = "채권추심 절차에 대한 설명"
        model_name = "test_model"
        embedding = np.random.rand(768).astype(np.float32)
        
        # 캐시에 저장
        self.cache.cache_embedding(text, embedding, model_name)
        
        # 캐시에서 조회
        cached_embedding = self.cache.get_cached_embedding(text, model_name)
        
        self.assertIsNotNone(cached_embedding)
        self.assertTrue(np.array_equal(embedding, cached_embedding))
    
    def test_cache_miss(self):
        """캐시 미스 테스트"""
        text = "존재하지 않는 텍스트"
        model_name = "test_model"
        
        cached_embedding = self.cache.get_cached_embedding(text, model_name)
        self.assertIsNone(cached_embedding)
    
    def test_cache_stats(self):
        """캐시 통계 테스트"""
        import numpy as np
        
        # 테스트 데이터 추가
        texts = ["텍스트1", "텍스트2", "텍스트3"]
        model_name = "test_model"
        
        for text in texts:
            embedding = np.random.rand(768).astype(np.float32)
            self.cache.cache_embedding(text, embedding, model_name)
        
        # 통계 조회
        stats = self.cache.get_cache_stats()
        
        self.assertEqual(stats['total_entries'], 3)
        self.assertEqual(stats['unique_models'], 1)
        self.assertGreaterEqual(stats['total_accesses'], 0)


class TestEmbeddingService(unittest.TestCase):
    """EmbeddingService 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_db_path = os.path.join(self.temp_dir, "test_embeddings.sqlite")
        
        # CPU 모델로 테스트 (GPU 없어도 실행 가능)
        self.service = EmbeddingService(
            model_name="intfloat/multilingual-e5-base",
            device="cpu",
            cache_db_path=self.cache_db_path
        )
    
    def tearDown(self):
        """테스트 정리"""
        self.service.close()
        shutil.rmtree(self.temp_dir)
    
    def test_embedding_computation(self):
        """임베딩 계산 테스트"""
        text = "채권추심 절차에 대한 설명입니다."
        
        embedding = self.service.get_or_compute_embedding(text)
        
        self.assertIsNotNone(embedding)
        self.assertEqual(len(embedding.shape), 1)  # 1차원 벡터
        self.assertGreater(embedding.shape[0], 0)  # 0보다 큰 차원
    
    def test_embedding_caching(self):
        """임베딩 캐싱 테스트"""
        text = "채권추심 절차에 대한 설명입니다."
        
        # 첫 번째 계산
        embedding1 = self.service.get_or_compute_embedding(text)
        
        # 두 번째 계산 (캐시에서 조회)
        embedding2 = self.service.get_or_compute_embedding(text)
        
        # 결과가 동일한지 확인
        import numpy as np
        self.assertTrue(np.array_equal(embedding1, embedding2))
    
    def test_batch_embedding(self):
        """배치 임베딩 테스트"""
        texts = [
            "채권추심 절차",
            "지급명령 신청 방법",
            "강제집행 절차"
        ]
        
        embeddings = self.service.get_embeddings_batch(texts)
        
        self.assertEqual(len(embeddings), len(texts))
        for embedding in embeddings:
            self.assertIsNotNone(embedding)
            self.assertEqual(len(embedding.shape), 1)
    
    def test_similarity_computation(self):
        """유사도 계산 테스트"""
        text1 = "채권추심 절차"
        text2 = "채권 회수 방법"
        text3 = "오늘 날씨가 좋습니다"
        
        similarity1 = self.service.get_similarity(text1, text2)
        similarity2 = self.service.get_similarity(text1, text3)
        
        # 관련 텍스트 간 유사도가 더 높아야 함
        self.assertGreater(similarity1, similarity2)
        self.assertGreaterEqual(similarity1, -1.0)
        self.assertLessEqual(similarity1, 1.0)
    
    def test_empty_text_handling(self):
        """빈 텍스트 처리 테스트"""
        empty_text = ""
        whitespace_text = "   "
        
        embedding1 = self.service.get_or_compute_embedding(empty_text)
        embedding2 = self.service.get_or_compute_embedding(whitespace_text)
        
        # 빈 텍스트는 0 벡터 반환
        import numpy as np
        self.assertTrue(np.allclose(embedding1, 0))
        self.assertTrue(np.allclose(embedding2, 0))


class TestSimpleVectorIndex(unittest.TestCase):
    """SimpleVectorIndex 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.index_dir = os.path.join(self.temp_dir, "test_index")
        
        self.manager = SimpleVectorIndex(
            index_name="test_collection",
            persist_directory=self.index_dir
        )
    
    def tearDown(self):
        """테스트 정리"""
        self.manager.close()
        shutil.rmtree(self.temp_dir)
    
    def test_index_creation(self):
        """인덱스 생성 테스트"""
        # 인덱스가 생성되었는지 확인
        self.assertIsNotNone(self.manager.documents)
        self.assertEqual(self.manager.index_name, "test_collection")
    
    def test_content_hash_generation(self):
        """콘텐츠 해시 생성 테스트"""
        content1 = "채권추심 절차"
        content2 = "채권추심 절차"
        content3 = "지급명령 신청"
        
        hash1 = self.manager.get_content_hash(content1)
        hash2 = self.manager.get_content_hash(content2)
        hash3 = self.manager.get_content_hash(content3)
        
        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)
        self.assertEqual(len(hash1), 64)
    
    def test_chunk_upsert(self):
        """청크 업서트 테스트"""
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
        
        result = self.manager.upsert_chunks(test_chunks)
        
        self.assertIn("added", result)
        self.assertIn("skipped", result)
        self.assertIn("failed", result)
        self.assertGreaterEqual(result["added"], 0)
    
    def test_duplicate_chunk_handling(self):
        """중복 청크 처리 테스트"""
        test_chunk = {
            "text": "중복 테스트 텍스트",
            "metadata": {
                "source_url": "https://test.com/duplicate",
                "logno": "99999",
                "published_at": "2024-01-15",
                "law_topic": "채권추심"
            }
        }
        
        # 첫 번째 업서트
        result1 = self.manager.upsert_chunks([test_chunk])
        
        # 두 번째 업서트 (중복)
        result2 = self.manager.upsert_chunks([test_chunk])
        
        # 첫 번째는 추가, 두 번째는 스킵되어야 함
        self.assertGreaterEqual(result1["added"], 1)
        self.assertGreaterEqual(result2["skipped"], 1)
    
    def test_vector_search(self):
        """벡터 검색 테스트"""
        # 테스트 데이터 추가
        test_chunks = [
            {
                "text": "채권추심 절차에 대한 상세한 설명입니다.",
                "metadata": {
                    "source_url": "https://test.com/search1",
                    "logno": "11111",
                    "published_at": "2024-01-15",
                    "law_topic": "채권추심"
                }
            },
            {
                "text": "지급명령 신청 방법과 절차를 설명합니다.",
                "metadata": {
                    "source_url": "https://test.com/search2",
                    "logno": "22222",
                    "published_at": "2024-01-16",
                    "law_topic": "채권추심"
                }
            }
        ]
        
        # 데이터 추가
        self.manager.upsert_chunks(test_chunks)
        
        # 검색 실행
        results = self.manager.search("채권추심 절차", top_k=5)
        
        self.assertIsInstance(results, list)
        self.assertGreaterEqual(len(results), 0)
        
        # 결과 구조 확인
        if results:
            result = results[0]
            self.assertIn("id", result)
            self.assertIn("text", result)
            self.assertIn("metadata", result)
    
    def test_index_stats(self):
        """인덱스 통계 테스트"""
        # 테스트 데이터 추가
        test_chunks = [
            {
                "text": "통계 테스트 텍스트 1",
                "metadata": {
                    "source_url": "https://test.com/stats1",
                    "logno": "33333",
                    "published_at": "2024-01-15",
                    "law_topic": "채권추심"
                }
            }
        ]
        
        self.manager.upsert_chunks(test_chunks)
        
        # 통계 조회
        stats = self.manager.get_index_stats()
        
        self.assertIn("total_documents", stats)
        self.assertIn("index_name", stats)
        self.assertGreaterEqual(stats["total_documents"], 0)


class TestIntegration(unittest.TestCase):
    """통합 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_db_path = os.path.join(self.temp_dir, "test_embeddings.sqlite")
        self.chroma_dir = os.path.join(self.temp_dir, "test_chroma")
    
    def tearDown(self):
        """테스트 정리"""
        shutil.rmtree(self.temp_dir)
    
    def test_embedding_and_indexing_pipeline(self):
        """임베딩 + 인덱싱 파이프라인 테스트"""
        # 임베딩 서비스 생성
        embedding_service = EmbeddingService(
            model_name="intfloat/multilingual-e5-base",
            device="cpu",
            cache_db_path=self.cache_db_path
        )
        
        # 인덱스 매니저 생성
        index_manager = SimpleVectorIndex(
            index_name="test_pipeline",
            persist_directory=self.chroma_dir,
            embedding_service=embedding_service
        )
        
        try:
            # 테스트 청크 생성
            test_chunks = [
                {
                    "text": "채권추심 절차는 내용증명 발송부터 시작됩니다.",
                    "metadata": {
                        "source_url": "https://test.com/pipeline1",
                        "logno": "44444",
                        "published_at": "2024-01-15",
                        "law_topic": "채권추심"
                    }
                },
                {
                    "text": "지급명령 신청 시 필요한 서류들을 준비해야 합니다.",
                    "metadata": {
                        "source_url": "https://test.com/pipeline2",
                        "logno": "55555",
                        "published_at": "2024-01-16",
                        "law_topic": "채권추심"
                    }
                }
            ]
            
            # 1단계: 청크 인덱싱
            index_result = index_manager.upsert_chunks(test_chunks)
            self.assertGreaterEqual(index_result["added"], 0)
            
            # 2단계: 벡터 검색
            search_results = index_manager.search("채권추심 절차", top_k=5)
            self.assertIsInstance(search_results, list)
            
            # 3단계: 통계 확인
            stats = index_manager.get_index_stats()
            self.assertIn("total_documents", stats)
            
        finally:
            embedding_service.close()
            index_manager.close()


if __name__ == '__main__':
    # 테스트 실행
    unittest.main(verbosity=2)
