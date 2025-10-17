#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_blog_id 함수 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.crawler.extractors import parse_blog_id

def test_parse_blog_id():
    """parse_blog_id 함수 테스트"""
    test_urls = [
        "https://blog.naver.com/tjwlswlsdl",
        "https://m.blog.naver.com/tjwlswlsdl",
        "https://blog.naver.com/PostList.naver?blogId=tjwlswlsdl",
        "tjwlswlsdl"  # 직접 ID
    ]
    
    for url in test_urls:
        blog_id = parse_blog_id(url)
        print(f"URL: {url}")
        print(f"  → Blog ID: {blog_id}")
        print()

if __name__ == "__main__":
    test_parse_blog_id()

