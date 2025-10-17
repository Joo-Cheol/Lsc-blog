# -*- coding: utf-8 -*-
"""
고도화된 GPU 최적화 벡터화 시스템
- e5 프리픽스 적용
- 의미 기반 청크링
- SHA256 기반 ID
- 하이브리드 검색 준비
- 자동 평가 시스템
"""
import os
import json
import math
import re
import hashlib
from pathlib import Path
from typing import Iterable, List, Dict, Tuple
import torch
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
from rank_bm25 import BM25Okapi
import numpy as np

# ===== 하드웨어 최적화 =====
torch.set_float32_matmul_precision("high")

def load_jsonl(path: Path) -> Iterable[Dict]:
    """JSONL 파일을 한 줄씩 읽어서 Dict로 반환"""
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def clean_text_advanced(text: str) -> str:
    """고도화된 텍스트 정리"""
    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    
    # 네비게이션/푸터/광고 패턴 제거
    nav_patterns = [
        r'홈\s*>\s*.*?>\s*현재페이지',
        r'이전\s*다음',
        r'목록\s*보기',
        r'더보기\s*펼치기',
        r'공유하기\s*스크랩',
        r'댓글\s*\d+',
        r'조회\s*\d+',
        r'좋아요\s*\d+',
    ]
    
    for pattern in nav_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # 불필요한 공백 정리
    text = re.sub(r'\s+', ' ', text)
    
    # 특수 문자 정리 (법률 용어 보존)
    text = re.sub(r'[^\w\s가-힣.,!?;:()「」『』【】]', '', text)
    
    return text.strip()

def detect_language(text: str) -> str:
    """언어 감지 (간단한 휴리스틱)"""
    korean_chars = len(re.findall(r'[가-힣]', text))
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    
    if korean_chars > english_chars * 2:
        return 'ko'
    elif english_chars > korean_chars * 2:
        return 'en'
    else:
        return 'mixed'

def generate_doc_hash(url: str, clean_text: str) -> str:
    """문서 해시 생성"""
    content = f"{url}|{clean_text}"
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def extract_sections(text: str) -> List[Dict]:
    """제목/소제목 계층 추출"""
    sections = []
    
    # H1, H2, H3 패턴 찾기
    header_patterns = [
        (r'^#\s+(.+)$', 'h1'),
        (r'^##\s+(.+)$', 'h2'),
        (r'^###\s+(.+)$', 'h3'),
        (r'^(.+)\n=+$', 'h1'),
        (r'^(.+)\n-+$', 'h2'),
    ]
    
    lines = text.split('\n')
    for i, line in enumerate(lines):
        for pattern, level in header_patterns:
            match = re.match(pattern, line.strip())
            if match:
                sections.append({
                    'level': level,
                    'title': match.group(1).strip(),
                    'line': i
                })
                break
    
    return sections

def create_semantic_chunks(text: str, chunk_size: int = 400, overlap: int = 50) -> List[Dict]:
    """의미 기반 청크 생성"""
    if len(text) <= chunk_size:
        return [{'text': text, 'start': 0, 'end': len(text), 'section': None}]
    
    # 문장 분할
    sentences = re.split(r'[.!?]\s+', text)
    if not sentences:
        return [{'text': text, 'start': 0, 'end': len(text), 'section': None}]
    
    chunks = []
    current_chunk = ""
    current_start = 0
    current_end = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # 새 청크가 필요한지 확인
        if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
            chunks.append({
                'text': current_chunk.strip(),
                'start': current_start,
                'end': current_end,
                'section': None
            })
            
            # 오버랩 처리
            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
            current_chunk = overlap_text + " " + sentence
            current_start = current_end - len(overlap_text)
        else:
            if current_chunk:
                current_chunk += ". " + sentence
            else:
                current_chunk = sentence
                current_start = current_end
        
        current_end = current_start + len(current_chunk)
    
    # 마지막 청크 추가
    if current_chunk:
        chunks.append({
            'text': current_chunk.strip(),
            'start': current_start,
            'end': current_end,
            'section': None
        })
    
    return chunks

def to_embed_text(chunk: str, is_query: bool = False) -> str:
    """e5 모델용 프리픽스 적용"""
    prefix = "query: " if is_query else "passage: "
    return prefix + chunk.strip()

