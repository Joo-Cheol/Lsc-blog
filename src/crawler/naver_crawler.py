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
from .storage import SeenStorage
from .extractors import extract_post_metadata, extract_post_content


logger = logging.getLogger(__name__)


class NaverBlogCrawler:
    """네이버 블로그 증분 크롤러"""
    
    def __init__(self, blog_id: str, category_no: int = None, seen_db_path: str = None, 
                 delay_min_ms: int = 600, delay_max_ms: int = 1400):
        self.blog_id = blog_id
        self.category_no = category_no
        self.storage = SeenStorage(seen_db_path) if seen_db_path else SeenStorage()
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
    
    def _get_blog_list_url(self, page: int = 1, category_no: int = None) -> str:
        """블로그 목록 URL 생성"""
        cat_no = category_no if category_no is not None else self.category_no
        return (
            f"https://blog.naver.com/PostList.naver?"
            f"blogId={self.blog_id}&categoryNo={cat_no}&currentPage={page}"
        )
    
    def _get_post_url(self, logno: str) -> str:
        """포스트 URL 생성"""
        return f"https://blog.naver.com/PostView.naver?blogId={self.blog_id}&logNo={logno}"
    
    def fetch_categories(self) -> List[int]:
        """카테고리 목록 조회 (실패 시 [None] 반환)"""
        try:
            # 네이버 블로그 카테고리 API 시도
            url = f"https://blog.naver.com/PostList.naver?blogId={self.blog_id}"
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            # 카테고리 링크에서 categoryNo 추출 시도
            category_links = soup.find_all('a', href=lambda x: x and 'categoryNo=' in x)
            categories = []
            
            for link in category_links:
                href = link.get('href', '')
                if 'categoryNo=' in href:
                    try:
                        cat_no = int(href.split('categoryNo=')[1].split('&')[0])
                        if cat_no not in categories:
                            categories.append(cat_no)
                    except (ValueError, IndexError):
                        continue
            
            if categories:
                logger.info(f"발견된 카테고리: {categories}")
                return categories
            else:
                logger.warning("카테고리를 찾을 수 없음, 전체(0)로 폴백")
                return [0]  # 전체 카테고리
                
        except Exception as e:
            logger.warning(f"카테고리 조회 실패: {e}, 전체(0)로 폴백")
            return [0]  # 전체 카테고리

    def fetch_post_list(self, page: int = 1, category_no: int = None) -> List[Dict[str, str]]:
        """포스트 목록 조회"""
        url = self._get_blog_list_url(page, category_no)
        
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
    
    def crawl_incremental(self, max_pages: int = 5, run_id: str = None, 
                         on_page: callable = None, on_new: callable = None, on_skip: callable = None, 
                         on_event: callable = None) -> Dict[str, int]:
        """증분 크롤링 실행"""
        if not run_id:
            run_id = f"crawl_{int(time.time())}"
        
        # 카테고리 자동화: category_no가 None이면 전체 카테고리 순회
        categories = [self.category_no] if self.category_no is not None else self.fetch_categories()
        logger.info(f"[{run_id}] 증분 크롤링 시작 - 블로그: {self.blog_id}, 카테고리: {categories}")
        
        # 시작 이벤트
        if on_event:
            on_event("crawl_started", {
                "blog_id": self.blog_id,
                "categories": categories,
                "max_pages": max_pages,
                "run_id": run_id
            })
        
        total_stats = {
            'total_found': 0,
            'new_posts': 0,
            'duplicate_content': 0,
            'failed': 0,
            'pages_processed': 0,
            'collected_posts': [],  # 수집된 글 목록 추가
            'categories_processed': 0,
            'start_time': time.time(),
            'request_errors': 0,
            'retry_count': 0
        }
        
        # 각 카테고리별로 크롤링
        for category_no in categories:
            logger.info(f"[{run_id}] 카테고리 {category_no} 크롤링 시작...")
            
            # 카테고리 시작 이벤트
            if on_event:
                on_event("category_started", {
                    "category_no": category_no,
                    "total_categories": len(categories)
                })
            
            stats = {
                'total_found': 0,
                'new_posts': 0,
                'duplicate_content': 0,
                'failed': 0,
                'pages_processed': 0,
                'collected_posts': [],  # 수집된 글 목록 추가
                'categories_processed': 1,  # 현재 카테고리 처리됨
                'category_start_time': time.time()
            }
            
            last_logno = self.storage.get_last_logno()
            logger.info(f"[{run_id}] 마지막 처리 logno: {last_logno}")
            
            for page in range(1, max_pages + 1):
                logger.info(f"[{run_id}] 카테고리 {category_no}, 페이지 {page} 처리 중...")
                
                # 페이지 콜백 호출
                if on_page:
                    on_page(category_no, page)
                
                posts = self.fetch_post_list(page, category_no)
                if not posts:
                    logger.info(f"[{run_id}] 카테고리 {category_no}, 페이지 {page}에서 포스트 없음")
                    # 페이지 완료 이벤트
                    if on_event:
                        on_event("page_completed", {
                            "category_no": category_no,
                            "page": page,
                            "posts_found": 0,
                            "status": "empty"
                        })
                    break
            
                stats['total_found'] += len(posts)
                stats['pages_processed'] = page
                logger.info(f"[{run_id}] 페이지 {page} 통계 업데이트 - posts: {len(posts)}, total_found: {stats['total_found']}, pages_processed: {stats['pages_processed']}")
                
                # 페이지 완료 이벤트
                if on_event:
                    on_event("page_completed", {
                        "category_no": category_no,
                        "page": page,
                        "posts_found": len(posts),
                        "status": "success"
                    })
                
                # logno 기준으로 필터링 (증분 수집) - 안전한 타입 비교
                if last_logno:
                    last_logno_int = int(last_logno)
                    posts = [p for p in posts if int(p.get('logno', 0)) > last_logno_int]
                    if not posts:
                        logger.info(f"[{run_id}] 카테고리 {category_no}, 페이지 {page}에서 새로운 포스트 없음")
                        continue
                
                for post in posts:
                    self._random_delay()
                    
                    # 이미 본 URL은 스킵 (이전 이름 is_new_post → 실제 구현에 맞게)
                    if self.storage.is_post_seen(post['url']):
                        logger.debug(f"[{run_id}] 이미 수집된 포스트 스킵: {post['url']}")
                        continue
                    
                    # 포스트 내용 조회
                    post_data = self.fetch_post_content(post['url'])
                    if not post_data:
                        stats['failed'] += 1
                        continue
                    
                    # 중복 콘텐츠 판단 및 저장 (add_seen_post가 'new/updated/unchanged' 반환)
                    status = self.storage.add_seen_post(
                        post['url'], 
                        int(post['logno']), 
                        post_data['content'], 
                        title=post['title']
                    )
                    
                    if status == "new":
                        stats['new_posts'] += 1
                        post_info = {
                            'title': post['title'],
                            'url': post['url'],
                            'logno': post['logno'],
                            'status': 'new'
                        }
                        stats['collected_posts'].append(post_info)
                        if on_new:
                            on_new(post_info)
                        logger.info(f"[{run_id}] 새 포스트 추가: {post['title'][:50]}...")
                    elif status == "unchanged":
                        stats['duplicate_content'] += 1
                        post_info = {
                            'title': post['title'],
                            'url': post['url'],
                            'logno': post['logno'],
                            'status': 'duplicate'
                        }
                        stats['collected_posts'].append(post_info)
                        if on_skip:
                            on_skip(post_info)
                        logger.info(f"[{run_id}] 중복 내용 스킵: {post['title'][:50]}...")
                    else:
                        # updated
                        stats['new_posts'] += 1
                        post_info = {
                            'title': post['title'],
                            'url': post['url'],
                            'logno': post['logno'],
                            'status': 'updated'
                        }
                        stats['collected_posts'].append(post_info)
                        if on_new:
                            on_new(post_info)
                        logger.info(f"[{run_id}] 포스트 업데이트: {post['title'][:50]}...")
                
                # 페이지 간 딜레이
                if page < max_pages:
                    self._random_delay()
            
            # 카테고리별 통계 누적
            logger.info(f"[{run_id}] 카테고리 {category_no} 통계 누적 전 - total_stats: {total_stats}")
            logger.info(f"[{run_id}] 카테고리 {category_no} 통계 누적 전 - stats: {stats}")
            
            for key in total_stats:
                if key in stats:
                    if key == 'collected_posts':
                        total_stats[key].extend(stats[key])
                    else:
                        total_stats[key] += stats[key]
            
            logger.info(f"[{run_id}] 카테고리 {category_no} 통계 누적 후 - total_stats: {total_stats}")
            logger.info(f"[{run_id}] 카테고리 {category_no} 완료 - {stats}")
        
        # 마지막 logno 갱신 (set_last_logno → update_checkpoint)
        if total_stats['total_found'] > 0:
            latest_posts = self.fetch_post_list(1)
            if latest_posts:
                latest_logno = max(int(p['logno']) for p in latest_posts)
                self.storage.update_checkpoint(latest_logno, {
                    'total': total_stats['total_found'],
                    'new': total_stats['new_posts'],
                    'updated': total_stats['duplicate_content'],
                })
                logger.info(f"[{run_id}] 마지막 logno 업데이트: {latest_logno}")
        
        logger.info(f"[{run_id}] 전체 크롤링 완료 - {total_stats}")
        return total_stats
    
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
