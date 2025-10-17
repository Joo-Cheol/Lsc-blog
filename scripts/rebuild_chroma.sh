#!/usr/bin/env bash
set -e

echo "🚀 RAG 인덱스 재구축 시작"

# 가상환경 생성 및 활성화
if [ ! -d ".venv" ]; then
    echo "📦 가상환경 생성 중..."
    python -m venv .venv
fi

echo "🔧 가상환경 활성화 중..."
source .venv/bin/activate  # Linux/Mac
# Windows의 경우: .venv\Scripts\activate

# 의존성 설치
echo "📥 의존성 설치 중..."
pip install -r requirements.txt

# 기존 인덱스 삭제
if [ -d ".chroma" ]; then
    echo "🗑️ 기존 인덱스 삭제 중..."
    rm -rf .chroma
fi

# 샘플 데이터로 인덱스 구축
echo "🏗️ 샘플 데이터로 인덱스 구축 중..."
python scripts/indexer_cli.py \
    --in data/samples/posts_sample_10.jsonl \
    --out .chroma \
    --normalize \
    --chunk 400 \
    --overlap 60

echo "✅ 인덱스 재구축 완료!"
echo "📁 저장 위치: $(pwd)/.chroma"
echo ""
echo "🎯 다음 단계:"
echo "1. 백엔드 실행: uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload"
echo "2. 프론트엔드 실행: npm run dev"






