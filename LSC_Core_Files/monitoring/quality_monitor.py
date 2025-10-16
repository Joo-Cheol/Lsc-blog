#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자동화된 품질 모니터링 및 리포트 시스템
"""
import os
import json
import numpy as np
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import torch
from datetime import datetime, timedelta
import statistics
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ===== 환경 가드 설정 =====
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

class QualityMonitor:
    """품질 모니터링 클래스"""
    
    def __init__(self, artifacts_dir: str = "artifacts"):
        self.artifacts_dir = Path(artifacts_dir)
        self.embeddings = None
        self.metadata = None
        self.model = None
        self.gold_queries = self._load_gold_queries()
        
    def _load_gold_queries(self) -> List[Dict[str, Any]]:
        """골드 쿼리 로드"""
        # 실제 운영에서는 별도 파일에서 로드
        return [
            {
                "query": "채권추심 방법",
                "expected_categories": ["채권추심"],
                "min_relevance_score": 0.8,
                "expected_results": 5
            },
            {
                "query": "지급명령 신청",
                "expected_categories": ["채권추심"],
                "min_relevance_score": 0.8,
                "expected_results": 5
            },
            {
                "query": "압류 절차",
                "expected_categories": ["채권추심"],
                "min_relevance_score": 0.8,
                "expected_results": 5
            },
            {
                "query": "제3채무자 통지",
                "expected_categories": ["채권추심"],
                "min_relevance_score": 0.8,
                "expected_results": 5
            },
            {
                "query": "채권 회수 방법",
                "expected_categories": ["채권추심"],
                "min_relevance_score": 0.8,
                "expected_results": 5
            }
        ]
    
    def load_artifacts(self):
        """아티팩트 로드"""
        # 최신 버전 찾기
        if not self.artifacts_dir.exists():
            index_path = "simple_vector_index.npy"
            metadata_path = "simple_metadata.json"
        else:
            versions = [d for d in self.artifacts_dir.iterdir() if d.is_dir()]
            if not versions:
                raise FileNotFoundError("No artifact versions found")
            
            latest_version = max(versions, key=lambda x: x.name)
            index_path = latest_version / "simple_vector_index.npy"
            metadata_path = latest_version / "simple_metadata.json"
        
        logger.info(f"Loading artifacts from: {index_path}")
        
        # 벡터 인덱스 로드
        self.embeddings = np.load(index_path, mmap_mode='r')
        
        # 메타데이터 로드
        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.metadata = {
                "ids": data["ids"],
                "metadatas": data["metadatas"],
                "documents": data["documents"]
            }
        
        # 모델 로드
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer("intfloat/multilingual-e5-base", device=device)
        self.model.max_seq_length = 512
        
        logger.info(f"Loaded {len(self.metadata['ids'])} chunks")
    
    def cosine_similarity(self, a, b):
        """코사인 유사도 계산"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def evaluate_recall_at_k(self, k: int = 10) -> Dict[str, float]:
        """Recall@k 평가"""
        if not self.model or not self.embeddings or not self.metadata:
            raise RuntimeError("Artifacts not loaded")
        
        recalls = []
        
        for gold_query in self.gold_queries:
            query = gold_query["query"]
            expected_categories = gold_query["expected_categories"]
            
            # 쿼리 임베딩 생성
            prefixed_query = f"query: {query}"
            query_embedding = self.model.encode([prefixed_query], normalize_embeddings=True)[0]
            
            # 검색 실행
            similarities = []
            for i, embedding in enumerate(self.embeddings):
                sim = self.cosine_similarity(query_embedding, embedding)
                similarities.append((sim, i))
            
            similarities.sort(reverse=True)
            
            # 상위 k개 결과의 관련성 평가
            relevant_count = 0
            for sim, idx in similarities[:k]:
                category = self.metadata["metadatas"][idx].get("category", "N/A")
                doc = self.metadata["documents"][idx].lower()
                title = self.metadata["metadatas"][idx].get("title", "").lower()
                
                # 카테고리 매칭 또는 키워드 매칭
                is_relevant = (
                    category in expected_categories or
                    any(keyword in doc or keyword in title for keyword in query.lower().split())
                )
                
                if is_relevant:
                    relevant_count += 1
            
            recall = relevant_count / k
            recalls.append(recall)
        
        return {
            f"recall@{k}": statistics.mean(recalls),
            f"recall@{k}_std": statistics.stdev(recalls) if len(recalls) > 1 else 0,
            f"recall@{k}_min": min(recalls),
            f"recall@{k}_max": max(recalls)
        }
    
    def evaluate_ndcg_at_k(self, k: int = 10) -> Dict[str, float]:
        """nDCG@k 평가"""
        if not self.model or not self.embeddings or not self.metadata:
            raise RuntimeError("Artifacts not loaded")
        
        ndcgs = []
        
        for gold_query in self.gold_queries:
            query = gold_query["query"]
            expected_categories = gold_query["expected_categories"]
            
            # 쿼리 임베딩 생성
            prefixed_query = f"query: {query}"
            query_embedding = self.model.encode([prefixed_query], normalize_embeddings=True)[0]
            
            # 검색 실행
            similarities = []
            for i, embedding in enumerate(self.embeddings):
                sim = self.cosine_similarity(query_embedding, embedding)
                similarities.append((sim, i))
            
            similarities.sort(reverse=True)
            
            # DCG 계산
            dcg = 0
            for i, (sim, idx) in enumerate(similarities[:k]):
                category = self.metadata["metadatas"][idx].get("category", "N/A")
                doc = self.metadata["documents"][idx].lower()
                title = self.metadata["metadatas"][idx].get("title", "").lower()
                
                # 관련성 점수 (0 또는 1)
                is_relevant = (
                    category in expected_categories or
                    any(keyword in doc or keyword in title for keyword in query.lower().split())
                )
                
                relevance = 1 if is_relevant else 0
                dcg += relevance / np.log2(i + 2)
            
            # IDCG 계산 (이상적인 순서)
            ideal_relevances = []
            for sim, idx in similarities[:k]:
                category = self.metadata["metadatas"][idx].get("category", "N/A")
                doc = self.metadata["documents"][idx].lower()
                title = self.metadata["metadatas"][idx].get("title", "").lower()
                
                is_relevant = (
                    category in expected_categories or
                    any(keyword in doc or keyword in title for keyword in query.lower().split())
                )
                
                ideal_relevances.append(1 if is_relevant else 0)
            
            ideal_relevances.sort(reverse=True)
            idcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(ideal_relevances))
            
            # nDCG 계산
            ndcg = dcg / idcg if idcg > 0 else 0
            ndcgs.append(ndcg)
        
        return {
            f"ndcg@{k}": statistics.mean(ndcgs),
            f"ndcg@{k}_std": statistics.stdev(ndcgs) if len(ndcgs) > 1 else 0,
            f"ndcg@{k}_min": min(ndcgs),
            f"ndcg@{k}_max": max(ndcgs)
        }
    
    def evaluate_mrr(self) -> Dict[str, float]:
        """MRR (Mean Reciprocal Rank) 평가"""
        if not self.model or not self.embeddings or not self.metadata:
            raise RuntimeError("Artifacts not loaded")
        
        reciprocal_ranks = []
        
        for gold_query in self.gold_queries:
            query = gold_query["query"]
            expected_categories = gold_query["expected_categories"]
            
            # 쿼리 임베딩 생성
            prefixed_query = f"query: {query}"
            query_embedding = self.model.encode([prefixed_query], normalize_embeddings=True)[0]
            
            # 검색 실행
            similarities = []
            for i, embedding in enumerate(self.embeddings):
                sim = self.cosine_similarity(query_embedding, embedding)
                similarities.append((sim, i))
            
            similarities.sort(reverse=True)
            
            # 첫 번째 관련 결과의 순위 찾기
            first_relevant_rank = None
            for rank, (sim, idx) in enumerate(similarities[:20], 1):  # 상위 20개만 확인
                category = self.metadata["metadatas"][idx].get("category", "N/A")
                doc = self.metadata["documents"][idx].lower()
                title = self.metadata["metadatas"][idx].get("title", "").lower()
                
                is_relevant = (
                    category in expected_categories or
                    any(keyword in doc or keyword in title for keyword in query.lower().split())
                )
                
                if is_relevant and first_relevant_rank is None:
                    first_relevant_rank = rank
                    break
            
            # Reciprocal Rank 계산
            if first_relevant_rank is not None:
                reciprocal_ranks.append(1.0 / first_relevant_rank)
            else:
                reciprocal_ranks.append(0.0)
        
        return {
            "mrr": statistics.mean(reciprocal_ranks),
            "mrr_std": statistics.stdev(reciprocal_ranks) if len(reciprocal_ranks) > 1 else 0,
            "mrr_min": min(reciprocal_ranks),
            "mrr_max": max(reciprocal_ranks)
        }
    
    def generate_quality_report(self) -> Dict[str, Any]:
        """품질 리포트 생성"""
        logger.info("Generating quality report...")
        
        # 아티팩트 로드
        self.load_artifacts()
        
        # 평가 실행
        recall_10 = self.evaluate_recall_at_k(10)
        ndcg_10 = self.evaluate_ndcg_at_k(10)
        mrr = self.evaluate_mrr()
        
        # 리포트 생성
        report = {
            "timestamp": datetime.now().isoformat(),
            "evaluation": {
                "recall@10": recall_10,
                "ndcg@10": ndcg_10,
                "mrr": mrr
            },
            "system_info": {
                "total_chunks": len(self.metadata["ids"]),
                "embedding_dimension": self.embeddings.shape[1],
                "model": "intfloat/multilingual-e5-base",
                "gold_queries_count": len(self.gold_queries)
            },
            "slo_status": {
                "recall@10_ok": recall_10["recall@10"] >= 0.7,
                "ndcg@10_ok": ndcg_10["ndcg@10"] >= 0.6,
                "mrr_ok": mrr["mrr"] >= 0.5
            }
        }
        
        return report

