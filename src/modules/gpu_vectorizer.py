#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU 가속 벡터화 시스템
sentence-transformers를 사용한 고속 임베딩 생성
"""

import os
import json
import argparse
from typing import List, Dict, Any
import torch

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("⚠️ sentence-transformers가 설치되지 않았습니다.")

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("⚠️ ChromaDB가 설치되지 않았습니다.")

class GPUEmbeddingFunction:
    """GPU 가속 임베딩 함수"""
    
    def __init__(self, model_name: str = "jhgan/ko-sroberta-multitask"):
        """
        초기화
        
        Args:
            model_name: 사용할 임베딩 모델명
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers가 필요합니다.")
        
        print(f"🚀 GPU 임베딩 모델 로딩: {model_name}")
        
        # GPU 사용 가능 여부 확인 및 강제 사용
        if torch.cuda.is_available():
            self.device = "cuda"
            print(f"🚀 GPU 사용 가능! CUDA 디바이스로 설정")
        else:
            self.device = "cpu"
            print(f"⚠️ GPU를 사용할 수 없습니다. CPU로 실행됩니다.")
            print(f"💡 GPU를 사용하려면 CUDA가 설치되어 있어야 합니다.")
        
        print(f"💻 사용 디바이스: {self.device}")
        
        # 모델 로드
        self.model = SentenceTransformer(model_name, device=self.device)
        print(f"✅ 모델 로드 완료")
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        텍스트를 임베딩으로 변환 (ChromaDB 0.4.16+ 호환 인터페이스)
        
        Args:
            input: 변환할 텍스트 리스트
            
        Returns:
            임베딩 벡터 리스트
        """
        if not input:
            return []
        
        # 배치 처리로 임베딩 생성 (GPU 사용 시 더 큰 배치 크기)
        batch_size = 64 if self.device == "cuda" else 16
        print(f"🔄 배치 크기: {batch_size} (디바이스: {self.device})")
        
        embeddings = self.model.encode(
            input,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_tensor=False
        )
        
        return embeddings.tolist()
    
    def encode(self, input_texts: List[str]) -> List[List[float]]:
        """
        ChromaDB 호환을 위한 encode 메서드
        """
        return self.__call__(input_texts)

class GPUVectorizer:
    """GPU 가속 벡터화 시스템"""
    
    def __init__(self, 
                 chroma_path: str = "src/data/indexes/chroma",
                 collection_name: str = "naver_blog_all",
                 model_name: str = "jhgan/ko-sroberta-multitask"):
        """
        초기화
        
        Args:
            chroma_path: ChromaDB 저장 경로
            collection_name: 컬렉션 이름
            model_name: 임베딩 모델명
        """
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        
        # GPU 임베딩 함수 초기화
        self.embedding_function = GPUEmbeddingFunction(model_name)
        
        # ChromaDB 클라이언트 초기화
        if CHROMADB_AVAILABLE:
            self.client = chromadb.PersistentClient(
                path=chroma_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            self._init_collection()
    
    def _init_collection(self):
        """ChromaDB 컬렉션 초기화"""
        try:
            self.collection = self.client.get_collection(self.collection_name)
            print(f"📚 기존 컬렉션 로드: {self.collection_name}")
        except Exception:
            try:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"description": "네이버 블로그 전체 지식 저장소 (GPU 가속)"}
                )
                print(f"📚 새 컬렉션 생성: {self.collection_name} (GPU 임베딩 함수 사용)")
            except Exception as e:
                print(f"⚠️ GPU 임베딩 함수로 컬렉션 생성 실패: {e}")
                # 기본 임베딩 함수로 시도
                try:
                    import chromadb.utils.embedding_functions as embedding_functions
                    default_embedding_function = embedding_functions.DefaultEmbeddingFunction()
                    self.collection = self.client.create_collection(
                        name=self.collection_name,
                        embedding_function=default_embedding_function,
                        metadata={"description": "네이버 블로그 전체 지식 저장소 (기본 임베딩)"}
                    )
                    print(f"📚 새 컬렉션 생성: {self.collection_name} (기본 임베딩 함수 사용)")
                except Exception as e2:
                    # 임베딩 함수 없이 생성
                    self.collection = self.client.create_collection(
                        name=self.collection_name,
                        metadata={"description": "네이버 블로그 전체 지식 저장소 (임베딩 함수 없음)"}
                    )
                    print(f"📚 새 컬렉션 생성: {self.collection_name} (임베딩 함수 없음)")
    
    def chunk_text(self, text: str, max_tokens: int = 1200, overlap: int = 200) -> List[str]:
        """텍스트를 청크로 분할"""
        if not text:
            return [""]
        
        # 간단한 글자수 기반 청킹
        max_chars = max_tokens * 2  # 대략적인 변환
        step = max_chars - overlap
        
        chunks = []
        for i in range(0, len(text), step):
            chunk = text[i:i + max_chars]
            if chunk.strip():
                chunks.append(chunk.strip())
        
        return chunks if chunks else [""]
    
    def vectorize_documents(self, docs: List[Dict], run_id: str, source_file: str) -> int:
        """
        문서들을 벡터화하여 ChromaDB에 저장
        
        Args:
            docs: 문서 리스트
            run_id: 실행 ID
            source_file: 소스 파일 경로
            
        Returns:
            저장된 청크 수
        """
        if not CHROMADB_AVAILABLE:
            print("❌ ChromaDB가 사용 불가능합니다.")
            return 0
        
        print(f"📄 {len(docs)}개 문서 벡터화 시작...")
        
        ids, texts, metas = [], [], []
        
        for doc in docs:
            chunks = self.chunk_text(doc.get("content", ""), max_tokens=1200, overlap=200)
            
            for i, chunk in enumerate(chunks):
                # logNo 또는 logno 필드 사용 (데이터 구조에 따라)
                logno = doc.get("logNo") or doc.get("logno", "unknown")
                chunk_id = f'{logno}:{i:03d}'
                ids.append(chunk_id)
                texts.append(chunk)
                metas.append({
                    "logno": int(logno) if str(logno).isdigit() else 0,
                    "chunk_idx": i,
                    "category_no": int(doc.get("category_no", 0)),
                    "posted_at": doc.get("posted_at", ""),
                    "title": doc.get("title", ""),
                    "url": doc.get("url", ""),
                    "run_id": run_id,
                    "source_file": source_file,
                    "content_hash": doc.get("content_hash", "")
                })
        
        print(f"🔧 {len(ids)}개 청크 생성 완료")
        
        # 배치 크기로 나누어 upsert
        batch_size = 100
        total_upserted = 0
        
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_texts = texts[i:i + batch_size]
            batch_metas = metas[i:i + batch_size]
            
            try:
                self.collection.upsert(
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
                        self.collection.upsert(
                            ids=[chunk_id],
                            documents=[chunk_text],
                            metadatas=[chunk_meta]
                        )
                        total_upserted += 1
                    except Exception as e2:
                        print(f"❌ 개별 청크 {chunk_id} upsert 실패: {str(e2)}")
        
        return total_upserted
    
    def get_stats(self) -> Dict[str, Any]:
        """컬렉션 통계 반환"""
        if not CHROMADB_AVAILABLE:
            return {"error": "ChromaDB 사용 불가"}
        
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "total_chunks": count,
                "device": self.embedding_function.device,
                "model_name": self.embedding_function.model.get_sentence_embedding_dimension()
            }
        except Exception as e:
            return {"error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="GPU 가속 벡터화 시스템")
    parser.add_argument("--input", required=True, help="입력 JSONL 파일 경로")
    parser.add_argument("--run-id", required=True, help="실행 ID")
    parser.add_argument("--source-file", required=True, help="소스 파일 경로")
    parser.add_argument("--chroma-path", default="src/data/indexes/chroma",
                       help="ChromaDB 저장 경로")
    parser.add_argument("--collection", default="naver_blog_all",
                       help="컬렉션 이름")
    parser.add_argument("--model", default="jhgan/ko-sroberta-multitask",
                       help="임베딩 모델명")
    parser.add_argument("--stats", action="store_true", help="통계 출력")
    
    args = parser.parse_args()
    
    try:
        # GPU 벡터화 시스템 초기화
        vectorizer = GPUVectorizer(
            chroma_path=args.chroma_path,
            collection_name=args.collection,
            model_name=args.model
        )
        
        # 통계 출력
        if args.stats:
            stats = vectorizer.get_stats()
            print("📊 벡터화 시스템 통계:")
            if "error" in stats:
                print(f"  - 오류: {stats['error']}")
            else:
                print(f"  - 컬렉션: {stats['collection_name']}")
                print(f"  - 총 청크 수: {stats['total_chunks']}개")
                print(f"  - 디바이스: {stats['device']}")
                print(f"  - 모델 차원: {stats['model_name']}")
            return
        
        # JSONL 파일 로드
        print(f"📄 JSONL 파일 로드: {args.input}")
        docs = []
        with open(args.input, "r", encoding="utf-8") as f:
            for line in f:
                docs.append(json.loads(line.strip()))
        
        print(f"📚 {len(docs)}개 문서 로드 완료")
        
        # 벡터화 실행
        upserted_count = vectorizer.vectorize_documents(
            docs, args.run_id, args.source_file
        )
        
        print(f"✅ 벡터화 완료!")
        print(f"  - 처리된 문서: {len(docs)}개")
        print(f"  - 저장된 청크: {upserted_count}개")
        
        # 최종 통계
        final_stats = vectorizer.get_stats()
        if "error" not in final_stats:
            print(f"  - 총 벡터 수: {final_stats['total_chunks']}개")
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")

if __name__ == "__main__":
    main()
