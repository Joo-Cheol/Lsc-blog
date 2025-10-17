import sqlite3
import json
from datetime import datetime

def check_old_crawler_data():
    try:
        # 오래된 크롤링 데이터베이스 연결
        conn = sqlite3.connect('archive/old_files/crawler.db')
        cursor = conn.cursor()
        
        # posts 테이블 구조 확인
        cursor.execute("PRAGMA table_info(posts);")
        columns = cursor.fetchall()
        print("posts 테이블 구조:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # 총 포스트 수
        cursor.execute("SELECT COUNT(*) FROM posts;")
        total_posts = cursor.fetchone()[0]
        print(f"\n총 수집된 포스트 수: {total_posts}")
        
        # 최근 포스트들 확인 (컬럼명을 실제 구조에 맞게 수정)
        cursor.execute("""
            SELECT title, url, logno, created_at
            FROM posts 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        recent_posts = cursor.fetchall()
        
        print("\n최근 수집된 포스트들:")
        for i, post in enumerate(recent_posts, 1):
            title, url, logno, created_at = post
            print(f"{i}. {title[:50]}...")
            print(f"   URL: {url}")
            print(f"   logno: {logno}")
            print(f"   생성일: {created_at}")
            print()
        
        # 가장 오래된 포스트도 확인
        cursor.execute("""
            SELECT title, url, logno, created_at
            FROM posts 
            ORDER BY created_at ASC 
            LIMIT 5
        """)
        oldest_posts = cursor.fetchall()
        
        print("가장 오래된 포스트들:")
        for i, post in enumerate(oldest_posts, 1):
            title, url, logno, created_at = post
            print(f"{i}. {title[:50]}...")
            print(f"   생성일: {created_at}")
            print()
        
        conn.close()
        
    except Exception as e:
        print(f"데이터베이스 조회 오류: {e}")

if __name__ == "__main__":
    check_old_crawler_data()