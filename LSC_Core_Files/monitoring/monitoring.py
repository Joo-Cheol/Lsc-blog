#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모니터링 및 성능 측정 스크립트
"""
import os
import json
import numpy as np
import time
import logging
from pathlib import Path
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import torch
from collections import defaultdict, deque
import statistics

# ===== 환경 가드 설정 =====
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """성능 모니터링 클래스"""
    
    def __init__(self):
        self.latency_history = deque(maxlen=1000)  # 최근 1000개 요청
        self.cache_hits = 0
        self.cache_misses = 0
        self.query_lengths = deque(maxlen=1000)
        self.token_lengths = deque(maxlen=1000)
        self.error_count = 0
        self.total_requests = 0
        
    def record_request(self, latency_ms: float, query: str, cache_hit: bool, error: bool = False):
        """요청 기록"""
        self.latency_history.append(latency_ms)
        self.query_lengths.append(len(query))
        self.total_requests += 1
        
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
            
        if error:
            self.error_count += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        if not self.latency_history:
            return {"error": "No data available"}
        
        latencies = list(self.latency_history)
        
        return {
            "total_requests": self.total_requests,
            "error_rate": self.error_count / self.total_requests if self.total_requests > 0 else 0,
            "cache_hit_rate": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0,
            "latency": {
                "mean": statistics.mean(latencies),
                "median": statistics.median(latencies),
                "p95": np.percentile(latencies, 95),
                "p99": np.percentile(latencies, 99),
                "min": min(latencies),
                "max": max(latencies)
            },
            "query_length": {
                "mean": statistics.mean(self.query_lengths) if self.query_lengths else 0,
                "median": statistics.median(self.query_lengths) if self.query_lengths else 0
            }
        }

def cosine_similarity(a, b):
    """코사인 유사도 계산"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

class QualityEvaluator:
    """검색 품질 평가 클래스"""
    
    def __init__(self, embeddings, metadata):
        self.embeddings = embeddings
        self.metadata = metadata
        self.model = None
        
    def load_model(self):
        """모델 로드"""
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer("intfloat/multilingual-e5-base", device=device)
        self.model.max_seq_length = 512
    
    def evaluate_recall_at_k(self, queries: List[str], k: int = 10) -> Dict[str, float]:
        """Recall@k 평가"""
        if not self.model:
            self.load_model()
        
        recalls = []
        
        for query in queries:
            # 쿼리 임베딩 생성
            prefixed_query = f"query: {query}"
            query_embedding = self.model.encode([prefixed_query], normalize_embeddings=True)[0]
            
            # 검색 실행
            similarities = []
            for i, embedding in enumerate(self.embeddings):
                sim = cosine_similarity(query_embedding, embedding)
                similarities.append((sim, i))
            
            similarities.sort(reverse=True)
            
            # 상위 k개 결과의 카테고리 분석
            top_k_categories = []
            for sim, idx in similarities[:k]:
                category = self.metadata["metadatas"][idx].get("category", "N/A")
                top_k_categories.append(category)
            
            # 관련성 평가 (간단한 휴리스틱)
            query_lower = query.lower()
            relevant_count = 0
            
            for sim, idx in similarities[:k]:
                doc = self.metadata["documents"][idx].lower()
                title = self.metadata["metadatas"][idx].get("title", "").lower()
                
                # 키워드 매칭으로 관련성 판단
                if any(keyword in doc or keyword in title for keyword in query_lower.split()):
                    relevant_count += 1
            
            recall = relevant_count / k
            recalls.append(recall)
        
        return {
            f"recall@{k}": statistics.mean(recalls),
            f"recall@{k}_std": statistics.stdev(recalls) if len(recalls) > 1 else 0
        }
    
    def evaluate_ndcg_at_k(self, queries: List[str], k: int = 10) -> Dict[str, float]:
        """nDCG@k 평가"""
        if not self.model:
            self.load_model()
        
        ndcgs = []
        
        for query in queries:
            # 쿼리 임베딩 생성
            prefixed_query = f"query: {query}"
            query_embedding = self.model.encode([prefixed_query], normalize_embeddings=True)[0]
            
            # 검색 실행
            similarities = []
            for i, embedding in enumerate(self.embeddings):
                sim = cosine_similarity(query_embedding, embedding)
                similarities.append((sim, i))
            
            similarities.sort(reverse=True)
            
            # DCG 계산
            dcg = 0
            for i, (sim, idx) in enumerate(similarities[:k]):
                # 관련성 점수 (유사도 기반)
                relevance = sim
                dcg += relevance / np.log2(i + 2)  # i+2 because log2(1) = 0
            
            # IDCG 계산 (이상적인 순서)
            ideal_similarities = [sim for sim, _ in similarities[:k]]
            ideal_similarities.sort(reverse=True)
            idcg = 0
            for i, sim in enumerate(ideal_similarities):
                idcg += sim / np.log2(i + 2)
            
            # nDCG 계산
            ndcg = dcg / idcg if idcg > 0 else 0
            ndcgs.append(ndcg)
        
        return {
            f"ndcg@{k}": statistics.mean(ndcgs),
            f"ndcg@{k}_std": statistics.stdev(ndcgs) if len(ndcgs) > 1 else 0
        }

