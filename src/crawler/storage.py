"""
크롤러 증분/중복 제어 스토리지
- seen_posts: 수집된 포스트 추적
- checkpoints: 마지막 수집 위치 추적
"""

import sqlite3
import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class CrawlerStorage:
    """크롤러 증분/중복 제어를 위한 스토리지"""
    
    def __init__(self, db_path: str = "data/crawler_storage.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """데이터베이스 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            # seen_posts 테이블: 수집된 포스트 추적
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seen_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    logno INTEGER NOT NULL,
                    content_hash TEXT NOT NULL,
                    title TEXT,
                    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_updated BOOLEAN DEFAULT FALSE
                )
            """)
            
            # checkpoints 테이블: 마지막 수집 위치
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id INTEGER PRIMARY KEY,
                    last_logno INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_posts INTEGER DEFAULT 0,
                    new_posts INTEGER DEFAULT 0,
                    updated_posts INTEGER DEFAULT 0
                )
            """)
            
            # 인덱스 생성
            conn.execute("CREATE INDEX IF NOT EXISTS idx_seen_posts_logno ON seen_posts(logno)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_seen_posts_hash ON seen_posts(content_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_seen_posts_url ON seen_posts(url)")
            
            # 기본 체크포인트 삽입 (없는 경우)
            conn.execute("""
                INSERT OR IGNORE INTO checkpoints (id, last_logno) 
                VALUES (1, 0)
            """)
            
            conn.commit()
    
    def get_last_logno(self) -> int:
        """마지막 수집된 logno 반환"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT last_logno FROM checkpoints WHERE id = 1")
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def update_checkpoint(self, last_logno: int, stats: Dict[str, int]):
        """체크포인트 업데이트"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE checkpoints 
                SET last_logno = ?, 
                    last_updated = CURRENT_TIMESTAMP,
                    total_posts = ?,
                    new_posts = ?,
                    updated_posts = ?
                WHERE id = 1
            """, (last_logno, stats.get('total', 0), stats.get('new', 0), stats.get('updated', 0)))
            conn.commit()
    
    def is_post_seen(self, url: str) -> bool:
        """포스트가 이미 수집되었는지 확인"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT 1 FROM seen_posts WHERE url = ?", (url,))
            return cursor.fetchone() is not None
    
    def get_content_hash(self, content: str) -> str:
        """콘텐츠 해시 생성"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def is_content_updated(self, url: str, content: str) -> bool:
        """콘텐츠가 업데이트되었는지 확인"""
        content_hash = self.get_content_hash(content)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT content_hash FROM seen_posts WHERE url = ?", 
                (url,)
            )
            result = cursor.fetchone()
            if not result:
                return True  # 새로운 포스트
            return result[0] != content_hash
    
    def add_seen_post(self, url: str, logno: int, content: str, title: str = None) -> str:
        """포스트를 seen_posts에 추가/업데이트"""
        content_hash = self.get_content_hash(content)
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # 기존 포스트 확인
            cursor = conn.execute("SELECT content_hash FROM seen_posts WHERE url = ?", (url,))
            existing = cursor.fetchone()
            
            if existing:
                if existing[0] != content_hash:
                    # 콘텐츠 업데이트
                    conn.execute("""
                        UPDATE seen_posts 
                        SET content_hash = ?, title = ?, last_seen_at = ?, is_updated = TRUE
                        WHERE url = ?
                    """, (content_hash, title, now, url))
                    conn.commit()
                    return "updated"
                else:
                    # 변경 없음
                    conn.execute("""
                        UPDATE seen_posts 
                        SET last_seen_at = ?
                        WHERE url = ?
                    """, (now, url))
                    conn.commit()
                    return "unchanged"
            else:
                # 새로운 포스트
                conn.execute("""
                    INSERT INTO seen_posts (url, logno, content_hash, title, first_seen_at, last_seen_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (url, logno, content_hash, title, now, now))
                conn.commit()
                return "new"
    
    def get_crawl_stats(self) -> Dict[str, Any]:
        """크롤링 통계 반환"""
        with sqlite3.connect(self.db_path) as conn:
            # 전체 통계
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_posts,
                    COUNT(CASE WHEN is_updated = TRUE THEN 1 END) as updated_posts,
                    MIN(first_seen_at) as first_crawl,
                    MAX(last_seen_at) as last_crawl
                FROM seen_posts
            """)
            stats = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))
            
            # 체크포인트 정보
            cursor = conn.execute("SELECT last_logno, last_updated FROM checkpoints WHERE id = 1")
            checkpoint = cursor.fetchone()
            if checkpoint:
                stats['last_logno'] = checkpoint[0]
                stats['last_checkpoint'] = checkpoint[1]
            
            return stats
    
    def get_recent_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 수집된 포스트 목록"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT url, logno, title, first_seen_at, last_seen_at, is_updated
                FROM seen_posts 
                ORDER BY last_seen_at DESC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def cleanup_old_posts(self, days: int = 30):
        """오래된 포스트 정리 (선택적)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM seen_posts 
                WHERE last_seen_at < datetime('now', '-{} days')
            """.format(days))
            deleted_count = cursor.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted_count} old posts")
            return deleted_count


# 전역 인스턴스
crawler_storage = CrawlerStorage()

# backward-compat alias
SeenStorage = CrawlerStorage
__all__ = ["CrawlerStorage", "SeenStorage", "get_content_hash"]