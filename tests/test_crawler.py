#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
크롤러 단위 테스트
"""
import unittest
import tempfile
import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawler.storage import SeenStorage, get_content_hash
from src.crawler.extractors import extract_post_metadata, extract_post_content
from bs4 import BeautifulSoup


class TestSeenStorage(unittest.TestCase):
    """SeenStorage 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False)
        self.temp_file.close()
        self.storage = SeenStorage(self.temp_file.name)
    
    def tearDown(self):
        """테스트 정리"""
        self.storage.close()
        os.unlink(self.temp_file.name)
    
    def test_schema_initialization(self):
        """스키마 초기화 테스트"""
        # 테이블 존재 확인
        cursor = self.storage.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        self.assertIn('seen_posts', tables)
        self.assertIn('checkpoints', tables)
    
    def test_add_new_post(self):
        """새 포스트 추가 테스트"""
        url = "https://blog.naver.com/test/123"
        logno = "12345"
        content = "테스트 내용입니다."
        
        # 새 포스트 추가
        result = self.storage.add_post(url, logno, content)
        self.assertTrue(result)
        
        # 중복 체크
        self.assertFalse(self.storage.is_new_post(url))
        
        # 통계 확인
        stats = self.storage.get_stats()
        self.assertEqual(stats['total_posts'], 1)
        self.assertEqual(stats['unique_contents'], 1)
    
    def test_duplicate_content(self):
        """중복 내용 테스트"""
        url1 = "https://blog.naver.com/test/123"
        url2 = "https://blog.naver.com/test/456"
        logno1 = "12345"
        logno2 = "12346"
        content = "동일한 내용입니다."
        
        # 첫 번째 포스트 추가
        result1 = self.storage.add_post(url1, logno1, content)
        self.assertTrue(result1)
        
        # 동일한 내용의 두 번째 포스트 추가
        result2 = self.storage.add_post(url2, logno2, content)
        self.assertFalse(result2)  # 내용 중복으로 False
        
        # 통계 확인
        stats = self.storage.get_stats()
        self.assertEqual(stats['total_posts'], 2)
        self.assertEqual(stats['unique_contents'], 1)
        self.assertGreater(stats['duplicate_rate'], 0)
    
    def test_checkpoint_management(self):
        """체크포인트 관리 테스트"""
        # 체크포인트 설정
        self.storage.set_last_logno("12345")
        
        # 체크포인트 조회
        last_logno = self.storage.get_last_logno()
        self.assertEqual(last_logno, "12345")
        
        # 체크포인트 업데이트
        self.storage.set_last_logno("67890")
        last_logno = self.storage.get_last_logno()
        self.assertEqual(last_logno, "67890")
    
    def test_content_hash(self):
        """내용 해시 테스트"""
        content1 = "테스트 내용"
        content2 = "테스트 내용"
        content3 = "다른 내용"
        
        hash1 = get_content_hash(content1)
        hash2 = get_content_hash(content2)
        hash3 = get_content_hash(content3)
        
        # 동일한 내용은 동일한 해시
        self.assertEqual(hash1, hash2)
        
        # 다른 내용은 다른 해시
        self.assertNotEqual(hash1, hash3)
        
        # 해시 길이 확인 (SHA-256 = 64자)
        self.assertEqual(len(hash1), 64)


class TestExtractors(unittest.TestCase):
    """Extractor 테스트"""
    
    def test_metadata_extraction(self):
        """메타데이터 추출 테스트"""
        html = """
        <html>
        <head><title>테스트 포스트</title></head>
        <body>
            <h3 class="se-title-text">채권추심 절차 가이드</h3>
            <span class="nick">법무법인혜안</span>
            <span class="se_publishDate">2024.1.15</span>
            <span class="category">채권추심</span>
            <a class="tag">법률</a>
            <a class="tag">채권</a>
        </body>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        metadata = extract_post_metadata(soup, "https://test.com")
        
        self.assertEqual(metadata['title'], "채권추심 절차 가이드")
        self.assertEqual(metadata['author'], "법무법인혜안")
        self.assertIn("2024-01-15", metadata['published_at'])
        self.assertEqual(metadata['category'], "채권추심")
        self.assertIn("법률", metadata['tags'])
        self.assertIn("채권", metadata['tags'])
    
    def test_content_extraction(self):
        """본문 추출 테스트"""
        html = """
        <html>
        <body>
            <div class="se-main-container">
                <p>채권추심은 다음과 같은 절차로 진행됩니다.</p>
                <ul>
                    <li>1단계: 내용증명 발송</li>
                    <li>2단계: 지급명령 신청</li>
                    <li>3단계: 강제집행</li>
                </ul>
                <p>각 단계별로 필요한 서류가 다릅니다.</p>
                <table>
                    <tr><th>단계</th><th>소요기간</th></tr>
                    <tr><td>내용증명</td><td>1-2주</td></tr>
                    <tr><td>지급명령</td><td>2-4주</td></tr>
                </table>
            </div>
        </body>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        content = extract_post_content(soup)
        
        self.assertIsNotNone(content)
        self.assertIn("채권추심은 다음과 같은 절차로 진행됩니다", content)
        self.assertIn("• 1단계: 내용증명 발송", content)
        self.assertIn("• 2단계: 지급명령 신청", content)
        self.assertIn("• 3단계: 강제집행", content)
        self.assertIn("단계 | 소요기간", content)
        self.assertIn("내용증명 | 1-2주", content)
    
    def test_content_extraction_with_unwanted_elements(self):
        """불필요한 요소 제거 테스트"""
        html = """
        <html>
        <body>
            <div class="se-main-container">
                <p>유용한 내용입니다.</p>
                <div class="ad">광고 내용</div>
                <div class="comment">댓글 영역</div>
                <script>alert('test');</script>
                <p>또 다른 유용한 내용입니다.</p>
            </div>
        </body>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        content = extract_post_content(soup)
        
        self.assertIsNotNone(content)
        self.assertIn("유용한 내용입니다", content)
        self.assertIn("또 다른 유용한 내용입니다", content)
        self.assertNotIn("광고 내용", content)
        self.assertNotIn("댓글 영역", content)
        self.assertNotIn("alert", content)


class TestIntegration(unittest.TestCase):
    """통합 테스트"""
    
    def test_crawler_storage_integration(self):
        """크롤러-저장소 통합 테스트"""
        temp_file = tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False)
        temp_file.close()
        
        try:
            storage = SeenStorage(temp_file.name)
            
            # 시뮬레이션: 여러 포스트 크롤링
            posts = [
                ("https://blog.naver.com/test/1", "1001", "첫 번째 포스트 내용"),
                ("https://blog.naver.com/test/2", "1002", "두 번째 포스트 내용"),
                ("https://blog.naver.com/test/3", "1003", "첫 번째 포스트 내용"),  # 중복 내용
            ]
            
            new_count = 0
            duplicate_count = 0
            
            for url, logno, content in posts:
                is_new = storage.add_post(url, logno, content)
                if is_new:
                    new_count += 1
                else:
                    duplicate_count += 1
            
            # 결과 검증
            self.assertEqual(new_count, 2)  # 고유한 내용 2개
            self.assertEqual(duplicate_count, 1)  # 중복 내용 1개
            
            stats = storage.get_stats()
            self.assertEqual(stats['total_posts'], 3)
            self.assertEqual(stats['unique_contents'], 2)
            
        finally:
            storage.close()
            os.unlink(temp_file.name)


if __name__ == '__main__':
    # 테스트 실행
    unittest.main(verbosity=2)
