#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 메모리 기반 벡터 스토어 (ChromaDB 대체)
"""
import json
import numpy as np
import os
from typing import List, Dict, Any
from src.search.embedding import E5Embedder
from src.config.settings import settings

class SimpleVectorStore:
    def __init__(self):
        self.documents = []
        self.embeddings = []
        self.metadatas = []
        self.ids = []
        self.embedder = E5Embedder(settings.EMBED_MODEL)
        
    def upsert(self, ids: List[str], documents: List[str], embeddings: List[List[float]], metadatas: List[Dict]):
        """문서 업서트"""
        for i, doc_id in enumerate(ids):
            if doc_id in self.ids:
                # 기존 문서 업데이트
                idx = self.ids.index(doc_id)
                self.documents[idx] = documents[i]
                self.embeddings[idx] = embeddings[i]
                self.metadatas[idx] = metadatas[i]
            else:
                # 새 문서 추가
                self.ids.append(doc_id)
                self.documents.append(documents[i])
                self.embeddings.append(embeddings[i])
                self.metadatas.append(metadatas[i])
    
    def query(self, query_embeddings: List[List[float]], n_results: int = 5, where: Dict = None) -> Dict:
        """유사도 검색"""
        if not self.documents:
            return {"documents": [[]], "metadatas": [[]], "ids": [[]], "embeddings": [[]]}
        
        query_vec = np.array(query_embeddings[0])
        doc_vecs = np.array(self.embeddings)
        
        # 코사인 유사도 계산
        similarities = np.dot(doc_vecs, query_vec) / (
            np.linalg.norm(doc_vecs, axis=1) * np.linalg.norm(query_vec) + 1e-9
        )
        
        # 상위 n_results개 선택
        top_indices = np.argsort(similarities)[::-1][:n_results]
        
        return {
            "documents": [[self.documents[i] for i in top_indices]],
            "metadatas": [[self.metadatas[i] for i in top_indices]],
            "ids": [[self.ids[i] for i in top_indices]],
            "embeddings": [[self.embeddings[i] for i in top_indices]]
        }

# 전역 스토어 인스턴스
_store = None

def get_store():
    global _store
    if _store is None:
        _store = SimpleVectorStore()
        # 서버 시작 시 자동으로 샘플 데이터 로드
        _load_sample_data()
    return _store

def _load_sample_data():
    """샘플 데이터 자동 로드"""
    try:
        import json
        import os
        
        corpus_file = "sample_corpus.jsonl"
        if os.path.exists(corpus_file):
            with open(corpus_file, "r", encoding="utf-8") as f:
                batch = [json.loads(line) for line in f]
            
            ids = [str(doc["id"]) for doc in batch]
            documents = [doc["text"] for doc in batch]
            metadatas = [{k: v for k, v in doc.items() if k not in ("id", "text")} for doc in batch]
            
            # 임베딩 생성
            embeddings = _store.embedder.encode_passage(documents).tolist()
            
            # 업서트
            _store.upsert(ids, documents, embeddings, metadatas)
            print(f"✅ 서버 시작 시 {len(batch)}개 샘플 문서 자동 로드")
    except Exception as e:
        print(f"⚠️ 샘플 데이터 로드 실패: {e}")

def upsert_docs(docs: List[Dict]):
    """문서 업서트 (ChromaDB 호환 인터페이스)"""
    store = get_store()
    
    ids = [str(doc["id"]) for doc in docs]
    documents = [doc["text"] for doc in docs]
    metadatas = [{k: v for k, v in doc.items() if k not in ("id", "text")} for doc in docs]
    
    # 임베딩 생성
    embeddings = store.embedder.encode_passage(documents).tolist()
    
    # 업서트
    store.upsert(ids, documents, embeddings, metadatas)
    
    print(f"✅ {len(docs)}개 문서 인덱싱 완료")

def retrieve(query: str, where: Dict = None, k: int = 8) -> List[Dict]:
    """검색 (ChromaDB 호환 인터페이스)"""
    store = get_store()
    
    # 쿼리 임베딩
    query_embedding = store.embedder.encode_query([query])
    
    # 검색
    results = store.query([query_embedding[0].tolist()], n_results=k, where=where)
    
    # 결과 변환
    hits = []
    for i, (doc, meta, doc_id, emb) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0], 
        results["ids"][0],
        results["embeddings"][0]
    )):
        # 유사도 계산
        query_vec = query_embedding[0]
        doc_vec = np.array(emb)
        sim = float(np.dot(query_vec, doc_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec) + 1e-9))
        
        hits.append({
            "id": doc_id,
            "text": doc,
            "meta": meta,
            "vec": doc_vec,
            "sim": sim,
            "bm25": 0.0,  # BM25는 일단 0으로 설정
            "bm25_norm": 0.0,
            "combo": sim  # 조합 스코어는 코사인 유사도만 사용
        })
    
    return hits
