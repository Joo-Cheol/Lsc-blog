#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Job 시스템 테스트
"""
import pytest
import asyncio
import json
import time
from datetime import datetime
from api.core.jobs import JobRegistry, JobState, JobEvent, JOBS


class TestJobRegistry:
    """JobRegistry 테스트"""
    
    def test_create_job(self):
        """Job 생성 테스트"""
        registry = JobRegistry(max_jobs=10, ttl_hours=1)
        job = registry.create("crawl")
        
        assert job.id is not None
        assert job.type == "crawl"
        assert job.status == "queued"
        assert job.progress == 0.0
        assert len(job.events) == 0
        
        # 레지스트리에 저장되었는지 확인
        retrieved = registry.get(job.id)
        assert retrieved is not None
        assert retrieved.id == job.id

    def test_job_events(self):
        """Job 이벤트 테스트"""
        job = JOBS.create("crawl")
        
        # 이벤트 추가
        event1 = job.push("info", "크롤링 시작")
        event2 = job.push("progress", "50% 완료", progress=0.5)
        
        assert len(job.events) == 2
        assert event1.type == "info"
        assert event1.message == "크롤링 시작"
        assert event2.data["progress"] == 0.5

    def test_structured_errors(self):
        """구조화된 에러 테스트"""
        job = JOBS.create("crawl")
        
        job.add_error("CRAWL_FAILED", "네트워크 오류", "잠시 후 다시 시도해주세요")
        
        assert len(job.errors) == 1
        error = job.errors[0]
        assert error["code"] == "CRAWL_FAILED"
        assert error["message"] == "네트워크 오류"
        assert error["suggestion"] == "잠시 후 다시 시도해주세요"
        assert "timestamp" in error

    def test_events_since(self):
        """이벤트 since 기능 테스트"""
        job = JOBS.create("crawl")
        
        # 이벤트 추가
        job.push("info", "이벤트 1")
        job.push("info", "이벤트 2")
        job.push("info", "이벤트 3")
        
        # 특정 이벤트 ID 이후 조회
        events_since = job.get_events_since(1)
        assert len(events_since) == 2
        assert events_since[0].message == "이벤트 2"
        assert events_since[1].message == "이벤트 3"

    def test_ttl_cleanup(self):
        """TTL 정리 테스트"""
        registry = JobRegistry(max_jobs=5, ttl_hours=0)  # 즉시 만료
        
        # Job 생성
        job = registry.create("crawl")
        job.status = "succeeded"
        
        # TTL 정리 실행
        registry._cleanup_old_jobs()
        
        # Job이 정리되었는지 확인
        assert registry.get(job.id) is None

    def test_lru_cleanup(self):
        """LRU 정리 테스트"""
        registry = JobRegistry(max_jobs=3, ttl_hours=24)
        
        # 최대 개수 초과 Job 생성
        jobs = []
        for i in range(5):
            job = registry.create("crawl")
            job.status = "succeeded"
            jobs.append(job)
        
        # LRU 정리 실행
        registry._cleanup_old_jobs()
        
        # 최대 개수 이하로 정리되었는지 확인
        assert len(registry._jobs) <= 3

    def test_job_stats(self):
        """Job 통계 테스트"""
        registry = JobRegistry()
        
        # 다양한 상태의 Job 생성
        job1 = registry.create("crawl")
        job1.status = "running"
        
        job2 = registry.create("preprocess_embed")
        job2.status = "succeeded"
        
        job3 = registry.create("crawl")
        job3.status = "failed"
        
        stats = registry.get_stats()
        
        assert stats["total_jobs"] == 3
        assert stats["status_counts"]["running"] == 1
        assert stats["status_counts"]["succeeded"] == 1
        assert stats["status_counts"]["failed"] == 1


class TestJobIntegration:
    """Job 통합 테스트"""
    
    def test_crawl_job_lifecycle(self):
        """크롤링 Job 생명주기 테스트"""
        job = JOBS.create("crawl")
        
        # 시작
        job.status = "running"
        job.started_at = datetime.utcnow().isoformat()
        job.push("info", "크롤링 시작", blog_id="test_blog")
        
        # 진행
        job.push("progress", "카테고리 1 처리 중", category=1, page=1)
        job.counters["found"] = 5
        job.counters["new"] = 3
        job.counters["skipped"] = 2
        
        # 완료
        job.status = "succeeded"
        job.finished_at = datetime.utcnow().isoformat()
        job.progress = 1.0
        job.results["posts"] = [
            {"title": "테스트 포스트 1", "url": "http://example.com/1"},
            {"title": "테스트 포스트 2", "url": "http://example.com/2"}
        ]
        job.push("done", "크롤링 완료", total_posts=3)
        
        # 검증
        assert job.status == "succeeded"
        assert job.progress == 1.0
        assert job.counters["found"] == 5
        assert job.counters["new"] == 3
        assert len(job.results["posts"]) == 2
        assert len(job.events) >= 3

    def test_pipeline_job_lifecycle(self):
        """파이프라인 Job 생명주기 테스트"""
        job = JOBS.create("preprocess_embed")
        
        # 시작
        job.status = "running"
        job.started_at = datetime.utcnow().isoformat()
        job.push("info", "파이프라인 시작")
        
        # 전처리
        job.push("progress", "전처리 중...")
        job.progress = 0.2
        
        # 청킹
        job.push("progress", "청킹 중...")
        job.progress = 0.5
        job.counters["found"] = 100
        
        # 임베딩
        job.push("progress", "임베딩 생성 중...")
        job.progress = 0.8
        job.counters["new"] = 100
        
        # 완료
        job.status = "succeeded"
        job.finished_at = datetime.utcnow().isoformat()
        job.progress = 1.0
        job.results.update({
            "chunks_created": 100,
            "embeddings_added": 100,
            "cache_hit_rate": 0.0,
            "collection_name": "test_collection"
        })
        job.push("done", "파이프라인 완료")
        
        # 검증
        assert job.status == "succeeded"
        assert job.progress == 1.0
        assert job.results["chunks_created"] == 100
        assert job.results["embeddings_added"] == 100
        assert job.results["collection_name"] == "test_collection"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

