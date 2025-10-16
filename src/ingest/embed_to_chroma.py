# -*- coding: utf-8 -*-
"""
GPU 최적화 벡터화 및 ChromaDB 색인 시스템
RTX 4070 Ti SUPER 16GB + 64GB RAM 최적화
"""
import os
import json
import math
from pathlib import Path
from typing import Iterable, List, Dict
import torch
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

# ===== 하드웨어 최적화 =====
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")   # venv 내에서는 0으로 인식됨(위에서 1을 노출시켰기 때문)
torch.set_float32_matmul_precision("high")

def load_jsonl(path: Path) -> Iterable[Dict]:
    """JSONL 파일을 한 줄씩 읽어서 Dict로 반환"""
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def build_text(doc: Dict) -> str:
    """문서에서 타이틀과 본문을 결합하여 임베딩용 텍스트 생성"""
    title = (doc.get("title") or "").strip()
    content = (doc.get("content_text") or "").strip()
    return (title + "\n\n" + content).strip()

def chunks(it, size):
    """이터레이터를 지정된 크기의 청크로 분할"""
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
    collection_name: str = "naver_blog_debt_collection",
    model_name: str = "intfloat/multilingual-e5-base",
    batch_size: int = 128,
    max_seq_len: int = 512,
):
    """메인 벡터화 및 색인 함수"""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[INFO] device={device}, cuda={torch.cuda.is_available()}, gpu={torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")

    # 모델 로드 (FP16/AMP)
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

    # 중복 방지: 이미 있는 id는 스킵
    existing_ids = set()
    try:
        # 컬렉션 사이즈가 굉장히 크면 전체 fetch는 비추 → 여기선 소규모 가정
        if hasattr(col, "count") and col.count() <= 500_000:
            # 일부 드라이버에서 get doesn't allow fetch all; skip for big sets
            pass
    except Exception:
        pass

    # 문서 로드 및 총 개수 계산
    docs_iter = load_jsonl(Path(input_jsonl))
    total = sum(1 for _ in load_jsonl(Path(input_jsonl)))
    print(f"[LOAD] {total} docs from {input_jsonl}")

    ids, texts, metas = [], [], []
    done = 0

    # AMP로 인퍼런스 가속
    autocast = torch.cuda.amp.autocast if device == "cuda" else torch.cpu.amp.autocast
    with torch.inference_mode():
        for batch in tqdm(chunks(docs_iter, batch_size), total=math.ceil(total/batch_size), desc="Embedding"):
            ids.clear(); texts.clear(); metas.clear()
            for doc in batch:
                _id = str(doc.get("id") or doc.get("logno") or doc.get("url"))
                if not _id:  # id가 없으면 스킵
                    continue
                if _id in existing_ids:
                    continue
                txt = build_text(doc)
                if not txt:
                    continue
                ids.append(_id)
                texts.append(txt)
                metas.append({
                    "title": doc.get("title"),
                    "url": doc.get("url"),
                    "category": doc.get("category"),
                    "date": doc.get("date"),
                })

            if not ids:
                continue

            # OOM 방지를 위한 자동 배치 크기 조정
            try:
                with autocast():
                    embs = model.encode(
                        texts,
                        batch_size=batch_size,             # ST 내부 미니배치와 동일하게 둬도 OK
                        convert_to_numpy=True,
                        normalize_embeddings=True,
                        show_progress_bar=False,
                    )
            except RuntimeError as e:
                if "out of memory" in str(e).lower() and batch_size > 32:
                    torch.cuda.empty_cache()
                    batch_size = max(32, batch_size // 2)
                    print(f"[WARN] OOM → batch_size={batch_size}로 감소 후 재시도")
                    with autocast():
                        embs = model.encode(
                            texts,
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
            if done % (batch_size * 10) == 0:
                client.persist()
                print(f"[SAVE] persisted at {done}/{total}")

    client.persist()
    print(f"[DONE] upserted {done}/{total} → collection='{collection_name}' path='{chroma_path}'")

if __name__ == "__main__":
    # 예) 입력/출력 경로는 날짜-시간 폴더 규칙
    run_id = os.environ.get("RUN_ID", "")
    if not run_id:
        from datetime import datetime
        run_id = datetime.now().strftime("%Y-%m-%d_%H%M")

    # 기존 데이터 경로 사용
    input_jsonl = r".\src\data\processed\2025-10-13_0934\posts_all.jsonl"
    chroma_path = r".\src\data\indexes\2025-10-13_0934\chroma"

    # 빠른 시작용 기본값
    main(
        input_jsonl=input_jsonl,
        chroma_path=chroma_path,
        collection_name="naver_blog_debt_collection",
        model_name="intfloat/multilingual-e5-base",
        batch_size=128,
        max_seq_len=512,
    )

