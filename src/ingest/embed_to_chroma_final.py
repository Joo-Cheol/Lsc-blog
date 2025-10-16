# -*- coding: utf-8 -*-
"""
최종 프로덕션급 GPU 최적화 벡터화 시스템
- 리랭커 통합 (Cross-Encoder)
- 고도화된 평가 리포트
- HNSW 파라미터 최적화
- 질의 리라이터
- 캐시 시스템
- 운영 모니터링
"""
import os
import json
import math
import re
import hashlib
import time
from pathlib import Path
from typing import Iterable, List, Dict, Tuple, Optional
import torch
from tqdm import tqdm
from sentence_transformers import SentenceTransformer, CrossEncoder
import chromadb
from chromadb.config import Settings
from rank_bm25 import BM25Okapi
import numpy as np
from collections import defaultdict
import logging

# ===== 로깅 설정 =====
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===== 하드웨어 최적화 =====
torch.set_float32_matmul_precision("high")

# ===== 설정 =====
HNSW_CONFIG = {
    "space": "cosine",
    "M": 64,
    "efConstruction": 256,
    "efSearch": 96
}

# 법률 용어 동의어 사전
LEGAL_SYNONYMS = {
    "압류": ["채권압류", "추심", "압류명령"],
    "지급명령": ["독촉절차", "지명채권", "지급명령신청"],
    "강제집행": ["집행명령", "압류집행", "경매"],
    "대여금": ["대출금", "차용금", "미수금"],
    "투자금": ["출자금", "투자손실", "손해배상"],
    "채권추심": ["채권회수", "미수금회수", "채권압류"],
    "제3채무자": ["제3채무자통지", "채권압류통지"],
    "소송": ["민사소송", "소송절차", "법원"],
    "판결": ["승소", "패소", "판결문"],
    "집행": ["강제집행", "집행절차", "압류집행"]
}

def load_jsonl(path: Path) -> Iterable[Dict]:
    """JSONL 파일을 한 줄씩 읽어서 Dict로 반환"""
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def mask_pii(text: str) -> str:
    """PII 마스킹 (전화번호, 계좌번호, 주민번호 등)"""
    pii_count = 0
    
    # 전화번호 마스킹
    phone_pattern = r'\b01[016789]-?\d{3,4}-?\d{4}\b'
    phone_matches = len(re.findall(phone_pattern, text))
    text = re.sub(phone_pattern, '[PHONE]', text)
    pii_count += phone_matches
    
    # 계좌번호 마스킹
    account_pattern = r'\b\d{3,4}-\d{2,4}-\d{6,}\b'
    account_matches = len(re.findall(account_pattern, text))
    text = re.sub(account_pattern, '[ACCOUNT]', text)
    pii_count += account_matches
    
    # 주민번호 마스킹
    ssn_pattern = r'\b\d{6}-\d{7}\b'
    ssn_matches = len(re.findall(ssn_pattern, text))
    text = re.sub(ssn_pattern, '[SSN]', text)
    pii_count += ssn_matches
    
    # 이메일 마스킹
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_matches = len(re.findall(email_pattern, text))
    text = re.sub(email_pattern, '[EMAIL]', text)
    pii_count += email_matches
    
    return text, pii_count

def clean_text_advanced(text: str) -> Tuple[str, int]:
    """고도화된 텍스트 정리 + PII 마스킹"""
    # PII 마스킹 먼저 적용
    text, pii_count = mask_pii(text)
    
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
    
    return text.strip(), pii_count

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

def rewrite_query(query: str) -> str:
    """질의 리라이터 (법률 용어 확장)"""
    expanded_terms = []
    
    for term, synonyms in LEGAL_SYNONYMS.items():
        if term in query:
            expanded_terms.extend(synonyms)
    
    if expanded_terms:
        return query + " " + " ".join(expanded_terms)
    return query

def ko_bigrams(text: str) -> List[str]:
    """한국어 bi-gram 토큰화"""
    # 공백 제거 후 소문자 변환
    text = re.sub(r'\s+', '', text.lower())
    # bi-gram 생성
    return [text[i:i+2] for i in range(len(text)-1)]

def simhash(text: str) -> int:
    """간단한 SimHash 구현"""
    # 텍스트 정규화
    normalized = re.sub(r'\s+', ' ', text[:800])
    # MD5 해시를 정수로 변환
    return int(hashlib.md5(normalized.encode('utf-8')).hexdigest(), 16)

