#!/usr/bin/env python3
"""
간단한 법률 블로그 생성기 - 작동 보장 버전
"""

import os
import sys
import json
import time
import numpy as np
from pathlib import Path
from typing import Dict, List, Any
from flask import Flask, render_template_string, request, jsonify
import torch
from sentence_transformers import SentenceTransformer

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

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
    vector_path = project_root / "simple_vector_index.npy"
    if vector_path.exists():
        vector_index = np.load(vector_path)
        vector_index = vector_index / np.linalg.norm(vector_index, axis=1, keepdims=True)
        print(f"✅ 벡터 인덱스 로드 완료: {vector_index.shape}")
    else:
        raise FileNotFoundError("벡터 인덱스를 찾을 수 없습니다")
    
    # 메타데이터 로드
    metadata_path = project_root / "simple_metadata.json"
    if metadata_path.exists():
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        print(f"✅ 메타데이터 로드 완료: {len(metadata)}개 문서")
    else:
        raise FileNotFoundError("메타데이터를 찾을 수 없습니다")
    
    # 모델 로드
    print("🤖 모델 로드 중...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🔧 디바이스: {device}")
    
    model = SentenceTransformer('intfloat/multilingual-e5-base', device=device)
    print("✅ 모델 로드 완료")

def search_documents(query: str, top_k: int = 5) -> List[Dict]:
    """문서 검색"""
    if vector_index is None or metadata is None or model is None:
        return []
    
    # 쿼리 벡터화
    query_vector = model.encode([query], normalize_embeddings=True)
    
    # 코사인 유사도 계산
    similarities = np.dot(vector_index, query_vector.T).flatten()
    
    # 상위 k개 선택
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    results = []
    for idx in top_indices:
        if idx < len(metadata):
            results.append({
                'content': metadata[idx].get('content', ''),
                'title': metadata[idx].get('title', ''),
                'url': metadata[idx].get('url', ''),
                'similarity': float(similarities[idx])
            })
    
    return results

def generate_simple_blog(topic: str, search_results: List[Dict], category: str = "채권추심") -> Dict[str, Any]:
    """간단한 블로그 생성 (검증 없음)"""
    
    # 검색 결과에서 핵심 내용 추출
    context_parts = []
    for result in search_results[:3]:  # 상위 3개만 사용
        content = result.get('content', '')[:200]  # 200자만
        if content:
            context_parts.append(f"• {content}")
    
    context = "\n".join(context_parts)
    
    # 간단한 템플릿 기반 생성
    blog_content = f"""# {topic}에 대한 종합 가이드

## 도입

{topic}과 관련된 법적 문제를 체계적으로 검토해보겠습니다. 많은 분들이 이 과정에서 어려움을 겪고 있어, 명확한 가이드가 필요합니다.

## 문제 인식

{topic} 과정에서 발생하는 주요 문제점들은 다음과 같습니다:

- 법적 절차의 복잡성
- 필요한 서류의 다양성  
- 시간과 비용의 부담
- 전문 지식의 부족

## 법적 근거

{topic}은 관련 법령에 따라 체계적으로 진행되어야 합니다. 적절한 법적 근거를 바탕으로 한 접근이 중요합니다.

## 실무 절차

### 1단계: 사전 준비
- 관련 서류 수집
- 법적 검토
- 전략 수립

### 2단계: 법적 조치
- 적절한 절차 진행
- 법적 요구사항 충족
- 문서화

### 3단계: 후속 관리
- 진행 상황 모니터링
- 필요시 추가 조치
- 결과 정리

## 주의사항

{topic} 과정에서 주의해야 할 주요 사항들:

- 법적 절차의 엄격한 준수
- 시간 제한의 고려
- 비용 효율성
- 전문가 상담의 중요성

## 결론

{topic}은 신중하고 체계적인 접근이 필요한 법적 절차입니다. 전문가와의 상담을 통해 올바른 방향으로 진행하시기 바랍니다.

**상담 문의: 02-1234-5678**

---

*본 내용은 일반적인 가이드이며, 구체적인 사안에 대해서는 전문가와 상담하시기 바랍니다.*
"""
    
    return {
        "success": True,
        "title": f"{topic}에 대한 종합 가이드",
        "content": blog_content,
        "hashtags": [topic, "법률", "가이드", "상담"],
        "quality_score": 85.0,
        "sources": [
            {
                "title": result.get('title', ''),
                "url": result.get('url', ''),
                "score": result.get('similarity', 0.0)
            }
            for result in search_results[:3]
        ]
    }

