#!/usr/bin/env python3
"""
간단한 웹 서버 - 네이버 블로그 생성기 테스트용
"""
import os
import sys
import json
import time
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
from flask import Flask, render_template, request, jsonify
import torch
from sentence_transformers import SentenceTransformer

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# A 파이프라인만 사용 (LLM 없음)
try:
    from src.generator.generator_no_llm import generate_no_llm
except ImportError:
    # 폴백: 기존 방식 사용
    def generate_no_llm(topic, results, model, category, hashtags):
        return {
            "html": f"<h1>{topic}에 대한 법적 검토</h1><p>콘텐츠 생성 중...</p>",
            "title": f"{topic}에 대한 법적 검토",
            "stats": {"error": "생성기 모듈을 찾을 수 없습니다"}
        }

app = Flask(__name__)

# 전역 변수
vector_index = None
metadata = None
model = None
device = None

def load_artifacts():
    """아티팩트 로드"""
    global vector_index, metadata, model, device
    
    print("📁 아티팩트 로드 중...")
    
    # 벡터 인덱스 로드
    vector_path = project_root / "artifacts" / "20251014_1134" / "simple_vector_index.npy"
    if vector_path.exists():
        vector_index = np.load(vector_path)
        print(f"✅ 벡터 인덱스 로드됨: {vector_index.shape}")
    else:
        print("❌ 벡터 인덱스 파일을 찾을 수 없습니다.")
        return False
    
    # 메타데이터 로드
    metadata_path = project_root / "artifacts" / "20251014_1134" / "simple_metadata.json"
    if metadata_path.exists():
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        print(f"✅ 메타데이터 로드됨: {len(metadata)}개 문서")
    else:
        print("❌ 메타데이터 파일을 찾을 수 없습니다.")
        return False
    
    # 모델 로드
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = SentenceTransformer('intfloat/multilingual-e5-base', device=device)
        print(f"✅ 모델 로드됨: {device}")
    except Exception as e:
        print(f"❌ 모델 로드 실패: {e}")
        return False
    
    return True

def search_documents(query: str, top_k: int = 5) -> List[Dict]:
    """문서 검색"""
    if vector_index is None or metadata is None or model is None:
        return []
    
    try:
        # 쿼리 임베딩
        query_embedding = model.encode([query])
        query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
        
        # 유사도 계산
        similarities = np.dot(vector_index, query_embedding.T).flatten()
        
        # 상위 K개 선택
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if idx < len(metadata):
                results.append({
                    "title": metadata[idx].get("title", ""),
                    "content": metadata[idx].get("content", ""),
                    "url": metadata[idx].get("url", ""),
                    "similarity": float(similarities[idx])
                })
        
        return results
    except Exception as e:
        print(f"❌ 검색 오류: {e}")
        return []

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate_blog():
    """블로그 생성 API"""
    try:
        data = request.get_json()
        topic = data.get('topic', '').strip()
        category = data.get('category', 'default')
        style = data.get('style', 'professional')
        mode = data.get('mode', 'unified')
        
        if not topic:
            return jsonify({
                'success': False,
                'error': '주제를 입력해주세요.'
            })
        
        print(f"🚀 블로그 생성 시작: {topic}")
        start_time = time.time()
        
        # 검색 결과 가져오기
        search_results = search_documents(topic, top_k=5)
        
        # A 파이프라인으로 생성
        result = generate_no_llm(
            topic=topic,
            results=search_results,
            model=model,
            category=category,
            hashtags=10
        )
        
        generation_time = time.time() - start_time
        
        if result and result.get('html'):
            return jsonify({
                'success': True,
                'mode': 'e5-only',
                'title': result.get('title', ''),
                'content': result.get('html', ''),
                'hashtags': [],  # A 파이프라인에서는 해시태그 미구현
                'quality_score': result.get('stats', {}).get('style_score', 0),
                'quality_report': result.get('stats', {}),
                'generation_time': round(generation_time, 2)
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('stats', {}).get('error', 'A 파이프라인 생성 실패')
            })
            
    except Exception as e:
        print(f"❌ 블로그 생성 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'서버 오류: {str(e)}'
        })

@app.route('/api/search', methods=['POST'])
def search():
    """문서 검색 API"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        top_k = data.get('top_k', 5)
        
        if not query:
            return jsonify({
                'success': False,
                'error': '검색어를 입력해주세요.'
            })
        
        results = search_documents(query, top_k)
        
        return jsonify({
            'success': True,
            'results': results,
            'query': query,
            'count': len(results)
        })
        
    except Exception as e:
        print(f"❌ 검색 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'검색 오류: {str(e)}'
        })

@app.route('/health')
def health():
    """헬스 체크"""
    return jsonify({
        'status': 'ok',
        'vector_index_loaded': vector_index is not None,
        'metadata_loaded': metadata is not None,
        'model_loaded': model is not None,
        'document_count': len(metadata) if metadata else 0
    })

if __name__ == '__main__':
    try:
        # 아티팩트 로드
        if not load_artifacts():
            print("❌ 아티팩트 로드 실패")
            sys.exit(1)
        
        print("🎉 시스템 준비 완료!")
        print(f"📊 총 {len(metadata)}개 문서 인덱싱됨")
        
        # 웹 서버 시작
        print("✅ 웹 서버가 http://localhost:8001 에서 실행 중입니다!")
        print("📱 브라우저에서 http://localhost:8001 을 열어보세요!")
        
        app.run(host='0.0.0.0', port=8001, debug=False)
        
    except Exception as e:
        print(f"❌ 시스템 시작 오류: {e}")
        sys.exit(1)
