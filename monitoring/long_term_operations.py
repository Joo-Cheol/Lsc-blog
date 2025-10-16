#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
장기 운영 관점 - 메모리/조각화, 데이터 드리프트, Chroma 재도입
"""
import os
import json
import numpy as np
import time
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import gc
import psutil
from collections import Counter, defaultdict
import hashlib

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

class MemoryCompactionManager:
    """메모리 압축 관리자"""
    
    def __init__(self, artifacts_base_path: str = "artifacts"):
        self.artifacts_base_path = Path(artifacts_base_path)
        self.compaction_threshold = 0.8  # 80% 이상 조각화 시 압축
        self.max_segments = 10  # 최대 세그먼트 수
    
    def analyze_memory_fragmentation(self) -> Dict[str, Any]:
        """메모리 조각화 분석"""
        logger.info("Analyzing memory fragmentation...")
        
        # 세그먼트 정보 수집
        segments = []
        if self.artifacts_base_path.exists():
            for version_dir in self.artifacts_base_path.iterdir():
                if version_dir.is_dir():
                    index_file = version_dir / "simple_vector_index.npy"
                    metadata_file = version_dir / "simple_metadata.json"
                    
                    if index_file.exists() and metadata_file.exists():
                        segment_info = {
                            "version": version_dir.name,
                            "index_size": index_file.stat().st_size,
                            "metadata_size": metadata_file.stat().st_size,
                            "created_at": datetime.fromtimestamp(index_file.stat().st_mtime),
                            "path": str(version_dir)
                        }
                        segments.append(segment_info)
        
        # 조각화 지표 계산
        total_segments = len(segments)
        total_size = sum(s["index_size"] + s["metadata_size"] for s in segments)
        
        # 크기 분포 분석
        size_distribution = Counter()
        for segment in segments:
            size_mb = (segment["index_size"] + segment["metadata_size"]) / (1024 * 1024)
            size_bucket = int(size_mb / 100) * 100  # 100MB 단위로 버킷팅
            size_distribution[size_bucket] += 1
        
        fragmentation_analysis = {
            "total_segments": total_segments,
            "total_size_mb": total_size / (1024 * 1024),
            "size_distribution": dict(size_distribution),
            "fragmentation_ratio": total_segments / max(1, total_size / (1024 * 1024 * 100)),  # 100MB당 세그먼트 수
            "needs_compaction": total_segments > self.max_segments or (total_segments / max(1, total_size / (1024 * 1024 * 100))) > self.compaction_threshold,
            "segments": segments
        }
        
        logger.info(f"Fragmentation analysis: {total_segments} segments, {fragmentation_analysis['fragmentation_ratio']:.2f} ratio")
        
        return fragmentation_analysis
    
    def compact_segments(self, target_segments: int = 3) -> str:
        """세그먼트 압축"""
        logger.info(f"Compacting segments to {target_segments}...")
        
        # 현재 세그먼트 분석
        fragmentation = self.analyze_memory_fragmentation()
        segments = fragmentation["segments"]
        
        if len(segments) <= target_segments:
            logger.info("No compaction needed")
            return None
        
        # 세그먼트 정렬 (최신순)
        segments.sort(key=lambda x: x["created_at"], reverse=True)
        
        # 압축할 세그먼트 선택 (오래된 것부터)
        segments_to_compact = segments[target_segments:]
        keep_segments = segments[:target_segments]
        
        logger.info(f"Compacting {len(segments_to_compact)} segments, keeping {len(keep_segments)}")
        
        # 압축 실행
        compacted_version = f"compacted_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        compacted_path = self.artifacts_base_path / compacted_version
        compacted_path.mkdir(parents=True, exist_ok=True)
        
        # 모든 세그먼트 데이터 로드 및 결합
        all_embeddings = []
        all_metadata = {
            "ids": [],
            "metadatas": [],
            "documents": []
        }
        
        for segment in segments:
            segment_path = Path(segment["path"])
            index_file = segment_path / "simple_vector_index.npy"
            metadata_file = segment_path / "simple_metadata.json"
            
            # 임베딩 로드
            embeddings = np.load(index_file, mmap_mode='r')
            all_embeddings.append(embeddings)
            
            # 메타데이터 로드
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            all_metadata["ids"].extend(metadata["ids"])
            all_metadata["metadatas"].extend(metadata["metadatas"])
            all_metadata["documents"].extend(metadata["documents"])
        
        # 결합된 데이터 저장
        combined_embeddings = np.vstack(all_embeddings)
        np.save(compacted_path / "simple_vector_index.npy", combined_embeddings)
        
        with open(compacted_path / "simple_metadata.json", "w", encoding="utf-8") as f:
            json.dump(all_metadata, f, ensure_ascii=False, indent=2)
        
        # 압축된 세그먼트 검증
        validation_result = self._validate_compacted_segment(compacted_path)
        
        if validation_result["passed"]:
            # 기존 세그먼트 백업 및 삭제
            backup_path = self.artifacts_base_path / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path.mkdir(parents=True, exist_ok=True)
            
            for segment in segments:
                segment_path = Path(segment["path"])
                if segment_path.exists():
                    shutil.move(str(segment_path), str(backup_path / segment_path.name))
            
            logger.info(f"✅ Compaction completed: {compacted_version}")
            logger.info(f"Backup created: {backup_path}")
            
            return str(compacted_path)
        else:
            logger.error("Compaction validation failed")
            shutil.rmtree(compacted_path)
            return None
    
    def _validate_compacted_segment(self, segment_path: Path) -> Dict[str, Any]:
        """압축된 세그먼트 검증"""
        try:
            # 파일 존재 확인
            index_file = segment_path / "simple_vector_index.npy"
            metadata_file = segment_path / "simple_metadata.json"
            
            if not index_file.exists() or not metadata_file.exists():
                return {"passed": False, "error": "Files not found"}
            
            # 임베딩 로드
            embeddings = np.load(index_file, mmap_mode='r')
            
            # 메타데이터 로드
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            # 길이 일치 확인
            if len(embeddings) != len(metadata["ids"]):
                return {"passed": False, "error": "Length mismatch"}
            
            # ID 유니크 확인
            unique_ids = set(metadata["ids"])
            if len(unique_ids) != len(metadata["ids"]):
                return {"passed": False, "error": "Duplicate IDs"}
            
            return {"passed": True, "count": len(embeddings)}
            
        except Exception as e:
            return {"passed": False, "error": str(e)}

class DataDriftDetector:
    """데이터 드리프트 감지기"""
    
    def __init__(self):
        self.baseline_stats = None
        self.drift_threshold = 0.1  # 10% 변화 시 드리프트 감지
        self.legal_terms = {
            "채권추심": ["채권추심", "추심", "채권회수"],
            "지급명령": ["지급명령", "독촉절차", "지명채권"],
            "압류": ["압류", "채권압류", "가압류"],
            "강제집행": ["강제집행", "집행", "집행절차"],
            "제3채무자": ["제3채무자", "제삼채무자", "압류명령"]
        }
    
    def establish_baseline(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """베이스라인 통계 설정"""
        logger.info("Establishing baseline statistics...")
        
        # 카테고리 분포
        categories = [meta.get("category", "N/A") for meta in metadata["metadatas"]]
        category_distribution = Counter(categories)
        
        # 문서 길이 분포
        doc_lengths = [len(doc) for doc in metadata["documents"]]
        
        # 키워드 분포
        keyword_counts = defaultdict(int)
        for doc in metadata["documents"]:
            doc_lower = doc.lower()
            for term, synonyms in self.legal_terms.items():
                for synonym in synonyms:
                    if synonym in doc_lower:
                        keyword_counts[term] += 1
                        break
        
        # 날짜 분포
        dates = []
        for meta in metadata["metadatas"]:
            date_str = meta.get("date", "")
            if date_str:
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    dates.append(date_obj)
                except:
                    pass
        
        baseline = {
            "timestamp": datetime.now().isoformat(),
            "total_documents": len(metadata["documents"]),
            "category_distribution": dict(category_distribution),
            "document_length": {
                "mean": np.mean(doc_lengths),
                "std": np.std(doc_lengths),
                "min": min(doc_lengths),
                "max": max(doc_lengths)
            },
            "keyword_distribution": dict(keyword_counts),
            "date_range": {
                "earliest": min(dates).isoformat() if dates else None,
                "latest": max(dates).isoformat() if dates else None
            }
        }
        
        self.baseline_stats = baseline
        logger.info("Baseline statistics established")
        
        return baseline
    
    def detect_drift(self, current_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """드리프트 감지"""
        if self.baseline_stats is None:
            logger.warning("No baseline established, creating new baseline")
            return self.establish_baseline(current_metadata)
        
        logger.info("Detecting data drift...")
        
        # 현재 통계 계산
        current_stats = self._calculate_current_stats(current_metadata)
        
        # 드리프트 분석
        drift_analysis = {
            "timestamp": datetime.now().isoformat(),
            "drift_detected": False,
            "drift_indicators": [],
            "changes": {}
        }
        
        # 카테고리 분포 변화
        baseline_cats = self.baseline_stats["category_distribution"]
        current_cats = current_stats["category_distribution"]
        
        category_changes = {}
        for category in set(list(baseline_cats.keys()) + list(current_cats.keys())):
            baseline_count = baseline_cats.get(category, 0)
            current_count = current_cats.get(category, 0)
            
            if baseline_count > 0:
                change_ratio = (current_count - baseline_count) / baseline_count
                category_changes[category] = change_ratio
                
                if abs(change_ratio) > self.drift_threshold:
                    drift_analysis["drift_detected"] = True
                    drift_analysis["drift_indicators"].append(f"Category '{category}' changed by {change_ratio:.1%}")
        
        drift_analysis["changes"]["category_distribution"] = category_changes
        
        # 문서 길이 변화
        baseline_length = self.baseline_stats["document_length"]
        current_length = current_stats["document_length"]
        
        length_change = (current_length["mean"] - baseline_length["mean"]) / baseline_length["mean"]
        drift_analysis["changes"]["document_length"] = {
            "mean_change_ratio": length_change,
            "baseline_mean": baseline_length["mean"],
            "current_mean": current_length["mean"]
        }
        
        if abs(length_change) > self.drift_threshold:
            drift_analysis["drift_detected"] = True
            drift_analysis["drift_indicators"].append(f"Document length changed by {length_change:.1%}")
        
        # 키워드 분포 변화
        baseline_keywords = self.baseline_stats["keyword_distribution"]
        current_keywords = current_stats["keyword_distribution"]
        
        keyword_changes = {}
        for keyword in set(list(baseline_keywords.keys()) + list(current_keywords.keys())):
            baseline_count = baseline_keywords.get(keyword, 0)
            current_count = current_keywords.get(keyword, 0)
            
            if baseline_count > 0:
                change_ratio = (current_count - baseline_count) / baseline_count
                keyword_changes[keyword] = change_ratio
                
                if abs(change_ratio) > self.drift_threshold:
                    drift_analysis["drift_detected"] = True
                    drift_analysis["drift_indicators"].append(f"Keyword '{keyword}' changed by {change_ratio:.1%}")
        
        drift_analysis["changes"]["keyword_distribution"] = keyword_changes
        
        # 드리프트 심각도 평가
        if drift_analysis["drift_detected"]:
            severity = "high" if len(drift_analysis["drift_indicators"]) > 3 else "medium"
            drift_analysis["severity"] = severity
        
        logger.info(f"Drift detection: {'DETECTED' if drift_analysis['drift_detected'] else 'NONE'}")
        
        return drift_analysis
    
    def _calculate_current_stats(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """현재 통계 계산"""
        # 카테고리 분포
        categories = [meta.get("category", "N/A") for meta in metadata["metadatas"]]
        category_distribution = Counter(categories)
        
        # 문서 길이 분포
        doc_lengths = [len(doc) for doc in metadata["documents"]]
        
        # 키워드 분포
        keyword_counts = defaultdict(int)
        for doc in metadata["documents"]:
            doc_lower = doc.lower()
            for term, synonyms in self.legal_terms.items():
                for synonym in synonyms:
                    if synonym in doc_lower:
                        keyword_counts[term] += 1
                        break
        
        return {
            "total_documents": len(metadata["documents"]),
            "category_distribution": dict(category_distribution),
            "document_length": {
                "mean": np.mean(doc_lengths),
                "std": np.std(doc_lengths),
                "min": min(doc_lengths),
                "max": max(doc_lengths)
            },
            "keyword_distribution": dict(keyword_counts)
        }
    
    def update_legal_terms(self, new_terms: Dict[str, List[str]]):
        """법률 용어 사전 업데이트"""
        logger.info("Updating legal terms dictionary...")
        
        for term, synonyms in new_terms.items():
            if term in self.legal_terms:
                # 기존 용어 확장
                self.legal_terms[term].extend(synonyms)
                self.legal_terms[term] = list(set(self.legal_terms[term]))  # 중복 제거
            else:
                # 새 용어 추가
                self.legal_terms[term] = synonyms
        
        logger.info(f"Updated legal terms: {len(self.legal_terms)} terms")

class ChromaReintroductionManager:
    """Chroma 재도입 관리자"""
    
    def __init__(self, chroma_path: str = "data/indexes/chroma"):
        self.chroma_path = Path(chroma_path)
        self.safe_mode_config = {
            "batch_size": 1000,  # 작은 배치 크기
            "persist_frequency": "end_only",  # 마지막에만 persist
            "use_add_instead_of_upsert": True,  # upsert 대신 add 사용
            "enable_telemetry": False,  # 텔레메트리 비활성화
            "hnsw_parameters": {
                "M": 16,  # 기본값 (성능 우선)
                "efConstruction": 100,  # 기본값
                "efSearch": 50  # 기본값
            }
        }
    
    def prepare_safe_chroma_setup(self) -> Dict[str, Any]:
        """안전한 Chroma 설정 준비"""
        logger.info("Preparing safe Chroma setup...")
        
        # 기존 Chroma 데이터 백업
        backup_path = self.chroma_path.parent / f"chroma_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if self.chroma_path.exists():
            shutil.copytree(self.chroma_path, backup_path)
            logger.info(f"Chroma backup created: {backup_path}")
        
        # 안전한 설정 생성
        safe_config = {
            "chroma_path": str(self.chroma_path),
            "backup_path": str(backup_path),
            "safe_mode_config": self.safe_mode_config,
            "migration_plan": {
                "phase1": "Create new collection with safe parameters",
                "phase2": "Migrate data in small batches",
                "phase3": "Validate migration results",
                "phase4": "Switch to new collection",
                "phase5": "Cleanup old data"
            }
        }
        
        return safe_config
    
    def create_safe_chroma_script(self, embeddings: np.ndarray, metadata: Dict[str, Any]) -> str:
        """안전한 Chroma 스크립트 생성"""
        script_content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
안전한 Chroma 재도입 스크립트
"""
import os
import json
import numpy as np
import time
import logging
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

