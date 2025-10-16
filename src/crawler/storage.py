#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
증분 수집 & 중복 제거를 위한 seen.sqlite 관리
"""
import sqlite3
import time
import hashlib
import os
from typing import Optional, List, Tuple
from pathlib import Path


def get_conn(path: str) -> sqlite3.Connection:
    """SQLite 연결 생성 (WAL 모드)"""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """테이블 스키마 초기화"""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS seen_posts(
      url TEXT PRIMARY KEY,
      logno TEXT,
      content_hash TEXT,
      first_seen_at INTEGER,
      last_seen_at INTEGER
    );
    CREATE TABLE IF NOT EXISTS checkpoints(
      key TEXT PRIMARY KEY,
      value TEXT,
      updated_at INTEGER
    );
    CREATE INDEX IF NOT EXISTS idx_seen_posts_logno ON seen_posts(logno);
    CREATE INDEX IF NOT EXISTS idx_seen_posts_content_hash ON seen_posts(content_hash);
    """)
    conn.commit()


def upsert_seen(conn: sqlite3.Connection, url: str, logno: str, content_hash: str) -> None:
    """seen_posts 테이블에 포스트 정보 저장/업데이트"""
    now = int(time.time())
    conn.execute("""
        INSERT INTO seen_posts(url, logno, content_hash, first_seen_at, last_seen_at)
        VALUES(?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET 
            last_seen_at = excluded.last_seen_at,
            content_hash = excluded.content_hash
    """, (url, logno, content_hash, now, now))
    conn.commit()


def get_checkpoint(conn: sqlite3.Connection, key: str) -> Optional[str]:
    """체크포인트 값 조회"""
    cur = conn.execute("SELECT value FROM checkpoints WHERE key = ?", (key,))
    row = cur.fetchone()
    return row[0] if row else None


def set_checkpoint(conn: sqlite3.Connection, key: str, value: str) -> None:
    """체크포인트 값 설정"""
    now = int(time.time())
    conn.execute("""
        INSERT INTO checkpoints(key, value, updated_at)
        VALUES(?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET 
            value = excluded.value, 
            updated_at = excluded.updated_at
    """, (key, value, now))
    conn.commit()


def is_url_seen(conn: sqlite3.Connection, url: str) -> bool:
    """URL이 이미 수집되었는지 확인"""
    cur = conn.execute("SELECT 1 FROM seen_posts WHERE url = ?", (url,))
    return cur.fetchone() is not None


def is_content_duplicate(conn: sqlite3.Connection, content_hash: str) -> bool:
    """동일한 내용이 이미 인덱싱되었는지 확인"""
    cur = conn.execute("SELECT 1 FROM seen_posts WHERE content_hash = ?", (content_hash,))
    return cur.fetchone() is not None


def get_content_hash(text: str) -> str:
    """텍스트의 SHA-256 해시 생성"""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def get_posts_after_logno(conn: sqlite3.Connection, last_logno: str) -> List[Tuple[str, str, str]]:
    """특정 logno 이후의 포스트 목록 조회"""
    cur = conn.execute("""
        SELECT url, logno, content_hash 
        FROM seen_posts 
        WHERE logno > ? 
        ORDER BY logno
    """, (last_logno,))
    return cur.fetchall()


def get_stats(conn: sqlite3.Connection) -> dict:
    """수집 통계 조회"""
    cur = conn.execute("SELECT COUNT(*) FROM seen_posts")
    total_posts = cur.fetchone()[0]
    
    cur = conn.execute("SELECT COUNT(DISTINCT content_hash) FROM seen_posts")
    unique_contents = cur.fetchone()[0]
    
    cur = conn.execute("SELECT MAX(logno) FROM seen_posts WHERE logno IS NOT NULL")
    max_logno = cur.fetchone()[0]
    
    return {
        "total_posts": total_posts,
        "unique_contents": unique_contents,
        "max_logno": max_logno,
        "duplicate_rate": (total_posts - unique_contents) / max(total_posts, 1) * 100
    }


class SeenStorage:
    """증분 수집 & 중복 제거 관리 클래스"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_dir()
        self.conn = get_conn(db_path)
        init_schema(self.conn)
    
    def _ensure_db_dir(self):
        """DB 디렉터리 생성"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def is_new_post(self, url: str) -> bool:
        """새로운 포스트인지 확인"""
        return not is_url_seen(self.conn, url)
    
    def is_new_content(self, content_hash: str) -> bool:
        """새로운 내용인지 확인"""
        return not is_content_duplicate(self.conn, content_hash)
    
    def add_post(self, url: str, logno: str, content: str) -> bool:
        """포스트 추가 (중복 체크 포함)"""
        content_hash = get_content_hash(content)
        
        # 이미 동일한 내용이 있으면 스킵
        if self.is_new_content(content_hash):
            upsert_seen(self.conn, url, logno, content_hash)
            return True
        else:
            # URL만 업데이트 (내용은 중복)
            upsert_seen(self.conn, url, logno, content_hash)
            return False
    
    def get_last_logno(self) -> Optional[str]:
        """마지막 처리된 logno 조회"""
        return get_checkpoint(self.conn, "last_logno")
    
    def set_last_logno(self, logno: str):
        """마지막 처리된 logno 설정"""
        set_checkpoint(self.conn, "last_logno", logno)
    
    def get_stats(self) -> dict:
        """통계 조회"""
        return get_stats(self.conn)
    
    def close(self):
        """연결 종료"""
        if self.conn:
            self.conn.close()


# 테스트용 함수
def test_storage():
    """저장소 기능 테스트"""
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        storage = SeenStorage(db_path)
        
        # 테스트 데이터
        test_url = "https://blog.naver.com/test/123"
        test_logno = "12345"
        test_content = "테스트 내용입니다."
        
        # 새 포스트 추가
        assert storage.is_new_post(test_url)
        assert storage.add_post(test_url, test_logno, test_content)
        
        # 중복 체크
        assert not storage.is_new_post(test_url)
        
        # 동일 내용 다른 URL
        test_url2 = "https://blog.naver.com/test/456"
        assert not storage.add_post(test_url2, "12346", test_content)  # 내용 중복
        
        # 체크포인트 테스트
        storage.set_last_logno("12345")
        assert storage.get_last_logno() == "12345"
        
        # 통계 확인
        stats = storage.get_stats()
        assert stats["total_posts"] == 2
        assert stats["unique_contents"] == 1
        
        print("✅ SeenStorage 테스트 통과")
        
    finally:
        storage.close()
        os.unlink(db_path)


if __name__ == "__main__":
    test_storage()
