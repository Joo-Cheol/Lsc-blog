#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
크롤러 간단 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.crawler.naver_crawler import NaverBlogCrawler

def test_crawler():
    """크롤러 테스트"""
    blog_id = "tjwlswlsdl"  # 테스트할 블로그 ID
    
    print(f"블로그 ID: {blog_id}")
    
    # 크롤러 초기화
    crawler = NaverBlogCrawler(blog_id=blog_id)
    
    # 카테고리 조회 테스트
    print("카테고리 조회 중...")
    categories = crawler.fetch_categories()
    print(f"발견된 카테고리: {categories}")
    
    # 첫 번째 페이지 포스트 목록 조회 테스트
    print("포스트 목록 조회 중...")
    posts = crawler.fetch_post_list(page=1, category_no=0)
    print(f"발견된 포스트 수: {len(posts)}")
    
    if posts:
        print("첫 번째 포스트:")
        print(f"  제목: {posts[0]['title']}")
        print(f"  URL: {posts[0]['url']}")
        print(f"  logno: {posts[0]['logno']}")
    else:
        print("포스트를 찾을 수 없습니다.")
        
        # URL 직접 확인
        test_url = crawler._get_blog_list_url(1, 0)
        print(f"테스트 URL: {test_url}")
        
        try:
            response = crawler.session.get(test_url, timeout=10)
            print(f"응답 상태: {response.status_code}")
            print(f"응답 크기: {len(response.content)} bytes")
            
            if response.status_code == 200:
                print("HTML 응답 받음 - 파싱 문제일 수 있음")
            else:
                print(f"HTTP 오류: {response.status_code}")
        except Exception as e:
            print(f"요청 실패: {e}")

if __name__ == "__main__":
    test_crawler()

