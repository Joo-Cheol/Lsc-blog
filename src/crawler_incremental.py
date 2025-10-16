#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
증분 크롤링 시스템 - 네이버 블로그 특정 카테고리 크롤링
페이지네이션 + 증분 방식으로 크롤링하여 실행마다 스냅샷 JSONL 생성
"""

import re
import json
import time
import random
import argparse
import pathlib
import datetime as dt
import traceback
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

from state_io import load_last_seen, save_last_seen
from utils_text import clean_text, calculate_content_hash, extract_title_from_content

# 상수
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

def setup_driver(headless: bool = True) -> webdriver.Chrome:
    """Chrome 드라이버 설정"""
    import tempfile
    import os
    
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument(f"--user-agent={UA}")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--lang=ko-KR")
    
    # 고유한 사용자 데이터 디렉토리 생성
    temp_dir = tempfile.mkdtemp()
    opts.add_argument(f"--user-data-dir={temp_dir}")
    
    # Chrome 드라이버 경로 지정
    driver_path = "selenium/drivers/chromedriver.exe"
    if os.path.exists(driver_path):
        driver = webdriver.Chrome(service=webdriver.chrome.service.Service(driver_path), options=opts)
    else:
        driver = webdriver.Chrome(options=opts)
    
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def fetch_list_page(driver: webdriver.Chrome, blog_id: str, category_no: int, page: int) -> str:
    """목록 페이지 HTML 가져오기"""
    url = (f"https://blog.naver.com/PostList.naver?blogId={blog_id}"
           f"&from=postList&categoryNo={category_no}&currentPage={page}")
    
    driver.get(url)
    time.sleep(2)
    
    # mainFrame으로 전환 시도
    try:
        driver.switch_to.default_content()
        WebDriverWait(driver, 8).until(
            EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, "iframe#mainFrame"))
        )
    except TimeoutException:
        pass  # mainFrame이 없으면 그대로 진행
    
    return driver.page_source

def parse_lognos(html: str) -> List[int]:
    """HTML에서 logNo 추출"""
    soup = BeautifulSoup(html, 'html.parser')
    lognos = set()
    
    # 다양한 패턴으로 logNo 추출
    patterns = [
        r'logNo=(\d+)',
        r'data-log-no=["\'](\d+)["\']',
        r'/(\d{6,})(?:\?.*)?$'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html)
        for match in matches:
            if match.isdigit() and len(match) >= 6:
                lognos.add(int(match))
    
    return sorted(lognos)

def fetch_post_detail(driver: webdriver.Chrome, blog_id: str, logno: int) -> Dict[str, Any]:
    """게시글 상세 정보 가져오기"""
    # 모바일 URL로 먼저 시도
    mobile_url = f"https://m.blog.naver.com/{blog_id}/{logno}"
    driver.get(mobile_url)
    time.sleep(2)
    
    # 제목 추출
    title = "제목 없음"
    for selector in ["h1.se-title-text", "h1.post-title", "h1.title", ".se-title-text", ".post-title"]:
        try:
            title_element = driver.find_element(By.CSS_SELECTOR, selector)
            title = title_element.text.strip()
            if title:
                break
        except:
            continue
    
    # 내용 추출
    content = ""
    for selector in ["div.se-main-container", "#post-view", "div#ct", "div.se_component_wrap"]:
        try:
            content_element = driver.find_element(By.CSS_SELECTOR, selector)
            content = content_element.text.strip()
            if content:
                break
        except:
            continue
    
    # 날짜 추출
    posted_at = None
    for selector in ["time[datetime]", "span.se_publishDate", ".se_publishDate", ".post-date"]:
        try:
            date_element = driver.find_element(By.CSS_SELECTOR, selector)
            posted_at = date_element.get_attribute("datetime") or date_element.text.strip()
            if posted_at:
                break
        except:
            continue
    
    # 내용 정제
    content = clean_text(content)
    if not title or title == "제목 없음":
        title = extract_title_from_content(content)
    
    return {
        "title": title,
        "content": content,
        "posted_at": posted_at,
        "url": f"https://blog.naver.com/{blog_id}/{logno}"
    }

def run_incremental_crawl(blog_id: str, category_no: int, category_name: str, 
                         outdir: str, max_pages: int = 9999) -> tuple:
    """
    증분 크롤링 실행
    
    Returns:
        (output_file_path, new_count, max_logno) 튜플
    """
    # 출력 디렉토리 설정
    run_id = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    base_dir = pathlib.Path(outdir) / run_id
    base_dir.mkdir(parents=True, exist_ok=True)
    output_file = base_dir / f"posts_{run_id}.jsonl"
    
    # 상태 로드
    last_seen = load_last_seen()
    print(f"🔄 증분 크롤링 시작 (마지막 logno: {last_seen})")
    
    # 드라이버 설정
    driver = setup_driver(headless=True)
    
    try:
        max_logno = last_seen
        new_count = 0
        no_new_pages = 0
        page = 1
        
        with output_file.open("w", encoding="utf-8") as f:
            while page <= max_pages:
                print(f"📄 페이지 {page} 처리 중...")
                
                # 목록 페이지 가져오기
                html = fetch_list_page(driver, blog_id, category_no, page)
                lognos = parse_lognos(html)
                
                if not lognos:
                    print(f"  ⚠️ 페이지 {page}에서 logNo를 찾을 수 없음")
                    no_new_pages += 1
                    if no_new_pages >= 3:
                        print("  🛑 연속 3페이지에서 게시글 없음 - 크롤링 종료")
                        break
                    page += 1
                    continue
                
                print(f"  📝 {len(lognos)}개 logNo 발견")
                
                # 신규 logNo만 필터링
                new_lognos = [ln for ln in lognos if ln > last_seen]
                
                if not new_lognos:
                    print(f"  ⚠️ 페이지 {page}에서 신규 게시글 없음")
                    no_new_pages += 1
                    if no_new_pages >= 2:
                        print("  🛑 연속 2페이지에서 신규 게시글 없음 - 크롤링 종료")
                        break
                else:
                    no_new_pages = 0
                    print(f"  🆕 신규 {len(new_lognos)}개 게시글")
                
                # 각 게시글 상세 정보 수집
                for i, logno in enumerate(new_lognos, 1):
                    print(f"    📝 [{i}/{len(new_lognos)}] {logno} 처리 중...")
                    
                    try:
                        detail = fetch_post_detail(driver, blog_id, logno)
                        
                        # 문서 생성
                        doc = {
                            "logno": logno,
                            "url": detail["url"],
                            "title": detail["title"],
                            "category_no": category_no,
                            "category_name": category_name,
                            "posted_at": detail["posted_at"],
                            "content": detail["content"],
                            "crawled_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                            "content_hash": calculate_content_hash(detail["content"])
                        }
                        
                        # JSONL 파일에 저장
                        f.write(json.dumps(doc, ensure_ascii=False) + "\n")
                        f.flush()  # 즉시 디스크에 쓰기
                        
                        new_count += 1
                        if logno > max_logno:
                            max_logno = logno
                        
                        print(f"      ✅ 완료: {detail['title'][:50]}...")
                        
                    except Exception as e:
                        print(f"      ❌ 실패: {e}")
                    
                    # 요청 간 지연
                    time.sleep(random.uniform(0.5, 1.0))
                
                # 페이지 간 지연
                time.sleep(random.uniform(1.0, 2.0))
                page += 1
        
        # 상태 저장
        if max_logno > last_seen:
            save_last_seen(max_logno)
            print(f"💾 상태 업데이트: {last_seen} → {max_logno}")
        
        print(f"\n🎉 증분 크롤링 완료!")
        print(f"📊 신규 수집: {new_count}개 게시글")
        print(f"💾 저장 위치: {output_file}")
        
        return str(output_file), new_count, max_logno
        
    except Exception as e:
        print(f"❌ 크롤링 실패: {e}")
        print(traceback.format_exc())
        raise
    finally:
        driver.quit()
        print("🔚 브라우저 종료")

def main():
    parser = argparse.ArgumentParser(description="증분 네이버 블로그 크롤러")
    parser.add_argument("--blog-id", required=True, help="블로그 ID")
    parser.add_argument("--category-no", type=int, required=True, help="카테고리 번호")
    parser.add_argument("--category-name", help="카테고리 이름")
    parser.add_argument("--outdir", default="src/data/processed", help="출력 디렉토리")
    parser.add_argument("--max-pages", type=int, default=9999, help="최대 페이지 수")
    parser.add_argument("--run-id", help="실행 ID (지정하지 않으면 자동 생성)")
    
    args = parser.parse_args()
    
    # 카테고리 이름 설정
    category_name = args.category_name or f"카테고리_{args.category_no}"
    
    try:
        output_file, new_count, max_logno = run_incremental_crawl(
            args.blog_id, 
            args.category_no, 
            category_name,
            args.outdir,
            args.max_pages
        )
        
        print(f"\n📋 실행 결과:")
        print(f"  - 출력 파일: {output_file}")
        print(f"  - 신규 게시글: {new_count}개")
        print(f"  - 최대 logno: {max_logno}")
        
    except Exception as e:
        print(f"❌ 실행 실패: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
