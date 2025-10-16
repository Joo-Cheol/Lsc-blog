#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전처리 모듈 단위 테스트
"""
import unittest
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.preprocess.normalize import TextNormalizer, normalize_text
from src.preprocess.chunking import SemanticChunker, Chunk, chunk_text


class TestTextNormalizer(unittest.TestCase):
    """TextNormalizer 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.normalizer = TextNormalizer()
    
    def test_html_normalization(self):
        """HTML 정규화 테스트"""
        html_content = """
        <html>
        <body>
            <h2>채권추심 절차</h2>
            <p>채권추심은 다음과 같은 절차로 진행됩니다.</p>
            <ul>
                <li>1단계: 내용증명 발송 (비용: 5000원)</li>
                <li>2단계: 지급명령 신청 (비용: 10000원)</li>
            </ul>
            <div class="ad">광고 내용</div>
            <p>법무법인 서울에서 전문적으로 처리합니다.</p>
        </body>
        </html>
        """
        
        result = self.normalizer.normalize_html(html_content)
        
        # 검증
        self.assertIn("## 채권추심 절차", result)
        self.assertIn("• 1단계: 내용증명 발송", result)
        self.assertIn("5,000원", result)
        self.assertIn("10,000원", result)
        self.assertNotIn("광고 내용", result)
        self.assertIn("법무법인 혜안", result)  # 정규화됨
    
    def test_text_normalization(self):
        """텍스트 정규화 테스트"""
        text = """
        채권추심은   다음과    같은 절차로 진행됩니다.
        
        
        각 단계별로 필요한 서류가 다릅니다.
        """
        
        result = self.normalizer._normalize_text(text)
        
        # 검증
        self.assertNotIn("   ", result)  # 여러 공백 제거
        self.assertNotIn("\n\n\n", result)  # 여러 개행 제거
        self.assertIn("채권추심은 다음과 같은 절차로 진행됩니다", result)
    
    def test_law_keyword_extraction(self):
        """법률 키워드 추출 테스트"""
        text = "채권추심 절차에서 지급명령을 신청하고 강제집행을 진행합니다."
        
        keywords = self.normalizer.extract_law_keywords(text)
        
        # 검증
        self.assertIn("채권추심", keywords)
        self.assertIn("지급명령", keywords)
        self.assertIn("강제집행", keywords)
        self.assertGreaterEqual(len(keywords), 3)  # 최소 3개 이상
    
    def test_law_related_detection(self):
        """법률 관련 텍스트 판단 테스트"""
        law_text = "채권추심 절차에서 지급명령을 신청합니다."
        non_law_text = "오늘 날씨가 좋습니다."
        
        # 검증
        self.assertTrue(self.normalizer.is_law_related(law_text))
        self.assertFalse(self.normalizer.is_law_related(non_law_text))
    
    def test_remove_patterns(self):
        """불필요한 패턴 제거 테스트"""
        text = """
        채권추심 절차입니다.
        본문과 관련된 광고입니다.
        ※ 주석 내용 ※
        [대괄호 내용]
        출처: 네이버 블로그
        """
        
        result = self.normalizer._normalize_text(text)
        
        # 검증
        self.assertIn("채권추심 절차입니다", result)
        self.assertNotIn("광고", result)
        self.assertNotIn("주석", result)
        self.assertNotIn("대괄호", result)
        self.assertNotIn("출처", result)
    
    def test_sentence_normalization(self):
        """문장 정규화 테스트"""
        text = "첫 번째 문장입니다! 두 번째 문장입니다? 세 번째 문장입니다."
        
        result = self.normalizer._normalize_sentences(text)
        
        # 검증 (문장 끝이 정규화되었는지 확인)
        self.assertIn("첫 번째 문장입니다", result)
        self.assertIn("두 번째 문장입니다", result)
        self.assertIn("세 번째 문장입니다", result)
        self.assertIn("\n", result)  # 줄바꿈이 있는지 확인


