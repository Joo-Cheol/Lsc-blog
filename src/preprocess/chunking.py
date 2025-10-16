#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
의미적 청킹 (Semantic Chunking) with Overlap
"""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from .normalize import TextNormalizer


@dataclass
class Chunk:
    """청크 데이터 클래스"""
    text: str
    metadata: Dict[str, str]
    chunk_id: str
    start_pos: int
    end_pos: int
    overlap_start: Optional[int] = None
    overlap_end: Optional[int] = None


class SemanticChunker:
    """의미적 청킹 클래스"""
    
    def __init__(self, max_tokens: int = 320, overlap_tokens: int = 30):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.normalizer = TextNormalizer()
        
        # 토큰 추정을 위한 평균 문자 수 (한국어 기준)
        self.chars_per_token = 2.5
        
        # 청킹 경계 패턴들 (우선순위 순)
        self.boundary_patterns = [
            r'\n\n',  # 문단 구분
            r'[.!?]\s*\n',  # 문장 끝 + 줄바꿈
            r'[.!?]\s+',  # 문장 끝
            r'\n',  # 줄바꿈
            r'[;:]\s+',  # 세미콜론, 콜론
            r',\s+',  # 쉼표
        ]
    
    def chunk_text(self, text: str, metadata: Dict[str, str]) -> List[Chunk]:
        """텍스트를 의미적 청크로 분할"""
        if not text or not text.strip():
            return []
        
        # 텍스트 정규화
        normalized_text = self.normalizer.normalize_html(text)
        
        # 문단 단위로 분할
        paragraphs = self._split_paragraphs(normalized_text)
        
        # 청크 생성
        chunks = []
        current_chunk = ""
        current_metadata = metadata.copy()
        chunk_start = 0
        chunk_id = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 현재 청크에 문단 추가 시 토큰 수 확인
            test_chunk = current_chunk + "\n\n" + para if current_chunk else para
            estimated_tokens = self._estimate_tokens(test_chunk)
            
            if estimated_tokens <= self.max_tokens:
                # 청크에 문단 추가
                current_chunk = test_chunk
            else:
                # 현재 청크 완료
                if current_chunk:
                    chunk = self._create_chunk(
                        current_chunk, current_metadata, chunk_id, chunk_start
                    )
                    chunks.append(chunk)
                    chunk_id += 1
                
                # 새 청크 시작
                current_chunk = para
                chunk_start = len(normalized_text) - len(para)
        
        # 마지막 청크 추가
        if current_chunk:
            chunk = self._create_chunk(
                current_chunk, current_metadata, chunk_id, chunk_start
            )
            chunks.append(chunk)
        
        # 오버랩 추가
        chunks = self._add_overlap(chunks, normalized_text)
        
        return chunks
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """문단 단위로 텍스트 분할"""
        # 문단 구분자로 분할
        paragraphs = re.split(r'\n\s*\n', text)
        
        # 각 문단을 문장 단위로 세분화 (너무 긴 문단 처리)
        refined_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 문단이 너무 길면 문장 단위로 분할
            if self._estimate_tokens(para) > self.max_tokens * 0.8:
                sentences = self._split_sentences(para)
                refined_paragraphs.extend(sentences)
            else:
                refined_paragraphs.append(para)
        
        return refined_paragraphs
    
    def _split_sentences(self, text: str) -> List[str]:
        """문장 단위로 텍스트 분할"""
        # 문장 끝 패턴으로 분할
        sentences = re.split(r'[.!?]+\s+', text)
        
        # 빈 문장 제거 및 정리
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _estimate_tokens(self, text: str) -> int:
        """토큰 수 추정 (한국어 기준)"""
        if not text:
            return 0
        
        # 기본 문자 수 기반 추정
        char_count = len(text)
        
        # 특수 문자 가중치 적용
        special_chars = len(re.findall(r'[^\w\s가-힣]', text))
        weighted_chars = char_count + special_chars * 0.5
        
        return int(weighted_chars / self.chars_per_token)
    
    def _create_chunk(self, text: str, metadata: Dict[str, str], 
                     chunk_id: int, start_pos: int) -> Chunk:
        """청크 객체 생성"""
        # 청크 메타데이터 생성
        chunk_metadata = metadata.copy()
        chunk_metadata.update({
            'chunk_id': str(chunk_id),
            'chunk_type': 'semantic',
            'law_topic': '채권추심',  # 기본값
            'token_count': str(self._estimate_tokens(text)),
            'char_count': str(len(text))
        })
        
        # 법률 키워드 추출
        keywords = self.normalizer.extract_law_keywords(text)
        if keywords:
            chunk_metadata['keywords'] = ','.join(keywords)
        
        return Chunk(
            text=text,
            metadata=chunk_metadata,
            chunk_id=f"{metadata.get('source_url', 'unknown')}_{chunk_id}",
            start_pos=start_pos,
            end_pos=start_pos + len(text)
        )
    
    def _add_overlap(self, chunks: List[Chunk], original_text: str) -> List[Chunk]:
        """청크 간 오버랩 추가"""
        if len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = []
        
        for i, chunk in enumerate(chunks):
            # 이전 청크와의 오버랩
            if i > 0:
                prev_chunk = chunks[i-1]
                overlap_text = self._get_overlap_text(
                    prev_chunk.text, chunk.text, self.overlap_tokens
                )
                if overlap_text:
                    chunk.overlap_start = len(chunk.text) - len(overlap_text)
                    chunk.overlap_end = len(chunk.text)
            
            # 다음 청크와의 오버랩
            if i < len(chunks) - 1:
                next_chunk = chunks[i+1]
                overlap_text = self._get_overlap_text(
                    chunk.text, next_chunk.text, self.overlap_tokens
                )
                if overlap_text:
                    # 오버랩 텍스트를 현재 청크에 추가
                    chunk.text += "\n" + overlap_text
            
            overlapped_chunks.append(chunk)
        
        return overlapped_chunks
    
    def _get_overlap_text(self, text1: str, text2: str, target_tokens: int) -> str:
        """두 텍스트 간 오버랩 텍스트 생성"""
        # text1의 끝부분과 text2의 시작부분에서 공통 부분 찾기
        words1 = text1.split()
        words2 = text2.split()
        
        # 공통 접두사 찾기
        common_prefix = []
        for i in range(min(len(words1), len(words2))):
            if words1[-(i+1)] == words2[i]:
                common_prefix.insert(0, words1[-(i+1)])
            else:
                break
        
        # 목표 토큰 수에 맞게 조정
        overlap_text = ' '.join(common_prefix)
        current_tokens = self._estimate_tokens(overlap_text)
        
        if current_tokens > target_tokens:
            # 토큰 수가 목표보다 많으면 줄이기
            words = overlap_text.split()
            while self._estimate_tokens(' '.join(words)) > target_tokens and len(words) > 1:
                words = words[1:]
            overlap_text = ' '.join(words)
        
        return overlap_text
    
    def get_chunk_stats(self, chunks: List[Chunk]) -> Dict[str, int]:
        """청크 통계 조회"""
        if not chunks:
            return {
                'total_chunks': 0,
                'avg_tokens': 0,
                'avg_chars': 0,
                'total_tokens': 0,
                'total_chars': 0
            }
        
        total_tokens = sum(self._estimate_tokens(chunk.text) for chunk in chunks)
        total_chars = sum(len(chunk.text) for chunk in chunks)
        
        return {
            'total_chunks': len(chunks),
            'avg_tokens': total_tokens // len(chunks),
            'avg_chars': total_chars // len(chunks),
            'total_tokens': total_tokens,
            'total_chars': total_chars
        }


def chunk_text(text: str, metadata: Dict[str, str], 
               max_tokens: int = 320, overlap_tokens: int = 30) -> List[Chunk]:
    """간편한 텍스트 청킹 함수"""
    chunker = SemanticChunker(max_tokens, overlap_tokens)
    return chunker.chunk_text(text, metadata)


# 테스트용 함수
def test_chunker():
    """청킹 기능 테스트"""
    chunker = SemanticChunker(max_tokens=100, overlap_tokens=20)
    
    # 테스트 텍스트
    test_text = """
    # 채권추심 절차 가이드
    
    채권추심은 다음과 같은 절차로 진행됩니다.
    
    ## 1단계: 내용증명 발송
    내용증명은 채무자에게 채권의 존재를 알리는 공식적인 방법입니다.
    비용은 약 5,000원이며, 1-2주 정도 소요됩니다.
    
    ## 2단계: 지급명령 신청
    지급명령은 법원에 신청하는 간이한 소송 절차입니다.
    비용은 약 10,000원이며, 2-4주 정도 소요됩니다.
    
    ## 3단계: 강제집행
    지급명령이 확정되면 강제집행을 통해 채권을 회수할 수 있습니다.
    이 단계에서는 채무자의 재산을 압류할 수 있습니다.
    
    각 단계별로 필요한 서류와 절차가 다르므로 전문가의 도움을 받는 것이 좋습니다.
    """
    
    metadata = {
        'source_url': 'https://test.com',
        'logno': '12345',
        'published_at': '2024-01-15',
        'title': '채권추심 절차 가이드'
    }
    
    chunks = chunker.chunk_text(test_text, metadata)
    
    # 검증
    assert len(chunks) > 0
    assert all(isinstance(chunk, Chunk) for chunk in chunks)
    assert all(chunk.metadata['law_topic'] == '채권추심' for chunk in chunks)
    
    # 토큰 수 검증
    for chunk in chunks:
        tokens = chunker._estimate_tokens(chunk.text)
        assert tokens <= chunker.max_tokens * 1.2  # 약간의 여유
    
    # 통계 확인
    stats = chunker.get_chunk_stats(chunks)
    assert stats['total_chunks'] == len(chunks)
    assert stats['total_tokens'] > 0
    
    print(f"✅ SemanticChunker 테스트 통과 - {len(chunks)}개 청크 생성")
    print(f"   평균 토큰: {stats['avg_tokens']}, 총 토큰: {stats['total_tokens']}")


if __name__ == "__main__":
    test_chunker()
