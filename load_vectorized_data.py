#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기존 벡터화된 데이터를 SimpleVectorStore에 로드하는 스크립트
"""
import json
import numpy as np
import os
import glob
from typing import List, Dict, Any
from simple_vector_store import get_store, upsert_docs

def load_vectorized_data():
    """벡터화된 데이터를 로드하여 벡터 스토어에 저장"""
    
    print("🚀 벡터화된 데이터 로딩 시작...")
    
    # JSON 파일들 (청크된 텍스트)
    json_files = glob.glob("embedding_output/docs_batch_*.json")
    json_files.sort(key=lambda x: int(x.split('_')[-1].split('.')[0]))
    
    # NPY 파일들 (벡터 임베딩)
    npy_files = glob.glob("embedding_output/embeddings_batch_*.npy")
    npy_files.sort(key=lambda x: int(x.split('_')[-1].split('.')[0]))
    
    print(f"📁 발견된 파일:")
    print(f"   - JSON 파일: {len(json_files)}개")
    print(f"   - NPY 파일: {len(npy_files)}개")
    
    all_documents = []
    all_embeddings = []
    all_metadatas = []
    all_ids = []
    
    # 배치별로 데이터 로드
    for i, (json_file, npy_file) in enumerate(zip(json_files, npy_files)):
        try:
            # 텍스트 청크 로드
            with open(json_file, 'r', encoding='utf-8') as f:
                texts = json.load(f)
            
            # 벡터 임베딩 로드
            embeddings = np.load(npy_file)
            
            print(f"📦 배치 {i+1}/{len(json_files)}: {len(texts)}개 청크, {embeddings.shape[0]}개 벡터")
            
            # 각 청크에 대해 메타데이터 생성
            for j, text in enumerate(texts):
                if j < len(embeddings):  # 벡터가 있는 경우만
                    doc_id = f"real_chunk_{i}_{j}"
                    
                    all_documents.append(text)
                    all_embeddings.append(embeddings[j].tolist())
                    all_metadatas.append({
                        "batch": i,
                        "chunk": j,
                        "source": "real_crawled_data",
                        "type": "legal_content"
                    })
                    all_ids.append(doc_id)
            
        except Exception as e:
            print(f"❌ 배치 {i} 로딩 오류: {e}")
            continue
    
    print(f"✅ 총 로드된 데이터:")
    print(f"   - 문서: {len(all_documents)}개")
    print(f"   - 임베딩: {len(all_embeddings)}개")
    print(f"   - 메타데이터: {len(all_metadatas)}개")
    
    # 벡터 스토어에 저장
    print("💾 벡터 스토어에 저장 중...")
    
    store = get_store()
    store.upsert(all_ids, all_documents, all_embeddings, all_metadatas)
    
    print("🎉 벡터화된 데이터 로딩 완료!")
    
    # 샘플 검색 테스트
    print("\n🔍 검색 테스트...")
    test_queries = [
        "채권추심 절차",
        "지급명령 신청",
        "독촉장 발송",
        "강제집행 방법"
    ]
    
    for query in test_queries:
        results = store.query(
            [store.embedder.encode_query([query])[0].tolist()], 
            n_results=3
        )
        print(f"\n📋 쿼리: '{query}'")
        for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
            print(f"   {i+1}. {doc[:100]}... (배치: {meta.get('batch', 'N/A')})")

def main():
    load_vectorized_data()

if __name__ == "__main__":
    main()






