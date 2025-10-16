"""
표절 검사 가드
- n-gram Jaccard 유사도
- SimHash 기반 중복 검사
- 임베딩 코사인 유사도
"""
import hashlib
import re
from typing import Dict, List, Any, Set
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class PlagiarismGuard:
    """표절 검사 가드"""
    
    def __init__(self):
        self.similarity_threshold = 0.8  # 유사도 임계값
        self.ngram_size = 3  # n-gram 크기
        self.simhash_bits = 64  # SimHash 비트 수
    
    def check_plagiarism(self, content: str, sources: List[Dict]) -> Dict[str, Any]:
        """
        표절 검사
        
        Args:
            content: 검사할 콘텐츠
            sources: 원본 소스 리스트
            
        Returns:
            표절 검사 결과
        """
        if not content or not sources:
            return {"score": 0.0, "is_plagiarized": False, "details": []}
        
        plagiarism_details = []
        max_similarity = 0.0
        
        for i, source in enumerate(sources):
            source_content = source.get('content', '')
            if not source_content:
                continue
            
            # 1. n-gram Jaccard 유사도
            jaccard_sim = self._calculate_jaccard_similarity(content, source_content)
            
            # 2. SimHash 유사도
            simhash_sim = self._calculate_simhash_similarity(content, source_content)
            
            # 3. TF-IDF 코사인 유사도
            cosine_sim = self._calculate_cosine_similarity(content, source_content)
            
            # 종합 유사도 (가중 평균)
            combined_similarity = (
                0.4 * jaccard_sim + 
                0.3 * simhash_sim + 
                0.3 * cosine_sim
            )
            
            if combined_similarity > max_similarity:
                max_similarity = combined_similarity
            
            if combined_similarity > self.similarity_threshold:
                plagiarism_details.append({
                    "source_index": i,
                    "source_title": source.get('title', ''),
                    "similarity": combined_similarity,
                    "jaccard_similarity": jaccard_sim,
                    "simhash_similarity": simhash_sim,
                    "cosine_similarity": cosine_sim,
                    "is_plagiarized": True
                })
        
        return {
            "score": max_similarity,
            "is_plagiarized": max_similarity > self.similarity_threshold,
            "details": plagiarism_details,
            "threshold": self.similarity_threshold
        }
    
    def _calculate_jaccard_similarity(self, text1: str, text2: str) -> float:
        """n-gram Jaccard 유사도 계산"""
        ngrams1 = self._get_ngrams(text1, self.ngram_size)
        ngrams2 = self._get_ngrams(text2, self.ngram_size)
        
        if not ngrams1 or not ngrams2:
            return 0.0
        
        set1 = set(ngrams1)
        set2 = set(ngrams2)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_simhash_similarity(self, text1: str, text2: str) -> float:
        """SimHash 유사도 계산"""
        hash1 = self._calculate_simhash(text1)
        hash2 = self._calculate_simhash(text2)
        
        # 해밍 거리 계산
        hamming_distance = bin(hash1 ^ hash2).count('1')
        
        # 유사도 = 1 - (해밍 거리 / 비트 수)
        similarity = 1 - (hamming_distance / self.simhash_bits)
        
        return max(0.0, similarity)
    
    def _calculate_cosine_similarity(self, text1: str, text2: str) -> float:
        """TF-IDF 코사인 유사도 계산"""
        try:
            vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words=None,
                ngram_range=(1, 2)
            )
            
            tfidf_matrix = vectorizer.fit_transform([text1, text2])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return float(similarity)
        except Exception:
            return 0.0
    
    def _get_ngrams(self, text: str, n: int) -> List[str]:
        """n-gram 추출"""
        if not text:
            return []
        
        # 텍스트 정리
        text = re.sub(r'[^\w\s가-힣]', '', text.lower())
        words = text.split()
        
        if len(words) < n:
            return words
        
        ngrams = []
        for i in range(len(words) - n + 1):
            ngram = ' '.join(words[i:i+n])
            ngrams.append(ngram)
        
        return ngrams
    
    def _calculate_simhash(self, text: str) -> int:
        """SimHash 계산"""
        if not text:
            return 0
        
        # 텍스트 정리
        text = re.sub(r'[^\w\s가-힣]', '', text.lower())
        words = text.split()
        
        if not words:
            return 0
        
        # 각 단어의 해시값 계산
        hash_values = []
        for word in words:
            word_hash = int(hashlib.md5(word.encode()).hexdigest(), 16)
            hash_values.append(word_hash)
        
        # 비트 벡터 계산
        bit_vector = [0] * self.simhash_bits
        
        for hash_val in hash_values:
            for i in range(self.simhash_bits):
                if hash_val & (1 << i):
                    bit_vector[i] += 1
                else:
                    bit_vector[i] -= 1
        
        # SimHash 생성
        simhash = 0
        for i, bit in enumerate(bit_vector):
            if bit > 0:
                simhash |= (1 << i)
        
        return simhash
    
    def find_similar_phrases(self, content: str, sources: List[Dict], 
                           min_length: int = 10) -> List[Dict[str, Any]]:
        """유사한 구문 찾기"""
        similar_phrases = []
        
        # 콘텐츠를 문장으로 분리
        sentences = re.split(r'[.!?]\s*', content)
        
        for sentence in sentences:
            if len(sentence.strip()) < min_length:
                continue
            
            for i, source in enumerate(sources):
                source_content = source.get('content', '')
                if not source_content:
                    continue
                
                # 구문 유사도 계산
                similarity = self._calculate_phrase_similarity(sentence, source_content)
                
                if similarity > 0.7:  # 높은 유사도
                    similar_phrases.append({
                        "phrase": sentence.strip(),
                        "source_index": i,
                        "source_title": source.get('title', ''),
                        "similarity": similarity
                    })
        
        return similar_phrases
    
    def _calculate_phrase_similarity(self, phrase: str, text: str) -> float:
        """구문 유사도 계산"""
        # 구문을 단어로 분리
        phrase_words = set(phrase.lower().split())
        text_words = set(text.lower().split())
        
        if not phrase_words or not text_words:
            return 0.0
        
        # Jaccard 유사도
        intersection = len(phrase_words.intersection(text_words))
        union = len(phrase_words.union(text_words))
        
        return intersection / union if union > 0 else 0.0
    
    def get_originality_score(self, content: str, sources: List[Dict]) -> float:
        """창작성 점수 계산 (0-1, 높을수록 창작성 높음)"""
        plagiarism_result = self.check_plagiarism(content, sources)
        
        # 표절 점수를 창작성 점수로 변환
        originality_score = 1 - plagiarism_result["score"]
        
        return max(0.0, originality_score)
    
    def suggest_improvements(self, content: str, sources: List[Dict]) -> List[str]:
        """개선 제안 생성"""
        suggestions = []
        
        plagiarism_result = self.check_plagiarism(content, sources)
        
        if plagiarism_result["is_plagiarized"]:
            suggestions.append("표절이 감지되었습니다. 내용을 재작성하세요.")
            
            for detail in plagiarism_result["details"]:
                if detail["similarity"] > 0.9:
                    suggestions.append(f"'{detail['source_title']}'와 매우 유사합니다.")
                elif detail["similarity"] > 0.8:
                    suggestions.append(f"'{detail['source_title']}'와 유사합니다.")
        
        # 유사한 구문 찾기
        similar_phrases = self.find_similar_phrases(content, sources)
        if similar_phrases:
            suggestions.append(f"{len(similar_phrases)}개의 유사한 구문이 발견되었습니다.")
        
        return suggestions