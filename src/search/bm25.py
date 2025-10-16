#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BM25 검색 구현
"""
import re
from typing import List, Dict, Any
from collections import Counter

class SimpleBM25:
    """간단한 BM25 구현 (외부 의존성 없이)"""
    
    def __init__(self, docs: List[Dict[str, Any]]):
        self.docs = docs
        self.corpus = [self._tokenize(doc.get("text", "")) for doc in docs]
        self.doc_count = len(docs)
        self.avg_doc_length = sum(len(doc) for doc in self.corpus) / self.doc_count if self.doc_count > 0 else 0
        
        # 단어 빈도 계산
        self.word_freqs = [Counter(doc) for doc in self.corpus]
        self.idf = self._calculate_idf()
    
    def _tokenize(self, text: str) -> List[str]:
        """한국어 텍스트 토크나이징 (간단한 구현)"""
        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', text)
        # 특수문자 제거하고 공백으로 분리
        text = re.sub(r'[^\w\s가-힣]', ' ', text)
        # 연속된 공백을 하나로
        text = re.sub(r'\s+', ' ', text)
        # 단어 단위로 분리
        tokens = [token.strip() for token in text.split() if len(token.strip()) > 1]
        return tokens
    
    def _calculate_idf(self) -> Dict[str, float]:
        """IDF (Inverse Document Frequency) 계산"""
        word_doc_count = Counter()
        for doc in self.corpus:
            unique_words = set(doc)
            for word in unique_words:
                word_doc_count[word] += 1
        
        idf = {}
        for word, doc_count in word_doc_count.items():
            idf[word] = 1.0 + (self.doc_count / (doc_count + 1))
        return idf
    
    def _bm25_score(self, query_tokens: List[str], doc_tokens: List[str], doc_freq: Counter) -> float:
        """BM25 점수 계산"""
        k1 = 1.2
        b = 0.75
        
        score = 0.0
        doc_length = len(doc_tokens)
        
        for token in query_tokens:
            if token in doc_freq:
                tf = doc_freq[token]
                idf = self.idf.get(token, 1.0)
                
                # BM25 공식
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (doc_length / self.avg_doc_length))
                score += idf * (numerator / denominator)
        
        return score
    
    def search(self, query: str, topk: int = 100) -> List[Dict[str, Any]]:
        """BM25 검색 수행"""
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        
        scores = []
        for i, (doc, doc_freq) in enumerate(zip(self.corpus, self.word_freqs)):
            score = self._bm25_score(query_tokens, doc, doc_freq)
            if score > 0:
                scores.append({
                    "id": self.docs[i]["id"],
                    "bm25": score,
                    "text": self.docs[i].get("text", ""),
                    "meta": self.docs[i].get("meta", {})
                })
        
        # 점수 순으로 정렬
        scores.sort(key=lambda x: x["bm25"], reverse=True)
        return scores[:topk]

def create_bm25_index(docs: List[Dict[str, Any]]) -> SimpleBM25:
    """BM25 인덱스 생성"""
    return SimpleBM25(docs)





