#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 블로그 포스트 메타데이터 및 내용 추출
"""
import re
from datetime import datetime
from typing import Dict, Optional
from bs4 import BeautifulSoup


def extract_post_metadata(soup: BeautifulSoup, url: str) -> Dict[str, str]:
    """포스트 메타데이터 추출"""
    metadata = {
        'url': url,
        'title': '',
        'author': '',
        'published_at': '',
        'category': '',
        'tags': []
    }
    
    try:
        # 제목 추출
        title_elem = soup.find('h3', class_='se-title-text') or soup.find('h1', class_='se-title-text')
        if title_elem:
            metadata['title'] = title_elem.get_text(strip=True)
        
        # 작성자 추출
        author_elem = soup.find('span', class_='nick') or soup.find('a', class_='nick')
        if author_elem:
            metadata['author'] = author_elem.get_text(strip=True)
        
        # 발행일 추출
        date_elem = soup.find('span', class_='se_publishDate') or soup.find('span', class_='date')
        if date_elem:
            date_text = date_elem.get_text(strip=True)
            metadata['published_at'] = _parse_date(date_text)
        
        # 카테고리 추출
        category_elem = soup.find('span', class_='category') or soup.find('a', class_='category')
        if category_elem:
            metadata['category'] = category_elem.get_text(strip=True)
        
        # 태그 추출
        tag_elems = soup.find_all('a', class_='tag')
        metadata['tags'] = [tag.get_text(strip=True) for tag in tag_elems]
        
    except Exception as e:
        print(f"메타데이터 추출 오류: {e}")
    
    return metadata


def extract_post_content(soup: BeautifulSoup) -> Optional[str]:
    """포스트 본문 내용 추출"""
    try:
        # 네이버 블로그 본문 영역 찾기
        content_selectors = [
            'div.se-main-container',  # 스마트에디터
            'div.post-view',          # 일반 에디터
            'div#postViewArea',       # 구버전
            'div.post-content'        # 대체 선택자
        ]
        
        content_elem = None
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                break
        
        if not content_elem:
            # 폴백: 전체 본문 영역에서 텍스트 추출
            content_elem = soup.find('div', {'id': 'postViewArea'}) or soup.find('div', class_='post-view')
        
        if not content_elem:
            return None
        
        # 불필요한 요소 제거
        _remove_unwanted_elements(content_elem)
        
        # 텍스트 추출 및 정제
        content = _extract_clean_text(content_elem)
        
        return content if content.strip() else None
        
    except Exception as e:
        print(f"본문 추출 오류: {e}")
        return None


def _remove_unwanted_elements(soup: BeautifulSoup):
    """불필요한 요소 제거"""
    unwanted_selectors = [
        'script', 'style', 'noscript',
        '.ad', '.advertisement', '.ads',
        '.comment', '.reply', '.comment-area',
        '.social-share', '.share-buttons',
        '.related-posts', '.recommend',
        '.copyright', '.disclaimer'
    ]
    
    for selector in unwanted_selectors:
        for elem in soup.select(selector):
            elem.decompose()


def _extract_clean_text(elem) -> str:
    """깔끔한 텍스트 추출"""
    if not elem:
        return ""
    
    # 리스트와 표는 구조 보존
    for list_elem in elem.find_all(['ul', 'ol']):
        list_text = []
        for li in list_elem.find_all('li'):
            list_text.append(f"• {li.get_text(strip=True)}")
        list_elem.replace_with('\n'.join(list_text))
    
    for table_elem in elem.find_all('table'):
        table_text = []
        for row in table_elem.find_all('tr'):
            row_text = []
            for cell in row.find_all(['td', 'th']):
                row_text.append(cell.get_text(strip=True))
            table_text.append(' | '.join(row_text))
        table_elem.replace_with('\n'.join(table_text))
    
    # 텍스트 추출
    text = elem.get_text(separator='\n', strip=True)
    
    # 텍스트 정제
    text = _normalize_text(text)
    
    return text


def _normalize_text(text: str) -> str:
    """텍스트 정규화"""
    # 여러 개의 개행을 하나로 축약
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    # 불필요한 공백 제거
    text = re.sub(r'[ \t]+', ' ', text)
    
    # 줄 시작/끝 공백 제거
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # 빈 줄 정리
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    return text.strip()


def _parse_date(date_text: str) -> str:
    """날짜 문자열 파싱"""
    if not date_text:
        return ""
    
    # 다양한 날짜 형식 처리
    date_patterns = [
        r'(\d{4})\.(\d{1,2})\.(\d{1,2})',  # 2024.1.15
        r'(\d{4})-(\d{1,2})-(\d{1,2})',    # 2024-01-15
        r'(\d{4})/(\d{1,2})/(\d{1,2})',    # 2024/01/15
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, date_text)
        if match:
            year, month, day = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    return date_text


# 테스트용 함수
def test_extractors():
    """추출기 기능 테스트"""
    html_sample = """
    <html>
    <head><title>테스트 포스트</title></head>
    <body>
        <h3 class="se-title-text">채권추심 절차 가이드</h3>
        <span class="nick">법무법인혜안</span>
        <span class="se_publishDate">2024.1.15</span>
        <div class="se-main-container">
            <p>채권추심은 다음과 같은 절차로 진행됩니다.</p>
            <ul>
                <li>1단계: 내용증명 발송</li>
                <li>2단계: 지급명령 신청</li>
                <li>3단계: 강제집행</li>
            </ul>
            <p>각 단계별로 필요한 서류가 다릅니다.</p>
        </div>
    </body>
    </html>
    """
    
    soup = BeautifulSoup(html_sample, 'html.parser')
    
    # 메타데이터 추출 테스트
    metadata = extract_post_metadata(soup, "https://test.com")
    assert metadata['title'] == "채권추심 절차 가이드"
    assert metadata['author'] == "법무법인혜안"
    assert "2024-01-15" in metadata['published_at']
    
    # 본문 추출 테스트
    content = extract_post_content(soup)
    assert "채권추심은 다음과 같은 절차로 진행됩니다" in content
    assert "• 1단계: 내용증명 발송" in content
    assert "• 2단계: 지급명령 신청" in content
    
    print("✅ Extractor 테스트 통과")


if __name__ == "__main__":
    test_extractors()
