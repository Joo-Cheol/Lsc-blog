#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
보안 및 PII 마스킹 유틸리티
"""
import re
import hashlib
import logging
from typing import Dict, Any, List, Optional
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

class PIIDetector:
    """PII 감지 및 마스킹 클래스"""
    
    def __init__(self):
        # 한국 PII 패턴들
        self.patterns = {
            # 전화번호 (한국 형식)
            'phone': [
                r'01[016789]-?\d{3,4}-?\d{4}',  # 휴대폰
                r'0\d{1,2}-?\d{3,4}-?\d{4}',   # 지역번호
                r'\d{2,3}-?\d{3,4}-?\d{4}',    # 일반 전화번호
            ],
            
            # 주민등록번호
            'ssn': [
                r'\d{6}-?\d{7}',  # 주민등록번호
                r'\d{6}-?[1-4]\d{6}',  # 주민등록번호 (성별코드 포함)
            ],
            
            # 계좌번호
            'account': [
                r'\d{3,4}-\d{2,3}-\d{6,7}',  # 은행 계좌번호
                r'\d{10,20}',  # 긴 숫자열 (계좌번호 가능성)
            ],
            
            # 이메일
            'email': [
                r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            ],
            
            # 신용카드
            'credit_card': [
                r'\d{4}-?\d{4}-?\d{4}-?\d{4}',  # 신용카드 번호
            ],
            
            # 사업자등록번호
            'business_number': [
                r'\d{3}-\d{2}-\d{5}',  # 사업자등록번호
            ],
            
            # 법인등록번호
            'corporate_number': [
                r'\d{6}-\d{7}',  # 법인등록번호
            ]
        }
        
        # 컴파일된 정규식
        self.compiled_patterns = {}
        for pii_type, patterns in self.patterns.items():
            self.compiled_patterns[pii_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
    
    def detect_pii(self, text: str) -> Dict[str, List[str]]:
        """텍스트에서 PII 감지"""
        detected = {}
        
        for pii_type, compiled_patterns in self.compiled_patterns.items():
            matches = []
            for pattern in compiled_patterns:
                matches.extend(pattern.findall(text))
            
            if matches:
                detected[pii_type] = list(set(matches))  # 중복 제거
        
        return detected
    
    def mask_pii(self, text: str, mask_char: str = '*') -> tuple[str, Dict[str, int]]:
        """PII 마스킹"""
        masked_text = text
        mask_counts = {}
        
        for pii_type, compiled_patterns in self.compiled_patterns.items():
            count = 0
            for pattern in compiled_patterns:
                def replace_func(match):
                    nonlocal count
                    count += 1
                    matched_text = match.group()
                    # 길이에 따라 마스킹
                    if len(matched_text) <= 4:
                        return mask_char * len(matched_text)
                    else:
                        # 앞뒤 2자리만 보여주고 나머지 마스킹
                        return matched_text[:2] + mask_char * (len(matched_text) - 4) + matched_text[-2:]
                
                masked_text = pattern.sub(replace_func, masked_text)
            
            if count > 0:
                mask_counts[pii_type] = count
        
        return masked_text, mask_counts
    
    def is_safe_for_logging(self, text: str) -> bool:
        """로깅에 안전한지 확인"""
        detected = self.detect_pii(text)
        return len(detected) == 0

class SecurityLogger:
    """보안 강화 로거"""
    
    def __init__(self, pii_detector: PIIDetector):
        self.pii_detector = pii_detector
        self.logger = logging.getLogger("security")
    
    def log_search_query(self, query: str, user_id: Optional[str] = None):
        """검색 쿼리 로깅 (PII 마스킹)"""
        masked_query, mask_counts = self.pii_detector.mask_pii(query)
        
        log_data = {
            "event": "search_query",
            "query_masked": masked_query,
            "query_length": len(query),
            "pii_detected": mask_counts,
            "user_id": user_id,
            "timestamp": time.time()
        }
        
        self.logger.info(f"Search query: {json.dumps(log_data, ensure_ascii=False)}")
    
    def log_search_result(self, query_id: str, result_count: int, processing_time_ms: float):
        """검색 결과 로깅 (PII 없음)"""
        log_data = {
            "event": "search_result",
            "query_id": query_id,
            "result_count": result_count,
            "processing_time_ms": processing_time_ms,
            "timestamp": time.time()
        }
        
        self.logger.info(f"Search result: {json.dumps(log_data, ensure_ascii=False)}")
    
    def log_error(self, error_type: str, error_message: str, context: Optional[Dict] = None):
        """에러 로깅 (컨텍스트 PII 마스킹)"""
        masked_context = {}
        if context:
            for key, value in context.items():
                if isinstance(value, str):
                    masked_value, _ = self.pii_detector.mask_pii(value)
                    masked_context[key] = masked_value
                else:
                    masked_context[key] = value
        
        log_data = {
            "event": "error",
            "error_type": error_type,
            "error_message": error_message,
            "context": masked_context,
            "timestamp": time.time()
        }
        
        self.logger.error(f"Error: {json.dumps(log_data, ensure_ascii=False)}")

class ContentSanitizer:
    """콘텐츠 정제 클래스"""
    
    def __init__(self, pii_detector: PIIDetector):
        self.pii_detector = pii_detector
    
    def sanitize_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """문서 정제"""
        sanitized = doc.copy()
        
        # 제목 정제
        if 'title' in sanitized and sanitized['title']:
            sanitized['title'], _ = self.pii_detector.mask_pii(sanitized['title'])
        
        # 본문 정제
        if 'content_text' in sanitized and sanitized['content_text']:
            sanitized['content_text'], _ = self.pii_detector.mask_pii(sanitized['content_text'])
        
        # URL은 그대로 유지 (PII 포함 가능성 낮음)
        
        return sanitized
    
    def sanitize_search_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """검색 결과 정제"""
        sanitized_results = []
        
        for result in results:
            sanitized = result.copy()
            
            # 제목 정제
            if 'title' in sanitized:
                sanitized['title'], _ = self.pii_detector.mask_pii(sanitized['title'])
            
            # 스니펫 정제
            if 'snippet' in sanitized:
                sanitized['snippet'], _ = self.pii_detector.mask_pii(sanitized['snippet'])
            
            sanitized_results.append(sanitized)
        
        return sanitized_results

class AccessController:
    """접근 제어 클래스"""
    
    def __init__(self):
        self.rate_limits = {}  # IP별 요청 제한
        self.blocked_ips = set()  # 차단된 IP
        self.max_requests_per_minute = 100
        self.max_requests_per_hour = 1000
    
    def check_rate_limit(self, client_ip: str) -> bool:
        """속도 제한 확인"""
        import time
        
        current_time = time.time()
        
        if client_ip not in self.rate_limits:
            self.rate_limits[client_ip] = []
        
        # 1분 이내 요청만 유지
        self.rate_limits[client_ip] = [
            req_time for req_time in self.rate_limits[client_ip]
            if current_time - req_time < 60
        ]
        
        # 요청 수 확인
        if len(self.rate_limits[client_ip]) >= self.max_requests_per_minute:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return False
        
        # 요청 기록
        self.rate_limits[client_ip].append(current_time)
        return True
    
    def is_ip_blocked(self, client_ip: str) -> bool:
        """IP 차단 확인"""
        return client_ip in self.blocked_ips
    
    def block_ip(self, client_ip: str, reason: str = "Rate limit exceeded"):
        """IP 차단"""
        self.blocked_ips.add(client_ip)
        logger.warning(f"Blocked IP {client_ip}: {reason}")
    
    def unblock_ip(self, client_ip: str):
        """IP 차단 해제"""
        self.blocked_ips.discard(client_ip)
        logger.info(f"Unblocked IP: {client_ip}")

# 전역 인스턴스
pii_detector = PIIDetector()
security_logger = SecurityLogger(pii_detector)
content_sanitizer = ContentSanitizer(pii_detector)
access_controller = AccessController()

def mask_sensitive_data(text: str) -> str:
    """민감 데이터 마스킹 (간편 함수)"""
    masked_text, _ = pii_detector.mask_pii(text)
    return masked_text

def is_safe_for_logging(text: str) -> bool:
    """로깅 안전성 확인 (간편 함수)"""
    return pii_detector.is_safe_for_logging(text)

def sanitize_query_for_logging(query: str) -> str:
    """로깅용 쿼리 정제 (간편 함수)"""
    return mask_sensitive_data(query)

if __name__ == "__main__":
    # PII 감지 테스트
    test_text = """
    연락처는 010-1234-5678이고, 이메일은 test@example.com입니다.
    주민등록번호는 901201-1234567이고, 계좌번호는 123-456-789012입니다.
    """
    
    print("Original text:")
    print(test_text)
    
    print("\nDetected PII:")
    detected = pii_detector.detect_pii(test_text)
    for pii_type, matches in detected.items():
        print(f"  {pii_type}: {matches}")
    
    print("\nMasked text:")
    masked, counts = pii_detector.mask_pii(test_text)
    print(masked)
    
    print(f"\nMask counts: {counts}")
    print(f"Safe for logging: {is_safe_for_logging(test_text)}")




