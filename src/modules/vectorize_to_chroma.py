#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
신규 포스트를 청크→임베딩→ChromaDB upsert
"""

import json
import os
import argparse
from pathlib import Path
from typing import List, Dict, Any
from utils_text import split_chunks, normalize_category_name

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("⚠️ ChromaDB가 설치되지 않았습니다. pip install chromadb")

def load_new_docs(jsonl_path: str) -> List[Dict[str, Any]]:
    """JSONL 파일에서 문서 로드"""
    if not os.path.exists(jsonl_path):
        raise FileNotFoundError(f"JSONL 파일을 찾을 수 없습니다: {jsonl_path}")
    
    docs = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                doc = json.loads(line.strip())
                docs.append(doc)
            except json.JSONDecodeError as e:
                print(f"⚠️ 라인 {line_num} JSON 파싱 실패: {e}")
                continue
    
    print(f"📄 {len(docs)}개 문서 로드 완료")
    return docs

def prepare_chunks_for_chroma(docs: List[Dict[str, Any]], run_id: str, source_file: str) -> tuple:
    """
    문서들을 ChromaDB용 청크로 변환
    
    Returns:
        (ids, documents, metadatas) 튜플
    """
    ids = []
    documents = []
    metadatas = []
    
    for doc in docs:
        logno = int(doc.get("logno", doc.get("post_no", 0)))
        content = doc.get("content", "")
        category_no = int(doc.get("category_no", 0))
        
        # 텍스트 청킹 (가이드: 300-600 토큰, 10-20% 오버랩)
        chunks = split_chunks(content, max_tokens=500, overlap=100)
        
        for chunk_idx, chunk_text in enumerate(chunks):
            # 고유 ID 생성: logno:chunk_idx
            chunk_id = f"{logno}:{chunk_idx:03d}"
            
            # 메타데이터 구성 (가이드 스키마)
            metadata = {
                "cat": normalize_category_name(category_no),
                "date": doc.get("published_at", doc.get("posted_at", "")),
                "title": doc.get("title", ""),
                "url": doc.get("url", ""),
                "author": doc.get("author", ""),
                "post_type": "blog_post",
                "logno": logno,
                "chunk_idx": chunk_idx,
                "run_id": run_id,
                "source_file": source_file,
                "category_no": category_no,
                "category_name": normalize_category_name(category_no),
                "content_hash": doc.get("content_hash", ""),
                "chunk_count": len(chunks)
            }
            
            ids.append(chunk_id)
            documents.append(chunk_text)
            metadatas.append(metadata)
    
    print(f"🔧 {len(ids)}개 청크 생성 완료")
    return ids, documents, metadatas

def upsert_to_chroma(ids: List[str], documents: List[str], metadatas: List[Dict], 
                    chroma_path: str, collection_name: str) -> int:
    """ChromaDB에 청크들 upsert"""
    if not CHROMADB_AVAILABLE:
        raise ImportError("ChromaDB가 설치되지 않았습니다.")
    
    # ChromaDB 클라이언트 초기화
    client = chromadb.PersistentClient(
        path=chroma_path,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    
    # 컬렉션 가져오기 또는 생성
    try:
        collection = client.get_collection(collection_name)
        print(f"📚 기존 컬렉션 로드: {collection_name}")
    except Exception as e:
        # E5-base 임베딩 함수 사용 (cosine 거리 + 정규화)
        try:
            import chromadb.utils.embedding_functions as embedding_functions
            embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="intfloat/multilingual-e5-base",
                normalize_embeddings=True
            )
            collection = client.create_collection(
                name=collection_name,
                embedding_function=embedding_function,
                metadata={
                    "description": "네이버 블로그 채권추심 포스트 벡터 저장소",
                    "embedding_model": "intfloat/multilingual-e5-base",
                    "distance_metric": "cosine",
                    "normalize_embeddings": True
                }
            )
            print(f"📚 새 컬렉션 생성: {collection_name} (E5-base 임베딩 함수 사용)")
        except Exception as e2:
            # 기본 임베딩 함수가 없으면 임베딩 함수 없이 생성
            collection = client.create_collection(
                name=collection_name,
                metadata={"description": "네이버 블로그 채권추심 포스트 벡터 저장소"}
            )
            print(f"📚 새 컬렉션 생성: {collection_name} (임베딩 함수 없음)")
    
    # 배치 크기 설정 (메모리 효율성)
    batch_size = 100
    total_upserted = 0
    
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i + batch_size]
        batch_docs = documents[i:i + batch_size]
        batch_metas = metadatas[i:i + batch_size]
        
        try:
            # Upsert 실행
            collection.upsert(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_metas
            )
            total_upserted += len(batch_ids)
            print(f"📤 배치 {i//batch_size + 1}: {len(batch_ids)}개 청크 upsert 완료")
            
        except Exception as e:
            print(f"❌ 배치 {i//batch_size + 1} upsert 실패: {e}")
            # 개별 upsert 시도
            for j, (chunk_id, doc, meta) in enumerate(zip(batch_ids, batch_docs, batch_metas)):
                try:
                    collection.upsert(
                        ids=[chunk_id],
                        documents=[doc],
                        metadatas=[meta]
                    )
                    total_upserted += 1
                except Exception as e2:
                    print(f"❌ 개별 청크 {chunk_id} upsert 실패: {e2}")
    
    print(f"✅ 총 {total_upserted}개 청크 upsert 완료")
    return total_upserted

def verify_chroma_data(collection_name: str, chroma_path: str, run_id: str = None, 
                      source_file: str = None) -> Dict[str, int]:
    """ChromaDB 데이터 검증"""
    if not CHROMADB_AVAILABLE:
        return {}
    
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_collection(collection_name)
    
    verification = {}
    
    # 전체 벡터 수
    total_count = collection.count()
    verification["total_vectors"] = total_count
    
    # run_id별 벡터 수
    if run_id:
        run_results = collection.get(where={"run_id": run_id}, limit=1000000)
        verification[f"run_{run_id}_vectors"] = len(run_results["ids"])
    
    # source_file별 벡터 수
    if source_file:
        file_results = collection.get(where={"source_file": source_file}, limit=1000000)
        verification[f"file_vectors"] = len(file_results["ids"])
    
    # 카테고리별 벡터 수
    category_results = collection.get(where={"category_no": 6}, limit=1000000)  # 채권추심
    verification["category_6_vectors"] = len(category_results["ids"])
    
    return verification

def main():
    parser = argparse.ArgumentParser(description="신규 포스트를 ChromaDB에 벡터화")
    parser.add_argument("--input", required=True, help="신규 포스트 JSONL 파일")
    parser.add_argument("--run-id", required=True, help="실행 ID")
    parser.add_argument("--source-file", required=True, help="원본 스냅샷 파일 경로")
    parser.add_argument("--chroma-path", default="src/data/indexes/chroma", help="ChromaDB 저장 경로")
    parser.add_argument("--collection", default="naver_blog_debt_collection", help="컬렉션 이름")
    parser.add_argument("--verify", action="store_true", help="벡터화 후 검증 실행")
    
    args = parser.parse_args()
    
    if not CHROMADB_AVAILABLE:
        print("❌ ChromaDB가 설치되지 않았습니다.")
        print("설치 명령: pip install chromadb")
        return
    
    try:
        # 1. 문서 로드
        docs = load_new_docs(args.input)
        if not docs:
            print("📝 처리할 문서가 없습니다.")
            return
        
        # 2. 청크 준비
        ids, documents, metadatas = prepare_chunks_for_chroma(
            docs, args.run_id, args.source_file
        )
        
        # 3. ChromaDB upsert
        upserted_count = upsert_to_chroma(
            ids, documents, metadatas, 
            args.chroma_path, args.collection
        )
        
        # 4. 검증
        if args.verify:
            verification = verify_chroma_data(
                args.collection, args.chroma_path, 
                args.run_id, args.source_file
            )
            print(f"\n🔍 검증 결과:")
            for key, value in verification.items():
                print(f"  - {key}: {value}")
        
        print(f"\n🎉 벡터화 완료!")
        print(f"  - 처리된 문서: {len(docs)}개")
        print(f"  - 생성된 청크: {len(ids)}개")
        print(f"  - Upsert된 벡터: {upserted_count}개")
        
    except Exception as e:
        print(f"❌ 벡터화 실패: {e}")
        raise

if __name__ == "__main__":
    main()
