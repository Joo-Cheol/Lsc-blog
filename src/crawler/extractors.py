"""
크롤러 유틸리티 함수들
"""
import re
from urllib.parse import urlparse, parse_qs
from typing import Optional


def parse_blog_id(blog_url: str) -> str:
    """
    네이버 블로그 URL 다양한 형태에서 blog_id를 추출
    예) https://blog.naver.com/tjwlswlsdl → tjwlswlsdl
        https://m.blog.naver.com/PostList.naver?blogId=tjwlswlsdl → tjwlswlsdl
        https://m.blog.naver.com/tjwlswlsdl → tjwlswlsdl
    """
    u = urlparse(blog_url)
    if u.netloc.endswith("blog.naver.com") or u.netloc.endswith("m.blog.naver.com"):
        # 1) path 기반
        path_bits = [p for p in u.path.split("/") if p]
        if path_bits:
            # /<blogId> 또는 /PostList.naver
            if path_bits[0].lower() not in ("postlist.naver", "postview.naver"):
                return path_bits[0]
        # 2) query 기반
        q = parse_qs(u.query)
        if "blogId" in q and q["blogId"]:
            return q["blogId"][0]
    # 마지막 fallback: 그냥 전달값(기존처럼 ID가 들어온 경우)
    return blog_url.strip()


def extract_post_metadata(soup, logno: str) -> dict:
    """포스트 메타데이터 추출"""
    # 기본 메타데이터 추출 로직
    title = soup.find("title")
    title_text = title.get_text().strip() if title else f"Post {logno}"
    
    return {
        "logno": logno,
        "title": title_text,
        "url": f"https://blog.naver.com/PostView.naver?logNo={logno}",
        "published_at": None,  # 실제 구현에서 추출
        "content_hash": None   # 실제 구현에서 계산
    }


def extract_post_content(soup) -> str:
    """포스트 본문 내용 추출"""
    # 본문 추출 로직
    content_div = soup.find("div", class_="se-main-container")
    if content_div:
        return content_div.get_text().strip()
    
    # 대안 추출 방법
    content_div = soup.find("div", id="postViewArea")
    if content_div:
        return content_div.get_text().strip()
    
    return ""