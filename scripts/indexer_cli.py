#!/usr/bin/env python3
"""
RAG 인덱스 구축 CLI 도구
샘플 데이터를 사용하여 Chroma 벡터 데이터베이스를 구축합니다.
"""
import argparse
import json
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.search.embedding import get_embedder
    from src.search.store import get_chroma
    from src.search.indexer import chunk_text
except ImportError as e:
    print(f"❌ 모듈 import 실패: {e}")
    print("프로젝트 루트에서 실행해주세요.")
    sys.exit(1)

def main():
    ap = argparse.ArgumentParser(description="RAG 인덱스 구축 도구")
    ap.add_argument("--in", dest="inp", required=True, help="입력 JSONL 파일 경로")
    ap.add_argument("--out", dest="out", default=".chroma", help="Chroma 저장 디렉터리 (기본: .chroma)")
    ap.add_argument("--model", default=os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-base"), help="임베딩 모델")
    ap.add_argument("--chunk", type=int, default=400, help="청크 크기 (기본: 400)")
    ap.add_argument("--overlap", type=int, default=60, help="청크 겹침 (기본: 60)")
    ap.add_argument("--normalize", action="store_true", help="임베딩 정규화")
    args = ap.parse_args()

    print(f"🚀 인덱싱 시작: {args.inp} → {args.out}")
    print(f"📊 설정: 모델={args.model}, 청크={args.chunk}, 겹침={args.overlap}")

    # 임베더 초기화
    print("🔧 임베더 초기화 중...")
    embedder = get_embedder(model_name=args.model, normalize=args.normalize)
    
    # Chroma DB 초기화
    print("🗄️ Chroma DB 초기화 중...")
    db = get_chroma(persist_dir=args.out, space="cosine")

    # 데이터 로드 및 청킹
    print("📖 데이터 로드 및 청킹 중...")
    docs, metas, ids = [], [], []
    
    input_file = Path(args.inp)
    if not input_file.exists():
        print(f"❌ 입력 파일을 찾을 수 없습니다: {args.inp}")
        sys.exit(1)
    
    for i, line in enumerate(input_file.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
            
        try:
            row = json.loads(line)
            chunks = chunk_text(row["content"], chunk_size=args.chunk, overlap=args.overlap)
            
            for j, chunk in enumerate(chunks):
                docs.append(chunk)
                metas.append({
                    k: row.get(k) for k in ["cat", "date", "title", "url", "author", "post_type"]
                })
                ids.append(f"{i}-{j}")
                
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON 파싱 오류 (라인 {i+1}): {e}")
            continue

    if not docs:
        print("❌ 처리할 데이터가 없습니다.")
        sys.exit(1)

    print(f"📝 총 {len(docs)}개 청크 생성 완료")

    # 임베딩 생성
    print("🧠 임베딩 생성 중...")
    embs = embedder.encode_passages(docs)
    
    # Chroma DB에 저장
    print("💾 Chroma DB에 저장 중...")
    db.add_texts(docs, metadatas=metas, ids=ids, embeddings=embs)
    
    print(f"✅ 인덱싱 완료: {len(docs)}개 청크 → {args.out}")
    print(f"📁 저장 위치: {Path(args.out).absolute()}")

if __name__ == "__main__":
    main()





