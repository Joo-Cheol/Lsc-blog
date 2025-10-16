# -*- coding: utf-8 -*-
"""
청크 기반 GPU 최적화 벡터화 시스템
문서를 작은 조각으로 분할하여 정밀한 검색 지원
"""
import os
import json
import math
import re
import time
import numpy as np
from pathlib import Path
from typing import Iterable, List, Dict
import torch
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import logging

# ===== 환경 가드 설정 =====
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
torch.set_float32_matmul_precision("high")

# PyTorch 스레드 제한
try:
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
except Exception:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def load_jsonl(path: Path) -> Iterable[Dict]:
    """JSONL 파일을 한 줄씩 읽어서 Dict로 반환"""
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def clean_text(text: str) -> str:
    """텍스트 정리"""
    # 불필요한 공백 제거
    text = re.sub(r'\s+', ' ', text)
    # 특수 문자 정리
    text = re.sub(r'[^\w\s가-힣.,!?;:()]', '', text)
    return text.strip()

def hard_sanitize(s: str, max_chars=4000):
    """텍스트 정제 강화 - 토크나이저 시간폭주 예방"""
    s = s.replace("\x00", " ").replace("\u200b", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s[:max_chars]

def safe_encode(model, texts, *, batch_size=64, normalize=True, device=None, max_retries=2):
    """
    encode()를 절대 안 멈추게 감싸는 헬퍼 함수
    - 배치 내 토큰 폭주/비정상 텍스트가 있어도 배치 쪼개기→개별 샘플 바이너리 서치→최대 길이 강제/로그를 통해 끝까지 전진
    """
    def _call(t):
        return model.encode(
            t, 
            batch_size=min(batch_size, max(1, len(t))),
            convert_to_numpy=True,
            normalize_embeddings=normalize,
            show_progress_bar=False,
        )

    # 텍스트 정제
    texts = [hard_sanitize(t) for t in texts]
    
    # 1) 빠른 시도
    try:
        return _call(texts)
    except Exception as e:
        logger.warning(f"[ENC] batch fail: {type(e).__name__} {e} → fallback split")

    # 2) 절반으로 쪼개며 진행
    out = []
    pending = [texts]
    while pending:
        cur = pending.pop()
        if len(cur) == 1:
            # 3) 단일 샘플도 실패하면 길이/문자 필터링 후 재시도
            s = cur[0]
            s = s.replace("\u200b", " ").replace("\x00", " ")
            if len(s) > 4000:   # tokenizer 시간폭주 방지
                s = s[:4000]
            ok = False
            for _ in range(max_retries + 1):
                try:
                    v = _call([s])[0]
                    out.append(v)
                    ok = True
                    break
                except Exception as e:
                    time.sleep(0.1)
            if not ok:
                # 마지막 안전장치: 영벡터 대체 + 로그
                logger.warning("[ENC] drop one sample due to repeated failure")
                out.append(np.zeros(model.get_sentence_embedding_dimension(), dtype="float32"))
            continue
        mid = len(cur) // 2
        pending.append(cur[:mid])
        pending.append(cur[mid:])
    return np.vstack(out)

def debug_batch_info(texts, batch_idx=0):
    """문제 배치를 즉시 특정하는 디버그 로그 4줄"""
    print(f"[DBG] batch_size={len(texts)}")
    lens = [len(t) for t in texts]
    print(f"[DBG] len(min/med/max)={min(lens)}/{sorted(lens)[len(lens)//2]}/{max(lens)}")
    weirds = [i for i, t in enumerate(texts) if ("\x00" in t) or (len(t) > 8000)]
    print(f"[DBG] suspicious={len(weirds)} at idx(head): {weirds[:3]}")
    print(f"[DBG] sample(text[:200])={(texts[0][:200]).replace(chr(10), ' ')}")

def create_chunks(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
    """텍스트를 청크로 분할"""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # 문장 경계에서 자르기
        if end < len(text):
            # 마지막 문장 부호 찾기
            last_period = text.rfind('.', start, end)
            last_question = text.rfind('?', start, end)
            last_exclamation = text.rfind('!', start, end)
            
            last_sentence = max(last_period, last_question, last_exclamation)
            if last_sentence > start + chunk_size // 2:  # 너무 앞에서 자르지 않도록
                end = last_sentence + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
    
    return chunks

def build_document_chunks(doc: Dict, chunk_size: int = 400) -> List[Dict]:
    """문서를 청크로 분할하여 청크 정보 반환"""
    title = (doc.get("title") or "").strip()
    content = (doc.get("content_text") or "").strip()
    
    # 제목과 본문 결합
    full_text = (title + "\n\n" + content).strip()
    full_text = clean_text(full_text)
    
    if not full_text:
        return []
    
    # 청크 생성
    chunks = create_chunks(full_text, chunk_size)
    
    # 청크 정보 생성
    chunk_docs = []
    original_id = doc.get("id") or doc.get("logno") or doc.get("url", "unknown")
    # URL에서 특수문자 제거하여 안전한 ID 생성
    safe_id = re.sub(r'[^\w\-_]', '_', str(original_id))
    for i, chunk in enumerate(chunks):
        chunk_id = f"{safe_id}_chunk_{i}"
        chunk_docs.append({
            "id": chunk_id,
            "text": chunk,
            "title": title,
            "url": doc.get("url"),
            "category": doc.get("category"),
            "date": doc.get("date"),
            "chunk_index": i,
            "total_chunks": len(chunks),
            "original_id": original_id
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

def main(
    input_jsonl: str,
    chroma_path: str,
    collection_name: str = "naver_blog_debt_collection_chunked",
    model_name: str = "intfloat/multilingual-e5-base",
    batch_size: int = 64,  # 청크가 많아서 배치 크기 줄임
    chunk_size: int = 400,
    max_seq_len: int = 512,
):
    """메인 청크 기반 벡터화 함수"""
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
    print(f"[CHUNK] Creating chunks from {len(docs)} documents...")
    
    all_chunks = []
    for doc in tqdm(docs, desc="Creating chunks"):
        chunks = build_document_chunks(doc, chunk_size)
        all_chunks.extend(chunks)
    
    total_chunks = len(all_chunks)
    print(f"[CHUNK] Created {total_chunks} chunks from {len(docs)} documents")
    
    # 청크 길이 순으로 정렬 (warmup 효과)
    all_chunks.sort(key=lambda c: len(c["text"]))
    print(f"[CHUNK] Sorted chunks by length for warmup effect")

    # 벡터화 및 저장
    done = 0
    
    with torch.inference_mode():
        for batch in tqdm(create_batches(all_chunks, batch_size), total=math.ceil(total_chunks/batch_size), desc="Embedding chunks"):
            ids, texts, metas = [], [], []
            
            for chunk in batch:
                ids.append(chunk["id"])
                texts.append(chunk["text"])
                metas.append({
                    "title": chunk["title"],
                    "url": chunk["url"],
                    "category": chunk["category"],
                    "date": chunk["date"],
                    "chunk_index": chunk["chunk_index"],
                    "total_chunks": chunk["total_chunks"],
                    "original_id": chunk["original_id"]
                })

            if not ids:
                continue

            # 디버그 로그
            debug_batch_info(texts, batch_idx=done//batch_size)
            
            # safe_encode 사용
            embs = safe_encode(model, texts, batch_size=batch_size, normalize=True, device=device)

            col.upsert(ids=ids, embeddings=embs.tolist(), metadatas=metas, documents=texts)
            done += len(ids)

            # 주기적 스냅샷
            if done % (batch_size * 5) == 0:
                client.persist()
                print(f"[SAVE] persisted at {done}/{total_chunks}")

    client.persist()
    print(f"[DONE] upserted {done}/{total_chunks} chunks → collection='{collection_name}' path='{chroma_path}'")

if __name__ == "__main__":
    # 기존 데이터 경로 사용
    input_jsonl = r".\src\data\processed\2025-10-13_0934\posts_all.jsonl"
    chroma_path = r".\src\data\indexes\2025-10-13_0934\chroma"

    # 청크 기반 벡터화
    main(
        input_jsonl=input_jsonl,
        chroma_path=chroma_path,
        collection_name="naver_blog_debt_collection_chunked",
        model_name="intfloat/multilingual-e5-base",
        batch_size=4,
        chunk_size=400,
        max_seq_len=512,
    )
