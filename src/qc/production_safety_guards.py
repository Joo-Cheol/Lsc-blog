#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프로덕션 안전장치 - 워밍업, 서킷 브레이커, 세그먼트 운용
"""
import os
import json
import numpy as np
import time
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps
import psutil
import gc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

class CircuitBreaker:
    """서킷 브레이커"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.lock = threading.Lock()
    
    def call(self, func: Callable, *args, **kwargs):
        """서킷 브레이커를 통한 함수 호출"""
        with self.lock:
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                    logger.info("Circuit breaker: Attempting recovery")
                else:
                    raise Exception("Circuit breaker is OPEN")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                self._on_failure()
                raise e
    
    def _on_success(self):
        """성공 시 처리"""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info("Circuit breaker: Recovered to CLOSED")
    
    def _on_failure(self):
        """실패 시 처리"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker: OPENED after {self.failure_count} failures")

class WarmupManager:
    """워밍업 관리자"""
    
    def __init__(self, embeddings: np.ndarray, metadata: Dict[str, Any], model):
        self.embeddings = embeddings
        self.metadata = metadata
        self.model = model
        self.warmup_queries = [
            "채권추심 방법",
            "지급명령 신청",
            "압류 절차",
            "제3채무자 통지",
            "채권 회수 방법",
            "강제집행 신청",
            "가압류 절차",
            "경매 신청",
            "법원 신청",
            "집행 절차"
        ]
        self.warmup_completed = False
        self.warmup_start_time = None
        self.warmup_duration = None
    
    def run_warmup(self, num_queries: int = 200) -> Dict[str, Any]:
        """워밍업 실행"""
        logger.info(f"Starting warmup with {num_queries} queries...")
        self.warmup_start_time = time.time()
        
        # 메모리 매핑 페이지 예열
        self._preload_mmap_pages()
        
        # 모델 워밍업
        self._warmup_model()
        
        # 검색 워밍업
        self._warmup_search(num_queries)
        
        self.warmup_duration = time.time() - self.warmup_start_time
        self.warmup_completed = True
        
        logger.info(f"✅ Warmup completed in {self.warmup_duration:.2f}s")
        
        return {
            "warmup_completed": True,
            "duration_seconds": self.warmup_duration,
            "queries_processed": num_queries,
            "timestamp": datetime.now().isoformat()
        }
    
    def _preload_mmap_pages(self):
        """메모리 매핑 페이지 예열"""
        logger.info("Preloading memory-mapped pages...")
        
        # 임베딩 배열의 일부를 읽어서 페이지 폴트 유발
        chunk_size = min(1000, len(self.embeddings))
        for i in range(0, len(self.embeddings), chunk_size):
            _ = self.embeddings[i:i+chunk_size]
        
        # 메타데이터 접근
        _ = self.metadata["ids"][:100]
        _ = self.metadata["metadatas"][:100]
        _ = self.metadata["documents"][:100]
        
        logger.info("Memory-mapped pages preloaded")
    
    def _warmup_model(self):
        """모델 워밍업"""
        logger.info("Warming up model...")
        
        # 간단한 텍스트로 모델 워밍업
        warmup_texts = ["query: 테스트", "passage: 테스트 문서"]
        _ = self.model.encode(warmup_texts, normalize_embeddings=True)
        
        logger.info("Model warmed up")
    
    def _warmup_search(self, num_queries: int):
        """검색 워밍업"""
        logger.info(f"Warming up search with {num_queries} queries...")
        
        # 워밍업 쿼리 반복
        for i in range(num_queries):
            query = self.warmup_queries[i % len(self.warmup_queries)]
            
            # 쿼리 임베딩 생성
            prefixed_query = f"query: {query}"
            query_embedding = self.model.encode([prefixed_query], normalize_embeddings=True)[0]
            
            # 검색 실행 (상위 10개만)
            similarities = []
            for j, embedding in enumerate(self.embeddings[:1000]):  # 샘플만
                sim = np.dot(query_embedding, embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(embedding))
                similarities.append((sim, j))
            
            similarities.sort(reverse=True)
            _ = similarities[:10]  # 결과 사용
        
        logger.info("Search warmed up")

class SegmentManager:
    """세그먼트 관리자"""
    
    def __init__(self, base_path: str = "artifacts"):
        self.base_path = Path(base_path)
        self.segments = []
        self.current_version = None
        self.lock = threading.Lock()
    
    def load_segments(self) -> Dict[str, Any]:
        """세그먼트 로드"""
        logger.info("Loading segments...")
        
        with self.lock:
            if not self.base_path.exists():
                raise FileNotFoundError(f"Base path not found: {self.base_path}")
            
            # 버전 디렉토리 찾기
            versions = [d for d in self.base_path.iterdir() if d.is_dir()]
            if not versions:
                raise FileNotFoundError("No segment versions found")
            
            # 최신 버전 선택
            self.current_version = max(versions, key=lambda x: x.name)
            logger.info(f"Loading version: {self.current_version.name}")
            
            # 세그먼트 파일 확인
            index_file = self.current_version / "simple_vector_index.npy"
            metadata_file = self.current_version / "simple_metadata.json"
            
            if not index_file.exists() or not metadata_file.exists():
                raise FileNotFoundError("Required segment files not found")
            
            # 세그먼트 정보 저장
            segment_info = {
                "version": self.current_version.name,
                "index_file": str(index_file),
                "metadata_file": str(metadata_file),
                "created_at": datetime.fromtimestamp(index_file.stat().st_mtime).isoformat()
            }
            
            self.segments = [segment_info]
            
            logger.info(f"✅ Loaded {len(self.segments)} segments")
            
            return {
                "segments_loaded": len(self.segments),
                "current_version": self.current_version.name,
                "segment_info": segment_info
            }
    
    def validate_segment_integrity(self, segment_path: str) -> Dict[str, Any]:
        """세그먼트 무결성 검증"""
        logger.info(f"Validating segment integrity: {segment_path}")
        
        segment_path = Path(segment_path)
        index_file = segment_path / "simple_vector_index.npy"
        metadata_file = segment_path / "simple_metadata.json"
        
        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "segment_path": str(segment_path),
            "checks": {},
            "passed": True
        }
        
        try:
            # 파일 존재 확인
            if not index_file.exists() or not metadata_file.exists():
                validation_results["checks"]["file_existence"] = {
                    "passed": False,
                    "error": "Required files not found"
                }
                validation_results["passed"] = False
                return validation_results
            
            # 임베딩 로드 및 검증
            embeddings = np.load(index_file, mmap_mode='r')
            validation_results["checks"]["embedding_load"] = {
                "passed": True,
                "shape": embeddings.shape,
                "dtype": str(embeddings.dtype)
            }
            
            # 메타데이터 로드 및 검증
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            validation_results["checks"]["metadata_load"] = {
                "passed": True,
                "ids_count": len(metadata["ids"]),
                "metadatas_count": len(metadata["metadatas"]),
                "documents_count": len(metadata["documents"])
            }
            
            # 길이 일치 검증
            if len(metadata["ids"]) != len(embeddings):
                validation_results["checks"]["length_consistency"] = {
                    "passed": False,
                    "error": f"Length mismatch: {len(metadata['ids'])} vs {len(embeddings)}"
                }
                validation_results["passed"] = False
            else:
                validation_results["checks"]["length_consistency"] = {
                    "passed": True,
                    "count": len(metadata["ids"])
                }
            
            # ID 유니크 검증
            unique_ids = set(metadata["ids"])
            if len(unique_ids) != len(metadata["ids"]):
                validation_results["checks"]["id_uniqueness"] = {
                    "passed": False,
                    "error": f"Duplicate IDs found: {len(metadata['ids']) - len(unique_ids)}"
                }
                validation_results["passed"] = False
            else:
                validation_results["checks"]["id_uniqueness"] = {
                    "passed": True,
                    "unique_count": len(unique_ids)
                }
            
        except Exception as e:
            validation_results["checks"]["general_error"] = {
                "passed": False,
                "error": str(e)
            }
            validation_results["passed"] = False
        
        logger.info(f"Segment validation: {'✅ PASSED' if validation_results['passed'] else '❌ FAILED'}")
        
        return validation_results
    
    def create_incremental_segment(self, new_data: Dict[str, Any], version_suffix: str = None) -> str:
        """증분 세그먼트 생성"""
        logger.info("Creating incremental segment...")
        
        if version_suffix is None:
            version_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        new_version_dir = self.base_path / f"incremental_{version_suffix}"
        new_version_dir.mkdir(parents=True, exist_ok=True)
        
        # 새 데이터 저장
        index_file = new_version_dir / "simple_vector_index.npy"
        metadata_file = new_version_dir / "simple_metadata.json"
        
        # 임베딩 저장
        np.save(index_file, new_data["embeddings"])
        
        # 메타데이터 저장
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(new_data["metadata"], f, ensure_ascii=False, indent=2)
        
        # 무결성 검증
        validation = self.validate_segment_integrity(new_version_dir)
        
        if validation["passed"]:
            logger.info(f"✅ Incremental segment created: {new_version_dir.name}")
            return str(new_version_dir)
        else:
            logger.error(f"❌ Incremental segment validation failed")
            # 실패한 세그먼트 삭제
            import shutil
            shutil.rmtree(new_version_dir)
            raise Exception("Incremental segment validation failed")

class LoggingGuard:
    """로깅 가드"""
    
    def __init__(self):
        self.pii_patterns = [
            r'\d{3}-\d{4}-\d{4}',  # 전화번호
            r'\d{6}-\d{7}',        # 주민번호
            r'\d{3}-\d{2}-\d{5}',  # 계좌번호
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'  # 이메일
        ]
        self.sensitive_fields = ['content', 'text', 'document', 'snippet']
    
    def sanitize_log_data(self, data: Any) -> Any:
        """로그 데이터 정화"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if key.lower() in self.sensitive_fields:
                    # 민감한 필드는 해시로 대체
                    if isinstance(value, str) and len(value) > 0:
                        import hashlib
                        sanitized[key] = f"[HASH:{hashlib.md5(value.encode()).hexdigest()[:8]}]"
                    else:
                        sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = self.sanitize_log_data(value)
            return sanitized
        elif isinstance(data, list):
            return [self.sanitize_log_data(item) for item in data]
        elif isinstance(data, str):
            # PII 패턴 마스킹
            import re
            for pattern in self.pii_patterns:
                data = re.sub(pattern, '[MASKED]', data)
            return data
        else:
            return data
    
    def safe_log(self, level: str, message: str, data: Any = None):
        """안전한 로깅"""
        if data is not None:
            sanitized_data = self.sanitize_log_data(data)
            getattr(logger, level)(f"{message}: {sanitized_data}")
        else:
            getattr(logger, level)(message)