def load_artifacts():
    """벡터 인덱스와 메타데이터 로드"""
    # 최신 버전 찾기
    artifacts_dir = Path("artifacts")
    if not artifacts_dir.exists():
        index_path = "simple_vector_index.npy"
        metadata_path = "simple_metadata.json"
    else:
        versions = [d for d in artifacts_dir.iterdir() if d.is_dir()]
        if not versions:
            raise FileNotFoundError("No artifact versions found")
        
        latest_version = max(versions, key=lambda x: x.name)
        index_path = latest_version / "simple_vector_index.npy"
        metadata_path = latest_version / "simple_metadata.json"
    
    logger.info(f"Loading artifacts from: {index_path}")
    
    # 벡터 인덱스 로드
    embeddings = np.load(index_path, mmap_mode='r')
    
    # 메타데이터 로드
    with open(metadata_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        metadata = {
            "ids": data["ids"],
            "metadatas": data["metadatas"],
            "documents": data["documents"]
        }
    
    return embeddings, metadata

def run_performance_test():
    """성능 테스트 실행"""
    logger.info("Starting performance test...")
    
    # 아티팩트 로드
    embeddings, metadata = load_artifacts()
    
    # 모니터 초기화
    monitor = PerformanceMonitor()
    
    # 테스트 쿼리들
    test_queries = [
        "채권추심 방법",
        "지급명령 신청",
        "압류 절차",
        "제3채무자 통지",
        "채권 회수 방법",
        "강제집행 신청",
        "가압류 절차",
        "경매 신청",
        "채무자 재산 조사",
        "법원 소송 절차"
    ]
    
    # 모델 로드
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer("intfloat/multilingual-e5-base", device=device)
    model.max_seq_length = 512
    
    logger.info(f"Running performance test with {len(test_queries)} queries...")
    
    # 성능 테스트 실행
    for i, query in enumerate(test_queries):
        start_time = time.time()
        
        try:
            # 쿼리 임베딩 생성
            prefixed_query = f"query: {query}"
            query_embedding = model.encode([prefixed_query], normalize_embeddings=True)[0]
            
            # 검색 실행
            similarities = []
            for j, embedding in enumerate(embeddings):
                sim = cosine_similarity(query_embedding, embedding)
                similarities.append((sim, j))
            
            similarities.sort(reverse=True)
            
            # 상위 20개 결과
            top_results = similarities[:20]
            
            latency_ms = (time.time() - start_time) * 1000
            
            # 모니터에 기록 (캐시 히트는 시뮬레이션)
            cache_hit = i % 3 == 0  # 33% 캐시 히트율 시뮬레이션
            monitor.record_request(latency_ms, query, cache_hit)
            
            logger.info(f"Query {i+1}/{len(test_queries)}: '{query}' - {latency_ms:.2f}ms")
            
        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}")
            monitor.record_request(0, query, False, error=True)
    
    # 통계 출력
    stats = monitor.get_stats()
    logger.info("\n=== Performance Statistics ===")
    logger.info(f"Total requests: {stats['total_requests']}")
    logger.info(f"Error rate: {stats['error_rate']:.2%}")
    logger.info(f"Cache hit rate: {stats['cache_hit_rate']:.2%}")
    logger.info(f"Mean latency: {stats['latency']['mean']:.2f}ms")
    logger.info(f"P95 latency: {stats['latency']['p95']:.2f}ms")
    logger.info(f"P99 latency: {stats['latency']['p99']:.2f}ms")
    
    return stats

def run_quality_evaluation():
    """품질 평가 실행"""
    logger.info("Starting quality evaluation...")
    
    # 아티팩트 로드
    embeddings, metadata = load_artifacts()
    
    # 평가자 초기화
    evaluator = QualityEvaluator(embeddings, metadata)
    
    # 테스트 쿼리들
    test_queries = [
        "채권추심 방법",
        "지급명령 신청",
        "압류 절차",
        "제3채무자 통지",
        "채권 회수 방법"
    ]
    
    # Recall@10 평가
    recall_stats = evaluator.evaluate_recall_at_k(test_queries, k=10)
    logger.info("\n=== Recall@10 Evaluation ===")
    logger.info(f"Recall@10: {recall_stats['recall@10']:.3f} ± {recall_stats['recall@10_std']:.3f}")
    
    # nDCG@10 평가
    ndcg_stats = evaluator.evaluate_ndcg_at_k(test_queries, k=10)
    logger.info("\n=== nDCG@10 Evaluation ===")
    logger.info(f"nDCG@10: {ndcg_stats['ndcg@10']:.3f} ± {ndcg_stats['ndcg@10_std']:.3f}")
    
    return {
        "recall": recall_stats,
        "ndcg": ndcg_stats
    }

def generate_monitoring_report():
    """모니터링 리포트 생성"""
    logger.info("Generating monitoring report...")
    
    # 성능 테스트 실행
    perf_stats = run_performance_test()
    
    # 품질 평가 실행
    quality_stats = run_quality_evaluation()
    
    # 리포트 생성
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "performance": perf_stats,
        "quality": quality_stats,
        "system_info": {
            "total_chunks": len(metadata["ids"]) if 'metadata' in globals() else 0,
            "embedding_dimension": embeddings.shape[1] if 'embeddings' in globals() else 0,
            "model": "intfloat/multilingual-e5-base"
        }
    }
    
    # 리포트 저장
    report_path = f"monitoring_report_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Monitoring report saved to: {report_path}")
    
    return report

if __name__ == "__main__":
    generate_monitoring_report()




