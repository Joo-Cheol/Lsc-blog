from typing import Iterable
from src.search.embedding import E5Embedder
from src.search.store import get_collection
from src.config.settings import settings

def upsert_docs(docs: Iterable[dict]):
    """
    docs: [{id, text, title, url, date, cat, author, post_type, ...}]
    """
    col = get_collection()
    em = E5Embedder(settings.EMBED_MODEL)
    ids, texts, metas = [], [], []
    for d in docs:
        ids.append(str(d["id"]))
        texts.append(d["text"])
        meta = {k: v for k, v in d.items() if k not in ("id", "text")}
        metas.append(meta)
    vecs = em.encode_passage(texts).tolist()
    col.upsert(ids=ids, documents=texts, embeddings=vecs, metadatas=metas)
