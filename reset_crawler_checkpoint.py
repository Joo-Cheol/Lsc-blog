import sqlite3

def reset_crawler_checkpoint():
    try:
        conn = sqlite3.connect('data/crawler_storage.db')
        cursor = conn.cursor()
        
        # 체크포인트 리셋
        cursor.execute("UPDATE checkpoints SET last_logno = 0, total = 0, new = 0, updated = 0")
        
        # seen_posts 테이블 비우기 (선택사항)
        cursor.execute("DELETE FROM seen_posts")
        
        conn.commit()
        conn.close()
        
        print("✅ 크롤러 체크포인트가 리셋되었습니다.")
        print("이제 처음부터 다시 크롤링할 수 있습니다.")
        
    except Exception as e:
        print(f"❌ 체크포인트 리셋 오류: {e}")

if __name__ == "__main__":
    reset_crawler_checkpoint()