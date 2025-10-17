#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
작업 스케줄러
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from .tasks import incremental_pipeline, cleanup_old_data

logger = logging.getLogger("job")

# 스케줄러 인스턴스
scheduler = BackgroundScheduler(timezone="Asia/Seoul")

def start_scheduler():
    """스케줄러 시작"""
    try:
        # 매일 새벽 3시 5분에 증분 업데이트
        scheduler.add_job(
            incremental_pipeline,
            CronTrigger(hour=3, minute=5),
            id="incremental_update",
            name="증분 데이터 업데이트",
            replace_existing=True
        )
        
        # 매주 일요일 새벽 2시에 정리 작업
        scheduler.add_job(
            cleanup_old_data,
            CronTrigger(day_of_week=0, hour=2, minute=0),
            id="cleanup_old_data",
            name="오래된 데이터 정리",
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("스케줄러 시작됨")
        
    except Exception as e:
        logger.error(f"스케줄러 시작 실패: {e}")

def stop_scheduler():
    """스케줄러 중지"""
    try:
        scheduler.shutdown()
        logger.info("스케줄러 중지됨")
    except Exception as e:
        logger.error(f"스케줄러 중지 실패: {e}")

def get_scheduler_status():
    """스케줄러 상태 조회"""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return {
        "running": scheduler.running,
        "jobs": jobs
    }









