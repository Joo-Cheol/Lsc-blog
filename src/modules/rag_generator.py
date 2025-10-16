#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG 기반 블로그 글 생성 시스템
ChromaDB에서 관련 문서 검색 → Gemini API로 전문 글 생성
"""

import os
import json
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("⚠️ ChromaDB가 설치되지 않았습니다. pip install chromadb")

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ Gemini API가 설치되지 않았습니다. pip install google-generativeai")

class RAGGenerator:
    def __init__(self, chroma_path: str = "src/data/indexes/chroma", 
                 collection_name: str = "naver_blog_debt_collection",
                 gemini_api_key: str = None):
        """
        RAG 생성기 초기화
        
        Args:
            chroma_path: ChromaDB 저장 경로
            collection_name: 컬렉션 이름
            gemini_api_key: Gemini API 키
        """
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        
        # ChromaDB 초기화
        if CHROMADB_AVAILABLE:
            self.client = chromadb.PersistentClient(path=chroma_path)
            try:
                self.collection = self.client.get_collection(collection_name)
                print(f"📚 ChromaDB 컬렉션 로드: {collection_name}")
            except ValueError:
                print(f"❌ 컬렉션을 찾을 수 없습니다: {collection_name}")
                self.collection = None
        else:
            self.collection = None
        
        # Gemini API 초기화
        if GEMINI_AVAILABLE and self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            print("🤖 Gemini API 초기화 완료")
        else:
            self.model = None
            print("⚠️ Gemini API를 사용할 수 없습니다.")
    
    def search_relevant_docs(self, query: str, n_results: int = 10) -> List[Dict[str, Any]]:
        """
        ChromaDB에서 관련 문서 검색
        
        Args:
            query: 검색 쿼리
            n_results: 반환할 결과 수
            
        Returns:
            관련 문서 리스트
        """
        if not self.collection:
            print("❌ ChromaDB 컬렉션이 없습니다.")
            return []
        
        try:
            # 벡터 검색 실행
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # 결과 정리
            docs = []
            for i in range(len(results['documents'][0])):
                doc = {
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i]
                }
                docs.append(doc)
            
            print(f"🔍 '{query}' 검색 결과: {len(docs)}개 문서")
            return docs
            
        except Exception as e:
            print(f"❌ 검색 실패: {e}")
            return []
    
    def build_context(self, docs: List[Dict[str, Any]], max_context_length: int = 4000) -> str:
        """
        검색된 문서들로 컨텍스트 구성
        
        Args:
            docs: 검색된 문서 리스트
            max_context_length: 최대 컨텍스트 길이
            
        Returns:
            구성된 컨텍스트 문자열
        """
        context_parts = []
        current_length = 0
        
        for i, doc in enumerate(docs):
            content = doc['content']
            metadata = doc['metadata']
            
            # 문서 정보 헤더
            header = f"[참고자료 {i+1}]"
            if metadata.get('title'):
                header += f" 제목: {metadata['title']}"
            if metadata.get('logno'):
                header += f" (글번호: {metadata['logno']})"
            if metadata.get('posted_at'):
                header += f" 작성일: {metadata['posted_at']}"
            
            # 컨텍스트 길이 확인
            doc_text = f"{header}\n{content}\n\n"
            if current_length + len(doc_text) > max_context_length:
                break
            
            context_parts.append(doc_text)
            current_length += len(doc_text)
        
        context = "\n".join(context_parts)
        print(f"📝 컨텍스트 구성 완료: {len(context)}자, {len(context_parts)}개 문서")
        return context
    
    def create_prompt(self, topic: str, context: str, style: str = "professional") -> str:
        """
        Gemini API용 프롬프트 생성
        
        Args:
            topic: 글 주제
            context: 참고 컨텍스트
            style: 글 스타일 (professional, friendly, academic)
            
        Returns:
            완성된 프롬프트
        """
        style_instructions = {
            "professional": "전문적이고 신뢰할 수 있는 톤으로 작성하되, 일반인도 이해하기 쉽게 설명해주세요.",
            "friendly": "친근하고 이해하기 쉬운 톤으로 작성해주세요.",
            "academic": "학술적이고 정확한 톤으로 작성해주세요."
        }
        
        prompt = f"""당신은 법무법인 혜안의 채권추심 전문가입니다. 아래 참고자료를 바탕으로 '{topic}'에 대한 전문적인 블로그 글을 작성해주세요.

**작성 요구사항:**
1. {style_instructions.get(style, style_instructions['professional'])}
2. 법무법인 혜안의 전문성을 강조하되, 상업적이지 않게 작성
3. 구체적인 사례와 실무 경험을 포함
4. 독자가 실제로 도움이 될 수 있는 실용적인 정보 제공
5. SEO를 고려한 제목과 구조화된 내용
6. 마지막에 "본 글은 법무법인 혜안에서 제공하는 일반적인 법률 정보입니다." 문구 포함

