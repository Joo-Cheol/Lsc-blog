#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프로덕션 RAG 기반 블로그 글 생성 시스템
카테고리 중심 리트리벌 + 조건부 스필오버 + 스타일 뱅크
"""

import os
import json
import sqlite3
import argparse
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re

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

class ProductionRAGGenerator:
    def __init__(self, 
                 db_path: str = "src/data/master/posts.sqlite",
                 chroma_path: str = "src/data/indexes/chroma",
                 knowledge_collection: str = "naver_blog_debt_collection",
                 gemini_api_key: str = None):
        """
        프로덕션 RAG 생성기 초기화
        
        Args:
            db_path: SQLite 데이터베이스 경로
            chroma_path: ChromaDB 저장 경로
            knowledge_collection: 지식 컬렉션 이름
            gemini_api_key: Gemini API 키
        """
        self.db_path = db_path
        self.chroma_path = chroma_path
        self.knowledge_collection = knowledge_collection
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.gemini_api_key:
            raise ValueError("Gemini API 키가 필요합니다. 환경변수 GEMINI_API_KEY를 설정하거나 직접 전달하세요.")
        
        if GEMINI_AVAILABLE:
            genai.configure(api_key=self.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # ChromaDB 클라이언트 초기화
        if CHROMADB_AVAILABLE:
            self.client = chromadb.PersistentClient(
                path=chroma_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            self._init_collections()
        
        # 데이터베이스 연결 확인
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"데이터베이스 파일을 찾을 수 없습니다: {db_path}")
    
    def _init_collections(self):
        """ChromaDB 컬렉션 초기화"""
        try:
            self.knowledge_col = self.client.get_collection(self.knowledge_collection)
            print(f"📚 기존 지식 컬렉션 로드: {self.knowledge_collection}")
        except Exception:
            try:
                import chromadb.utils.embedding_functions as embedding_functions
                embedding_function = embedding_functions.DefaultEmbeddingFunction()
                self.knowledge_col = self.client.create_collection(
                    name=self.knowledge_collection,
                    embedding_function=embedding_function,
                    metadata={"description": "네이버 블로그 전체 지식 저장소"}
                )
                print(f"📚 새 지식 컬렉션 생성: {self.knowledge_collection}")
            except Exception:
                self.knowledge_col = self.client.create_collection(
                    name=self.knowledge_collection,
                    metadata={"description": "네이버 블로그 전체 지식 저장소"}
                )
                print(f"📚 새 지식 컬렉션 생성: {self.knowledge_collection} (임베딩 함수 없음)")
    
    def get_style_collection(self, category_no: int) -> str:
        """카테고리별 스타일 컬렉션 이름 반환"""
        return f"style_cat_{category_no}"
    
    def create_style_collection(self, category_no: int):
        """카테고리별 스타일 컬렉션 생성"""
        collection_name = self.get_style_collection(category_no)
        try:
            return self.client.get_collection(collection_name)
        except Exception:
            try:
                import chromadb.utils.embedding_functions as embedding_functions
                embedding_function = embedding_functions.DefaultEmbeddingFunction()
                return self.client.create_collection(
                    name=collection_name,
                    embedding_function=embedding_function,
                    metadata={"description": f"카테고리 {category_no} 스타일 뱅크"}
                )
            except Exception:
                return self.client.create_collection(
                    name=collection_name,
                    metadata={"description": f"카테고리 {category_no} 스타일 뱅크"}
                )
    
    def chunk_text(self, text: str, max_tokens: int = 1200, overlap: int = 200) -> List[str]:
        """텍스트를 청크로 분할"""
        if not text:
            return [""]
        
        # 간단한 글자수 기반 청킹 (토큰 대신 글자수 사용)
        max_chars = max_tokens * 2  # 대략적인 변환
        step = max_chars - overlap
        
        chunks = []
        for i in range(0, len(text), step):
            chunk = text[i:i + max_chars]
            if chunk.strip():
                chunks.append(chunk.strip())
        
        return chunks if chunks else [""]
    
    def upsert_to_chroma(self, docs: List[Dict], run_id: str, source_file: str) -> int:
        """문서들을 ChromaDB에 upsert"""
        if not CHROMADB_AVAILABLE:
            print("❌ ChromaDB가 사용 불가능합니다.")
            return 0
        
        ids, texts, metas = [], [], []
        
        for doc in docs:
            chunks = self.chunk_text(doc.get("content", ""), max_tokens=1200, overlap=200)
            
            for i, chunk in enumerate(chunks):
                chunk_id = f'{doc["logno"]}:{i:03d}'
                ids.append(chunk_id)
                texts.append(chunk)
                metas.append({
                    "logno": int(doc["logno"]),
                    "chunk_idx": i,
                    "category_no": int(doc.get("category_no", 0)),
                    "posted_at": doc.get("posted_at", ""),
                    "title": doc.get("title", ""),
                    "url": doc.get("url", ""),
                    "run_id": run_id,
                    "source_file": source_file,
                    "content_hash": doc.get("content_hash", "")
                })
        
        # 배치 크기로 나누어 upsert
        batch_size = 100
        total_upserted = 0
        
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_texts = texts[i:i + batch_size]
            batch_metas = metas[i:i + batch_size]
            
            try:
                self.knowledge_col.upsert(
                    ids=batch_ids,
                    documents=batch_texts,
                    metadatas=batch_metas
                )
                total_upserted += len(batch_ids)
                print(f"📤 배치 {i//batch_size + 1}: {len(batch_ids)}개 청크 upsert 완료")
            except Exception as e:
                print(f"❌ 배치 {i//batch_size + 1} upsert 실패: {str(e)}")
                # 개별 청크로 시도
                for j, (chunk_id, chunk_text, chunk_meta) in enumerate(zip(batch_ids, batch_texts, batch_metas)):
                    try:
                        self.knowledge_col.upsert(
                            ids=[chunk_id],
                            documents=[chunk_text],
                            metadatas=[chunk_meta]
                        )
                        total_upserted += 1
                    except Exception as e2:
                        print(f"❌ 개별 청크 {chunk_id} upsert 실패: {str(e2)}")
        
        return total_upserted
    
    def retrieve_with_spillover(self, query: str, category_no: int, 
                               spillover_categories: List[int] = None,
                               top_k: int = 8, spillover_k: int = 2) -> Dict[str, Any]:
        """
        카테고리 중심 리트리벌 + 조건부 스필오버
        
        Args:
            query: 검색 쿼리
            category_no: 메인 카테고리 번호
            spillover_categories: 스필오버 대상 카테고리들
            top_k: 메인 검색 결과 수
            spillover_k: 스필오버 결과 수
            
        Returns:
            검색 결과 딕셔너리
        """
        if not CHROMADB_AVAILABLE:
            return {"documents": [], "metadatas": [], "distances": []}
        
        # 1차 검색: 카테고리 잠금
        try:
            main_results = self.knowledge_col.query(
                query_texts=[query],
                n_results=top_k,
                where={"category_no": int(category_no)},
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            print(f"❌ 메인 검색 실패: {str(e)}")
            return {"documents": [], "metadatas": [], "distances": []}
        
        # 품질 평가
        need_spillover = self._evaluate_quality(main_results)
        
        spillover_results = {"documents": [], "metadatas": []}
        
        if need_spillover and spillover_categories:
            try:
                spillover_results = self.knowledge_col.query(
                    query_texts=[query],
                    n_results=spillover_k,
                    where={"category_no": {"$in": [int(cat) for cat in spillover_categories]}},
                    include=["documents", "metadatas"]
                )
                print(f"🔄 스필오버 활성화: {spillover_categories}에서 {len(spillover_results.get('documents', [[]])[0])}개 추가")
            except Exception as e:
                print(f"❌ 스필오버 검색 실패: {str(e)}")
        
        # 결과 병합
        return self._merge_results(main_results, spillover_results)
    
    def _evaluate_quality(self, results: Dict[str, Any]) -> bool:
        """검색 결과 품질 평가"""
        if not results.get("distances") or not results["distances"][0]:
            return True
        
        distances = results["distances"][0][:3]  # 상위 3개만 평가
        similarities = [1 - d for d in distances]
        avg_similarity = sum(similarities) / len(similarities)
        
        # 평균 유사도가 0.72 미만이면 스필오버 필요
        return avg_similarity < 0.72
    
    def _merge_results(self, main: Dict[str, Any], spillover: Dict[str, Any]) -> Dict[str, Any]:
        """검색 결과 병합"""
        merged = {
            "documents": main.get("documents", [[]])[0] + spillover.get("documents", [[]])[0],
            "metadatas": main.get("metadatas", [[]])[0] + spillover.get("metadatas", [[]])[0],
            "distances": main.get("distances", [[]])[0] + [0.5] * len(spillover.get("documents", [[]])[0])
        }
        
        # 중복 제거 (동일 logno에서 최대 2개만)
        seen_lognos = {}
        filtered_docs, filtered_metas, filtered_dists = [], [], []
        
        for doc, meta, dist in zip(merged["documents"], merged["metadatas"], merged["distances"]):
            logno = meta.get("logno", 0)
            if logno not in seen_lognos:
                seen_lognos[logno] = 0
            
            if seen_lognos[logno] < 2:  # 동일 logno에서 최대 2개
                filtered_docs.append(doc)
                filtered_metas.append(meta)
                filtered_dists.append(dist)
                seen_lognos[logno] += 1
        
        return {
            "documents": filtered_docs,
            "metadatas": filtered_metas,
            "distances": filtered_dists
        }
    
    def get_style_context(self, query: str, category_no: int, top_m: int = 3) -> str:
        """스타일 컨텍스트 추출"""
        if not CHROMADB_AVAILABLE:
            return ""
        
        try:
            style_col = self.create_style_collection(category_no)
            results = style_col.query(
                query_texts=[query],
                n_results=top_m,
                include=["documents", "metadatas"]
            )
            
            if not results.get("documents") or not results["documents"][0]:
                return ""
            
            # 스타일 요소만 추출 (헤더, 문장 패턴 등)
            style_snippets = []
            for doc in results["documents"][0]:
                # 간단한 스타일 추출 (실제로는 더 정교한 로직 필요)
                lines = doc.split('\n')
                for line in lines:
                    if any(keyword in line for keyword in ['##', '**', '•', '1.', '2.', '3.']):
                        style_snippets.append(line.strip())
                        if len(style_snippets) >= 5:  # 최대 5개 스니펫
                            break
            
            return '\n'.join(style_snippets[:5])
        except Exception as e:
            print(f"❌ 스타일 컨텍스트 추출 실패: {str(e)}")
            return ""
    
    def build_context(self, query: str, category_no: int, 
                     spillover_categories: List[int] = None,
                     max_tokens: int = 2800) -> str:
        """전체 컨텍스트 구성"""
        # 지식 검색
        knowledge_results = self.retrieve_with_spillover(
            query, category_no, spillover_categories
        )
        
        # 스타일 컨텍스트
        style_context = self.get_style_context(query, category_no)
        
        # 컨텍스트 구성
        context_parts = []
        
        # 지식 컨텍스트 (80-90%)
        if knowledge_results.get("documents"):
            for i, (doc, meta) in enumerate(zip(knowledge_results["documents"], knowledge_results["metadatas"])):
                context_parts.append(f"""
