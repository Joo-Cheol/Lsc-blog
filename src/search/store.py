import chromadb, os
from src.config.settings import settings

def get_chroma():
    os.makedirs(settings.CHROMA_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
    return client

def get_collection(client=None):
    client = client or get_chroma()
    try:
        col = client.get_collection(settings.CHROMA_COLLECTION)
    except Exception:
        # 기본 임베딩 함수 사용하지 않고 우리가 직접 임베딩 제공
        col = client.create_collection(
            settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )
    return col
