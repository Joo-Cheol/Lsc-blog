#!/usr/bin/env python3
"""
법률 블로그 생성 웹 애플리케이션 - 통합 파이프라인
"""

import os
import sys
import json
import time
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
from flask import Flask, render_template_string, request, jsonify
import torch
from sentence_transformers import SentenceTransformer

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
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

def extract_title_from_html(html: str) -> str:
    """HTML에서 제목 추출"""
    import re
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    if title_match:
        return title_match.group(1).strip()
    return "제목 없음"

def load_artifacts():
    """아티팩트 로드"""
    global vector_index, metadata, model, device
    
    print("📁 아티팩트 로드 중...")
    
    # 벡터 인덱스 로드
    vector_path = project_root / "simple_vector_index.npy"
    if vector_path.exists():
        vector_index = np.load(vector_path)
        # L2 정규화
        vector_index = vector_index / np.linalg.norm(vector_index, axis=1, keepdims=True)
        print(f"✅ 벡터 인덱스 로드 및 정규화 완료: {vector_index.shape}")
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

# HTML 템플릿
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 법률 블로그 생성기</title>
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
                <h2>🤖 AI 블로그 포스팅 생성기</h2>
                <p class="text-muted">통합 파이프라인으로 고품질 법률 블로그를 생성합니다</p>
            </div>
        </div>

        <!-- 통합 파이프라인 선택 -->
        <div class="row mb-4">
            <div class="col-12">
                <h4>📋 생성 모드 선택</h4>
                <div class="row">
                    <div class="col-md-12">
                        <div class="card">
                            <div class="card-body">
                                <div class="form-check">
                                    <input class="form-check-input" type="radio" name="mode" id="unified" value="unified" checked>
                                    <label class="form-check-label" for="unified">
                                        <strong>🚀 통합 파이프라인 (2단계 생성)</strong>
                                        <br><small class="text-muted">Draft → Rewrite 과정으로 고품질 블로그 생성</small>
                                    </label>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
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
                                    <option value="default">기본</option>
                                    <option value="채권추심">채권추심</option>
                                    <option value="계약법">계약법</option>
                                    <option value="손해배상">손해배상</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="style" class="form-label">스타일</label>
                                <select class="form-control" id="style" name="style">
                                    <option value="professional">전문적</option>
                                    <option value="friendly">친근한</option>
                                    <option value="formal">격식있는</option>
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
                            <li>• <strong>통합 파이프라인</strong>: 2단계 생성으로 고품질</li>
                            <li>• <strong>품질 검증</strong>: 표절/스타일/형식 자동 검증</li>
                            <li>• 구체적인 주제가 더 좋은 결과</li>
                            <li>• 카테고리별 스타일 프로파일 적용</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let selectedMode = 'unified';

        function selectMode(mode) {
            selectedMode = mode;
            document.querySelectorAll('input[name="mode"]').forEach(radio => {
                radio.checked = radio.value === mode;
            });
        }

        document.getElementById('generateForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = {
                topic: formData.get('topic'),
                category: formData.get('category'),
                style: formData.get('style'),
                mode: selectedMode
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
                    const modeText = result.mode === 'unified-2stage' ? '통합 파이프라인 (2단계 생성)' : 
                                   result.mode === 'e5+enhanced-jaemin' ? 'B 파이프라인 (향상된 재미나이)' : 
                                   result.mode === 'e5+enhanced-gemini' ? 'B 파이프라인 (향상된 구글 Gemini)' : 
                                   result.mode === 'e5+gemini' ? 'B 파이프라인 (구글 Gemini)' : 
                                   result.mode === 'e5' ? '통합 파이프라인 (e5)' : 
                                   result.mode === 'fallback' ? '폴백 모드' : result.mode;
                    
                    document.getElementById('result').innerHTML = `
                        <div class="alert alert-success">
                            <h5>✅ 생성 완료!</h5>
                            <p><strong>모드:</strong> ${modeText}</p>
                            <p><strong>생성 시간:</strong> ${result.generation_time}초</p>
                            <p><strong>품질 점수:</strong> ${result.quality_score || 'N/A'}</p>
                        </div>
                        <div class="result-content">
                            <h4>📝 생성된 블로그</h4>
                            <div class="mb-3">
                                <strong>제목:</strong> ${result.title || 'N/A'}
                            </div>
                            <div class="mb-3">
                                <strong>내용:</strong>
                                <div style="white-space: pre-wrap; background: white; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6;">
${result.content || 'N/A'}
                                </div>
                            </div>
                            ${result.hashtags ? `
                            <div class="mb-3">
                                <strong>해시태그:</strong><br>
                                ${result.hashtags.map(tag => `<span class="hashtag">#${tag}</span>`).join(' ')}
                            </div>
                            ` : ''}
                            ${result.quality_report ? `
                            <div class="mb-3">
                                <strong>품질 보고서:</strong>
                                <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; font-size: 0.9em;">
                                    ${JSON.stringify(result.quality_report, null, 2)}
                                </div>
                            </div>
                            ` : ''}
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
    """블로그 생성 API - 통합 파이프라인"""
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
        
        print(f"🚀 블로그 생성 시작: {topic} (카테고리: {category}, 스타일: {style}, 모드: {mode})")
        start_time = time.time()
        
        # A 파이프라인 사용 (LLM 없음)
        if mode == 'unified':
            # 검색 결과 먼저 가져오기
            search_results = search_documents(topic, top_k=5)
            
            # A 파이프라인으로 생성
            result = generate_no_llm(
                topic=topic,
                results=search_results,
                model=model,
                category=category,
                hashtags=hashtags
            )
            
            generation_time = time.time() - start_time
            
            if result and result.get('html'):
                return jsonify({
                    'success': True,
                    'mode': 'e5-only',
                    'title': extract_title_from_html(result.get('html', '')),
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
        
        else:
            return jsonify({
                'success': False,
                'error': f'지원하지 않는 모드: {mode}'
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

if __name__ == '__main__':
    try:
        # 아티팩트 로드
        load_artifacts()
        
        print("🎉 시스템 준비 완료!")
        print(f"📊 총 {len(metadata)}개 문서 인덱싱됨")
        
        # 웹 서버 시작
        print("✅ 웹 서버가 http://localhost:8001 에서 실행 중입니다!")
        print("📱 브라우저에서 http://localhost:8001 을 열어보세요!")
        
        app.run(host='0.0.0.0', port=8001, debug=False)
        
    except Exception as e:
        print(f"❌ 시스템 시작 오류: {e}")
        sys.exit(1)


법률 블로그 생성 웹 애플리케이션 - 통합 파이프라인
"""

import os
import sys
import json
import time
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
from flask import Flask, render_template_string, request, jsonify
import torch
from sentence_transformers import SentenceTransformer

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
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

def extract_title_from_html(html: str) -> str:
    """HTML에서 제목 추출"""
    import re
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    if title_match:
        return title_match.group(1).strip()
    return "제목 없음"

def load_artifacts():
    """아티팩트 로드"""
    global vector_index, metadata, model, device
    
    print("📁 아티팩트 로드 중...")
    
    # 벡터 인덱스 로드
    vector_path = project_root / "simple_vector_index.npy"
    if vector_path.exists():
        vector_index = np.load(vector_path)
        # L2 정규화
        vector_index = vector_index / np.linalg.norm(vector_index, axis=1, keepdims=True)
        print(f"✅ 벡터 인덱스 로드 및 정규화 완료: {vector_index.shape}")
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

# HTML 템플릿
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 법률 블로그 생성기</title>
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
                <h2>🤖 AI 블로그 포스팅 생성기</h2>
                <p class="text-muted">통합 파이프라인으로 고품질 법률 블로그를 생성합니다</p>
            </div>
        </div>

        <!-- 통합 파이프라인 선택 -->
        <div class="row mb-4">
            <div class="col-12">
                <h4>📋 생성 모드 선택</h4>
                <div class="row">
                    <div class="col-md-12">
                        <div class="card">
                            <div class="card-body">
                                <div class="form-check">
                                    <input class="form-check-input" type="radio" name="mode" id="unified" value="unified" checked>
                                    <label class="form-check-label" for="unified">
                                        <strong>🚀 통합 파이프라인 (2단계 생성)</strong>
                                        <br><small class="text-muted">Draft → Rewrite 과정으로 고품질 블로그 생성</small>
                                    </label>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
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
                                    <option value="default">기본</option>
                                    <option value="채권추심">채권추심</option>
                                    <option value="계약법">계약법</option>
                                    <option value="손해배상">손해배상</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label for="style" class="form-label">스타일</label>
                                <select class="form-control" id="style" name="style">
                                    <option value="professional">전문적</option>
                                    <option value="friendly">친근한</option>
                                    <option value="formal">격식있는</option>
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
                            <li>• <strong>통합 파이프라인</strong>: 2단계 생성으로 고품질</li>
                            <li>• <strong>품질 검증</strong>: 표절/스타일/형식 자동 검증</li>
                            <li>• 구체적인 주제가 더 좋은 결과</li>
                            <li>• 카테고리별 스타일 프로파일 적용</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let selectedMode = 'unified';

        function selectMode(mode) {
            selectedMode = mode;
            document.querySelectorAll('input[name="mode"]').forEach(radio => {
                radio.checked = radio.value === mode;
            });
        }

        document.getElementById('generateForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = {
                topic: formData.get('topic'),
                category: formData.get('category'),
                style: formData.get('style'),
                mode: selectedMode
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
                    const modeText = result.mode === 'unified-2stage' ? '통합 파이프라인 (2단계 생성)' : 
                                   result.mode === 'e5+enhanced-jaemin' ? 'B 파이프라인 (향상된 재미나이)' : 
                                   result.mode === 'e5+enhanced-gemini' ? 'B 파이프라인 (향상된 구글 Gemini)' : 
                                   result.mode === 'e5+gemini' ? 'B 파이프라인 (구글 Gemini)' : 
                                   result.mode === 'e5' ? '통합 파이프라인 (e5)' : 
                                   result.mode === 'fallback' ? '폴백 모드' : result.mode;
                    
                    document.getElementById('result').innerHTML = `
                        <div class="alert alert-success">
                            <h5>✅ 생성 완료!</h5>
                            <p><strong>모드:</strong> ${modeText}</p>
                            <p><strong>생성 시간:</strong> ${result.generation_time}초</p>
                            <p><strong>품질 점수:</strong> ${result.quality_score || 'N/A'}</p>
                        </div>
                        <div class="result-content">
                            <h4>📝 생성된 블로그</h4>
                            <div class="mb-3">
                                <strong>제목:</strong> ${result.title || 'N/A'}
                            </div>
                            <div class="mb-3">
                                <strong>내용:</strong>
                                <div style="white-space: pre-wrap; background: white; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6;">
${result.content || 'N/A'}
                                </div>
                            </div>
                            ${result.hashtags ? `
                            <div class="mb-3">
                                <strong>해시태그:</strong><br>
                                ${result.hashtags.map(tag => `<span class="hashtag">#${tag}</span>`).join(' ')}
                            </div>
                            ` : ''}
                            ${result.quality_report ? `
                            <div class="mb-3">
                                <strong>품질 보고서:</strong>
                                <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; font-size: 0.9em;">
                                    ${JSON.stringify(result.quality_report, null, 2)}
                                </div>
                            </div>
                            ` : ''}
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
    """블로그 생성 API - 통합 파이프라인"""
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
        
        print(f"🚀 블로그 생성 시작: {topic} (카테고리: {category}, 스타일: {style}, 모드: {mode})")
        start_time = time.time()
        
        # A 파이프라인 사용 (LLM 없음)
        if mode == 'unified':
            # 검색 결과 먼저 가져오기
            search_results = search_documents(topic, top_k=5)
            
            # A 파이프라인으로 생성
            result = generate_no_llm(
                topic=topic,
                results=search_results,
                model=model,
                category=category,
                hashtags=hashtags
            )
            
            generation_time = time.time() - start_time
            
            if result and result.get('html'):
                return jsonify({
                    'success': True,
                    'mode': 'e5-only',
                    'title': extract_title_from_html(result.get('html', '')),
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
        
        else:
            return jsonify({
                'success': False,
                'error': f'지원하지 않는 모드: {mode}'
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

if __name__ == '__main__':
    try:
        # 아티팩트 로드
        load_artifacts()
        
        print("🎉 시스템 준비 완료!")
        print(f"📊 총 {len(metadata)}개 문서 인덱싱됨")
        
        # 웹 서버 시작
        print("✅ 웹 서버가 http://localhost:8001 에서 실행 중입니다!")
        print("📱 브라우저에서 http://localhost:8001 을 열어보세요!")
        
        app.run(host='0.0.0.0', port=8001, debug=False)
        
    except Exception as e:
        print(f"❌ 시스템 시작 오류: {e}")
        sys.exit(1)
