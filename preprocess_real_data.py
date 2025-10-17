#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실제 크롤링 데이터 전처리 스크립트
네이버 블로그 HTML에서 실제 법률 콘텐츠만 추출
"""
import json
import re
import os
from typing import List, Dict, Any

def clean_naver_blog_content(content: str) -> str:
    """네이버 블로그 HTML에서 실제 콘텐츠만 추출"""
    if not content:
        return ""
    
    # HTML 태그 제거
    content = re.sub(r'<[^>]+>', '', content)
    
    # 네이버 블로그 UI 요소 제거
    ui_patterns = [
        r'로그인이 필요합니다\.',
        r'내소식.*?닫기',
        r'이웃목록.*?닫기',
        r'통계.*?닫기',
        r'클립만들기.*?닫기',
        r'글쓰기.*?닫기',
        r'My Menu 닫기',
        r'내 체크인.*?닫기',
        r'최근 본 글.*?닫기',
        r'내 동영상.*?닫기',
        r'내 클립.*?닫기',
        r'내 상품 관리.*?닫기',
        r'NEW.*?닫기',
        r'마켓 플레이스.*?닫기',
        r'장바구니.*?닫기',
        r'마켓 구매내역.*?닫기',
        r'블로그팀 공식블로그.*?닫기',
        r'이달의 블로그.*?닫기',
        r'공식 블로그.*?닫기',
        r'블로그 앱.*?닫기',
        r'로그인.*?닫기',
        r'PC버전으로 보기.*?닫기',
        r'블로그 고객센터.*?닫기',
        r'ⓒ NAVER Corp\.',
        r'본문 바로가기.*?닫기',
        r'블로그.*?닫기',
        r'카테고리 이동.*?닫기',
        r'채권추심의 혜안.*?닫기',
        r'검색.*?닫기',
        r'MY메뉴 열기.*?닫기',
        r'오시는길/소개.*?닫기',
        r'면책공고.*?닫기',
        r'이웃추가.*?닫기',
        r'본문 기타 기능.*?닫기',
        r'본문 폰트 크기 조정.*?닫기',
        r'본문 폰트 크기 작게 보기.*?닫기',
        r'본문 폰트 크기 크게 보기.*?닫기',
        r'공유하기.*?닫기',
        r'URL 복사.*?닫기',
        r'신고하기.*?닫기',
        r'이웃추가.*?닫기',
        r'비즈니스·경제.*?닫기',
        r'이웃.*?명.*?닫기',
        r'서초역 7번출구 대한변호사협회 전문로펌 1800-9263.*?닫기',
        r'이 블로그.*?닫기',
        r'카테고리 글.*?닫기',
        r'정성과 실력으로 채권추심의 결과를.*?닫기',
        r'혜안의 변호사를 소개합니다.*?닫기',
        r'채권추심전문로펌vs일반로펌.*?닫기',
        r'최병천 변호사 소개.*?닫기',
        r'요즘 뜨는 신규 글.*?닫기',
        r'요즘엔 뭐가 좋을지.*?닫기',
        r'진상손님.*?닫기',
        r'보통날.*?닫기',
        r'은치.*?닫기',
        r'장수돌.*?닫기',
        r'상은이.*?닫기',
        r'부티뿡이.*?닫기',
        r'공감.*?닫기',
        r'칭찬.*?닫기',
        r'감사.*?닫기',
        r'웃김.*?닫기',
        r'놀람.*?닫기',
        r'슬픔.*?닫기',
        r'댓글.*?닫기',
        r'이전.*?닫기',
        r'다음.*?닫기',
        r'취소.*?닫기',
        r'공유.*?닫기',
        r'닫기',
        r'이웃추가하고 새글을 받아보세요.*?닫기',
        r'님을 이웃추가하고 새글을 받아보세요.*?닫기',
    ]
    
    for pattern in ui_patterns:
        content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # JSON 메타데이터 제거
    content = re.sub(r'\{[^}]*"title"[^}]*\}', '', content)
    
    # 연속된 공백과 줄바꿈 정리
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'\n\s*\n', '\n', content)
    
    # 빈 줄 제거
    content = re.sub(r'^\s*\n', '', content, flags=re.MULTILINE)
    
    return content.strip()

def extract_legal_content(content: str) -> str:
    """법률 관련 콘텐츠만 추출"""
    if not content:
        return ""
    
    # 법률 관련 키워드가 포함된 문단만 추출
    legal_keywords = [
        '채권', '채무', '추심', '지급명령', '독촉', '집행', '소송', '판결',
        '법원', '변호사', '법무법인', '법률', '계약', '손해', '배상',
        '강제집행', '압류', '경매', '신용정보', '대여금', '미수금',
        '소액사건', '민사', '형사', '가처분', '가압류', '가산금',
        '이자', '연체', '변제', '상환', '담보', '보증', '연대보증'
    ]
    
    # 문단별로 분리
    paragraphs = content.split('\n')
    legal_paragraphs = []
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if len(paragraph) < 20:  # 너무 짧은 문단 제외
            continue
            
        # 법률 키워드가 포함된 문단만 선택
        if any(keyword in paragraph for keyword in legal_keywords):
            legal_paragraphs.append(paragraph)
    
    return '\n'.join(legal_paragraphs)

def preprocess_crawled_data(input_file: str, output_file: str) -> int:
    """크롤링 데이터 전처리"""
    processed_count = 0
    
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        
        for line_num, line in enumerate(f_in, 1):
            try:
                data = json.loads(line.strip())
                
                # 원본 콘텐츠 추출
                raw_content = data.get('content', '')
                
                # 네이버 블로그 UI 제거
                cleaned_content = clean_naver_blog_content(raw_content)
                
                # 법률 콘텐츠만 추출
                legal_content = extract_legal_content(cleaned_content)
                
                # 최소 길이 체크 (100자 이상)
                if len(legal_content) < 100:
                    continue
                
                # 전처리된 데이터 구조
                processed_data = {
                    "id": f"real_doc_{data.get('logno', line_num)}",
                    "text": legal_content,
                    "title": data.get('title', ''),
                    "url": data.get('url', ''),
                    "date": data.get('posted_at', ''),
                    "cat": "채권추심",
                    "author": "법무법인 혜안",
                    "post_type": "법률정보",
                    "original_logno": data.get('logno'),
                    "crawled_at": data.get('crawled_at', ''),
                    "content_length": len(legal_content)
                }
                
                f_out.write(json.dumps(processed_data, ensure_ascii=False) + '\n')
                processed_count += 1
                
                if processed_count % 100 == 0:
                    print(f"처리 완료: {processed_count}개 문서")
                    
            except Exception as e:
                print(f"라인 {line_num} 처리 오류: {e}")
                continue
    
    return processed_count

def main():
    input_file = "src/data/master/exports/full_crawl_export_2025-10-13_1141.jsonl"
    output_file = "real_legal_corpus.jsonl"
    
    print("🚀 실제 크롤링 데이터 전처리 시작...")
    print(f"입력 파일: {input_file}")
    print(f"출력 파일: {output_file}")
    
    if not os.path.exists(input_file):
        print(f"❌ 입력 파일을 찾을 수 없습니다: {input_file}")
        return
    
    processed_count = preprocess_crawled_data(input_file, output_file)
    
    print(f"✅ 전처리 완료!")
    print(f"📊 처리된 문서 수: {processed_count}개")
    print(f"📁 출력 파일: {output_file}")
    
    # 샘플 확인
    if processed_count > 0:
        print("\n📋 샘플 데이터 확인:")
        with open(output_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= 3:  # 처음 3개만
                    break
                data = json.loads(line)
                print(f"\n--- 문서 {i+1} ---")
                print(f"제목: {data['title']}")
                print(f"길이: {data['content_length']}자")
                print(f"내용 미리보기: {data['text'][:100]}...")

if __name__ == "__main__":
    main()