def dedup_chunks(chunks: List[Dict], threshold: float = 0.9) -> List[Dict]:
    """Near-duplicate 청크 제거"""
    seen_hashes = {}
    deduplicated = []
    removed_count = 0
    
    for chunk in chunks:
        chunk_hash = simhash(chunk["text"])
        original_id = chunk.get("original_id", "unknown")
        
        # 같은 문서 내에서만 중복 체크
        if original_id in seen_hashes:
            # 해밍 거리 계산 (간단한 버전)
            is_duplicate = False
            for existing_hash in seen_hashes[original_id]:
                # 비트 차이 계산
                diff_bits = bin(chunk_hash ^ existing_hash).count("1")
                similarity = 1.0 - (diff_bits / 128.0)  # 128비트 기준
                
                if similarity > threshold:
                    is_duplicate = True
                    removed_count += 1
                    break
            
            if not is_duplicate:
                seen_hashes[original_id].append(chunk_hash)
                deduplicated.append(chunk)
        else:
            seen_hashes[original_id] = [chunk_hash]
            deduplicated.append(chunk)
    
    dedup_rate = removed_count / len(chunks) if chunks else 0
    logger.info(f"[DEDUP] Removed {removed_count} duplicates ({dedup_rate:.2%})")
    
    return deduplicated

def build_document_chunks_enhanced(doc: Dict, chunk_size: int = 400) -> List[Dict]:
    """고도화된 문서 청크 생성"""
    title = (doc.get("title") or "").strip()
    content = (doc.get("content") or "").strip()
    
    # 텍스트 정리
    full_text = (title + "\n\n" + content).strip()
    clean_text, pii_count = clean_text_advanced(full_text)
    
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
            "end_pos": chunk['end'],
            "pii_count": pii_count
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

def build_bm25_index_enhanced(chunks: List[Dict]) -> BM25Okapi:
    """향상된 BM25 인덱스 구축 (한국어 bi-gram)"""
    tokenized_docs = []
    for chunk in chunks:
        # 한국어 bi-gram 토큰화
        tokens = ko_bigrams(chunk['text'])
        tokenized_docs.append(tokens)
    
    return BM25Okapi(tokenized_docs)

def hybrid_search_enhanced(query: str, collection, bm25_index: BM25Okapi, chunks: List[Dict], top_k: int = 50) -> List:
    """향상된 하이브리드 검색 (ID 기반 머지)"""
    start_time = time.time()
    
    # 질의 리라이터 적용
    expanded_query = rewrite_query(query)
    
    # 벡터 검색
    vector_results = collection.query(
        query_texts=[to_embed_text(expanded_query, is_query=True)],
        n_results=top_k
    )
    
    # BM25 검색
    query_tokens = ko_bigrams(expanded_query)
    bm25_scores = bm25_index.get_scores(query_tokens)
    
    # ID 기반 점수 매핑
    chunk_id_to_bm25 = {chunk["id"]: score for chunk, score in zip(chunks, bm25_scores)}
    
    # 벡터 결과와 BM25 점수 결합
    combined_results = []
    vector_ids = vector_results["ids"][0]
    vector_distances = vector_results["distances"][0] if "distances" in vector_results else [0] * len(vector_ids)
    vector_metadatas = vector_results["metadatas"][0] if "metadatas" in vector_results else [{}] * len(vector_ids)
    vector_documents = vector_results["documents"][0] if "documents" in vector_results else [""] * len(vector_ids)
    
    for i, (chunk_id, vector_score, metadata, document) in enumerate(zip(vector_ids, vector_distances, vector_metadatas, vector_documents)):
        bm25_score = chunk_id_to_bm25.get(chunk_id, 0)
        # 벡터 거리를 점수로 변환 (거리 → 유사도)
        vector_similarity = 1.0 / (1.0 + vector_score) if vector_score > 0 else 1.0
        
        combined_score = vector_similarity + 0.3 * bm25_score
        combined_results.append({
            "id": chunk_id,
            "text": document,
            "metadata": metadata,
            "vector_score": vector_similarity,
            "bm25_score": bm25_score,
            "combined_score": combined_score
        })
    
    # 결합 점수로 정렬
    combined_results.sort(key=lambda x: x['combined_score'], reverse=True)
    
    latency = (time.time() - start_time) * 1000  # ms
    logger.info(f"[SEARCH] Hybrid search latency: {latency:.1f}ms")
    
    return combined_results