class AlertManager:
    """알림 관리 클래스"""
    
    def __init__(self, smtp_config: Optional[Dict] = None):
        self.smtp_config = smtp_config or {}
        self.alert_thresholds = {
            "recall@10": 0.7,
            "ndcg@10": 0.6,
            "mrr": 0.5,
            "error_rate": 0.01,
            "p95_latency_ms": 200
        }
    
    def check_alerts(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """알림 조건 확인"""
        alerts = []
        
        # 품질 지표 알림
        evaluation = report.get("evaluation", {})
        slo_status = report.get("slo_status", {})
        
        for metric, threshold in self.alert_thresholds.items():
            if metric in evaluation:
                value = evaluation[metric]
                if isinstance(value, dict):
                    value = value.get(metric, 0)
                
                if value < threshold:
                    alerts.append({
                        "type": "quality_degradation",
                        "metric": metric,
                        "value": value,
                        "threshold": threshold,
                        "severity": "warning"
                    })
        
        return alerts
    
    def send_alert(self, alert: Dict[str, Any], recipients: List[str]):
        """알림 전송"""
        if not self.smtp_config:
            logger.warning("SMTP not configured, alert not sent")
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config.get('from_email')
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"Search Quality Alert: {alert['metric']}"
            
            body = f"""
            Quality Alert Detected
            
            Metric: {alert['metric']}
            Current Value: {alert['value']}
            Threshold: {alert['threshold']}
            Severity: {alert['severity']}
            
            Please investigate the search quality degradation.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_config['smtp_server'], self.smtp_config['smtp_port'])
            server.starttls()
            server.login(self.smtp_config['username'], self.smtp_config['password'])
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Alert sent to {recipients}")
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")

def run_quality_monitoring():
    """품질 모니터링 실행"""
    logger.info("Starting quality monitoring...")
    
    # 모니터 초기화
    monitor = QualityMonitor()
    
    # 리포트 생성
    report = monitor.generate_quality_report()
    
    # 리포트 저장
    report_path = f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Quality report saved to: {report_path}")
    
    # 알림 확인
    alert_manager = AlertManager()
    alerts = alert_manager.check_alerts(report)
    
    if alerts:
        logger.warning(f"Found {len(alerts)} alerts")
        for alert in alerts:
            logger.warning(f"Alert: {alert['metric']} = {alert['value']} (threshold: {alert['threshold']})")
    else:
        logger.info("No alerts detected")
    
    # 리포트 출력
    print("\n=== Quality Report ===")
    print(f"Timestamp: {report['timestamp']}")
    print(f"Total chunks: {report['system_info']['total_chunks']}")
    print(f"Recall@10: {report['evaluation']['recall@10']['recall@10']:.3f}")
    print(f"nDCG@10: {report['evaluation']['ndcg@10']['ndcg@10']:.3f}")
    print(f"MRR: {report['evaluation']['mrr']['mrr']:.3f}")
    
    return report

if __name__ == "__main__":
    run_quality_monitoring()




