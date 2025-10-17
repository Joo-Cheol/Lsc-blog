import sqlite3
import json
from datetime import datetime

def check_crawler_data():
    try:
        # 크롤링 데이터베이스 연결
        conn = sqlite3.connect('data/crawler_storage.db')
        cursor = conn.cursor()
        
        # 테이블 목록 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("테이블 목록:", [table[0] for table in tables])
        
        # seen_posts 테이블 확인
        if ('seen_posts',) in tables:
            cursor.execute("SELECT COUNT(*) FROM seen_posts;")
            total_posts = cursor.fetchone()[0]
            print(f"\n총 수집된 포스트 수: {total_posts}")
            
            # 최근 포스트들 확인
            cursor.execute("""
                SELECT url, title, logno, first_seen_at, last_seen_at, content_hash
                FROM seen_posts 
                ORDER BY first_seen_at DESC 
                LIMIT 10
            """)
            recent_posts = cursor.fetchall()
            
            print("\n최근 수집된 포스트들:")
            for i, post in enumerate(recent_posts, 1):
                url, title, logno, first_seen, last_seen, content_hash = post
                print(f"{i}. {title[:50]}...")
                print(f"   URL: {url}")
                print(f"   logno: {logno}")
                print(f"   첫 수집: {first_seen}")
                print(f"   마지막 확인: {last_seen}")
                print()
        
        # checkpoints 테이블 확인
        if ('checkpoints',) in tables:
            cursor.execute("SELECT * FROM checkpoints;")
            checkpoints = cursor.fetchall()
            print("체크포인트 정보:")
            for checkpoint in checkpoints:
                print(f"  {checkpoint}")
        
        conn.close()
        
    except Exception as e:
        print(f"데이터베이스 조회 오류: {e}")

if __name__ == "__main__":
    check_crawler_data()