**참고자료:**
{context}

**출력 형식:**
- 제목: SEO 최적화된 매력적인 제목
- 서론: 독자 관심 유도 및 문제 제기
- 본문: 3-4개의 소제목으로 구성된 구체적 내용
- 결론: 핵심 요약 및 행동 지침
- 면책조항: 법률 정보 제공에 대한 면책 조항

이제 전문적이고 유용한 블로그 글을 작성해주세요."""

        return prompt
    
    def generate_blog_post(self, topic: str, query: str = None, n_results: int = 8, 
                          style: str = "professional", max_context_length: int = 4000) -> Dict[str, Any]:
        """
        블로그 글 생성
        
        Args:
            topic: 글 주제
            query: 검색 쿼리 (None이면 topic 사용)
            n_results: 검색할 문서 수
            style: 글 스타일
            max_context_length: 최대 컨텍스트 길이
            
        Returns:
            생성된 글 정보
        """
        if not self.model:
            return {"error": "Gemini API를 사용할 수 없습니다."}
        
        # 검색 쿼리 설정
        search_query = query or topic
        
        # 1. 관련 문서 검색
        docs = self.search_relevant_docs(search_query, n_results)
        if not docs:
            return {"error": "관련 문서를 찾을 수 없습니다."}
        
        # 2. 컨텍스트 구성
        context = self.build_context(docs, max_context_length)
        
        # 3. 프롬프트 생성
        prompt = self.create_prompt(topic, context, style)
        
        # 4. 글 생성
        try:
            print(f"🤖 '{topic}' 주제로 글 생성 중...")
            response = self.model.generate_content(prompt)
            generated_text = response.text
            
            # 5. 결과 정리
            result = {
                "topic": topic,
                "query": search_query,
                "generated_at": datetime.now().isoformat(),
                "content": generated_text,
                "context_info": {
                    "num_docs": len(docs),
                    "context_length": len(context),
                    "search_results": [
                        {
                            "logno": doc['metadata'].get('logno'),
                            "title": doc['metadata'].get('title'),
                            "distance": doc['distance']
                        }
                        for doc in docs
                    ]
                }
            }
            
            print(f"✅ 글 생성 완료: {len(generated_text)}자")
            return result
            
        except Exception as e:
            return {"error": f"글 생성 실패: {e}"}
    
    def save_generated_post(self, result: Dict[str, Any], output_dir: str = "generated_posts") -> str:
        """생성된 글을 파일로 저장"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        topic_safe = "".join(c for c in result["topic"] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{timestamp}_{topic_safe}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"💾 글 저장 완료: {filepath}")
        return filepath

def main():
    parser = argparse.ArgumentParser(description="RAG 기반 블로그 글 생성")
    parser.add_argument("--topic", required=True, help="글 주제")
    parser.add_argument("--query", help="검색 쿼리 (기본값: topic과 동일)")
    parser.add_argument("--n-results", type=int, default=8, help="검색할 문서 수")
    parser.add_argument("--style", choices=["professional", "friendly", "academic"], 
                       default="professional", help="글 스타일")
    parser.add_argument("--chroma-path", default="src/data/indexes/chroma", help="ChromaDB 경로")
    parser.add_argument("--collection", default="naver_blog_debt_collection", help="컬렉션 이름")
    parser.add_argument("--output-dir", default="generated_posts", help="출력 디렉토리")
    parser.add_argument("--save", action="store_true", help="생성된 글을 파일로 저장")
    
    args = parser.parse_args()
    
    # RAG 생성기 초기화
    generator = RAGGenerator(
        chroma_path=args.chroma_path,
        collection_name=args.collection
    )
    
    # 글 생성
    result = generator.generate_blog_post(
        topic=args.topic,
        query=args.query,
        n_results=args.n_results,
        style=args.style
    )
    
    if "error" in result:
        print(f"❌ 오류: {result['error']}")
        return 1
    
    # 결과 출력
    print(f"\n{'='*80}")
    print(f"📝 생성된 글: {result['topic']}")
    print(f"{'='*80}")
    print(result['content'])
    print(f"{'='*80}")
    
    # 컨텍스트 정보
    print(f"\n📊 생성 정보:")
    print(f"  - 검색 쿼리: {result['query']}")
    print(f"  - 참고 문서: {result['context_info']['num_docs']}개")
    print(f"  - 컨텍스트 길이: {result['context_info']['context_length']}자")
    print(f"  - 생성 시간: {result['generated_at']}")
    
    # 파일 저장
    if args.save:
        filepath = generator.save_generated_post(result, args.output_dir)
        print(f"💾 저장 위치: {filepath}")
    
    return 0

if __name__ == "__main__":
    exit(main())
