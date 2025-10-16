#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
스냅샷 JSONL → SQLite 병합 (중복 차단 + 신규만 추출)
"""

import sqlite3
import json
import os
import argparse
from pathlib import Path
from utils_text import calculate_content_hash

DB_PATH = "src/data/master/posts.sqlite"

def init_database():
    """데이터베이스 초기화"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.executescript("""
    PRAGMA journal_mode=WAL;
    PRAGMA synchronous=NORMAL;
    
    CREATE TABLE IF NOT EXISTS posts (
        logno INTEGER PRIMARY KEY,
        url TEXT,
        title TEXT,
        category_no INTEGER,
        posted_at TEXT,
        content TEXT,
        content_hash TEXT,
        crawled_at TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    );
    
    CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category_no);
    CREATE INDEX IF NOT EXISTS idx_posts_posted_at ON posts(posted_at);
    CREATE INDEX IF NOT EXISTS idx_posts_crawled_at ON posts(crawled_at);
    """)
    
    conn.commit()
    conn.close()
    print(f"✅ 데이터베이스 초기화 완료: {DB_PATH}")

def upsert_jsonl(jsonl_path: str) -> list:
    """
    JSONL 파일을 SQLite에 병합하고 신규 삽입된 logno 리스트 반환
    
    Args:
        jsonl_path: JSONL 파일 경로
        
    Returns:
        신규 삽입된 logno 리스트
    """
    if not os.path.exists(jsonl_path):
        raise FileNotFoundError(f"JSONL 파일을 찾을 수 없습니다: {jsonl_path}")
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    inserted_lognos = []
    updated_count = 0
    new_count = 0
    
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                
                # post_no를 logno로 매핑
                logno = int(data.get("post_no", data.get("logno", 0)))
                content_hash = calculate_content_hash(data.get("content_text", data.get("content", "")))
                
                # 기존 레코드 확인
                cur.execute("SELECT content_hash FROM posts WHERE logno = ?", (logno,))
                existing = cur.fetchone()
                
                # UPSERT 실행
                cur.execute("""
                INSERT INTO posts (logno, url, title, category_no, posted_at, content, content_hash, crawled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(logno) DO UPDATE SET
                    url = excluded.url,
                    title = excluded.title,
                    category_no = excluded.category_no,
                    posted_at = excluded.posted_at,
                    content = CASE 
                        WHEN posts.content_hash != excluded.content_hash 
                        THEN excluded.content 
                        ELSE posts.content 
                    END,
                    content_hash = CASE 
                        WHEN posts.content_hash != excluded.content_hash 
                        THEN excluded.content_hash 
                        ELSE posts.content_hash 
                    END,
                    crawled_at = excluded.crawled_at,
                    updated_at = datetime('now')
                """, (
                    logno,
                    data.get("url", ""),
                    data.get("title", ""),
                    int(data.get("category_no", 0)),
                    data.get("published_at", data.get("posted_at", "")),
                    data.get("content_text", data.get("content", "")),
                    content_hash,
                    data.get("crawled_at", "")
                ))
                
                if existing is None:
                    # 신규 삽입
                    inserted_lognos.append(logno)
                    new_count += 1
                elif existing[0] != content_hash:
                    # 내용 변경으로 업데이트
                    updated_count += 1
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"⚠️ 라인 {line_num} 처리 실패: {e}")
                continue
    
    conn.commit()
    conn.close()
    
    print(f"📊 병합 완료:")
    print(f"  - 신규 삽입: {new_count}개")
    print(f"  - 내용 업데이트: {updated_count}개")
    print(f"  - 총 처리: {len(inserted_lognos)}개")
    
    return inserted_lognos

def export_new_posts(inserted_lognos: list, run_id: str) -> str:
    """신규 삽입된 포스트들을 별도 JSONL로 내보내기"""
    if not inserted_lognos:
        print("📝 신규 포스트가 없어 내보내기를 건너뜁니다.")
        return ""
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 신규 포스트 조회
    placeholders = ",".join("?" * len(inserted_lognos))
    cur.execute(f"""
    SELECT logno, url, title, category_no, posted_at, content, content_hash, crawled_at
    FROM posts 
    WHERE logno IN ({placeholders})
    ORDER BY logno
    """, inserted_lognos)
    
    posts = cur.fetchall()
    conn.close()
    
    # 내보내기 파일 경로
    export_dir = "src/data/master/exports"
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, f"new_for_index_{run_id}.jsonl")
    
    # JSONL 파일 생성
    with open(export_path, "w", encoding="utf-8") as f:
        for post in posts:
            data = {
                "logno": post[0],
                "url": post[1],
                "title": post[2],
                "category_no": post[3],
                "posted_at": post[4],
                "content": post[5],
                "content_hash": post[6],
                "crawled_at": post[7]
            }
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    
    print(f"📤 신규 포스트 내보내기 완료: {export_path}")
    return export_path

def get_database_stats() -> dict:
    """데이터베이스 통계 정보"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 전체 포스트 수
    cur.execute("SELECT COUNT(*) FROM posts")
    total_posts = cur.fetchone()[0]
    
    # 카테고리별 통계
    cur.execute("""
    SELECT category_no, COUNT(*) 
    FROM posts 
    GROUP BY category_no 
    ORDER BY category_no
    """)
    category_stats = dict(cur.fetchall())
    
    # 최신/최오래된 포스트
    cur.execute("SELECT MIN(crawled_at), MAX(crawled_at) FROM posts")
    min_date, max_date = cur.fetchone()
    
    conn.close()
    
    return {
        "total_posts": total_posts,
        "category_stats": category_stats,
        "date_range": {"min": min_date, "max": max_date}
    }

def main():
    parser = argparse.ArgumentParser(description="JSONL 스냅샷을 SQLite에 병합")
    parser.add_argument("--input", required=True, help="입력 JSONL 파일 경로")
    parser.add_argument("--run-id", help="실행 ID (내보내기 파일명용)")
    parser.add_argument("--stats", action="store_true", help="통계 정보 출력")
    
    args = parser.parse_args()
    
    # 데이터베이스 초기화
    init_database()
    
    # 병합 실행
    inserted_lognos = upsert_jsonl(args.input)
    
    # 신규 포스트 내보내기
    if inserted_lognos and args.run_id:
        export_new_posts(inserted_lognos, args.run_id)
    
    # 통계 출력
    if args.stats:
        stats = get_database_stats()
        print(f"\n📈 데이터베이스 통계:")
        print(f"  - 총 포스트: {stats['total_posts']}개")
        print(f"  - 카테고리별: {stats['category_stats']}")
        print(f"  - 날짜 범위: {stats['date_range']['min']} ~ {stats['date_range']['max']}")

if __name__ == "__main__":
    main()
