#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 블로그 크롤러 - 모든/개별 카테고리 지원
모바일 목록 우선 + 데스크톱 목록 폴백(클릭 내비게이션) + 노이즈 제거
"""
from __future__ import annotations
import re, json, time, random, argparse, pathlib, datetime as dt, traceback, requests
from requests.adapters import HTTPAdapter, Retry
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

# ---------- 상수/정규식 ----------
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

ASYNC_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://blog.naver.com/",
    "Cache-Control": "no-cache",
}

def make_session():
    """재시도와 연결 풀링이 포함된 requests 세션 생성"""
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.headers.update(ASYNC_HEADERS)
    return s
LOGNO_QS_RE = re.compile(r"logNo=(\d+)")
M_LOGNO_PATH_RE = re.compile(r"/(\d+)(?:\?.*)?$")
M_TOTAL_RE = re.compile(r"(\d{1,3}(?:,\d{3})*)\s*개의\s*글")

# ---------- 유틸 ----------
def setup_driver(headless: bool = True):
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
    opts.add_argument(f"--remote-debugging-port={random.randint(9222, 65500)}")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-plugins")
    # opts.add_argument("--disable-images")  # 일부 스킨에서 이미지 로딩이 목록 DOM 트리거
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--lang=ko-KR")
    opts.add_experimental_option("prefs", {"intl.accept_languages": "ko-KR,ko"})
    driver = webdriver.Chrome(options=opts)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def ensure_dirs(base: pathlib.Path):
    (base / "logs").mkdir(parents=True, exist_ok=True)
    (base / "by_category").mkdir(parents=True, exist_ok=True)

def load_state(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

def save_state(path: pathlib.Path, state: dict):
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def sanitize_filename(s: str) -> str:
    return re.sub(r"[\\/:*?\"<>|]", "_", s).strip()

def switch_to_mainframe_if_present(driver, timeout=8) -> bool:
    driver.switch_to.default_content()
    try:
        WebDriverWait(driver, timeout).until(
            EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, "iframe#mainFrame"))
        )
        return True
    except TimeoutException:
        return False

def ensure_in_mainframe(driver, timeout=8) -> bool:
    driver.switch_to.default_content()
    try:
        WebDriverWait(driver, timeout).until(
            EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, "iframe#mainFrame"))
        )
        return True
    except TimeoutException:
        return False

def _bs(html: str) -> BeautifulSoup:
    for parser in ("lxml", "html5lib", "html.parser"):
        try:
            return BeautifulSoup(html, parser)
        except Exception:
            continue
    return BeautifulSoup(html, "html.parser")

def clean_text(html: str) -> tuple[str, str]:
    soup = _bs(html)
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text("\n", strip=True), str(soup)

# ---------- 카테고리 탐색(데스크톱) ----------
def discover_categories(driver, blog_id: str) -> list[dict]:
    url = f"https://blog.naver.com/PostList.naver?blogId={blog_id}&from=postList&categoryNo=0&currentPage=1"
    driver.get(url)
    switch_to_mainframe_if_present(driver, timeout=10)

    cats: dict[int, dict] = {}
    anchors = driver.find_elements(By.CSS_SELECTOR, "a[href*='categoryNo=']")
    for a in anchors:
        href = a.get_attribute("href") or ""
        m = re.search(r"categoryNo=(\d+)", href)
        if not m:
            continue
        cat_no = int(m.group(1))
        if cat_no == 0:
            continue
        name = (a.text or "").strip()
        name_clean = re.sub(r"[()\uFF08\uFF09]\s*\d[\d,]*\s*[()\uFF08\uFF09]", "", name).strip()
        mcount = re.search(r"[()\uFF08\uFF09]\s*(\d[\d,]*)\s*[()\uFF08\uFF09]", name)
        count_hint = int(mcount.group(1).replace(",", "")) if mcount else None
        # 카테고리 8번 "쉬는시간" 제외
        if cat_no == 8 and ("쉬는시간" in name_clean or "휴식" in name_clean):
            continue
        cats.setdefault(cat_no, {"cat_no": cat_no, "name": name_clean, "count_hint": count_hint})

    out = sorted(cats.values(), key=lambda d: d["cat_no"])
    if not out:
        print("⚠️ 카테고리 탐색 실패(스킨 차이).")
    return out

# ---------- 목록 진입 ----------
def goto_mobile_list(driver, blog_id: str, cat_no: int, page: int, wait_seconds: int = 15):
    url = (f"https://m.blog.naver.com/PostList.naver?blogId={blog_id}"
           f"&from=postList&categoryNo={cat_no}&currentPage={page}")
    driver.get(url)
    WebDriverWait(driver, wait_seconds).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a")))
    _gentle_scroll(driver, steps=4, pause=0.35)

def _frame_src_current_page(driver) -> int | None:
    """mainFrame src의 currentPage 값을 읽음(없으면 None). 호출 전 mainFrame 안이어야 함."""
    try:
        frame = driver.find_element(By.CSS_SELECTOR, "iframe#mainFrame")
        src = frame.get_attribute("src") or ""
    except Exception:
        try:
            # 이미 프레임 내부라면 document.URL 사용
            src = driver.execute_script("return document.location.href;") or ""
        except Exception:
            return None
    m = re.search(r"currentPage=(\d+)", src)
    return int(m.group(1)) if m else None

def get_category_total_async(blog_id: str, cat_no: int, count_per_page: int = 30) -> tuple[int,int,int,str]:
    """async 엔드포인트로 정확한 총 글 수와 마지막 페이지 계산"""
    total = 0
    page = 1
    session = make_session()
    while True:
        url = ("https://blog.naver.com/PostTitleListAsync.naver"
               f"?blogId={blog_id}&from=postList&categoryNo={cat_no}"
               f"&currentPage={page}&countPerPage={count_per_page}")
        try:
            r = session.get(url, timeout=8)
            if not r.ok or not r.text:
                break
            lognos = set(re.findall(r"logNo=(\d{6,})", r.text))
            if not lognos:
                break
            total += len(lognos)
            page += 1
            # 방어: 과도한 페이지 순회 제한
            if page > 2000: break
            # 요청 간 지연 (안티봇)
            time.sleep(random.uniform(0.1, 0.3))
        except Exception:
            break
    last_page = max(1, (total - 1)//count_per_page + 1) if total else 1
    return total, count_per_page, last_page, "async"

def fetch_lognos_async(blog_id: str, cat_no: int, page: int) -> list[str]:
    """
    네이버 내부 목록 비동기 엔드포인트를 직접 조회해서 logNo 리스트를 뽑는다.
    1) 데스크톱: PostTitleListAsync.naver
    2) 모바일:  CategoryPostListAsync.naver (폴백)
    """
    out = set()
    session = make_session()

    # 데스크톱 async
    desktop_url = (
        "https://blog.naver.com/PostTitleListAsync.naver"
        f"?blogId={blog_id}&from=postList&categoryNo={cat_no}"
        f"&currentPage={page}&countPerPage=30"
    )
    try:
        r = session.get(desktop_url, timeout=8)
        if r.ok and r.text:
            out.update(re.findall(r"logNo=(\d{6,})", r.text))
            out.update(re.findall(r"data-log-no=[\"'](\d+)[\"']", r.text))
    except Exception:
        pass

    # 모바일 async (폴백)
    if not out:
        mobile_url = (
            "https://m.blog.naver.com/CategoryPostListAsync.naver"
            f"?blogId={blog_id}&categoryNo={cat_no}"
            f"&currentPage={page}&countPerPage=30"
        )
        try:
            r = session.get(mobile_url, timeout=8)
            if r.ok and r.text:
                out.update(re.findall(r"/%s/(\d{6,})" % re.escape(blog_id), r.text))
                out.update(re.findall(r"logNo=(\d{6,})", r.text))
                out.update(re.findall(r"data-log-no=[\"'](\d+)[\"']", r.text))
        except Exception:
            pass

    return sorted(out)

def _gentle_scroll(driver, steps=3, pause=0.4):
    """지연 로딩 대비 천천히 스크롤"""
    for _ in range(steps):
        driver.execute_script("window.scrollBy(0, document.body.scrollHeight/2);")
        time.sleep(pause)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(pause)

def goto_desktop_list(driver, blog_id: str, cat_no: int, page: int, wait_seconds: int = 15):
    url = (f"https://blog.naver.com/PostList.naver?blogId={blog_id}"
           f"&from=postList&categoryNo={cat_no}&currentPage={page}")
    driver.get(url)

    in_frame = ensure_in_mainframe(driver, timeout=wait_seconds)
    WebDriverWait(driver, wait_seconds).until(
        EC.presence_of_any_elements_located((By.CSS_SELECTOR, "a[href*='logNo='], [data-log-no]"))
        if in_frame else
        EC.presence_of_any_elements_located((By.CSS_SELECTOR, "iframe#mainFrame, a[href*='logNo='], [data-log-no]"))
    )
    _gentle_scroll(driver, steps=4, pause=0.35)

# ---------- 목록에서 logNo 추출 ----------
def collect_lognos_on_mobile_page(driver, blog_id: str) -> list[str]:
    out = set()
    for a in driver.find_elements(By.CSS_SELECTOR, "a[href]"):
        href = a.get_attribute("href") or ""
        m = re.search(r"/%s/(\d{6,})" % re.escape(blog_id), href)
        if m: out.add(m.group(1))
    if not out:
        html = driver.page_source
        out.update(re.findall(r"/%s/(\d{6,})" % re.escape(blog_id), html))
    return sorted(out)

def collect_lognos_on_desktop_page(driver, blog_id: str) -> list[str]:
    out = set()

    # DOM 기반
    for a in driver.find_elements(By.CSS_SELECTOR, "a[href*='logNo=']"):
        href = a.get_attribute("href") or ""
        m = LOGNO_QS_RE.search(href)
        if m: out.add(m.group(1))
    for node in driver.find_elements(By.CSS_SELECTOR, "[data-log-no]"):
        ln = (node.get_attribute("data-log-no") or "").strip()
        if ln.isdigit(): out.add(ln)

    # 폴백: HTML 전체에서 정규식
    if not out:
        html = driver.page_source
        out.update(re.findall(r"logNo=(\d{6,})", html))

    return sorted(out)

# ---------- 본문 수집 ----------
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def fetch_post_html_mobile(driver, blog_id: str, logno: str) -> str:
    url = f"https://m.blog.naver.com/{blog_id}/{logno}"
    driver.get(url)
    for sel in ["div.se-main-container", "#post-view", "div#ct", "div.se_component_wrap"]:
        try:
            WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
            return driver.page_source
        except TimeoutException:
            continue
    return driver.page_source

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=6))
def fetch_post_html_desktop(driver, blog_id: str, logno: str) -> str:
    url = f"https://blog.naver.com/{blog_id}/{logno}"
    driver.get(url)
    switch_to_mainframe_if_present(driver, timeout=12)
    for sel in ["div.se-main-container", "div#postViewArea", "[id^='post-view']",
                "div.post_ct", "div.post-view", "div.contents"]:
        try:
            WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
            return driver.page_source
        except TimeoutException:
            continue
    return driver.page_source

def fetch_post_html_mobile_first(driver, blog_id: str, logno: str) -> str:
    try:
        return fetch_post_html_mobile(driver, blog_id, logno)
    except Exception:
        return fetch_post_html_desktop(driver, blog_id, logno)

def extract_metadata(soup: BeautifulSoup) -> dict:
    md = {"title": None, "published_at": None, "author": None, "images": [], "tags": []}
    # 제목 후보 추가 (더 다양한 스킨 지원)
    for sel in ["meta[property='og:title']", "h1.se-title-text", "h1.post-title", "h1.title", 
                ".se-title-text", ".post-title", "h3.se_textarea", ".pcol1 .htitle", 
                "h2#title_1", "h2#logNo", "title"]:
        el = soup.select_one(sel)
        if el:
            md["title"] = el.get("content", None) or el.get_text(strip=True)
            if md["title"]: break
    # 날짜 후보 추가 (더 다양한 스킨 지원)
    for sel in ["time[datetime]", "span.se_publishDate", "span#se_publishDate", 
                ".se_publishDate", ".post-date", ".date", "[class*='date']",
                "meta[property='article:published_time']", "meta[name='date']", ".publish-date"]:
        el = soup.select_one(sel)
        if el:
            md["published_at"] = el.get("datetime") or el.get("content") or el.get_text(strip=True)
            if md["published_at"]: break
    # 작성자 후보 추가
    for sel in [".nick", ".bloger", "[class*='author']", "span.se_author", "span.author", 
                ".author", ".post-author", "meta[property='article:author']", ".blog-author", ".writer"]:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            md["author"] = el.get_text(strip=True)
            if md["author"]: break
    # 이미지 수집 (더 포괄적)
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if src and src.startswith("http") and ("blog.naver.com" in src or "mblogthumb-phinf.pstatic.net" in src):
            md["images"].append(src)
    # 태그 수집 (더 포괄적)
    for sel in [".tag", ".tags a", "[class*='tag'] a", "a[href*='tag=']", ".post-tag", ".category-tag"]:
        for t in soup.select(sel):
            val = t.get_text(strip=True)
            if val and val not in md["tags"] and len(val) < 50:  # 너무 긴 텍스트 제외
                md["tags"].append(val)
    return md

# ---------- 총합/마지막 페이지 계산 ----------
def parse_total_from_screen(driver) -> int:
    try:
        inner = driver.find_element(By.CSS_SELECTOR, "body").get_attribute("innerText") or ""
    except Exception:
        return 0
    m = M_TOTAL_RE.search(inner)
    return int(m.group(1).replace(",", "")) if m else 0

def get_category_total(driver, blog_id: str, cat_no: int, count_hint: int | None) -> tuple[int, int, int, str]:
    """
    (total, page_size, last_page, method)
    1) async 엔드포인트 우선 (정확도 최고)
    2) sidebar-hint 폴백
    3) 실패 시: 데스크톱 1페이지 강제 진입 후 page_size 측정 → 9999 점프 방식
    4) 그래도 실패시 모바일로 동일
    """
    # 0) async 엔드포인트로 정확한 총 개수 계산 (최우선)
    try:
        total, page_size, last_page, method = get_category_total_async(blog_id, cat_no)
        if total > 0:
            return total, page_size, last_page, method
    except Exception:
        pass

    # 1) 사이드바 힌트가 있으면 폴백
    if count_hint and count_hint > 0:
        # 실제 1페이지의 page_size를 데스크톱에서 측정
        try:
            goto_desktop_list(driver, blog_id, cat_no, 1)
            page1 = collect_lognos_on_desktop_page(driver, blog_id)
            page_size = len(page1) or 50
        except Exception:
            page_size = 50  # 안전 기본값
        last_page = max(1, (count_hint - 1) // page_size + 1)
        return count_hint, page_size, last_page, "sidebar-hint"

    # 2) 사이드바 힌트가 없으면 데스크톱 페이지 워크
    try:
        goto_desktop_list(driver, blog_id, cat_no, 1)
        p1 = collect_lognos_on_desktop_page(driver, blog_id)
        page_size = len(p1) or 50
        # 마지막 블록 추정
        goto_desktop_list(driver, blog_id, cat_no, 9999)
        # 현재 mainFrame URL에서 currentPage를 읽어 최댓값으로 사용 (9999 → 자동 클램프)
        driver.switch_to.default_content()
        ensure_in_mainframe(driver, timeout=8)  # 프레임 보장
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#mainFrame"))
        )
        last_src = driver.find_element(By.CSS_SELECTOR, "iframe#mainFrame").get_attribute("src") or ""
        m = re.search(r"currentPage=(\d+)", last_src)
        max_page = int(m.group(1)) if m else 1
        goto_desktop_list(driver, blog_id, cat_no, max_page)
        last_count = len(collect_lognos_on_desktop_page(driver, blog_id)) or page_size
        total = (max_page - 1) * page_size + last_count
        return total, page_size, max_page, "desktop-walk"
    except Exception:
        pass

    # 3) 최후엔 모바일
    try:
        goto_mobile_list(driver, blog_id, cat_no, 1)
        p1 = collect_lognos_on_mobile_page(driver, blog_id)
        page_size = len(p1) or 10
        # 모바일은 앵커가 없을 수 있으므로 9999 점프 후 body 텍스트의 "N개의 글" 문구를 시도
        goto_mobile_list(driver, blog_id, cat_no, 9999)
        total = parse_total_from_screen(driver)
        if not total:
            total = page_size  # 최소값
        last_page = max(1, (total - 1) // page_size + 1)
        return total, page_size, last_page, "mobile-fallback"
    except Exception:
        return 0, 10, 1, "unknown"

# ---------- 카테고리 수집 ----------
def crawl_category(driver, blog_id: str, cat_no: int, cat_name: str,
                   start_page: int, max_pages: int,
                   state: dict, out_jsonl: pathlib.Path, sidebar_counts: dict[int, int] | None = None) -> list[dict]:
    print(f"\n🗂️ 카테고리[{cat_no}] {cat_name} 시작")

    count_hint = (sidebar_counts or {}).get(cat_no)
    total, page_size, last_page, method = get_category_total(driver, blog_id, cat_no, count_hint)
    print(f"🧮 총 글 수 추정: {total} (page_size≈{page_size}, last_page≈{last_page}, via {method})")

    if not total:
        print("  ⚠️ 총합 계산 실패 → 'max-pages' 한도까지 전진합니다.")
        effective_max_pages = max_pages
    else:
        effective_max_pages = max(0, min(max_pages, last_page - start_page + 1))
    print(f"📊 실제 수집 페이지 수: {effective_max_pages}")

    state.setdefault("categories", {})
    prev = state["categories"].get(str(cat_no), {})
    last_log_no = prev.get("last_log_no")

    # 같은 실행 내/파일 내 중복 방지
    seen_already = set()
    if out_jsonl.exists():
        with out_jsonl.open(encoding="utf-8") as f:
            for line in f:
                try:
                    j = json.loads(line)
                    if j.get("source", {}).get("category_no") == cat_no and j.get("post_no"):
                        seen_already.add(j["post_no"])
                except Exception:
                    continue

    results, seen_session = [], set()
    page = start_page
    stop_at_page = start_page + effective_max_pages - 1
    empty_streak = 0
    consecutive_empty = 0
    prev_sig = None
    repeat_hits = 0

    while effective_max_pages == 0 or page <= stop_at_page:
        print(f"📄 페이지 {page} 처리 중...")

        # 0) 비동기 엔드포인트로 먼저 시도
        lognos = []
        try:
            lognos = fetch_lognos_async(blog_id, cat_no, page)
            if lognos:
                print(f"  ⚡ async 목록 {len(lognos)}건")
        except Exception:
            lognos = []

        # 1) (비었으면) 모바일 목록 시도
        if not lognos:
            try:
                goto_mobile_list(driver, blog_id, cat_no, page)
                lognos = collect_lognos_on_mobile_page(driver, blog_id)
            except Exception:
                lognos = []

        # 2) (그래도 비면) 데스크톱 목록 폴백
        if not lognos:
            print("  🔁 모바일 목록 비어있음 → 데스크톱 목록 폴백")
            try:
                goto_desktop_list(driver, blog_id, cat_no, page)
                ensure_in_mainframe(driver, timeout=6)
                lognos = collect_lognos_on_desktop_page(driver, blog_id)
                print(f"  📌 got {len(lognos)} lognos (desktop)")
            except Exception:
                lognos = []

        if not lognos:
            # 안티봇/빈화면 디버그 가드
            in_frame = ensure_in_mainframe(driver, timeout=6)
            try:
                cur_url = driver.execute_script("return document.location.href;")
            except Exception:
                cur_url = "(no frame url)"
            try:
                body_txt = driver.find_element(By.TAG_NAME, "body").get_attribute("innerText")[:500].replace("\n"," ")
            except Exception:
                body_txt = "(no body)"
            print(f"  🪵 empty-list peek @ {cur_url} :: {body_txt[:220]} ...")
                
            print("  ❗ 목록 비어있음 → 다음 페이지")
            page += 1
            empty_streak += 1
            if empty_streak >= 3:   # 연속 빈 페이지 3회면 종료(스킨/페이징 보호)
                print("  🛑 연속 3페이지 비어있음 → 카테고리 종료")
                break
            continue
        empty_streak = 0

        # 같은 페이지 반복 감지
        sig = ",".join(lognos[:10])  # 앞 10개만 서명처럼 사용
        if sig == prev_sig:
            repeat_hits += 1
        else:
            repeat_hits = 0
        prev_sig = sig

        if repeat_hits >= 2:
            print("  🛑 같은 목록이 3페이지 연속 반복됨 → 카테고리 종료(페이지 이동 실패 추정)")
            break

        print("  🔎 샘플 logno:", ", ".join(lognos[:5]))

        filtered = []
        for ln in lognos:
            if last_log_no and int(ln) <= int(last_log_no):
                continue
            if ln in seen_session or ln in seen_already:
                continue
            seen_session.add(ln)
            filtered.append(ln)

        print(f"  📝 신규 {len(filtered)}개")
        
        # 중단 조건 강화 (증분 수집)
        if not filtered and last_log_no:
            consecutive_empty += 1
            if consecutive_empty >= 2:
                print("  ⛳ 신규 없음 2페이지 연속 → 카테고리 종료")
                break
        else:
            consecutive_empty = 0
            
        for ln in sorted(filtered):
            print(f"    📝 {ln} 수집 중...")
            try:
                html = fetch_post_html_mobile_first(driver, blog_id, ln)
                text, content_html = clean_text(html)
                soup = _bs(html)
                meta = extract_metadata(soup)
                now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
                rec = {
                    "post_no": ln,
                    "title": meta["title"] or f"게시글 {ln}",
                    "category": cat_name,
                    "author": meta["author"],
                    "url": f"https://blog.naver.com/{blog_id}/{ln}",
                    "published_at": meta["published_at"],
                    "crawled_at": now,
                    "content_text": text,
                    "content_html": content_html,
                    "images": meta["images"],
                    "tags": meta["tags"],
                    "source": {"blog_id": blog_id, "category_no": cat_no, "page": page}
                }
                results.append(rec)
                with out_jsonl.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                print(f"      ✅ 완료: {(rec['title'] or '')[:50]}...")
            except Exception as e:
                print(f"      ❌ 실패: {e}")
            time.sleep(random.uniform(0.4, 1.0))

        time.sleep(random.uniform(0.4, 0.8))
        page += 1

    # 카테고리별 파일
    cat_file = out_jsonl.parent / "by_category" / f"{cat_no}_{sanitize_filename(cat_name or str(cat_no))}.json"
    cat_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    # 상태 갱신
    new_max = max([int(r["post_no"]) for r in results], default=prev.get("last_log_no", 0) or 0)
    state["categories"][str(cat_no)] = {
        "last_log_no": new_max,
        "last_page": last_page,
        "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "name": cat_name
    }
    return results

# ---------- 메인 ----------
def main():
    ap = argparse.ArgumentParser(description="네이버 블로그 크롤러 (모바일 목록 우선 + 데스크톱 클릭 폴백)")
    ap.add_argument("--blog-id", required=True)
    ap.add_argument("--category-no", type=int, default=6)
    ap.add_argument("--all-categories", action="store_true")
    ap.add_argument("--start-page", type=int, default=1)
    ap.add_argument("--max-pages", type=int, default=9999)
    ap.add_argument("--outdir", default="src/data/processed")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--since-logno", type=int, default=None)
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()

    run_id = args.run_id or dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    base = pathlib.Path(args.outdir) / run_id
    ensure_dirs(base)

    state_path = pathlib.Path(args.outdir) / "state.json"
    state = load_state(state_path) if args.resume else {}
    if "categories" not in state:
        state["categories"] = {}

    driver = setup_driver(headless=args.headless)
    out_jsonl = base / "posts_all.jsonl"

    try:
        if args.all_categories:
            cats = discover_categories(driver, args.blog_id)
            if not cats:
                print("❗ 카테고리 자동 탐색 실패. --category-no 로 개별 실행하세요.")
                return
            target_cats = cats
            sidebar_counts = { c["cat_no"]: c.get("count_hint") for c in cats }
            print("🧭 순회 대상 카테고리:", ", ".join(f"{c['cat_no']}:{c['name']}" for c in cats))
        else:
            target_cats = [{"cat_no": args.category_no, "name": f"category_{args.category_no}", "count_hint": None}]
            sidebar_counts = {}

        grand_total = 0
        for cat in target_cats:
            cat_no = int(cat["cat_no"])
            cat_name = cat.get("name") or f"category_{cat_no}"
            if args.since_logno is not None:
                state["categories"][str(cat_no)] = {"last_log_no": args.since_logno}
            rows = crawl_category(driver, args.blog_id, cat_no, cat_name,
                                  args.start_page, args.max_pages, state, out_jsonl, sidebar_counts)
            grand_total += len(rows)
            state.update({"blog_id": args.blog_id, "run_id": run_id})
            save_state(state_path, state)

        print(f"\n🎉 전체 수집 완료: {grand_total}개 게시글")
        print(f"💾 저장 디렉토리: {base}")

    except Exception as e:
        print(f"❌ 실행 중 오류: {e}")
        print(traceback.format_exc())
    finally:
        driver.quit()
        print("🔚 브라우저 종료")

if __name__ == "__main__":
    main()
    