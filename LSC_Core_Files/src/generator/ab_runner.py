"""
A/B 배치 비교 시스템
"""

import json
import time
import csv
from typing import List, Dict, Any
from .generator_no_llm import generate_no_llm
from .generator_llm import generate_llm, MockLLMClient

def run_ab_batch(topics_file: str, results_provider, model, output_file: str = None) -> Dict[str, Any]:
    """
    A/B 배치 비교 실행
    
    Args:
        topics_file: 주제 목록 JSONL 파일
        results_provider: 검색 결과 제공 함수 (topic -> results)
        model: e5 모델
        output_file: 결과 저장 파일 (선택사항)
    
    Returns:
        비교 결과
    """
    
    # 주제 로드
    topics = []
    with open(topics_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                topics.append(json.loads(line))
    
    # LLM 클라이언트 초기화
    llm_client = MockLLMClient()
    
    results = []
    
    for i, topic_data in enumerate(topics):
        topic = topic_data.get("topic", topic_data.get("query", ""))
        if not topic:
            continue
            
        print(f"처리 중 ({i+1}/{len(topics)}): {topic}")
        
        try:
            # 검색 결과 가져오기
            search_results = results_provider(topic)
            
            # A 파이프라인 (LLM 없음)
            start_time = time.time()
            result_a = generate_no_llm(topic, search_results, model, "default", 10)
            latency_a = int((time.time() - start_time) * 1000)
            
            # B 파이프라인 (LLM 있음)
            start_time = time.time()
            result_b = generate_llm(topic, search_results, model, "default", llm_client, 10)
            latency_b = int((time.time() - start_time) * 1000)
            
            # 결과 수집
            record = {
                "topic": topic,
                "label_a": "A",
                "label_b": "B",
                "latency_a_ms": latency_a,
                "latency_b_ms": latency_b,
                "style_score_a": result_a["stats"].get("style_score", 0.0),
                "style_score_b": result_b["stats"].get("style_score", 0.0),
                "plag_ok_a": result_a["stats"]["plagiarism"].get("ok", False),
                "plag_ok_b": result_b["stats"]["plagiarism"].get("ok", False),
                "jaccard_a": result_a["stats"]["plagiarism"].get("jaccard", 0.0),
                "jaccard_b": result_b["stats"]["plagiarism"].get("jaccard", 0.0),
                "cosine_max_a": result_a["stats"]["plagiarism"].get("cosine_max", 0.0),
                "cosine_max_b": result_b["stats"]["plagiarism"].get("cosine_max", 0.0),
                "simhash_dist_a": result_a["stats"]["plagiarism"].get("simhash_dist", 0),
                "simhash_dist_b": result_b["stats"]["plagiarism"].get("simhash_dist", 0),
                "length_chars_a": len(result_a["html"]),
                "length_chars_b": len(result_b["html"]),
                "density_a": result_a["stats"].get("validators", {}).get("density", {}).get("density", 0.0),
                "density_b": result_b["stats"].get("validators", {}).get("density", {}).get("density", 0.0),
                "sections_ok_a": result_a["stats"].get("validators", {}).get("sections", {}).get("valid", False),
                "sections_ok_b": result_b["stats"].get("validators", {}).get("sections", {}).get("valid", False),
                "fail_reason_a": result_a["stats"].get("error", ""),
                "fail_reason_b": result_b["stats"].get("error", ""),
                "mode_a": result_a["stats"].get("mode", "unknown"),
                "mode_b": result_b["stats"].get("mode", "unknown")
            }
            
            results.append(record)
            
        except Exception as e:
            print(f"에러 발생 ({topic}): {e}")
            # 에러 레코드 추가
            results.append({
                "topic": topic,
                "label_a": "A",
                "label_b": "B",
                "error": str(e)
            })
    
    # 결과 분석
    analysis = analyze_results(results)
    
    # 결과 저장
    if output_file:
        save_results(results, analysis, output_file)
    
    return {
        "results": results,
        "analysis": analysis,
        "total_topics": len(topics),
        "successful_topics": len([r for r in results if "error" not in r])
    }

def analyze_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """결과 분석"""
    
    # 성공한 결과만 필터링
    successful = [r for r in results if "error" not in r]
    
    if not successful:
        return {"error": "성공한 결과가 없습니다"}
    
    # A/B 비교 분석
    analysis = {
        "summary": {
            "total_topics": len(results),
            "successful_topics": len(successful),
            "success_rate": len(successful) / len(results) if results else 0
        },
        "performance": {
            "latency_a_p95": calculate_percentile([r["latency_a_ms"] for r in successful], 95),
            "latency_b_p95": calculate_percentile([r["latency_b_ms"] for r in successful], 95),
            "latency_a_avg": sum(r["latency_a_ms"] for r in successful) / len(successful),
            "latency_b_avg": sum(r["latency_b_ms"] for r in successful) / len(successful)
        },
        "quality": {
            "style_score_a_avg": sum(r["style_score_a"] for r in successful) / len(successful),
            "style_score_b_avg": sum(r["style_score_b"] for r in successful) / len(successful),
            "plag_ok_a_rate": sum(r["plag_ok_a"] for r in successful) / len(successful),
            "plag_ok_b_rate": sum(r["plag_ok_b"] for r in successful) / len(successful),
            "sections_ok_a_rate": sum(r["sections_ok_a"] for r in successful) / len(successful),
            "sections_ok_b_rate": sum(r["sections_ok_b"] for r in successful) / len(successful)
        },
        "pass_criteria": {
            "a_passes_latency": sum(1 for r in successful if r["latency_a_ms"] <= 200) / len(successful),
            "b_passes_latency": sum(1 for r in successful if r["latency_b_ms"] <= 1500) / len(successful),
            "a_passes_style": sum(1 for r in successful if r["style_score_a"] >= 0.75) / len(successful),
            "b_passes_style": sum(1 for r in successful if r["style_score_b"] >= 0.75) / len(successful),
            "a_passes_plagiarism": sum(1 for r in successful if r["plag_ok_a"]) / len(successful),
            "b_passes_plagiarism": sum(1 for r in successful if r["plag_ok_b"]) / len(successful)
        }
    }
    
    return analysis

def calculate_percentile(values: List[float], percentile: int) -> float:
    """퍼센타일 계산"""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int((percentile / 100) * len(sorted_values))
    return sorted_values[min(index, len(sorted_values) - 1)]

def save_results(results: List[Dict[str, Any]], analysis: Dict[str, Any], output_file: str):
    """결과 저장"""
    
    # JSON 저장
    json_file = output_file.replace('.csv', '.json')
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            "results": results,
            "analysis": analysis,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }, f, ensure_ascii=False, indent=2)
    
    # CSV 저장
    if results:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    
    print(f"결과 저장 완료: {json_file}, {output_file}")

def create_test_topics_file(filename: str = "test_topics.jsonl"):
    """테스트용 주제 파일 생성"""
    test_topics = [
        {"topic": "채권추심 방법"},
        {"topic": "지급명령 신청"},
        {"topic": "압류 절차"},
        {"topic": "강제집행"},
        {"topic": "부동산 경매"},
        {"topic": "이혼 절차"},
        {"topic": "상속 절차"},
        {"topic": "교통사고 처리"},
        {"topic": "근로계약서 작성"},
        {"topic": "회사 설립"}
    ]
    
    with open(filename, 'w', encoding='utf-8') as f:
        for topic in test_topics:
            f.write(json.dumps(topic, ensure_ascii=False) + '\n')
    
    print(f"테스트 주제 파일 생성: {filename}")
    return filename
