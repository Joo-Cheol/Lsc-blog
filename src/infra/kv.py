#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis 기반 키-값 저장소
"""
import redis
import os
import json
from typing import List, Set

# Redis 연결
r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

def push_history(user_id: str, query: str):
    """검색 히스토리에 쿼리 추가"""
    r.lpush(f"hist:{user_id}", query)
    r.ltrim(f"hist:{user_id}", 0, 100)  # 최대 100개 유지

def add_fav(user_id: str, query: str):
    """즐겨찾기에 쿼리 추가"""
    r.sadd(f"fav:{user_id}", query)

def remove_fav(user_id: str, query: str):
    """즐겨찾기에서 쿼리 제거"""
    r.srem(f"fav:{user_id}", query)

def list_history(user_id: str) -> List[str]:
    """검색 히스토리 조회"""
    return [x.decode() for x in r.lrange(f"hist:{user_id}", 0, 50)]

def list_fav(user_id: str) -> Set[str]:
    """즐겨찾기 목록 조회"""
    return {x.decode() for x in r.smembers(f"fav:{user_id}")}

def is_fav(user_id: str, query: str) -> bool:
    """즐겨찾기 여부 확인"""
    return r.sismember(f"fav:{user_id}", query)









