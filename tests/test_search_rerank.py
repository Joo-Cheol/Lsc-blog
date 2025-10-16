#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
검색 및 리랭킹 모듈 단위 테스트
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

from src.vector.reranker import CrossEncoderReranker, TwoStageRetriever
from src.search.search_service import SearchService


class TestCrossEncoderReranker(unittest.TestCase):
    """CrossEncoderReranker 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.reranker = CrossEncoderReranker(device="cpu")  # 테스트용으로 CPU 사용
    
    def test_rerank_basic(self):
        """기본 리랭킹 테스트"""
        query = "채권추심 절차"
        documents = [
            "채권추심은 내용증명 발송부터 시작됩니다.",
            "지급명령 신청 시 필요한 서류들을 준비해야 합니다.",
            "오늘 날씨가 좋습니다.",
            "강제집행 절차에 대해 설명합니다."
        ]
        
        results = self.reranker.rerank(query, documents, top_k=3)
        
        # 검증
        self.assertEqual(len(results), 3)
        self.assertTrue(all(isinstance(result, tuple) for result in results))
        self.assertTrue(all(len(result) == 2 for result in results))
        
        # 점수가 내림차순으로 정렬되었는지 확인
        scores = [result[1] for result in results]
        self.assertEqual(scores, sorted(scores, reverse=True))
    
    def test_rerank_with_metadata(self):
        """메타데이터가 포함된 리랭킹 테스트"""
        query = "채권추심 절차"
        documents = [
            {"text": "채권추심은 내용증명 발송부터 시작됩니다.", "source": "doc1"},
            {"text": "지급명령 신청 시 필요한 서류들을 준비해야 합니다.", "source": "doc2"},
            {"text": "오늘 날씨가 좋습니다.", "source": "doc3"},
            {"text": "강제집행 절차에 대해 설명합니다.", "source": "doc4"}
        ]
        
        results = self.reranker.rerank_with_metadata(query, documents, top_k=3)
        
        # 검증
        self.assertEqual(len(results), 3)
        self.assertTrue(all(isinstance(result, dict) for result in results))
        
        for result in results:
            self.assertIn("text", result)
            self.assertIn("rerank_score", result)
            self.assertIn("source", result)
        
        # 점수가 내림차순으로 정렬되었는지 확인
        scores = [result["rerank_score"] for result in results]
        self.assertEqual(scores, sorted(scores, reverse=True))
    
    def test_rerank_empty_documents(self):
        """빈 문서 리스트 테스트"""
        query = "테스트 쿼리"
        documents = []
        
        results = self.reranker.rerank(query, documents)
        
        # 검증
        self.assertEqual(len(results), 0)
    
    def test_rerank_single_document(self):
        """단일 문서 리랭킹 테스트"""
        query = "채권추심"
        documents = ["채권추심 절차에 대해 설명합니다."]
        
        results = self.reranker.rerank(query, documents)
        
        # 검증
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], documents[0])
        # numpy float도 허용
        import numpy as np
        self.assertTrue(isinstance(results[0][1], (float, np.floating)))


class TestTwoStageRetriever(unittest.TestCase):
    """TwoStageRetriever 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.temp_dir = tempfile.mkdtemp()
        
        # 테스트용 벡터 인덱스 생성
        from src.vector.simple_index import SimpleVectorIndex
        self.vector_index = SimpleVectorIndex(
            index_name="test_retriever",
            persist_directory=self.temp_dir
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
        
        self.vector_index.upsert_chunks(test_chunks)
        
        # 2단계 검색기 생성
        self.retriever = TwoStageRetriever(
            vector_index=self.vector_index,
            top_k_first=10,
            top_k_final=3
        )
    
    def tearDown(self):
        """테스트 정리"""
        self.vector_index.close()
        shutil.rmtree(self.temp_dir)
    
    def test_search_with_rerank(self):
        """2단계 검색 테스트"""
        query = "채권추심 절차"
        
        results = self.retriever.search_with_rerank(query)
        
        # 검증
        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 3)  # top_k_final 제한
        
        for result in results:
            self.assertIn("text", result)
            self.assertIn("metadata", result)
            self.assertIn("search_rank", result)
            self.assertIn("vector_score", result)
            self.assertIn("final_score", result)
    
    def test_search_with_filter(self):
        """필터가 포함된 검색 테스트"""
        query = "절차"
        where_filter = {"law_topic": "채권추심"}
        
        results = self.retriever.search_with_rerank(query, where_filter=where_filter)
        
        # 검증
        self.assertIsInstance(results, list)
        
        for result in results:
            self.assertEqual(result["metadata"]["law_topic"], "채권추심")
    
    def test_search_stats(self):
        """검색 통계 테스트"""
        query = "채권추심 절차"
        
        stats = self.retriever.get_search_stats(query)
        
        # 검증
        self.assertIn("query", stats)
        self.assertIn("vector_search_count", stats)
        self.assertIn("reranked_count", stats)
        self.assertIn("top_k_first", stats)
        self.assertIn("top_k_final", stats)
        
        self.assertEqual(stats["query"], query)
        self.assertEqual(stats["top_k_first"], 10)
        self.assertEqual(stats["top_k_final"], 3)


