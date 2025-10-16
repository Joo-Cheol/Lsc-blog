#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
텍스트 정제 및 정규화
"""
import re
import html
from typing import Optional, List
from bs4 import BeautifulSoup


class TextNormalizer:
    """텍스트 정제 및 정규화 클래스"""
    
    def __init__(self):
        # 법률 관련 키워드 패턴
        self.law_keywords = [
            '채권추심', '지급명령', '강제집행', '소액사건', '내용증명',
            '채무', '채권', '미수금', '손해배상', '계약', '위약금',
            '법원', '법무법인', '변호사', '법률', '소송', '재판'
        ]
        
        # 제거할 패턴들
        self.remove_patterns = [
            r'본문과 관련된 광고.*?$',  # 광고 문구
            r'※.*?※',  # 주석 블록
            r'\[.*?\]',  # 대괄호 내용
            r'출처:.*?$',  # 출처 문구
            r'저작권.*?$',  # 저작권 문구
            r'무단전재.*?$',  # 무단전재 문구
        ]
        
        # 정규화할 패턴들
        self.normalize_patterns = [
            (r'법무법인\s*[가-힣]+', '법무법인 혜안'),  # 법무법인명 통일
            (r'[가-힣]+\s*변호사', '변호사'),  # 변호사 호칭 통일
        ]
    
    def normalize_html(self, html_content: str) -> str:
        """HTML을 정제된 텍스트로 변환"""
        if not html_content:
            return ""
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 불필요한 요소 제거
            self._remove_unwanted_elements(soup)
            
            # 텍스트 추출
            text = self._extract_clean_text(soup)
            
            # 텍스트 정규화
            text = self._normalize_text(text)
            
            return text
            
        except Exception as e:
            print(f"HTML 정규화 오류: {e}")
            return html_content
    
    def _remove_unwanted_elements(self, soup: BeautifulSoup):
        """불필요한 HTML 요소 제거"""
        unwanted_selectors = [
            'script', 'style', 'noscript',
            '.ad', '.advertisement', '.ads', '.banner',
            '.comment', '.reply', '.comment-area',
            '.social-share', '.share-buttons', '.sns',
            '.related-posts', '.recommend', '.sidebar',
            '.copyright', '.disclaimer', '.footer',
            '.header', '.navigation', '.nav',
            '.popup', '.modal', '.overlay'
        ]
        
        for selector in unwanted_selectors:
            for elem in soup.select(selector):
                # 리스트나 중요한 구조 요소가 아닌 경우에만 제거
                if not elem.find_parent(['ul', 'ol', 'li', 'table', 'tr', 'td', 'th']):
                    elem.decompose()
    
    def _extract_clean_text(self, soup: BeautifulSoup) -> str:
        """깔끔한 텍스트 추출"""
        # 리스트 구조 보존 (텍스트 추출 전에 처리)
        for list_elem in soup.find_all(['ul', 'ol']):
            list_text = []
            for li in list_elem.find_all('li'):
                li_text = li.get_text(strip=True)
                list_text.append(f"• {li_text}")
            list_elem.replace_with('\n'.join(list_text))
        
        # 표 구조 보존
        for table_elem in soup.find_all('table'):
            table_text = []
            for row in table_elem.find_all('tr'):
                row_text = []
                for cell in row.find_all(['td', 'th']):
                    row_text.append(cell.get_text(strip=True))
                if row_text:
                    table_text.append(' | '.join(row_text))
            if table_text:
                table_elem.replace_with('\n'.join(table_text))
        
        # 제목 구조 보존
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            level = int(heading.name[1])
            heading_text = heading.get_text(strip=True)
            heading.replace_with(f"\n{'#' * level} {heading_text}\n")
        
        # 텍스트 추출
        text = soup.get_text(separator='\n', strip=True)
        return text
    
    def _normalize_text(self, text: str) -> str:
        """텍스트 정규화"""
        if not text:
            return ""
        
        # HTML 엔티티 디코딩
        text = html.unescape(text)
        
        # 불필요한 패턴 제거
        for pattern in self.remove_patterns:
            text = re.sub(pattern, '', text, flags=re.MULTILINE | re.DOTALL)
        
        # 정규화 패턴 적용
        for pattern, replacement in self.normalize_patterns:
            text = re.sub(pattern, replacement, text)
        
        # 금액 포맷팅 (별도 처리)
        text = re.sub(r'(\d+)원', lambda m: f"{int(m.group(1)):,}원", text)
        
        # 공백 정규화
        text = self._normalize_whitespace(text)
        
        # 문장 정규화
        text = self._normalize_sentences(text)
        
        return text.strip()
    
    def _normalize_whitespace(self, text: str) -> str:
        """공백 정규화"""
        # 여러 개의 개행을 최대 2개로 축약
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # 줄 내부의 여러 공백을 하나로 축약
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 줄 시작/끝 공백 제거
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # 빈 줄 정리
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        return text
    
    def _normalize_sentences(self, text: str) -> str:
        """문장 정규화"""
        # 문장 끝 정규화 (더 정확한 패턴)
        text = re.sub(r'([.!?]+)\s*', r'\1\n', text)
        
        # 문단 구분 정규화
        text = re.sub(r'\.\n\s*[가-힣]', '.\n\n', text)
        
        return text
    
    def extract_law_keywords(self, text: str) -> List[str]:
        """법률 관련 키워드 추출"""
        found_keywords = []
        text_lower = text.lower()
        
        for keyword in self.law_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def is_law_related(self, text: str, threshold: int = 2) -> bool:
        """법률 관련 텍스트인지 판단"""
        keywords = self.extract_law_keywords(text)
        return len(keywords) >= threshold


def normalize_text(text: str) -> str:
    """간편한 텍스트 정규화 함수"""
    normalizer = TextNormalizer()
    return normalizer.normalize_html(text)


# 테스트용 함수
def test_normalizer():
    """정규화 기능 테스트"""
    normalizer = TextNormalizer()
    
    # HTML 정규화 테스트
    html_sample = """
    <html>
    <body>
        <h2>채권추심 절차 가이드</h2>
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
    
    result = normalizer.normalize_html(html_sample)
    
    # 검증
    assert "## 채권추심 절차 가이드" in result
    assert "• 1단계: 내용증명 발송" in result
    assert "5,000원" in result
    assert "10,000원" in result
    assert "광고 내용" not in result
    assert "법무법인 혜안" in result  # 정규화됨
    
    # 키워드 추출 테스트
    keywords = normalizer.extract_law_keywords(result)
    assert "채권추심" in keywords
    assert "내용증명" in keywords
    assert "지급명령" in keywords
    
    # 법률 관련 텍스트 판단
    assert normalizer.is_law_related(result)
    
    print("✅ TextNormalizer 테스트 통과")


if __name__ == "__main__":
    test_normalizer()
