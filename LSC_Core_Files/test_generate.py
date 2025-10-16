#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
블로그 생성 테스트 스크립트
"""
import sys
sys.path.insert(0, '.')

from src.llm.services.generator import generate_blog

def main():
    print("🚀 블로그 생성 테스트 시작...")
    
    try:
        # 테스트 데이터
        payload = {
            "topic": "채권추심 지급명령 절차",
            "keywords": "지급명령, 독촉, 집행권원"
        }
        
        print("📝 블로그 생성 중...")
        result = generate_blog(payload)
        
        print("✅ 생성 완료!")
        print(f"📊 Provider: {result.get('provider')}")
        print(f"📊 Topic: {result.get('topic')}")
        print(f"📊 Success: {result.get('success')}")
        print(f"📊 Length: {len(result.get('text', ''))}자")
        print(f"📊 QC Passed: {result.get('qc', {}).get('passed')}")
        print(f"📊 Plag Score: {result.get('plag_score', 0)}")
        print(f"📊 Top Sources: {len(result.get('top_sources', []))}개")
        
        if not result.get('success'):
            print(f"❌ 실패 사유: {result.get('qc', {}).get('reason')}")
        
        # 생성된 텍스트 미리보기
        text = result.get('text', '')
        if text:
            print(f"\n📄 생성된 텍스트 미리보기:")
            print(text[:300] + "..." if len(text) > 300 else text)
        
        return True
        
    except Exception as e:
        print(f"❌ 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()