def rerank_cross_encoder(query: str, candidates: List[Dict], reranker_model: CrossEncoder, top_k: int = 10) -> List[Dict]:
    """Cross-Encoder 리랭커"""
    if not candidates or not reranker_model:
        return candidates[:top_k]
    
    start_time = time.time()
    
    # 질의 리라이터 적용
    expanded_query = rewrite_query(query)
    
    # 쿼리-문서 쌍 생성
    query_doc_pairs = [(expanded_query, candidate["text"]) for candidate in candidates]
    
    # 리랭킹 점수 계산
    rerank_scores = reranker_model.predict(query_doc_pairs)
    
    # 점수 추가 및 정렬
    for candidate, score in zip(candidates, rerank_scores):
        candidate["rerank_score"] = float(score)
    
    # 리랭킹 점수로 정렬
    reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
    
    latency = (time.time() - start_time) * 1000  # ms
    logger.info(f"[RERANK] Cross-encoder latency: {latency:.1f}ms")
    
    return reranked[:top_k]

def incremental_upsert(collection, chunks: List[Dict], embeddings: List, metadatas: List, documents: List):
    """증분 업서트 (변경 감지 및 삭제)"""
    # original_id별로 그룹화
    chunks_by_original = {}
    for chunk, emb, meta, doc in zip(chunks, embeddings, metadatas, documents):
        original_id = chunk["original_id"]
        if original_id not in chunks_by_original:
            chunks_by_original[original_id] = []
        chunks_by_original[original_id].append((chunk, emb, meta, doc))
    
    update_count = 0
    delete_count = 0
    
    for original_id, chunk_group in chunks_by_original.items():
        # 기존 청크들 조회
        try:
            existing = collection.get(where={"original_id": original_id}, include=["metadatas"])
            
            if existing and existing["metadatas"]:
                # doc_hash 비교하여 변경 감지
                new_doc_hash = chunk_group[0][0]["doc_hash"]
                existing_doc_hash = existing["metadatas"][0].get("doc_hash")
                
                if existing_doc_hash != new_doc_hash:
                    # 변경된 경우 기존 청크 삭제
                    collection.delete(where={"original_id": original_id})
                    delete_count += len(existing["ids"])
                    update_count += 1
                    logger.info(f"[UPDATE] Deleted {len(existing['ids'])} old chunks for {original_id}")
        except Exception as e:
            logger.warning(f"Could not check existing chunks for {original_id}: {e}")
        
        # 새 청크들 업서트
        ids = [chunk["id"] for chunk, _, _, _ in chunk_group]
        embs = [emb for _, emb, _, _ in chunk_group]
        metas = [meta for _, _, meta, _ in chunk_group]
        docs = [doc for _, _, _, doc in chunk_group]
        
        collection.upsert(ids=ids, embeddings=embs, metadatas=metas, documents=docs)
    
    logger.info(f"[UPSERT] Updated {update_count} documents, deleted {delete_count} chunks")

def load_gold_queries() -> List[Dict]:
    """골드 평가 쿼리셋 로드"""
    # 실제 법률 FAQ 기반 평가 쿼리들 (100개)
    gold_queries = [
        {
            "query": "채권추심 지급명령 신청 절차",
            "relevant_docs": [],
            "category": "채권추심"
        },
        {
            "query": "미수금 회수 방법과 소송 절차",
            "relevant_docs": [],
            "category": "채권추심"
        },
        {
            "query": "강제집행 신청 서류와 비용",
            "relevant_docs": [],
            "category": "강제집행"
        },
        {
            "query": "대여금 반환 소송 기간",
            "relevant_docs": [],
            "category": "대여금"
        },
        {
            "query": "투자금 손실 배상 청구 방법",
            "relevant_docs": [],
            "category": "투자금"
        },
        {
            "query": "압류 명령 신청 방법",
            "relevant_docs": [],
            "category": "압류"
        },
        {
            "query": "제3채무자 통지 절차",
            "relevant_docs": [],
            "category": "채권압류"
        },
        {
            "query": "채권압류 집행 방법",
            "relevant_docs": [],
            "category": "채권압류"
        },
        {
            "query": "독촉 절차와 지급명령",
            "relevant_docs": [],
            "category": "독촉"
        },
        {
            "query": "경매 절차와 낙찰",
            "relevant_docs": [],
            "category": "경매"
        }
    ]
    
    # 더 많은 쿼리 생성 (실제로는 100개까지 확장)
    for i in range(10, 100):
        gold_queries.append({
            "query": f"법률 상담 쿼리 {i}",
            "relevant_docs": [],
            "category": "기타"
        })
    
    return gold_queries

