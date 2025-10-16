#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
법률 문서 백필 인덱싱 스크립트
"""
import json
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, '.')

from simple_vector_store import upsert_docs

def main():
    print("🚀 법률 문서 백필 인덱싱 시작...")
    
    # 샘플 데이터 로드
    corpus_file = "sample_corpus.jsonl"
    if not os.path.exists(corpus_file):
        print(f"❌ {corpus_file} 파일이 없습니다.")
        return False
    
    try:
        with open(corpus_file, "r", encoding="utf-8") as f:
            batch = [json.loads(line) for line in f]
        
        print(f"📚 {len(batch)}개 문서 로드 완료")
        
        # 스키마 검증
        required_fields = ["id", "text", "title", "url", "date", "cat", "author", "post_type"]
        for i, doc in enumerate(batch):
            missing = [field for field in required_fields if field not in doc]
            if missing:
                print(f"❌ 문서 {i+1}에 필수 필드 누락: {missing}")
                return False
        
        print("✅ 스키마 검증 완료")
        
        # 인덱싱 실행
        print("🔄 ChromaDB에 인덱싱 중...")
        upsert_docs(batch)
        
        print("✅ 백필 인덱싱 완료!")
        print(f"📊 인덱싱된 문서: {len(batch)}개")
        print("🔍 이제 검색 API를 테스트할 수 있습니다.")
        
        return True
        
    except Exception as e:
        print(f"❌ 인덱싱 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
