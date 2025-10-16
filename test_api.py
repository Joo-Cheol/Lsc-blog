#!/usr/bin/env python3
"""
API 테스트 스크립트
"""
import requests
import json
import time

def test_api():
    """API 테스트"""
    try:
        # 서버가 실행 중인지 확인
        print("🔍 서버 상태 확인 중...")
        response = requests.get("http://localhost:8001/", timeout=5)
        print(f"서버 상태: {response.status_code}")
        
        # 블로그 생성 API 테스트
        print("\n🚀 블로그 생성 API 테스트...")
        
        payload = {
            "topic": "채권추심 절차",
            "category": "채권추심", 
            "mode": "unified"
        }
        
        response = requests.post(
            "http://localhost:8001/api/generate",
            json=payload,
            timeout=30
        )
        
        print(f"응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"성공: {result.get('success', False)}")
            print(f"모드: {result.get('mode', 'N/A')}")
            print(f"제목: {result.get('title', 'N/A')}")
            print(f"생성 시간: {result.get('generation_time', 0):.2f}초")
            print(f"HTML 길이: {len(result.get('content', ''))}")
            
            if result.get('content'):
                print("\n📝 생성된 콘텐츠 미리보기:")
                content_preview = result['content'][:300] + "..." if len(result['content']) > 300 else result['content']
                print(content_preview)
            
            print("\n🎉 API 테스트 성공!")
            return True
        else:
            print(f"❌ API 오류: {response.status_code}")
            print(f"응답: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.")
        return False
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
        return False

if __name__ == "__main__":
    success = test_api()
    exit(0 if success else 1)