# 환경 가드 설정
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def safe_chroma_migration():
    """안전한 Chroma 마이그레이션"""
    logger.info("Starting safe Chroma migration...")
    
    # Chroma 클라이언트 설정
    chroma_path = "{self.chroma_path}"
    client = chromadb.PersistentClient(
        path=chroma_path,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    
    # 컬렉션 생성 (안전한 파라미터)
    collection_name = "legal_blog_safe"
    try:
        # 기존 컬렉션 삭제 (있다면)
        try:
            client.delete_collection(name=collection_name)
            logger.info("Deleted existing collection")
        except:
            pass
        
        # 새 컬렉션 생성
        collection = client.create_collection(
            name=collection_name,
            metadata={{"hnsw:space": "cosine"}}
        )
        logger.info(f"Created new collection: {{collection_name}}")
        
    except Exception as e:
        logger.error(f"Collection creation failed: {{e}}")
        return False
    
    # 모델 로드
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer("intfloat/multilingual-e5-base", device=device)
    model.max_seq_length = 512
    
    # 데이터 로드
    embeddings = np.load("simple_vector_index.npy", mmap_mode='r')
    
    with open("simple_metadata.json", "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    logger.info(f"Loaded {{len(embeddings)}} embeddings and {{len(metadata['ids'])}} documents")
    
    # 안전한 배치 처리
    batch_size = {self.safe_mode_config['batch_size']}
    total_batches = (len(embeddings) + batch_size - 1) // batch_size
    
    for i in range(0, len(embeddings), batch_size):
        batch_num = i // batch_size + 1
        logger.info(f"Processing batch {{batch_num}}/{{total_batches}}")
        
        # 배치 데이터 준비
        end_idx = min(i + batch_size, len(embeddings))
        batch_embeddings = embeddings[i:end_idx]
        batch_ids = metadata["ids"][i:end_idx]
        batch_metadatas = metadata["metadatas"][i:end_idx]
        batch_documents = metadata["documents"][i:end_idx]
        
        # 메타데이터 정리
        cleaned_metadatas = []
        for meta in batch_metadatas:
            cleaned_meta = {{}}
            for key, value in meta.items():
                if value is None:
                    cleaned_meta[key] = ""
                else:
                    cleaned_meta[key] = str(value)
            cleaned_metadatas.append(cleaned_meta)
        
        try:
            # 안전한 추가 (upsert 대신 add 사용)
            collection.add(
                ids=batch_ids,
                embeddings=batch_embeddings.tolist(),
                metadatas=cleaned_metadatas,
                documents=batch_documents
            )
            
            logger.info(f"Batch {{batch_num}} added successfully")
            
        except Exception as e:
            logger.error(f"Batch {{batch_num}} failed: {{e}}")
            continue
        
        # 배치 간 잠시 대기 (시스템 부하 방지)
        time.sleep(0.1)
    
    # 마지막에 한 번만 persist (PersistentClient는 자동으로 처리)
    logger.info("Migration completed successfully")
    
    # 검증
    final_count = collection.count()
    logger.info(f"Final collection count: {{final_count}}")
    
    if final_count == len(embeddings):
        logger.info("✅ Migration validation passed")
        return True
    else:
        logger.error(f"❌ Migration validation failed: {{final_count}} != {{len(embeddings)}}")
        return False

if __name__ == "__main__":
    success = safe_chroma_migration()
    if success:
        print("✅ Safe Chroma migration completed successfully")
    else:
        print("❌ Safe Chroma migration failed")
'''
        
        # 스크립트 저장
        script_path = "safe_chroma_migration.py"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        
        logger.info(f"Safe Chroma script created: {script_path}")
        return script_path
    
    def validate_chroma_migration(self, collection_name: str = "legal_blog_safe") -> Dict[str, Any]:
        """Chroma 마이그레이션 검증"""
        logger.info("Validating Chroma migration...")
        
        try:
            import chromadb
            
            client = chromadb.PersistentClient(path=str(self.chroma_path))
            collection = client.get_collection(name=collection_name)
            
            # 기본 검증
            count = collection.count()
            
            # 샘플 쿼리 테스트
            test_queries = ["채권추심 방법", "지급명령 신청"]
            query_results = []
            
            for query in test_queries:
                try:
                    results = collection.query(
                        query_texts=[query],
                        n_results=5,
                        include=["distances", "metadatas", "documents"]
                    )
                    query_results.append({
                        "query": query,
                        "result_count": len(results["ids"][0]) if results["ids"] else 0,
                        "success": True
                    })
                except Exception as e:
                    query_results.append({
                        "query": query,
                        "error": str(e),
                        "success": False
                    })
            
            validation_result = {
                "timestamp": datetime.now().isoformat(),
                "collection_name": collection_name,
                "total_documents": count,
                "query_tests": query_results,
                "validation_passed": all(r["success"] for r in query_results),
                "recommendations": []
            }
            
            if count == 0:
                validation_result["recommendations"].append("Collection is empty, check migration process")
            
            if not validation_result["validation_passed"]:
                validation_result["recommendations"].append("Query tests failed, check collection integrity")
            
            logger.info(f"Chroma validation: {'✅ PASSED' if validation_result['validation_passed'] else '❌ FAILED'}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Chroma validation error: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "validation_passed": False,
                "error": str(e)
            }

def main():
    """메인 함수"""
    logger.info("Testing long-term operations...")
    
    # 메모리 압축 테스트
    compaction_manager = MemoryCompactionManager()
    fragmentation = compaction_manager.analyze_memory_fragmentation()
    logger.info(f"Fragmentation analysis: {fragmentation['total_segments']} segments")
    
    # 데이터 드리프트 감지 테스트
    drift_detector = DataDriftDetector()
    
    # 샘플 메타데이터로 베이스라인 설정
    sample_metadata = {
        "ids": ["doc1", "doc2", "doc3"],
        "metadatas": [
            {"category": "채권추심", "date": "2024-01-01"},
            {"category": "채권추심", "date": "2024-01-02"},
            {"category": "법무법인", "date": "2024-01-03"}
        ],
        "documents": [
            "채권추심 방법에 대한 문서입니다.",
            "지급명령 신청 절차를 설명합니다.",
            "법무법인 소개 내용입니다."
        ]
    }
    
    baseline = drift_detector.establish_baseline(sample_metadata)
    logger.info(f"Baseline established: {baseline['total_documents']} documents")
    
    # Chroma 재도입 준비 테스트
    chroma_manager = ChromaReintroductionManager()
    safe_config = chroma_manager.prepare_safe_chroma_setup()
    logger.info(f"Safe Chroma config prepared: {safe_config['chroma_path']}")
    
    logger.info("✅ Long-term operations test completed")

if __name__ == "__main__":
    main()




