#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
검색 테스트 스크립트
"""
import sys
sys.path.insert(0, '.')

from simple_vector_store import get_store, retrieve

def main():
    print("🔍 검색 테스트 시작...")
    
    # 스토어 상태 확인
    store = get_store()
    print(f"📊 스토어에 저장된 문서 수: {len(store.documents)}")
    
    if len(store.documents) == 0:
        print("❌ 문서가 없습니다. 백필 인덱싱을 먼저 실행하세요.")
        return False
    
    # 첫 번째 문서 확인
    print(f"📄 첫 번째 문서: {store.documents[0][:100]}...")
    
    # 검색 테스트
    print("🔍 검색 테스트...")
    results = retrieve("지급명령 절차", k=3)
    
    print(f"📊 검색 결과: {len(results)}개")
    for i, result in enumerate(results):
        print(f"  {i+1}. {result['meta'].get('title', 'No title')} (sim: {result['sim']:.4f})")
        print(f"     {result['text'][:100]}...")
    
    return True

if __name__ == "__main__":
    main()






