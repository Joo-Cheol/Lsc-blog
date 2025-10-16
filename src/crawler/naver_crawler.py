#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 블로그 증분 크롤링
"""
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional, Generator
import logging
from .storage import SeenStorage, get_content_hash
from .extractors import extract_post_metadata, extract_post_content


logger = logging.getLogger(__name__)


class NaverBlogCrawler:
    """네이버 블로그 증분 크롤러"""
    
    def __init__(self, blog_id: str, category_no: int, seen_db_path: str, 
                 delay_min_ms: int = 600, delay_max_ms: int = 1400):
        self.blog_id = blog_id
        self.category_no = category_no
        self.storage = SeenStorage(seen_db_path)
        self.delay_min_ms = delay_min_ms
        self.delay_max_ms = delay_max_ms
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def _random_delay(self):
        """랜덤 딜레이"""
        delay_ms = random.randint(self.delay_min_ms, self.delay_max_ms)
        time.sleep(delay_ms / 1000.0)
    
    def _get_blog_list_url(self, page: int = 1) -> str:
        """블로그 목록 URL 생성"""
        return f"https://blog.naver.com/PostList.naver?blogId={self.blog_id}&categoryNo={self.category_no}&currentPage={page}"
    
    def _get_post_url(self, logno: str) -> str:
        """포스트 URL 생성"""
        return f"https://blog.naver.com/PostView.naver?blogId={self.blog_id}&logNo={logno}"
    
    def fetch_post_list(self, page: int = 1) -> List[Dict[str, str]]:
        """포스트 목록 조회"""
        url = self._get_blog_list_url(page)
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            posts = []
            
            # 네이버 블로그 목록 구조에 따라 파싱
            post_links = soup.find_all('a', href=True)
            
            for link in post_links:
                href = link.get('href')
                if href and 'logNo=' in href:
                    # logno 추출
                    logno = href.split('logNo=')[1].split('&')[0]
                    post_url = self._get_post_url(logno)
                    
                    # 제목 추출
                    title = link.get_text(strip=True)
                    
                    posts.append({
                        'logno': logno,
                        'url': post_url,
                        'title': title
                    })
            
            logger.info(f"페이지 {page}에서 {len(posts)}개 포스트 발견")
            return posts
            
        except Exception as e:
            logger.error(f"포스트 목록 조회 실패 (페이지 {page}): {e}")
            return []
    
    def fetch_post_content(self, url: str) -> Optional[Dict[str, str]]:
        """개별 포스트 내용 조회"""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 메타데이터 추출
            metadata = extract_post_metadata(soup, url)
            
            # 본문 내용 추출
            content = extract_post_content(soup)
            
            if not content:
                logger.warning(f"포스트 내용 추출 실패: {url}")
                return None
            
            return {
                'url': url,
                'content': content,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"포스트 내용 조회 실패 {url}: {e}")
            return None
    
    def crawl_incremental(self, max_pages: int = 5, run_id: str = None) -> Dict[str, int]:
        """증분 크롤링 실행"""
        if not run_id:
            run_id = f"crawl_{int(time.time())}"
        
        logger.info(f"[{run_id}] 증분 크롤링 시작 - 블로그: {self.blog_id}, 카테고리: {self.category_no}")
        
        stats = {
            'total_found': 0,
            'new_posts': 0,
            'duplicate_content': 0,
            'failed': 0,
            'pages_processed': 0
        }
        
        last_logno = self.storage.get_last_logno()
        logger.info(f"[{run_id}] 마지막 처리 logno: {last_logno}")
        
        for page in range(1, max_pages + 1):
            logger.info(f"[{run_id}] 페이지 {page} 처리 중...")
            
            posts = self.fetch_post_list(page)
            if not posts:
                logger.info(f"[{run_id}] 페이지 {page}에서 포스트 없음, 크롤링 종료")
                break
            
            stats['total_found'] += len(posts)
            stats['pages_processed'] = page
            
            # logno 기준으로 필터링 (증분 수집)
            if last_logno:
                posts = [p for p in posts if p['logno'] > last_logno]
                if not posts:
                    logger.info(f"[{run_id}] 페이지 {page}에서 새로운 포스트 없음")
                    continue
            
            for post in posts:
                self._random_delay()
                
                # 이미 수집된 URL인지 확인
                if not self.storage.is_new_post(post['url']):
                    logger.debug(f"[{run_id}] 이미 수집된 포스트 스킵: {post['url']}")
                    continue
                
                # 포스트 내용 조회
                post_data = self.fetch_post_content(post['url'])
                if not post_data:
                    stats['failed'] += 1
                    continue
                
                # 중복 내용 체크 및 저장
                content_hash = get_content_hash(post_data['content'])
                is_new_content = self.storage.add_post(
                    post['url'], 
                    post['logno'], 
                    post_data['content']
                )
                
                if is_new_content:
                    stats['new_posts'] += 1
                    logger.info(f"[{run_id}] 새 포스트 추가: {post['title'][:50]}...")
                else:
                    stats['duplicate_content'] += 1
                    logger.info(f"[{run_id}] 중복 내용 스킵: {post['title'][:50]}...")
            
            # 페이지 간 딜레이
            if page < max_pages:
                self._random_delay()
        
        # 마지막 logno 업데이트
        if stats['total_found'] > 0:
            latest_posts = self.fetch_post_list(1)
            if latest_posts:
                latest_logno = max(p['logno'] for p in latest_posts)
                self.storage.set_last_logno(latest_logno)
                logger.info(f"[{run_id}] 마지막 logno 업데이트: {latest_logno}")
        
        logger.info(f"[{run_id}] 크롤링 완료 - {stats}")
        return stats
    
    def get_crawl_stats(self) -> Dict:
        """크롤링 통계 조회"""
        return self.storage.get_stats()
    
    def close(self):
        """리소스 정리"""
        self.storage.close()


# 테스트용 함수
def test_crawler():
    """크롤러 기본 기능 테스트"""
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # 테스트용 크롤러 (실제 크롤링은 하지 않음)
        crawler = NaverBlogCrawler(
            blog_id="test_blog",
            category_no=6,
            seen_db_path=db_path
        )
        
        # URL 생성 테스트
        list_url = crawler._get_blog_list_url(1)
        assert "blog.naver.com" in list_url
        assert "test_blog" in list_url
        
        post_url = crawler._get_post_url("12345")
        assert "logNo=12345" in post_url
        
        print("✅ NaverBlogCrawler 기본 테스트 통과")
        
    finally:
        crawler.close()
        import os
        os.unlink(db_path)


if __name__ == "__main__":
    test_crawler()
