#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기존 ChromaDB 인덱스를 사용하여 실제 데이터와 연동하는 스크립트
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_chromadb_connection():
    """ChromaDB 연결 테스트"""
    try:
        import chromadb
        from chromadb.config import Settings
        
        print("🔍 ChromaDB 연결 테스트 시작...")
        
        # ChromaDB 인덱스 경로
        chroma_path = "src/data/indexes/2025-10-13_0934/chroma"
        
        if not os.path.exists(chroma_path):
            print(f"❌ ChromaDB 인덱스를 찾을 수 없습니다: {chroma_path}")
            return False
        
        # ChromaDB 클라이언트 생성
        client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 컬렉션 목록 확인
        collections = client.list_collections()
        print(f"📋 발견된 컬렉션: {len(collections)}개")
        
        for collection in collections:
            print(f"   - {collection.name}: {collection.count()}개 문서")
        
        # 첫 번째 컬렉션으로 테스트 검색
        if collections:
            test_collection = collections[0]
            print(f"\n🔍 테스트 검색: '{test_collection.name}' 컬렉션")
            
            # 샘플 검색
            results = test_collection.query(
                query_texts=["채권추심 절차"],
                n_results=3
            )
            
            print(f"✅ 검색 결과: {len(results['documents'][0])}개 문서")
            for i, doc in enumerate(results['documents'][0]):
                print(f"   {i+1}. {doc[:100]}...")
            
            return True
        else:
            print("❌ 컬렉션이 없습니다.")
            return False
            
    except ImportError as e:
        print(f"❌ ChromaDB 라이브러리가 설치되지 않았습니다: {e}")
        print("💡 설치 방법: pip install chromadb")
        return False
    except Exception as e:
        print(f"❌ ChromaDB 연결 오류: {e}")
        return False

def update_retriever_to_use_chromadb():
    """retriever.py를 ChromaDB 사용하도록 업데이트"""
    
    retriever_path = "src/search/retriever.py"
    
    if not os.path.exists(retriever_path):
        print(f"❌ retriever.py를 찾을 수 없습니다: {retriever_path}")
        return False
    
    print("🔧 retriever.py를 ChromaDB 사용하도록 업데이트...")
    
    # 현재 retriever.py 내용 읽기
    with open(retriever_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # USE_SIMPLE_STORE = True를 False로 변경
    if "USE_SIMPLE_STORE = True" in content:
        content = content.replace("USE_SIMPLE_STORE = True", "USE_SIMPLE_STORE = False")
        print("✅ USE_SIMPLE_STORE를 False로 변경")
    else:
        print("⚠️ USE_SIMPLE_STORE 설정을 찾을 수 없습니다.")
    
    # 변경된 내용 저장
    with open(retriever_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ retriever.py 업데이트 완료")
    return True

def main():
    print("🚀 실제 ChromaDB 데이터 연동 시작...")
    
    # 1. ChromaDB 연결 테스트
    if not test_chromadb_connection():
        print("❌ ChromaDB 연결에 실패했습니다.")
        return
    
    # 2. retriever.py 업데이트
    if not update_retriever_to_use_chromadb():
        print("❌ retriever.py 업데이트에 실패했습니다.")
        return
    
    print("\n🎉 실제 데이터 연동 완료!")
    print("📋 다음 단계:")
    print("   1. 서버 재시작: uvicorn src.app.main:app --host 0.0.0.0 --port 8000")
    print("   2. 블로그 생성 테스트")
    print("   3. 실제 법률 데이터 기반 RAG 검증")

if __name__ == "__main__":
    main()









