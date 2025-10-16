#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
골든셋 품질 리포트 자동화 스크립트
"""
import json
import http.client
import urllib.parse
import statistics
import math
import time
from datetime import datetime
from pathlib import Path

# 설정
ENDPOINT = "localhost:8000"
GOLDEN_FILE = "golden_production_test.jsonl"
K = 10
TIMEOUT = 30
SERVER_TYPE = "working_web"  # "working_web" or "fastapi"

def http_get_results(query):
    """검색 API 호출 (서버 버전 호환)"""
    try:
        if SERVER_TYPE == "working_web":
            # working_web.py: GET /api/search?q=...
            conn = http.client.HTTPConnection(ENDPOINT, timeout=TIMEOUT)
            conn.request("GET", "/api/search?q=" + urllib.parse.quote(query))
            resp = conn.getresponse()
            data = json.loads(resp.read().decode("utf-8"))
            conn.close()
            return [x["id"] for x in data][:K]
        elif SERVER_TYPE == "fastapi":
            # FastAPI: POST /api/search with JSON
            conn = http.client.HTTPConnection(ENDPOINT, timeout=TIMEOUT)
            payload = json.dumps({"q": query, "top_k": K})
            headers = {'Content-Type': 'application/json'}
            conn.request('POST', '/api/search', payload, headers)
            resp = conn.getresponse()
            data = json.loads(resp.read().decode("utf-8"))
            conn.close()
            return [x["id"] for x in data.get("results", [])][:K]
        else:
            raise ValueError(f"Unknown server type: {SERVER_TYPE}")
    except Exception as e:
        print(f"❌ API 호출 실패 '{query}': {e}")
        return []

def dcg(gains):
    """Discounted Cumulative Gain 계산"""
    return sum(g / (math.log2(i + 2)) for i, g in enumerate(gains))

def ndcg_at_k(predicted, relevant, k):
    """nDCG@k 계산"""
    relevant_set = set(relevant)
    gains = [1.0 if pid in relevant_set else 0.0 for pid in predicted[:k]]
    ideal = sorted(gains, reverse=True)
    return (dcg(gains) / dcg(ideal)) if dcg(ideal) > 0 else 0.0

def recall_at_k(predicted, relevant, k):
    """Recall@k 계산"""
    if not relevant:
        return 0.0
    return len(set(predicted[:k]) & set(relevant)) / len(set(relevant))

def mrr(predicted, relevant):
    """Mean Reciprocal Rank 계산"""
    relevant_set = set(relevant)
    for i, p in enumerate(predicted, start=1):
        if p in relevant_set:
            return 1.0 / i
    return 0.0

def load_golden_set():
    """골든셋 로드"""
    if not Path(GOLDEN_FILE).exists():
        print(f"❌ 골든셋 파일이 없습니다: {GOLDEN_FILE}")
        return []
    
    rows = []
    with open(GOLDEN_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON 파싱 오류: {line[:50]}... - {e}")
    
    print(f"✅ 골든셋 로드 완료: {len(rows)}개 쿼리")
    return rows

def run_quality_evaluation():
    """품질 평가 실행"""
    print("🚀 골든셋 품질 평가 시작...")
    
    # 골든셋 로드
    golden_rows = load_golden_set()
    if not golden_rows:
        return None
    
    # 메트릭 수집
    recalls, ndcgs, mrr_scores = [], [], []
    detailed_results = []
    
    print(f"📊 {len(golden_rows)}개 쿼리 평가 중...")
    
    for i, row in enumerate(golden_rows, 1):
        query = row["query"]
        relevant_ids = row.get("relevant_ids", [])
        
        print(f"  [{i:2d}/{len(golden_rows)}] '{query}'")
        
        # 검색 실행
        predicted_ids = http_get_results(query)
        
        if not predicted_ids:
            print(f"    ⚠️ 검색 결과 없음")
            continue
        
        # 메트릭 계산
        recall = recall_at_k(predicted_ids, relevant_ids, K)
        ndcg = ndcg_at_k(predicted_ids, relevant_ids, K)
        mrr_score = mrr(predicted_ids, relevant_ids)
        
        recalls.append(recall)
        ndcgs.append(ndcg)
        mrr_scores.append(mrr_score)
        
        # 상세 결과 저장
        detailed_results.append({
            "query": query,
            "predicted_ids": predicted_ids,
            "relevant_ids": relevant_ids,
            "recall_at_10": recall,
            "ndcg_at_10": ndcg,
            "mrr": mrr_score
        })
        
        print(f"    📈 Recall@{K}: {recall:.3f}, nDCG@{K}: {ndcg:.3f}, MRR: {mrr_score:.3f}")
        
        # API 부하 방지
        time.sleep(0.1)
    
    # 전체 리포트 생성
    if not recalls:
        print("❌ 평가 가능한 쿼리가 없습니다.")
        return None
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_queries": len(golden_rows),
        "evaluated_queries": len(recalls),
        f"recall_at_{K}": round(statistics.mean(recalls), 4),
        f"ndcg_at_{K}": round(statistics.mean(ndcgs), 4),
        "mrr": round(statistics.mean(mrr_scores), 4),
        "passing_criteria": {
            f"recall_at_{K}_target": 0.70,
            f"ndcg_at_{K}_target": 0.60,
            "mrr_target": 0.50
        },
        "passing_status": {
            f"recall_at_{K}": statistics.mean(recalls) >= 0.70,
            f"ndcg_at_{K}": statistics.mean(ndcgs) >= 0.60,
            "mrr": statistics.mean(mrr_scores) >= 0.50
        },
        "detailed_results": detailed_results
    }
    
    return report

def save_report(report):
    """리포트 저장"""
    if not report:
        return
    
    # 리포트 디렉토리 생성
    reports_dir = Path("artifacts/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    # 파일명 생성 (날짜별)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    report_file = reports_dir / f"quality_report_{timestamp}.json"
    
    # 저장
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 리포트 저장 완료: {report_file}")
    
    # 최신 리포트 심볼릭 링크
    latest_file = reports_dir / "latest_quality_report.json"
    if latest_file.exists():
        latest_file.unlink()
    latest_file.symlink_to(report_file.name)
    
    return report_file

def print_summary(report):
    """요약 출력"""
    if not report:
        return
    
    print("\n" + "="*60)
    print("📊 품질 평가 결과 요약")
    print("="*60)
    print(f"📅 평가 시간: {report['timestamp']}")
    print(f"📝 총 쿼리: {report['total_queries']}개")
    print(f"✅ 평가 완료: {report['evaluated_queries']}개")
    print()
    
    # 메트릭 출력
    recall = report[f"recall_at_{K}"]
    ndcg = report[f"ndcg_at_{K}"]
    mrr = report["mrr"]
    
    print(f"📈 Recall@{K}:  {recall:.4f} (목표: ≥0.70) {'✅' if recall >= 0.70 else '❌'}")
    print(f"📈 nDCG@{K}:    {ndcg:.4f} (목표: ≥0.60) {'✅' if ndcg >= 0.60 else '❌'}")
    print(f"📈 MRR:         {mrr:.4f} (목표: ≥0.50) {'✅' if mrr >= 0.50 else '❌'}")
    
    # 전체 합격 여부
    all_passing = all(report["passing_status"].values())
    print(f"\n🎯 전체 합격: {'✅ PASS' if all_passing else '❌ FAIL'}")
    
    if not all_passing:
        print("\n🔧 개선 권장사항:")
        if not report["passing_status"][f"recall_at_{K}"]:
            print("  - Recall@10 향상: top_k 확대 (10→20) 또는 하이브리드 검색")
        if not report["passing_status"][f"ndcg_at_{K}"]:
            print("  - nDCG@10 향상: 리랭커 적용 또는 청크 크기 조정")
        if not report["passing_status"]["mrr"]:
            print("  - MRR 향상: 상위 결과 품질 개선 또는 쿼리 확장")

def main():
    """메인 함수"""
    print("🚀 골든셋 품질 리포트 자동화")
    print(f"🔗 API 엔드포인트: http://{ENDPOINT}")
    print(f"📁 골든셋 파일: {GOLDEN_FILE}")
    print(f"📊 평가 지표: Recall@{K}, nDCG@{K}, MRR")
    print()
    
    # 품질 평가 실행
    report = run_quality_evaluation()
    
    if report:
        # 리포트 저장
        report_file = save_report(report)
        
        # 요약 출력
        print_summary(report)
        
        # JSON 출력 (자동화용)
        print("\n" + "="*60)
        print("📄 JSON 리포트 (자동화용)")
        print("="*60)
        print(json.dumps({
            f"recall_at_{K}": report[f"recall_at_{K}"],
            f"ndcg_at_{K}": report[f"ndcg_at_{K}"],
            "mrr": report["mrr"],
            "all_passing": all(report["passing_status"].values())
        }, ensure_ascii=False, indent=2))
    else:
        print("❌ 품질 평가 실패")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
