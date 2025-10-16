#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
증분 크롤링 상태 관리 모듈
last_seen_logno 저장/로드 기능
"""

import json
import os
from pathlib import Path

STATE_PATH = "state/last_seen_logno.json"

def load_last_seen() -> int:
    """마지막으로 처리된 logno 로드"""
    if not os.path.exists(STATE_PATH):
        return 0
    
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("last_seen", 0)
    except (json.JSONDecodeError, KeyError, FileNotFoundError):
        return 0

def save_last_seen(logno: int) -> None:
    """마지막으로 처리된 logno 저장"""
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    
    data = {
        "last_seen": logno,
        "updated_at": __import__("datetime").datetime.now().isoformat()
    }
    
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_state_info() -> dict:
    """현재 상태 정보 반환"""
    last_seen = load_last_seen()
    return {
        "last_seen_logno": last_seen,
        "state_file": STATE_PATH,
        "exists": os.path.exists(STATE_PATH)
    }

if __name__ == "__main__":
    # 테스트
    print("현재 상태:", get_state_info())
    save_last_seen(12345)
    print("저장 후:", get_state_info())