class TestSearchService(unittest.TestCase):
    """SearchService 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.temp_dir = tempfile.mkdtemp()
        
        # 테스트용 검색 서비스 생성
        self.service = SearchService(
            index_name="test_search_service",
            index_directory=self.temp_dir,
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
            }
        ]
        
        self.service.vector_index.upsert_chunks(test_chunks)
    
    def tearDown(self):
        """테스트 정리"""
        self.service.close()
        shutil.rmtree(self.temp_dir)
    
    def test_search_basic(self):
        """기본 검색 테스트"""
        query = "채권추심 절차"
        
        results = self.service.search(query)
        
        # 검증
        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 3)  # top_k_final 제한
        
        for result in results:
            self.assertIn("text", result)
            self.assertIn("metadata", result)
            self.assertIn("search_rank", result)
            self.assertIn("final_score", result)
    
    def test_search_with_rerank_disabled(self):
        """리랭킹 비활성화 검색 테스트"""
        query = "채권추심 절차"
        
        results = self.service.search(query, use_rerank=False)
        
        # 검증
        self.assertIsInstance(results, list)
        
        for result in results:
            self.assertIn("text", result)
            self.assertIn("metadata", result)
            self.assertIn("search_rank", result)
            self.assertIn("vector_score", result)
            self.assertIn("final_score", result)
    
    def test_search_by_law_topic(self):
        """법률 주제별 검색 테스트"""
        query = "절차"
        
        results = self.service.search_by_law_topic(query, "채권추심")
        
        # 검증
        self.assertIsInstance(results, list)
        
        for result in results:
            self.assertEqual(result["metadata"]["law_topic"], "채권추심")
    
    def test_search_suggestions(self):
        """검색 제안 테스트"""
        query = "채권추심"
        
        suggestions = self.service.get_search_suggestions(query, limit=3)
        
        # 검증
        self.assertIsInstance(suggestions, list)
        self.assertLessEqual(len(suggestions), 3)
        self.assertTrue(all(isinstance(s, str) for s in suggestions))
    
    def test_search_stats(self):
        """검색 통계 테스트"""
        query = "채권추심 절차"
        
        stats = self.service.get_search_stats(query)
        
        # 검증
        self.assertIn("query", stats)
        self.assertIn("vector_search_count", stats)
        self.assertIn("reranked_count", stats)
        self.assertIn("index_stats", stats)
        self.assertIn("search_config", stats)
    
    def test_index_info(self):
        """인덱스 정보 테스트"""
        info = self.service.get_index_info()
        
        # 검증
        self.assertIn("index_name", info)
        self.assertIn("index_directory", info)
        self.assertIn("stats", info)
        self.assertIn("search_config", info)
        
        self.assertEqual(info["index_name"], "test_search_service")


class TestIntegration(unittest.TestCase):
    """통합 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """테스트 정리"""
        shutil.rmtree(self.temp_dir)
    
    def test_full_search_pipeline(self):
        """전체 검색 파이프라인 테스트"""
        # 검색 서비스 생성
        service = SearchService(
            index_name="test_pipeline",
            index_directory=self.temp_dir
        )
        
        try:
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
                }
            ]
            
            # 1단계: 데이터 인덱싱
            index_result = service.vector_index.upsert_chunks(test_chunks)
            self.assertGreaterEqual(index_result["added"], 0)
            
            # 2단계: 검색 실행
            search_results = service.search("채권추심 절차")
            self.assertIsInstance(search_results, list)
            
            # 3단계: 통계 확인
            stats = service.get_search_stats("채권추심 절차")
            self.assertIn("query", stats)
            
        finally:
            service.close()


if __name__ == '__main__':
    # 테스트 실행
    unittest.main(verbosity=2)