제목: {meta.get('title', 'N/A')}
URL: {meta.get('url', 'N/A')}
작성일: {meta.get('posted_at', 'N/A')}
내용: {doc[:800]}...
---
""")
        
        # 스타일 컨텍스트 (10-20%)
        if style_context:
            context_parts.append(f"""
스타일 참고:
{style_context}
---
""")
        
        full_context = '\n'.join(context_parts)
        
        # 토큰 수 제한 (대략적인 글자수 기반)
        if len(full_context) > max_tokens * 2:
            full_context = full_context[:max_tokens * 2] + "..."
        
        return full_context
    
    def generate_article(self, topic: str, category_no: int, 
                        style: str = "professional",
                        spillover_categories: List[int] = None) -> str:
        """
        주제에 대한 전문 글 생성
        
        Args:
            topic: 글 주제
            category_no: 카테고리 번호
            style: 글 스타일
            spillover_categories: 스필오버 대상 카테고리들
            
        Returns:
            생성된 글
        """
        if not GEMINI_AVAILABLE:
            return "❌ Gemini API가 설치되지 않았습니다."
        
        print(f"🔍 '{topic}' 관련 포스트 검색 중 (카테고리: {category_no})...")
        
        # 컨텍스트 구성
        context = self.build_context(topic, category_no, spillover_categories)
        
        if not context:
            return "❌ 관련 포스트를 찾을 수 없습니다."
        
        print(f"📚 컨텍스트 구성 완료 ({len(context)}자)")
        
        # 프롬프트 생성
        style_instructions = {
            "professional": "전문적이고 신뢰할 수 있는 톤으로 작성하세요.",
            "casual": "친근하고 읽기 쉬운 톤으로 작성하세요.",
            "academic": "학술적이고 정확한 톤으로 작성하세요."
        }
        
        prompt = f"""
