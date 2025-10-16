from typing import List, Tuple, Optional, Dict, Any
import numpy as np, math
from src.search.embedding import E5Embedder
# ChromaDB 대신 간단한 벡터 스토어 사용
try:
    from simple_vector_store import retrieve as simple_retrieve
    USE_SIMPLE_STORE = True
except ImportError:
    from src.search.store import get_collection
    USE_SIMPLE_STORE = False
from src.config.settings import settings

# 하이브리드 검색 (BM25 + 벡터)
try:
    from .hybrid_retriever import hybrid_search
    HYBRID_ENABLED = True
except ImportError:
    HYBRID_ENABLED = False

try:
    from rank_bm25 import BM25Okapi
except Exception:
    BM25Okapi = None  # 선택

def cosine(a, b): 
    return float(np.dot(a, b) / (np.linalg.norm(a)*np.linalg.norm(b) + 1e-9))

def mmr_select(query_vec, cand_vecs, lambda_div=0.7, topk=8):
    selected, remaining = [], list(range(len(cand_vecs)))
    if not remaining: return []
    # 1st: 최고 유사도 후보
    sims = [cosine(query_vec, v) for v in cand_vecs]
    selected.append(int(np.argmax(sims))); remaining.remove(selected[0])
    while len(selected) < min(topk, len(cand_vecs)):
        best_i, best_score = None, -1e9
        for i in remaining:
            rel = cosine(query_vec, cand_vecs[i])
            div = max(cosine(cand_vecs[i], cand_vecs[j]) for j in selected) if selected else 0
            score = lambda_div*rel - (1-lambda_div)*div
            if score > best_score: best_i, best_score = i, score
        selected.append(best_i); remaining.remove(best_i)
    return selected

def retrieve(query: str, where: dict|None=None, k: int|None=None, use_hybrid: bool = True) -> List[dict]:
    k = k or settings.RETRIEVAL_K
    
    # 하이브리드 검색 사용 (BM25 + 벡터)
    if use_hybrid and HYBRID_ENABLED:
        try:
            return hybrid_search(query, where, k)
        except Exception as e:
            print(f"⚠️ 하이브리드 검색 실패, 벡터 검색으로 폴백: {e}")
    
    # 간단한 벡터 스토어 사용
    if USE_SIMPLE_STORE:
        return simple_retrieve(query, where, k)
    
    # ChromaDB 사용 (기존 코드)
    col = get_collection()
    em = E5Embedder(settings.EMBED_MODEL)
    qv = em.encode_query([query])[0]

    # 1) 벡터 후보(최종 k의 ≥3배)
    cand = max(k*settings.CAND_MULTIPLIER, k)
    rr = col.query(
        query_embeddings=[qv.tolist()],
        n_results=cand,
        where=where or {"cat":"채권추심","date":{"$gte":"2024-01-01"}}
    )
    docs = rr["documents"][0]; metas = rr["metadatas"][0]; ids = rr["ids"][0]; embs = rr["embeddings"][0]
    # 제목/URL 중복 벌점
    seen = set(); uniq = []
    for i,(d,m,e,id_) in enumerate(zip(docs, metas, embs, ids)):
        key = (m.get("title"), m.get("url"))
        if key in seen: continue
        seen.add(key); uniq.append({"id":id_,"text":d,"meta":m,"vec":np.array(e, dtype=np.float32)})
    if not uniq: return []

    # (선택) BM25 하이브리드
    if settings.USE_BM25 and BM25Okapi:
        # 한국어 토크나이저 개선 (간단한 형태소 분할 시뮬레이션)
        def korean_tokenize(text):
            # 공백 + 문장부호 기준으로 토큰화 (향후 kiwi/kss로 교체 가능)
            import re
            tokens = re.findall(r'\b\w+\b', text)
            return [t for t in tokens if len(t) > 1]  # 1글자 토큰 제거
        
        corpus = [korean_tokenize(u["text"]) for u in uniq]
        bm = BM25Okapi(corpus)
        bm_scores = bm.get_scores(korean_tokenize(query))
        # BM25 점수 정규화 (0-1 범위)
        max_bm25 = max(bm_scores) if bm_scores else 1.0
        for u, s in zip(uniq, bm_scores):
            u["bm25"] = float(s)
            u["bm25_norm"] = float(s / max_bm25) if max_bm25 > 0 else 0.0
    else:
        for u in uniq: 
            u["bm25"] = 0.0
            u["bm25_norm"] = 0.0

    # 2) BM25-코사인 조합 스코어 계산
    alpha = 0.2  # BM25 가중치
    for u in uniq:
        cos_sim = cosine(qv, u["vec"])
        u["combo"] = (1 - alpha) * cos_sim + alpha * u["bm25_norm"]
    
    # 3) 조합 스코어 기준으로 상위 후보 선별 후 MMR 적용
    uniq.sort(key=lambda x: x["combo"], reverse=True)
    top_candidates = uniq[:min(len(uniq), k*2)]  # 상위 2k개 후보
    
    cand_vecs = [u["vec"] for u in top_candidates]
    sel_idx = mmr_select(qv, cand_vecs, lambda_div=0.7, topk=k)
    picked = [top_candidates[i] for i in sel_idx]

    # top_sources 메타 반환용
    for u in picked:
        u["sim"] = cosine(qv, u["vec"])
    return picked
