#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
텍스트 정제 및 청킹 유틸리티
"""

import re
import hashlib
from typing import List

def clean_text(text: str) -> str:
    """텍스트 정제"""
    if not text:
        return ""
    
    # 기본 정제
    text = text.strip()
    
    # 연속된 공백 제거
    text = re.sub(r'\s+', ' ', text)
    
    # 특수 문자 정리
    text = re.sub(r'[^\w\s가-힣.,!?;:()\[\]{}"\'-]', '', text)
    
    return text

def split_chunks(text: str, max_tokens: int = 512, overlap: int = 64) -> List[str]:
    """
    텍스트를 청크로 분할 (토큰 기반이 아닌 글자수 기반)
    
    Args:
        text: 분할할 텍스트
        max_tokens: 최대 토큰 수 (글자수로 근사)
        overlap: 겹치는 글자 수
    
    Returns:
        청크 리스트
    """
    if not text:
        return [""]
    
    text = clean_text(text)
    if len(text) <= max_tokens:
        return [text]
    
    chunks = []
    step = max_tokens - overlap
    
    for i in range(0, len(text), step):
        chunk = text[i:i + max_tokens]
        if chunk.strip():
            chunks.append(chunk)
        
        # 마지막 청크에 도달했으면 종료
        if i + max_tokens >= len(text):
            break
    
    return chunks if chunks else [text]

def calculate_content_hash(content: str) -> str:
    """콘텐츠 해시 계산"""
    if not content:
        return ""
    
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def extract_title_from_content(content: str, max_length: int = 100) -> str:
    """콘텐츠에서 제목 추출 (첫 줄 또는 요약)"""
    if not content:
        return "제목 없음"
    
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if line and len(line) > 10:  # 의미있는 길이의 첫 줄
            return line[:max_length]
    
    # 첫 줄이 없으면 전체에서 요약
    return content[:max_length] + "..." if len(content) > max_length else content

def normalize_category_name(category_no: int, category_name: str = None) -> str:
    """카테고리 이름 정규화"""
    if category_name:
        return category_name
    
    # 기본 카테고리 매핑
    category_map = {
        6: "채권추심",
        21: "생활과법률", 
        22: "법무법인 혜안",
        23: "오시는길/소개",
        24: "소식/보도/칼럼",
        35: "공사/물품/용역",
        36: "투자금/동업",
        37: "대여금/미수금",
        38: "강제집행/신용조사"
    }
    
    return category_map.get(category_no, f"카테고리_{category_no}")

if __name__ == "__main__":
    # 테스트
    test_text = "이것은 테스트 텍스트입니다. " * 100
    chunks = split_chunks(test_text, max_tokens=50, overlap=10)
    print(f"원본 길이: {len(test_text)}")
    print(f"청크 수: {len(chunks)}")
    print(f"첫 번째 청크: {chunks[0][:50]}...")
    print(f"해시: {calculate_content_hash(test_text)[:16]}...")