class TestSemanticChunker(unittest.TestCase):
    """SemanticChunker 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.chunker = SemanticChunker(max_tokens=100, overlap_tokens=20)
    
    def test_chunk_creation(self):
        """청크 생성 테스트"""
        text = """
        # 채권추심 절차 가이드
        
        채권추심은 다음과 같은 절차로 진행됩니다.
        
        ## 1단계: 내용증명 발송
        내용증명은 채무자에게 채권의 존재를 알리는 공식적인 방법입니다.
        비용은 약 5,000원이며, 1-2주 정도 소요됩니다.
        
        ## 2단계: 지급명령 신청
        지급명령은 법원에 신청하는 간이한 소송 절차입니다.
        비용은 약 10,000원이며, 2-4주 정도 소요됩니다.
        """
        
        metadata = {
            'source_url': 'https://test.com',
            'logno': '12345',
            'published_at': '2024-01-15',
            'title': '채권추심 절차 가이드'
        }
        
        chunks = self.chunker.chunk_text(text, metadata)
        
        # 검증
        self.assertGreater(len(chunks), 0)
        self.assertTrue(all(isinstance(chunk, Chunk) for chunk in chunks))
        self.assertTrue(all(chunk.metadata['law_topic'] == '채권추심' for chunk in chunks))
        
        # 각 청크의 토큰 수 검증
        for chunk in chunks:
            tokens = self.chunker._estimate_tokens(chunk.text)
            self.assertLessEqual(tokens, self.chunker.max_tokens * 1.2)  # 약간의 여유
    
    def test_token_estimation(self):
        """토큰 수 추정 테스트"""
        text1 = "짧은 텍스트"
        text2 = "이것은 좀 더 긴 텍스트입니다. 여러 문장으로 구성되어 있습니다."
        
        tokens1 = self.chunker._estimate_tokens(text1)
        tokens2 = self.chunker._estimate_tokens(text2)
        
        # 검증
        self.assertGreater(tokens1, 0)
        self.assertGreater(tokens2, tokens1)
        self.assertLessEqual(tokens1, 10)
        self.assertLessEqual(tokens2, 30)
    
    def test_paragraph_splitting(self):
        """문단 분할 테스트"""
        text = """
        첫 번째 문단입니다.
        
        두 번째 문단입니다.
        
        세 번째 문단입니다.
        """
        
        paragraphs = self.chunker._split_paragraphs(text)
        
        # 검증
        self.assertEqual(len(paragraphs), 3)
        self.assertIn("첫 번째 문단", paragraphs[0])
        self.assertIn("두 번째 문단", paragraphs[1])
        self.assertIn("세 번째 문단", paragraphs[2])
    
    def test_sentence_splitting(self):
        """문장 분할 테스트"""
        text = "첫 번째 문장입니다. 두 번째 문장입니다! 세 번째 문장입니다?"
        
        sentences = self.chunker._split_sentences(text)
        
        # 검증
        self.assertEqual(len(sentences), 3)
        self.assertIn("첫 번째 문장", sentences[0])
        self.assertIn("두 번째 문장", sentences[1])
        self.assertIn("세 번째 문장", sentences[2])
    
    def test_chunk_metadata(self):
        """청크 메타데이터 테스트"""
        text = "채권추심 절차에 대한 설명입니다."
        metadata = {
            'source_url': 'https://test.com',
            'logno': '12345',
            'title': '테스트 제목'
        }
        
        chunks = self.chunker.chunk_text(text, metadata)
        
        # 검증
        self.assertGreater(len(chunks), 0)
        chunk = chunks[0]
        
        self.assertEqual(chunk.metadata['source_url'], 'https://test.com')
        self.assertEqual(chunk.metadata['logno'], '12345')
        self.assertEqual(chunk.metadata['title'], '테스트 제목')
        self.assertEqual(chunk.metadata['law_topic'], '채권추심')
        self.assertIn('chunk_id', chunk.metadata)
        self.assertIn('token_count', chunk.metadata)
        self.assertIn('char_count', chunk.metadata)
    
    def test_chunk_stats(self):
        """청크 통계 테스트"""
        text = "첫 번째 청크입니다. 두 번째 청크입니다. 세 번째 청크입니다."
        metadata = {'source_url': 'https://test.com'}
        
        chunks = self.chunker.chunk_text(text, metadata)
        stats = self.chunker.get_chunk_stats(chunks)
        
        # 검증
        self.assertIn('total_chunks', stats)
        self.assertIn('avg_tokens', stats)
        self.assertIn('avg_chars', stats)
        self.assertIn('total_tokens', stats)
        self.assertIn('total_chars', stats)
        
        self.assertEqual(stats['total_chunks'], len(chunks))
        self.assertGreater(stats['total_tokens'], 0)
        self.assertGreater(stats['total_chars'], 0)


class TestIntegration(unittest.TestCase):
    """통합 테스트"""
    
    def test_normalize_and_chunk_pipeline(self):
        """정규화 + 청킹 파이프라인 테스트"""
        html_content = """
        <html>
        <body>
            <h2>채권추심 절차</h2>
            <p>채권추심은 다음과 같은 절차로 진행됩니다.</p>
            <ul>
                <li>1단계: 내용증명 발송</li>
                <li>2단계: 지급명령 신청</li>
                <li>3단계: 강제집행</li>
            </ul>
            <div class="ad">광고</div>
            <p>각 단계별로 필요한 서류가 다릅니다.</p>
        </body>
        </html>
        """
        
        metadata = {
            'source_url': 'https://test.com',
            'logno': '12345',
            'title': '채권추심 절차'
        }
        
        # 1단계: 정규화
        normalizer = TextNormalizer()
        normalized_text = normalizer.normalize_html(html_content)
        
        # 2단계: 청킹
        chunker = SemanticChunker(max_tokens=50, overlap_tokens=10)
        chunks = chunker.chunk_text(normalized_text, metadata)
        
        # 검증
        self.assertGreater(len(chunks), 0)
        self.assertIn("## 채권추심 절차", normalized_text)
        self.assertNotIn("광고", normalized_text)
        
        # 모든 청크에 법률 키워드가 있는지 확인
        for chunk in chunks:
            keywords = normalizer.extract_law_keywords(chunk.text)
            self.assertGreater(len(keywords), 0)
    
    def test_convenience_functions(self):
        """편의 함수 테스트"""
        text = "채권추심 절차에 대한 설명입니다."
        metadata = {'source_url': 'https://test.com'}
        
        # normalize_text 함수 테스트
        normalized = normalize_text(text)
        self.assertIsInstance(normalized, str)
        self.assertIn("채권추심", normalized)
        
        # chunk_text 함수 테스트
        chunks = chunk_text(text, metadata, max_tokens=50)
        self.assertGreater(len(chunks), 0)
        self.assertTrue(all(isinstance(chunk, Chunk) for chunk in chunks))


if __name__ == '__main__':
    # 테스트 실행
    unittest.main(verbosity=2)