def build_document_chunks_enhanced(doc: Dict, chunk_size: int = 400) -> List[Dict]:
    """고도화된 문서 청크 생성"""
    title = (doc.get("title") or "").strip()
    content = (doc.get("content") or "").strip()
    
    # 텍스트 정리
    full_text = (title + "\n\n" + content).strip()
    clean_text = clean_text_advanced(full_text)
    
    if not clean_text:
        return []
    
    # 언어 감지
    lang = detect_language(clean_text)
    
    # 문서 해시 생성
    doc_hash = generate_doc_hash(doc.get("url", ""), clean_text)
    
    # 섹션 추출
    sections = extract_sections(clean_text)
    
    # 의미 기반 청크 생성
    chunks = create_semantic_chunks(clean_text, chunk_size)
    
    # 청크 정보 생성
    chunk_docs = []
    original_id = doc.get("id") or doc.get("logno") or doc.get("url", "unknown")
    safe_id = re.sub(r'[^\w\-_]', '_', str(original_id))
    
    for i, chunk in enumerate(chunks):
        chunk_id = hashlib.sha256(f"{doc_hash}-{i}".encode()).hexdigest()
        
        # 임베딩용 텍스트 (e5 프리픽스 적용)
        embed_text = to_embed_text(chunk['text'], is_query=False)
        
        chunk_docs.append({
            "id": chunk_id,
            "text": chunk['text'],
            "embed_text": embed_text,
            "title": title,
            "url": doc.get("url"),
            "category": doc.get("category"),
            "date": doc.get("date"),
            "chunk_index": i,
            "total_chunks": len(chunks),
            "original_id": original_id,
            "doc_hash": doc_hash,
            "lang": lang,
            "section": chunk.get('section'),
            "start_pos": chunk['start'],
            "end_pos": chunk['end']
        })
    
    return chunk_docs

def create_batches(it, size):
    """이터레이터를 지정된 크기의 배치로 분할"""
    buf = []
    for x in it:
        buf.append(x)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf

def build_bm25_index(chunks: List[Dict]) -> BM25Okapi:
    """BM25 인덱스 구축"""
    tokenized_docs = []
    for chunk in chunks:
        # 한국어 토큰화 (간단한 공백 기반)
        tokens = re.findall(r'\w+', chunk['text'].lower())
        tokenized_docs.append(tokens)
    
    return BM25Okapi(tokenized_docs)

def hybrid_search(query: str, vector_results: List, bm25_index: BM25Okapi, chunks: List[Dict], top_k: int = 10) -> List:
    """하이브리드 검색 (BM25 + 벡터)"""
    # BM25 검색
    query_tokens = re.findall(r'\w+', query.lower())
    bm25_scores = bm25_index.get_scores(query_tokens)
    
    # 벡터 결과와 BM25 결과 결합
    combined_results = []
    
    # 벡터 결과에 BM25 점수 추가
    for i, result in enumerate(vector_results):
        if i < len(bm25_scores):
            combined_results.append({
                **result,
                'bm25_score': bm25_scores[i],
                'combined_score': result.get('score', 0) + bm25_scores[i] * 0.3  # 가중치 조정
            })
    
    # 결합 점수로 정렬
    combined_results.sort(key=lambda x: x['combined_score'], reverse=True)
    
    return combined_results[:top_k]

def evaluate_retrieval(collection, test_queries: List[Dict]) -> Dict:
    """검색 성능 평가"""
    results = {
        'recall_at_5': [],
        'recall_at_10': [],
        'precision_at_5': [],
        'precision_at_10': [],
        'mrr': []
    }
    
    for query_data in test_queries:
        query = query_data['query']
        relevant_docs = set(query_data['relevant_docs'])
        
        # 벡터 검색
        search_results = collection.query(
            query_texts=[to_embed_text(query, is_query=True)],
            n_results=10
        )
        
        retrieved_docs = set()
        for i, doc_id in enumerate(search_results['ids'][0]):
            retrieved_docs.add(doc_id)
            
            # Recall@k 계산
            if i < 5:
                results['recall_at_5'].append(len(relevant_docs & retrieved_docs) / len(relevant_docs) if relevant_docs else 0)
            if i < 10:
                results['recall_at_10'].append(len(relevant_docs & retrieved_docs) / len(relevant_docs) if relevant_docs else 0)
        
        # Precision@k 계산
        if len(retrieved_docs) > 0:
            precision_5 = len(relevant_docs & set(search_results['ids'][0][:5])) / 5
            precision_10 = len(relevant_docs & set(search_results['ids'][0][:10])) / 10
            results['precision_at_5'].append(precision_5)
            results['precision_at_10'].append(precision_10)
        
        # MRR 계산
        for i, doc_id in enumerate(search_results['ids'][0]):
            if doc_id in relevant_docs:
                results['mrr'].append(1.0 / (i + 1))
                break
        else:
            results['mrr'].append(0.0)
    
    # 평균 계산
    for metric in results:
        results[metric] = np.mean(results[metric]) if results[metric] else 0.0
    
    return results