다음은 채권추심 관련 블로그 포스트들입니다:

{context}

위 정보를 바탕으로 "{topic}"에 대한 전문적인 블로그 글을 작성해주세요.

요구사항:
1. {style_instructions.get(style, style_instructions['professional'])}
2. 컨텍스트(카테고리 {category_no})에서 제공된 근거만 사용해 작성하세요.
3. 근거가 없으면 일반적 가이드로 한정하고 추정하거나 단정하지 마세요.
4. 법률명/절차/기한/기관명/수치는 컨텍스트에 있는 경우에만 인용하고, 출처/날짜가 불명확하면 '사례에 따라 다름'을 명시하세요.
5. 문체는 스타일 컨텍스트를 따르되, 사실과 충돌 시 사실을 우선하세요.
6. 실제 사례와 구체적인 정보를 포함하세요
7. 독자에게 실용적인 도움이 되는 내용으로 구성하세요
8. 1000-1500자 정도의 분량으로 작성하세요
9. 제목, 본문, 결론으로 구성하세요

글을 작성해주세요:
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"❌ 글 생성 중 오류 발생: {str(e)}"
    
    def get_database_stats(self) -> Dict[str, Any]:
        """데이터베이스 통계 정보 반환"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # 총 포스트 수
        cur.execute("SELECT COUNT(*) FROM posts")
        total_posts = cur.fetchone()[0]
        
        # 카테고리별 통계
        cur.execute("SELECT category_no, COUNT(*) FROM posts GROUP BY category_no")
        category_stats = dict(cur.fetchall())
        
        # 날짜 범위
        cur.execute("SELECT MIN(posted_at), MAX(posted_at) FROM posts")
        date_range = cur.fetchone()
        
        conn.close()
        
        return {
            "total_posts": total_posts,
            "category_stats": category_stats,
            "date_range": date_range
        }
    
    def get_chroma_stats(self) -> Dict[str, Any]:
        """ChromaDB 통계 정보 반환"""
        if not CHROMADB_AVAILABLE:
            return {"error": "ChromaDB 사용 불가"}
        
        try:
            count = self.knowledge_col.count()
            return {
                "knowledge_collection_count": count,
                "collection_name": self.knowledge_collection
            }
        except Exception as e:
            return {"error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="프로덕션 RAG 기반 블로그 글 생성기")
    parser.add_argument("--topic", help="글 주제")
    parser.add_argument("--category", type=int, help="카테고리 번호")
    parser.add_argument("--style", choices=["professional", "casual", "academic"], 
                       default="professional", help="글 스타일")
    parser.add_argument("--spillover", nargs="*", type=int, help="스필오버 대상 카테고리들")
    parser.add_argument("--db-path", default="src/data/master/posts.sqlite", 
                       help="SQLite 데이터베이스 경로")
    parser.add_argument("--chroma-path", default="src/data/indexes/chroma",
                       help="ChromaDB 저장 경로")
    parser.add_argument("--collection", default="naver_blog_all",
                       help="지식 컬렉션 이름")
    parser.add_argument("--stats", action="store_true", help="통계 출력")
    parser.add_argument("--vectorize", help="벡터화할 JSONL 파일 경로")
    parser.add_argument("--run-id", help="실행 ID (벡터화 시 필요)")
    parser.add_argument("--source-file", help="소스 파일 경로 (벡터화 시 필요)")
    
    args = parser.parse_args()
    
    try:
        # RAG 생성기 초기화
        rag = ProductionRAGGenerator(
            db_path=args.db_path,
            chroma_path=args.chroma_path,
            knowledge_collection=args.collection
        )
        
        # 벡터화 모드
        if args.vectorize:
            if not args.run_id or not args.source_file:
                print("❌ 벡터화 모드에서는 --run-id와 --source-file이 필요합니다.")
                return
            
            print(f"📄 벡터화 시작: {args.vectorize}")
            
            # JSONL 파일 로드
            docs = []
            with open(args.vectorize, "r", encoding="utf-8") as f:
                for line in f:
                    docs.append(json.loads(line.strip()))
            
            print(f"📚 {len(docs)}개 문서 로드 완료")
            
            # 벡터화
            upserted_count = rag.upsert_to_chroma(docs, args.run_id, args.source_file)
            print(f"✅ 벡터화 완료: {upserted_count}개 청크 upsert")
            return
        
        # 통계 출력
        if args.stats:
            db_stats = rag.get_database_stats()
            chroma_stats = rag.get_chroma_stats()
            
            print("📊 데이터베이스 통계:")
            print(f"  - 총 포스트: {db_stats['total_posts']}개")
            print(f"  - 카테고리별: {db_stats['category_stats']}")
            print(f"  - 날짜 범위: {db_stats['date_range'][0]} ~ {db_stats['date_range'][1]}")
            
            print("\n📊 ChromaDB 통계:")
            if "error" in chroma_stats:
                print(f"  - 오류: {chroma_stats['error']}")
            else:
                print(f"  - 지식 컬렉션: {chroma_stats['collection_name']}")
                print(f"  - 총 벡터 수: {chroma_stats['knowledge_collection_count']}개")
            print()
        
        # 글 생성
        if not args.topic or not args.category:
            print("❌ 글 생성 모드에서는 --topic과 --category가 필요합니다.")
            return
        
        print(f"🎯 주제: {args.topic}")
        print(f"📂 카테고리: {args.category}")
        print(f"📝 스타일: {args.style}")
        if args.spillover:
            print(f"🔄 스필오버: {args.spillover}")
        print("=" * 50)
        
        article = rag.generate_article(
            topic=args.topic,
            category_no=args.category,
            style=args.style,
            spillover_categories=args.spillover
        )
        
        print(article)
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")

if __name__ == "__main__":
    main()
