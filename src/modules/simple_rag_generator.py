#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 RAG 기반 블로그 글 생성 시스템 (ChromaDB 없이)
SQLite에서 직접 검색하여 Gemini API로 전문 글 생성
"""

import os
import json
import sqlite3
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ Gemini API가 설치되지 않았습니다. pip install google-generativeai")

class SimpleRAGGenerator:
    def __init__(self, db_path: str = "src/data/master/posts.sqlite", 
                 gemini_api_key: str = None):
        """
        간단한 RAG 생성기 초기화
        
        Args:
            db_path: SQLite 데이터베이스 경로
            gemini_api_key: Gemini API 키
        """
        self.db_path = db_path
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.gemini_api_key:
            raise ValueError("Gemini API 키가 필요합니다. 환경변수 GEMINI_API_KEY를 설정하거나 직접 전달하세요.")
        
        if GEMINI_AVAILABLE:
            genai.configure(api_key=self.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # 데이터베이스 연결 확인
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"데이터베이스 파일을 찾을 수 없습니다: {db_path}")
    
    def search_posts(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        SQLite에서 관련 포스트 검색
        
        Args:
            query: 검색 쿼리
            limit: 반환할 포스트 수
            
        Returns:
            관련 포스트 리스트
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # 제목과 내용에서 키워드 검색
        search_terms = query.split()
        where_conditions = []
        params = []
        
        for term in search_terms:
            where_conditions.append("(title LIKE ? OR content LIKE ?)")
            params.extend([f"%{term}%", f"%{term}%"])
        
        if where_conditions:
            where_clause = " OR ".join(where_conditions)
            sql = f"""
            SELECT logno, url, title, category_no, posted_at, content, crawled_at
            FROM posts 
            WHERE {where_clause}
            ORDER BY posted_at DESC
            LIMIT ?
            """
            params.append(limit)
        else:
            sql = """
            SELECT logno, url, title, category_no, posted_at, content, crawled_at
            FROM posts 
            ORDER BY posted_at DESC
            LIMIT ?
            """
            params = [limit]
        
        cur.execute(sql, params)
        results = [dict(row) for row in cur.fetchall()]
        conn.close()
        
        return results
    
    def create_context(self, posts: List[Dict[str, Any]], max_length: int = 3000) -> str:
        """
        검색된 포스트들로부터 컨텍스트 생성
        
        Args:
            posts: 검색된 포스트 리스트
            max_length: 최대 컨텍스트 길이
            
        Returns:
            생성된 컨텍스트
        """
        context_parts = []
        current_length = 0
        
        for post in posts:
            # 포스트 정보 요약
            post_info = f"""
제목: {post['title']}
URL: {post['url']}
작성일: {post['posted_at']}
내용: {post['content'][:500]}...
---
"""
            
            if current_length + len(post_info) > max_length:
                break
                
            context_parts.append(post_info)
            current_length += len(post_info)
        
        return "\n".join(context_parts)
    
    def generate_article(self, topic: str, style: str = "professional", 
                        n_results: int = 5) -> str:
        """
        주제에 대한 전문 글 생성
        
        Args:
            topic: 글 주제
            style: 글 스타일 (professional, casual, academic)
            n_results: 참조할 포스트 수
            
        Returns:
            생성된 글
        """
        if not GEMINI_AVAILABLE:
            return "❌ Gemini API가 설치되지 않았습니다."
        
        # 관련 포스트 검색
        print(f"🔍 '{topic}' 관련 포스트 검색 중...")
        relevant_posts = self.search_posts(topic, n_results)
        
        if not relevant_posts:
            return "❌ 관련 포스트를 찾을 수 없습니다."
        
        print(f"📚 {len(relevant_posts)}개 관련 포스트 발견")
        
        # 컨텍스트 생성
        context = self.create_context(relevant_posts)
        
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
2. 실제 사례와 구체적인 정보를 포함하세요
3. 독자에게 실용적인 도움이 되는 내용으로 구성하세요
4. 1000-1500자 정도의 분량으로 작성하세요
5. 제목, 본문, 결론으로 구성하세요

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

def main():
    parser = argparse.ArgumentParser(description="간단한 RAG 기반 블로그 글 생성기")
    parser.add_argument("--topic", required=True, help="글 주제")
    parser.add_argument("--style", choices=["professional", "casual", "academic"], 
                       default="professional", help="글 스타일")
    parser.add_argument("--n-results", type=int, default=5, help="참조할 포스트 수")
    parser.add_argument("--db-path", default="src/data/master/posts.sqlite", 
                       help="SQLite 데이터베이스 경로")
    parser.add_argument("--stats", action="store_true", help="데이터베이스 통계 출력")
    
    args = parser.parse_args()
    
    try:
        # RAG 생성기 초기화
        rag = SimpleRAGGenerator(db_path=args.db_path)
        
        # 통계 출력
        if args.stats:
            stats = rag.get_database_stats()
            print("📊 데이터베이스 통계:")
            print(f"  - 총 포스트: {stats['total_posts']}개")
            print(f"  - 카테고리별: {stats['category_stats']}")
            print(f"  - 날짜 범위: {stats['date_range'][0]} ~ {stats['date_range'][1]}")
            print()
        
        # 글 생성
        print(f"🎯 주제: {args.topic}")
        print(f"📝 스타일: {args.style}")
        print(f"📚 참조 포스트: {args.n_results}개")
        print("=" * 50)
        
        article = rag.generate_article(
            topic=args.topic,
            style=args.style,
            n_results=args.n_results
        )
        
        print(article)
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")

if __name__ == "__main__":
    main()