def main(
    input_jsonl: str,
    chroma_path: str,
    collection_name: str = "naver_blog_debt_collection_enhanced",
    model_name: str = "intfloat/multilingual-e5-base",
    batch_size: int = 64,
    chunk_size: int = 400,
    max_seq_len: int = 512,
    enable_evaluation: bool = True,
):
    """고도화된 메인 벡터화 함수"""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[INFO] device={device}, cuda={torch.cuda.is_available()}, gpu={torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")

    # 모델 로드
    print(f"[LOAD] Loading model: {model_name}")
    model = SentenceTransformer(
        model_name,
        device=device,
        trust_remote_code=True
    )
    model.max_seq_length = max_seq_len

    # ChromaDB 클라이언트 설정
    print(f"[CHROMA] Initializing ChromaDB at: {chroma_path}")
    client = chromadb.PersistentClient(path=chroma_path, settings=Settings(anonymized_telemetry=False))
    col = client.get_or_create_collection(name=collection_name, metadata={"hnsw:space":"cosine"})

    # 문서 로드 및 청크 생성
    print(f"[LOAD] Loading documents from: {input_jsonl}")
    docs = list(load_jsonl(Path(input_jsonl)))
    print(f"[CHUNK] Creating enhanced chunks from {len(docs)} documents...")
    
    all_chunks = []
    for doc in tqdm(docs, desc="Creating enhanced chunks"):
        chunks = build_document_chunks_enhanced(doc, chunk_size)
        all_chunks.extend(chunks)
    
    total_chunks = len(all_chunks)
    print(f"[CHUNK] Created {total_chunks} enhanced chunks from {len(docs)} documents")

    # BM25 인덱스 구축
    print(f"[BM25] Building BM25 index...")
    bm25_index = build_bm25_index(all_chunks)

    # 벡터화 및 저장
    done = 0
    
    with torch.inference_mode():
        for batch in tqdm(create_batches(all_chunks, batch_size), total=math.ceil(total_chunks/batch_size), desc="Embedding enhanced chunks"):
            ids, texts, embed_texts, metas = [], [], [], []
            
            for chunk in batch:
                ids.append(chunk["id"])
                texts.append(chunk["text"])
                embed_texts.append(chunk["embed_text"])  # e5 프리픽스 적용된 텍스트
                metas.append({
                    "title": chunk["title"],
                    "url": chunk["url"],
                    "category": chunk["category"],
                    "date": chunk["date"],
                    "chunk_index": chunk["chunk_index"],
                    "total_chunks": chunk["total_chunks"],
                    "original_id": chunk["original_id"],
                    "doc_hash": chunk["doc_hash"],
                    "lang": chunk["lang"],
                    "section": chunk.get("section"),
                    "start_pos": chunk["start_pos"],
                    "end_pos": chunk["end_pos"]
                })

            if not ids:
                continue

            # OOM 방지를 위한 자동 배치 크기 조정
            try:
                with torch.amp.autocast('cuda' if device == "cuda" else 'cpu'):
                    embs = model.encode(
                        embed_texts,  # e5 프리픽스 적용된 텍스트 사용
                        batch_size=batch_size,
                        convert_to_numpy=True,
                        normalize_embeddings=True,
                        show_progress_bar=False,
                    )
            except RuntimeError as e:
                if "out of memory" in str(e).lower() and batch_size > 16:
                    torch.cuda.empty_cache()
                    batch_size = max(16, batch_size // 2)
                    print(f"[WARN] OOM → batch_size={batch_size}로 감소 후 재시도")
                    with torch.amp.autocast('cuda' if device == "cuda" else 'cpu'):
                        embs = model.encode(
                            embed_texts,
                            batch_size=batch_size,
                            convert_to_numpy=True,
                            normalize_embeddings=True,
                            show_progress_bar=False,
                        )
                else:
                    raise

            col.upsert(ids=ids, embeddings=embs.tolist(), metadatas=metas, documents=texts)
            done += len(ids)

            # 주기적 스냅샷
            if done % (batch_size * 5) == 0:
                client.persist()
                print(f"[SAVE] persisted at {done}/{total_chunks}")

    client.persist()
    print(f"[DONE] upserted {done}/{total_chunks} enhanced chunks → collection='{collection_name}' path='{chroma_path}'")

    # 평가 실행
    if enable_evaluation:
        print(f"[EVAL] Running evaluation...")
        test_queries = [
            {
                "query": "채권추심 지급명령 절차",
                "relevant_docs": []  # 실제로는 정답 문서 ID들
            },
            {
                "query": "미수금 회수 방법",
                "relevant_docs": []
            }
        ]
        
        eval_results = evaluate_retrieval(col, test_queries)
        print(f"[EVAL] Results: {eval_results}")

    # 하이브리드 검색 테스트
    print(f"[TEST] Testing hybrid search...")
    test_query = "채권추심 지급명령 절차와 준비서류"
    
    # 벡터 검색
    vector_results = col.query(
        query_texts=[to_embed_text(test_query, is_query=True)],
        n_results=20
    )
    
    # 하이브리드 검색
    hybrid_results = hybrid_search(test_query, vector_results, bm25_index, all_chunks, top_k=10)
    
    print(f"[TEST] Hybrid search results:")
    for i, result in enumerate(hybrid_results[:3]):
        print(f"  {i+1}. {result.get('title', 'N/A')[:50]}... (score: {result.get('combined_score', 0):.3f})")

if __name__ == "__main__":
    # 기존 데이터 경로 사용
    input_jsonl = r".\src\data\processed\2025-10-13_0934\posts_all.jsonl"
    chroma_path = r".\src\data\indexes\2025-10-13_0934\chroma"

    # 고도화된 벡터화
    main(
        input_jsonl=input_jsonl,
        chroma_path=chroma_path,
        collection_name="naver_blog_debt_collection_enhanced",
        model_name="intfloat/multilingual-e5-base",
        batch_size=64,
        chunk_size=400,
        max_seq_len=512,
        enable_evaluation=True,
    )