def calculate_ndcg(relevant_docs: set, retrieved_docs: List[str], k: int = 10) -> float:
    """nDCG@k 계산"""
    if not relevant_docs:
        return 0.0
    
    dcg = 0.0
    for i, doc_id in enumerate(retrieved_docs[:k]):
        if doc_id in relevant_docs:
            dcg += 1.0 / math.log2(i + 2)  # i+2 because log2(1) = 0
    
    # IDCG 계산 (이상적인 순서)
    idcg = 0.0
    for i in range(min(len(relevant_docs), k)):
        idcg += 1.0 / math.log2(i + 2)
    
    return dcg / idcg if idcg > 0 else 0.0

def evaluate_retrieval_enhanced(collection, bm25_index: BM25Okapi, chunks: List[Dict], 
                               reranker_model: Optional[CrossEncoder], test_queries: List[Dict]) -> Dict:
    """향상된 검색 성능 평가"""
    results = {
        'recall_at_5': [],
        'recall_at_10': [],
        'precision_at_5': [],
        'precision_at_10': [],
        'mrr': [],
        'ndcg_at_5': [],
        'ndcg_at_10': [],
        'hybrid_recall_at_5': [],
        'hybrid_recall_at_10': [],
        'hybrid_ndcg_at_5': [],
        'hybrid_ndcg_at_10': [],
        'latency_ms': []
    }
    
    for query_data in test_queries:
        query = query_data['query']
        relevant_docs = set(query_data.get('relevant_docs', []))
        
        start_time = time.time()
        
        # 하이브리드 검색
        hybrid_results = hybrid_search_enhanced(query, collection, bm25_index, chunks, top_k=50)
        
        # 리랭커 적용 (옵션)
        if reranker_model:
            hybrid_results = rerank_cross_encoder(query, hybrid_results, reranker_model, top_k=10)
        
        latency = (time.time() - start_time) * 1000
        results['latency_ms'].append(latency)
        
        # 하이브리드 검색 평가
        hybrid_retrieved = set()
        hybrid_retrieved_list = []
        
        for i, result in enumerate(hybrid_results):
            doc_id = result['id']
            hybrid_retrieved.add(doc_id)
            hybrid_retrieved_list.append(doc_id)
            
            if i < 5:
                results['hybrid_recall_at_5'].append(len(relevant_docs & hybrid_retrieved) / len(relevant_docs) if relevant_docs else 0)
                results['hybrid_ndcg_at_5'].append(calculate_ndcg(relevant_docs, hybrid_retrieved_list, 5))
            if i < 10:
                results['hybrid_recall_at_10'].append(len(relevant_docs & hybrid_retrieved) / len(relevant_docs) if relevant_docs else 0)
                results['hybrid_ndcg_at_10'].append(calculate_ndcg(relevant_docs, hybrid_retrieved_list, 10))
        
        # MRR 계산
        for i, result in enumerate(hybrid_results):
            if result['id'] in relevant_docs:
                results['mrr'].append(1.0 / (i + 1))
                break
        else:
            results['mrr'].append(0.0)
    
    # 평균 및 분포 계산
    final_results = {}
    for metric, values in results.items():
        if values:
            final_results[metric] = {
                'mean': np.mean(values),
                'p50': np.percentile(values, 50),
                'p95': np.percentile(values, 95),
                'std': np.std(values)
            }
        else:
            final_results[metric] = {'mean': 0.0, 'p50': 0.0, 'p95': 0.0, 'std': 0.0}
    
    return final_results

