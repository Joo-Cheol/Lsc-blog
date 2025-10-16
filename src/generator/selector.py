"""
MMR (Maximal Marginal Relevance) 문장 선택기
- 다양성과 관련성의 균형
- 중복 제거
- 핵심 문장 선택
"""
import numpy as np
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class MMRSelector:
    """MMR 기반 문장 선택기"""
    
    def __init__(self, lambda_param: float = 0.7):
        self.lambda_param = lambda_param  # 다양성 가중치 (0.7 = 다양성 70%, 관련성 30%)
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words=None,
            ngram_range=(1, 2)
        )
    
    def select_sentences(self, results: List[Dict], topic: str, top_k: int = 15) -> List[str]:
        """
        MMR로 문장 선택
        
        Args:
            results: 검색 결과 리스트
            topic: 주제
            top_k: 선택할 문장 수
            
        Returns:
            선택된 문장 리스트
        """
        if not results:
            return []
        
        # 문장 추출
        sentences = self._extract_sentences(results)
        if len(sentences) <= top_k:
            return sentences
        
        # TF-IDF 벡터화
        try:
            tfidf_matrix = self.vectorizer.fit_transform(sentences)
        except ValueError:
            # 벡터화 실패 시 단순 선택
            return sentences[:top_k]
        
        # 주제와의 유사도 계산
        topic_vector = self.vectorizer.transform([topic])
        relevance_scores = cosine_similarity(tfidf_matrix, topic_vector).flatten()
        
        # MMR 선택
        selected_indices = self._mmr_selection(
            tfidf_matrix, relevance_scores, top_k
        )
        
        return [sentences[i] for i in selected_indices]
    
    def _extract_sentences(self, results: List[Dict]) -> List[str]:
        """검색 결과에서 문장 추출"""
        sentences = []
        
        for result in results:
            content = result.get('content', '')
            if not content:
                continue
            
            # 문장 분리
            import re
            content_sentences = re.split(r'[.!?]\s*', content)
            
            for sentence in content_sentences:
                sentence = sentence.strip()
                if len(sentence) > 20:  # 최소 길이 필터
                    sentences.append(sentence)
        
        return sentences
    
    def _mmr_selection(self, tfidf_matrix, relevance_scores, top_k):
        """MMR 알고리즘으로 문장 선택"""
        n_sentences = tfidf_matrix.shape[0]
        selected_indices = []
        remaining_indices = list(range(n_sentences))
        
        # 첫 번째 문장: 가장 관련성 높은 것
        first_idx = np.argmax(relevance_scores)
        selected_indices.append(first_idx)
        remaining_indices.remove(first_idx)
        
        # 나머지 문장들: MMR 점수로 선택
        for _ in range(min(top_k - 1, len(remaining_indices))):
            best_idx = None
            best_score = -1
            
            for idx in remaining_indices:
                # 관련성 점수
                relevance = relevance_scores[idx]
                
                # 다양성 점수 (이미 선택된 문장들과의 최대 유사도)
                if selected_indices:
                    similarities = cosine_similarity(
                        tfidf_matrix[idx:idx+1], 
                        tfidf_matrix[selected_indices]
                    ).flatten()
                    diversity = 1 - np.max(similarities)
                else:
                    diversity = 1
                
                # MMR 점수
                mmr_score = (self.lambda_param * relevance + 
                           (1 - self.lambda_param) * diversity)
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            
            if best_idx is not None:
                selected_indices.append(best_idx)
                remaining_indices.remove(best_idx)
        
        return selected_indices
import numpy as np
from typing import List, Tuple
from .config import CONFIG

def mmr_select(embs: np.ndarray, qvec: np.ndarray, k: int = 40, lam: float = None) -> List[int]:
    """
    MMR (Maximal Marginal Relevance) 선택
    
    Args:
        embs: 문장 임베딩 (n, d) normalized
        qvec: 쿼리 임베딩 (d,) normalized
        k: 선택할 문장 수
        lam: relevance vs diversity 가중치 (0.7 권장)
    
    Returns:
        선택된 문장 인덱스 리스트
    """
    if lam is None:
        lam = CONFIG["mmr_lambda"]
    
    S = embs  # (n, d) normalized
    sims_q = S @ qvec  # 쿼리와의 유사도
    
    selected = []
    taken = set()
    
    for _ in range(min(k, len(S))):
        if not selected:
            # 첫 번째는 쿼리와 가장 유사한 것
            i = int(np.argmax(sims_q))
        else:
            # 이후는 relevance - diversity로 선택
            selected_embs = S[selected]
            max_sim = (S @ selected_embs.T).max(axis=1)  # 이미 선택된 것들과의 최대 유사도
            score = lam * sims_q - (1 - lam) * max_sim
            score[list(taken)] = -1e9  # 이미 선택된 것 제외
            i = int(np.argmax(score))
        
        taken.add(i)
        selected.append(i)
    
    return selected

def select_by_score(embs: np.ndarray, qvec: np.ndarray, k: int = 40, min_score: float = 0.0) -> List[int]:
    """단순 점수 기반 선택 (MMR 대안)"""
    scores = embs @ qvec
    top_indices = np.argsort(scores)[::-1]
    
    selected = []
    for i in top_indices:
        if len(selected) >= k:
            break
        if scores[i] >= min_score:
            selected.append(int(i))
    
    return selected