class SystemMonitor:
    """시스템 모니터"""
    
    def __init__(self):
        self.monitoring = False
        self.monitor_thread = None
        self.metrics_history = []
        self.max_history = 100
    
    def start_monitoring(self, interval: int = 30):
        """모니터링 시작"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("System monitoring started")
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        
        logger.info("System monitoring stopped")
    
    def _monitor_loop(self, interval: int):
        """모니터링 루프"""
        while self.monitoring:
            try:
                metrics = self._collect_metrics()
                self.metrics_history.append(metrics)
                
                # 히스토리 크기 제한
                if len(self.metrics_history) > self.max_history:
                    self.metrics_history.pop(0)
                
                # 임계값 체크
                self._check_thresholds(metrics)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
            
            time.sleep(interval)
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """메트릭 수집"""
        # CPU 사용률
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 메모리 사용률
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # 디스크 사용률
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # 프로세스 정보
        process = psutil.Process()
        process_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "disk_percent": disk_percent,
            "process_memory_mb": process_memory
        }
    
    def _check_thresholds(self, metrics: Dict[str, Any]):
        """임계값 체크"""
        # CPU 임계값 (80%)
        if metrics["cpu_percent"] > 80:
            logger.warning(f"High CPU usage: {metrics['cpu_percent']:.1f}%")
        
        # 메모리 임계값 (85%)
        if metrics["memory_percent"] > 85:
            logger.warning(f"High memory usage: {metrics['memory_percent']:.1f}%")
        
        # 디스크 임계값 (90%)
        if metrics["disk_percent"] > 90:
            logger.warning(f"High disk usage: {metrics['disk_percent']:.1f}%")
        
        # 프로세스 메모리 임계값 (2GB)
        if metrics["process_memory_mb"] > 2048:
            logger.warning(f"High process memory: {metrics['process_memory_mb']:.1f}MB")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """메트릭 요약"""
        if not self.metrics_history:
            return {"status": "no_data"}
        
        recent_metrics = self.metrics_history[-10:]  # 최근 10개
        
        return {
            "status": "monitoring",
            "sample_count": len(recent_metrics),
            "cpu_avg": sum(m["cpu_percent"] for m in recent_metrics) / len(recent_metrics),
            "memory_avg": sum(m["memory_percent"] for m in recent_metrics) / len(recent_metrics),
            "disk_avg": sum(m["disk_percent"] for m in recent_metrics) / len(recent_metrics),
            "process_memory_avg": sum(m["process_memory_mb"] for m in recent_metrics) / len(recent_metrics)
        }

def main():
    """메인 함수"""
    # 안전장치 테스트
    logger.info("Testing production safety guards...")
    
    # 서킷 브레이커 테스트
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=10)
    
    def failing_function():
        raise Exception("Test failure")
    
    def working_function():
        return "success"
    
    # 실패 테스트
    for i in range(3):
        try:
            cb.call(failing_function)
        except Exception as e:
            logger.info(f"Failure {i+1}: {e}")
    
    # 서킷 브레이커 열림 테스트
    try:
        cb.call(failing_function)
    except Exception as e:
        logger.info(f"Circuit breaker open: {e}")
    
    # 복구 테스트
    time.sleep(11)
    try:
        result = cb.call(working_function)
        logger.info(f"Recovery successful: {result}")
    except Exception as e:
        logger.info(f"Recovery failed: {e}")
    
    # 로깅 가드 테스트
    guard = LoggingGuard()
    test_data = {
        "id": "test123",
        "content": "전화번호는 010-1234-5678이고 이메일은 test@example.com입니다.",
        "metadata": {"category": "test"}
    }
    
    guard.safe_log("info", "Test log", test_data)
    
    # 시스템 모니터 테스트
    monitor = SystemMonitor()
    monitor.start_monitoring(interval=5)
    
    time.sleep(15)
    
    summary = monitor.get_metrics_summary()
    logger.info(f"System metrics: {summary}")
    
    monitor.stop_monitoring()
    
    logger.info("✅ Safety guards test completed")

if __name__ == "__main__":
    main()