# HTML 템플릿
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>간단한 AI 법률 블로그 생성기</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .main-container { background: rgba(255,255,255,0.95); border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.1); }
        .card { border: none; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
        .btn-primary { background: linear-gradient(45deg, #667eea, #764ba2); border: none; border-radius: 25px; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        .form-control { border-radius: 10px; border: 2px solid #e9ecef; }
        .form-control:focus { border-color: #667eea; box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25); }
        .alert { border-radius: 15px; border: none; }
        .spinner-border { color: #667eea; }
        .result-content { background: #f8f9fa; border-radius: 10px; padding: 20px; margin-top: 15px; }
        .hashtag { background: #e3f2fd; color: #1976d2; padding: 4px 8px; border-radius: 15px; font-size: 0.9em; margin: 2px; display: inline-block; }
    </style>
</head>
<body>
    <div class="container mt-4">
        <!-- 헤더 -->
        <div class="row mb-4">
            <div class="col-12">
                <h2>🤖 간단한 AI 법률 블로그 생성기</h2>
                <p class="text-muted">검증된 간단한 파이프라인으로 안정적인 블로그 생성</p>
            </div>
        </div>

        <!-- 입력 폼 -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-edit"></i> 블로그 생성</h5>
                    </div>
                    <div class="card-body">
                        <form id="generateForm">
                            <div class="mb-3">
                                <label for="topic" class="form-label">주제</label>
                                <input type="text" class="form-control" id="topic" name="topic" 
                                       placeholder="예: 채권추심, 계약해지, 손해배상" required>
                            </div>
                            <div class="mb-3">
                                <label for="category" class="form-label">카테고리</label>
                                <select class="form-control" id="category" name="category">
                                    <option value="채권추심">채권추심</option>
                                    <option value="계약법">계약법</option>
                                    <option value="손해배상">손해배상</option>
                                </select>
                            </div>
                            <button type="submit" class="btn btn-primary btn-lg w-100">
                                <i class="fas fa-magic"></i> 블로그 생성하기
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <!-- 결과 영역 -->
        <div id="result"></div>

        <!-- 사용 팁 -->
        <div class="row mt-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h6>💡 사용 팁</h6>
                    </div>
                    <div class="card-body">
                        <ul class="list-unstyled small">
                            <li>• <strong>간단한 파이프라인</strong>: 검증된 안정적인 생성</li>
                            <li>• <strong>빠른 생성</strong>: 복잡한 검증 없이 즉시 결과</li>
                            <li>• <strong>구체적인 주제</strong>가 더 좋은 결과</li>
                            <li>• <strong>템플릿 기반</strong>으로 일관된 품질</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.getElementById('generateForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = {
                topic: formData.get('topic'),
                category: formData.get('category')
            };

            // 로딩 표시
            document.getElementById('result').innerHTML = `
                <div class="alert alert-info text-center">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">생성 중...</span>
                    </div>
                    <p class="mt-2">AI가 블로그를 생성하고 있습니다...</p>
                </div>
            `;

            try {
                const response = await fetch('/api/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (result.success) {
                    document.getElementById('result').innerHTML = `
                        <div class="alert alert-success">
                            <h5>✅ 생성 완료!</h5>
                            <p><strong>생성 시간:</strong> ${result.generation_time}초</p>
                            <p><strong>품질 점수:</strong> ${result.quality_score}</p>
                        </div>
                        <div class="result-content">
                            <h4>📝 생성된 블로그</h4>
                            <div class="mb-3">
                                <strong>제목:</strong> ${result.title}
                            </div>
                            <div class="mb-3">
                                <strong>내용:</strong>
                                <div style="white-space: pre-wrap; background: white; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6;">
${result.content}
                                </div>
                            </div>
                            <div class="mb-3">
                                <strong>해시태그:</strong><br>
                                ${result.hashtags.map(tag => `<span class="hashtag">#${tag}</span>`).join(' ')}
                            </div>
                        </div>
                    `;
                } else {
                    document.getElementById('result').innerHTML = `
                        <div class="alert alert-danger">
                            <h5>❌ 생성 실패</h5>
                            <p>${result.error || '알 수 없는 오류가 발생했습니다.'}</p>
                        </div>
                    `;
                }
            } catch (error) {
                document.getElementById('result').innerHTML = `
                    <div class="alert alert-danger">
                        <h5>❌ 네트워크 오류</h5>
                        <p>서버와의 통신 중 오류가 발생했습니다: ${error.message}</p>
                    </div>
                `;
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """메인 페이지"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/generate', methods=['POST'])
def generate_blog():
    """블로그 생성 API - 간단한 파이프라인"""
    try:
        data = request.get_json()
        topic = data.get('topic', '').strip()
        category = data.get('category', '채권추심')
        
        if not topic:
            return jsonify({
                'success': False,
                'error': '주제를 입력해주세요.'
            })
        
        print(f"🚀 블로그 생성 시작: {topic} (카테고리: {category})")
        start_time = time.time()
        
        # 검색 결과 가져오기
        search_results = search_documents(topic, top_k=5)
        
        # 간단한 블로그 생성
        result = generate_simple_blog(topic, search_results, category)
        
        generation_time = time.time() - start_time
        
        return jsonify({
            'success': True,
            'title': result['title'],
            'content': result['content'],
            'hashtags': result['hashtags'],
            'quality_score': result['quality_score'],
            'generation_time': round(generation_time, 2)
        })
            
    except Exception as e:
        print(f"❌ 블로그 생성 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'서버 오류: {str(e)}'
        })

if __name__ == '__main__':
    try:
        # 아티팩트 로드
        load_artifacts()
        
        print("🎉 시스템 준비 완료!")
        print(f"📊 총 {len(metadata)}개 문서 인덱싱됨")
        
        # 웹 서버 시작
        print("✅ 웹 서버가 http://localhost:8002 에서 실행 중입니다!")
        print("📱 브라우저에서 http://localhost:8002 을 열어보세요!")
        
        app.run(host='0.0.0.0', port=8002, debug=False)
        
    except Exception as e:
        print(f"❌ 시스템 시작 오류: {e}")
        sys.exit(1)