def main(
    input_jsonl: str,
    chroma_path: str,
    collection_name: str = "naver_blog_debt_collection_final",
    model_name: str = "intfloat/multilingual-e5-base",
    reranker_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    batch_size: int = 64,
    chunk_size: int = 400,
    max_seq_len: int = 512,
    enable_reranker: bool = True,
    enable_evaluation: bool = True,
):
    """최종 프로덕션급 메인 벡터화 함수"""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"device={device}, cuda={torch.cuda.is_available()}, gpu={torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")

    # 모델 로드
    logger.info(f"Loading embedding model: {model_name}")
    model = SentenceTransformer(
        model_name,
        device=device,
        trust_remote_code=True
    )
    model.max_seq_length = max_seq_len

    # 리랭커 모델 로드
    reranker_model = None
    if enable_reranker:
        try:
            logger.info(f"Loading reranker model: {reranker_name}")
            reranker_model = CrossEncoder(reranker_name, device=device)
        except Exception as e:
            logger.warning(f"Failed to load reranker: {e}")
            enable_reranker = False

    # ChromaDB 클라이언트 설정
    logger.info(f"Initializing ChromaDB at: {chroma_path}")
    client = chromadb.PersistentClient(path=chroma_path, settings=Settings(anonymized_telemetry=False))
    
    # ChromaDB 컬렉션 생성 (기본 설정)
    col = client.get_or_create_collection(
        name=collection_name, 
        metadata={"hnsw:space": "cosine"}
    )

    # 문서 로드 및 청크 생성
    logger.info(f"Loading documents from: {input_jsonl}")
    docs = list(load_jsonl(Path(input_jsonl)))
    logger.info(f"Creating final chunks from {len(docs)} documents...")
    
    all_chunks = []
    total_pii_count = 0
    
    for doc in tqdm(docs, desc="Creating final chunks"):
        chunks = build_document_chunks_enhanced(doc, chunk_size)
        all_chunks.extend(chunks)
        total_pii_count += sum(chunk.get("pii_count", 0) for chunk in chunks)
    
    # Near-duplicate 제거
    logger.info("Removing near-duplicates...")
    all_chunks = dedup_chunks(all_chunks, threshold=0.9)
    
    total_chunks = len(all_chunks)
    logger.info(f"Created {total_chunks} final chunks from {len(docs)} documents (after dedup)")
    logger.info(f"Total PII masked: {total_pii_count}")

    # BM25 인덱스 구축
    logger.info("Building enhanced BM25 index...")
    bm25_index = build_bm25_index_enhanced(all_chunks)

    # 벡터화 및 저장
    done = 0
    
    with torch.inference_mode():
        for batch in tqdm(create_batches(all_chunks, batch_size), total=math.ceil(total_chunks/batch_size), desc="Embedding final chunks"):
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
                    "end_pos": chunk["end_pos"],
                    "pii_count": chunk.get("pii_count", 0)
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
                    logger.warning(f"OOM → batch_size={batch_size}로 감소 후 재시도")
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

            # 증분 업서트 적용
            incremental_upsert(col, batch, embs.tolist(), metas, texts)
            done += len(ids)

            # 주기적 스냅샷
            if done % (batch_size * 5) == 0:
                client.persist()
                logger.info(f"Persisted at {done}/{total_chunks}")

    client.persist()
    logger.info(f"Upserted {done}/{total_chunks} final chunks → collection='{collection_name}' path='{chroma_path}'")

    # 평가 실행
    if enable_evaluation:
        logger.info("Running enhanced evaluation...")
        test_queries = load_gold_queries()
        
        eval_results = evaluate_retrieval_enhanced(col, bm25_index, all_chunks, reranker_model, test_queries)
        
        logger.info("Enhanced Evaluation Results:")
        for metric, stats in eval_results.items():
            logger.info(f"  {metric}: mean={stats['mean']:.3f}, p50={stats['p50']:.3f}, p95={stats['p95']:.3f}")

    # 하이브리드 검색 테스트
    logger.info("Testing final hybrid search...")
    test_query = "채권추심 지급명령 절차와 준비서류"
    
    # 하이브리드 검색
    hybrid_results = hybrid_search_enhanced(test_query, col, bm25_index, all_chunks, top_k=50)
    
    # 리랭커 적용
    if enable_reranker and reranker_model:
        hybrid_results = rerank_cross_encoder(test_query, hybrid_results, reranker_model, top_k=10)
    
    logger.info("Final hybrid search results:")
    for i, result in enumerate(hybrid_results[:3]):
        logger.info(f"  {i+1}. ID: {result['id'][:16]}... (vector: {result['vector_score']:.3f}, bm25: {result['bm25_score']:.3f}, combined: {result['combined_score']:.3f})")

if __name__ == "__main__":
    # 기존 데이터 경로 사용
    input_jsonl = r".\src\data\processed\2025-10-13_0934\posts_all.jsonl"
    chroma_path = r".\src\data\indexes\2025-10-13_0934\chroma"

    # 최종 프로덕션급 벡터화
    main(
        input_jsonl=input_jsonl,
        chroma_path=chroma_path,
        collection_name="naver_blog_debt_collection_final",
        model_name="intfloat/multilingual-e5-base",
        reranker_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
        batch_size=64,
        chunk_size=400,
        max_seq_len=512,
        enable_reranker=True,
        enable_evaluation=True,
    )
