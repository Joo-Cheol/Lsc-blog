from sentence_transformers import SentenceTransformer
import numpy as np

# 싱글턴 모델 캐시
_model = None

def _get_model(name):
    global _model
    if _model is None:
        _model = SentenceTransformer(name)
    return _model

class E5Embedder:
    def __init__(self, model_name: str):
        self.model = _get_model(model_name)
    
    def encode_query(self, texts: list[str]) -> np.ndarray:
        """쿼리 임베딩 (검색 시 사용)"""
        texts = [f"query: {t}" for t in texts]
        X = self.model.encode(texts, batch_size=32, normalize_embeddings=True)
        return X.astype(np.float32)
    
    def encode_passage(self, texts: list[str]) -> np.ndarray:
        """문서 임베딩 (인덱싱 시 사용)"""
        texts = [f"passage: {t}" for t in texts]
        X = self.model.encode(texts, batch_size=32, normalize_embeddings=True)
        return X.astype(np.float32)
    
    def encode(self, texts: list[str]) -> np.ndarray:
        """하위 호환성을 위한 기본 메서드 (쿼리로 처리)"""
        return self.encode_query(texts)
