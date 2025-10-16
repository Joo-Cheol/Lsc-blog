#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
백그라운드 작업들
"""
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

logger = logging.getLogger("job")

def incremental_pipeline():
    """증분 업데이트 파이프라인"""
    try:
        logger.info("증분 업데이트 시작")
        
        # 1. 새로운 포스트 크롤링 (실제 구현에서는 크롤러 호출)
        new_posts = fetch_new_posts()
        
        if not new_posts:
            logger.info("새로운 포스트 없음")
            return
        
        # 2. 데이터 전처리
        processed_docs = []
        for post in new_posts:
            try:
                # HTML 정리
                clean_text = clean_html(post.get("html", ""))
                if not clean_text.strip():
                    continue
                
                # 문서 ID 생성
                doc_id = hashlib.md5(post["url"].encode()).hexdigest()
                
                processed_docs.append({
                    "id": doc_id,
                    "title": post.get("title", ""),
                    "url": post["url"],
                    "date": post.get("date", ""),
                    "category": post.get("category", "채권추심"),
                    "text": clean_text,
                    "meta": {
                        "title": post.get("title", ""),
                        "url": post["url"],
                        "date": post.get("date", ""),
                        "category": post.get("category", "채권추심"),
                        "source": "incremental_crawl"
                    }
                })
            except Exception as e:
                logger.error(f"포스트 처리 실패: {post.get('url', 'unknown')} - {e}")
                continue
        
        # 3. 중복 제거 및 벡터 스토어에 업서트
        if processed_docs:
            # 중복 제거 (URL 기반)
            unique_docs = {}
            for doc in processed_docs:
                url = doc["url"]
                if url not in unique_docs:
                    unique_docs[url] = doc
                else:
                    logger.info(f"중복 제거: {url}")
            
            final_docs = list(unique_docs.values())
            
            # 벡터 스토어에 업서트
            upsert_result = upsert_docs(final_docs)
            
            logger.info("증분 업데이트 완료", extra={
                "original_count": len(processed_docs),
                "unique_count": len(final_docs),
                "duplicates_removed": len(processed_docs) - len(final_docs),
                "upsert_result": upsert_result,
                "urls": [doc["url"] for doc in final_docs[:5]]
            })
        else:
            logger.info("처리된 문서 없음")
            
    except Exception as e:
        logger.error(f"증분 업데이트 실패: {e}")

def cleanup_old_data():
    """오래된 데이터 정리"""
    try:
        logger.info("데이터 정리 시작")
        
        # 1. 오래된 백업 파일 정리
        backup_dir = "./backups"
        if os.path.exists(backup_dir):
            cutoff_date = datetime.now() - timedelta(days=30)
            removed_count = 0
            
            for filename in os.listdir(backup_dir):
                if filename.startswith("backup_") and filename.endswith(".tar.gz"):
                    filepath = os.path.join(backup_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    if file_time < cutoff_date:
                        os.remove(filepath)
                        removed_count += 1
            
            logger.info(f"오래된 백업 파일 {removed_count}개 삭제")
        
        # 2. 임시 파일 정리
        temp_dirs = ["./temp", "./tmp"]
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                for filename in os.listdir(temp_dir):
                    filepath = os.path.join(temp_dir, filename)
                    if os.path.isfile(filepath):
                        # 7일 이상 된 임시 파일 삭제
                        file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                        if datetime.now() - file_time > timedelta(days=7):
                            os.remove(filepath)
        
        logger.info("데이터 정리 완료")
        
    except Exception as e:
        logger.error(f"데이터 정리 실패: {e}")

def fetch_new_posts() -> List[Dict[str, Any]]:
    """새로운 포스트 크롤링"""
    try:
        # 실제 크롤러 호출 (기존 크롤러 모듈 사용)
        from src.crawler import crawl_new_posts
        
        logger.info("새로운 포스트 크롤링 시작")
        new_posts = crawl_new_posts()
        
        if new_posts:
            logger.info(f"크롤링 완료: {len(new_posts)}개 포스트 발견")
        else:
            logger.info("새로운 포스트 없음")
        
        return new_posts
        
    except ImportError:
        # 크롤러 모듈이 없는 경우 시뮬레이션
        logger.warning("크롤러 모듈 없음, 시뮬레이션 모드")
        return []
    except Exception as e:
        logger.error(f"크롤링 실패: {e}")
        return []

def clean_html(html: str) -> str:
    """HTML 정리"""
    import re
    
    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', html)
    
    # 연속된 공백 정리
    text = re.sub(r'\s+', ' ', text)
    
    # 특수문자 정리
    text = re.sub(r'[^\w\s가-힣.,!?]', '', text)
    
    return text.strip()

def upsert_docs(docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """문서를 벡터 스토어에 업서트"""
    import time
    
    result = {
        "total": len(docs),
        "success": 0,
        "failed": 0,
        "added": 0,
        "updated": 0,
        "errors": [],
        "embedding_times": [],
        "total_time_ms": 0
    }
    
    start_time = time.time()
    
    try:
        from simple_vector_store import get_store
        
        store = get_store()
        
        # 문서들을 벡터화하고 저장
        for doc in docs:
            doc_start = time.time()
            try:
                # 임베딩 생성
                embedding = store.embedder.encode_docs([doc["text"]])[0]
                embedding_time = (time.time() - doc_start) * 1000  # ms
                result["embedding_times"].append(embedding_time)
                
                # 기존 문서 존재 여부 확인
                existing = any(d["id"] == doc["id"] for d in store.documents)
                
                # 벡터 스토어에 추가/업데이트
                store.upsert(
                    [doc["id"]],
                    [doc["text"]],
                    [embedding.tolist()],
                    [doc["meta"]]
                )
                
                result["success"] += 1
                if existing:
                    result["updated"] += 1
                else:
                    result["added"] += 1
                
            except Exception as e:
                result["failed"] += 1
                result["errors"].append(f"{doc['id']}: {str(e)}")
                logger.error(f"문서 업서트 실패: {doc['id']} - {e}")
                continue
        
        result["total_time_ms"] = (time.time() - start_time) * 1000
        
        # 품질 지표 계산
        success_rate = (result["success"] / result["total"]) * 100 if result["total"] > 0 else 0
        avg_embedding_time = sum(result["embedding_times"]) / len(result["embedding_times"]) if result["embedding_times"] else 0
        
        logger.info("문서 업서트 완료", extra={
            "total": result["total"],
            "success": result["success"],
            "failed": result["failed"],
            "added": result["added"],
            "updated": result["updated"],
            "success_rate": round(success_rate, 2),
            "avg_embedding_time_ms": round(avg_embedding_time, 2),
            "total_time_ms": round(result["total_time_ms"], 2)
        })
        
    except Exception as e:
        result["total_time_ms"] = (time.time() - start_time) * 1000
        logger.error(f"벡터 스토어 업서트 실패: {e}")
        result["errors"].append(f"벡터 스토어 오류: {str(e)}")
    
    return result
