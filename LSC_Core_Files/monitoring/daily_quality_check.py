#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
일일 품질 체크 자동화 스크립트
- 골든셋 기반 품질 평가
- 기준 미달 시 알림
- 리포트 저장 및 트렌드 추적
"""
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 설정
GOLDEN_FILE = "golden_smoke.jsonl"  # 스모크 테스트용
# GOLDEN_FILE = "golden_improved.jsonl"  # 전체 골든셋용
REPORTS_DIR = Path("artifacts/reports")
ALERT_THRESHOLDS = {
    "recall_at_10": 0.70,
    "ndcg_at_10": 0.60,
    "mrr": 0.50
}

def run_quality_report():
    """품질 리포트 실행"""
    try:
        # quality_report.py 실행
        result = subprocess.run([
            sys.executable, "quality_report.py"
        ], capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode != 0:
            print(f"❌ 품질 리포트 실행 실패: {result.stderr}")
            return None
        
        # JSON 리포트 파싱 (stdout에서 마지막 JSON 블록 추출)
        lines = result.stdout.strip().split('\n')
        json_start = -1
        for i, line in enumerate(lines):
            if line.strip() == '{':
                json_start = i
                break
        
        if json_start == -1:
            print("❌ JSON 리포트를 찾을 수 없습니다.")
            return None
        
        # JSON 블록 추출
        json_lines = lines[json_start:]
        json_str = '\n'.join(json_lines)
        
        try:
            report = json.loads(json_str)
            return report
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 실패: {e}")
            return None
            
    except Exception as e:
        print(f"❌ 품질 리포트 실행 중 오류: {e}")
        return None

def check_thresholds(report):
    """임계값 체크"""
    if not report:
        return False, "리포트 없음"
    
    failed_metrics = []
    for metric, threshold in ALERT_THRESHOLDS.items():
        if report.get(metric, 0) < threshold:
            failed_metrics.append(f"{metric}: {report[metric]:.3f} < {threshold}")
    
    if failed_metrics:
        return False, "; ".join(failed_metrics)
    else:
        return True, "모든 지표 통과"

def save_daily_report(report):
    """일일 리포트 저장"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d")
    report_file = REPORTS_DIR / f"daily_quality_{timestamp}.json"
    
    daily_report = {
        "date": timestamp,
        "timestamp": datetime.now().isoformat(),
        "golden_file": GOLDEN_FILE,
        "metrics": report,
        "thresholds": ALERT_THRESHOLDS,
        "status": "PASS" if report.get("all_passing", False) else "FAIL"
    }
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(daily_report, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 일일 리포트 저장: {report_file}")
    return report_file

def get_trend_data(days=7):
    """트렌드 데이터 수집"""
    trend_data = []
    
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        report_file = REPORTS_DIR / f"daily_quality_{date}.json"
        
        if report_file.exists():
            try:
                with open(report_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    trend_data.append({
                        "date": date,
                        "recall_at_10": data["metrics"].get("recall_at_10", 0),
                        "ndcg_at_10": data["metrics"].get("ndcg_at_10", 0),
                        "mrr": data["metrics"].get("mrr", 0),
                        "status": data["status"]
                    })
            except Exception as e:
                print(f"⚠️ 트렌드 데이터 로드 실패 {date}: {e}")
    
    return sorted(trend_data, key=lambda x: x["date"])

def send_alert(message, is_critical=False):
    """알림 전송 (이메일 예시)"""
    # 실제 환경에서는 Slack, Teams, 이메일 등으로 구현
    print(f"🚨 {'CRITICAL' if is_critical else 'WARNING'} 알림:")
    print(f"   {message}")
    
    # 이메일 전송 예시 (설정 필요)
    # try:
    #     msg = MIMEMultipart()
    #     msg['From'] = "alerts@yourcompany.com"
    #     msg['To'] = "admin@yourcompany.com"
    #     msg['Subject'] = f"{'CRITICAL' if is_critical else 'WARNING'}: 검색 품질 저하"
    #     msg.attach(MIMEText(message, 'plain', 'utf-8'))
    #     
    #     server = smtplib.SMTP('smtp.gmail.com', 587)
    #     server.starttls()
    #     server.login("your_email", "your_password")
    #     server.send_message(msg)
    #     server.quit()
    # except Exception as e:
    #     print(f"❌ 알림 전송 실패: {e}")

def print_trend_summary(trend_data):
    """트렌드 요약 출력"""
    if not trend_data:
        print("📊 트렌드 데이터 없음")
        return
    
    print("\n📊 최근 7일 트렌드:")
    print("날짜       Recall@10  nDCG@10   MRR      상태")
    print("-" * 50)
    
    for data in trend_data[-7:]:  # 최근 7일
        status_icon = "✅" if data["status"] == "PASS" else "❌"
        print(f"{data['date']}  {data['recall_at_10']:.3f}     {data['ndcg_at_10']:.3f}    {data['mrr']:.3f}   {status_icon}")
    
    # 평균 계산
    if len(trend_data) >= 3:
        avg_recall = sum(d["recall_at_10"] for d in trend_data[-3:]) / 3
        avg_ndcg = sum(d["ndcg_at_10"] for d in trend_data[-3:]) / 3
        avg_mrr = sum(d["mrr"] for d in trend_data[-3:]) / 3
        
        print("-" * 50)
        print(f"3일 평균   {avg_recall:.3f}     {avg_ndcg:.3f}    {avg_mrr:.3f}")
        
        # 트렌드 분석
        if avg_recall < ALERT_THRESHOLDS["recall_at_10"]:
            print("⚠️ Recall@10 트렌드 저하 감지")
        if avg_ndcg < ALERT_THRESHOLDS["ndcg_at_10"]:
            print("⚠️ nDCG@10 트렌드 저하 감지")
        if avg_mrr < ALERT_THRESHOLDS["mrr"]:
            print("⚠️ MRR 트렌드 저하 감지")

def main():
    """메인 함수"""
    print("🚀 일일 품질 체크 자동화")
    print(f"📁 골든셋: {GOLDEN_FILE}")
    print(f"📊 임계값: {ALERT_THRESHOLDS}")
    print()
    
    # 1. 품질 리포트 실행
    print("1️⃣ 품질 평가 실행 중...")
    report = run_quality_report()
    
    if not report:
        print("❌ 품질 평가 실패")
        send_alert("품질 평가 실행 실패", is_critical=True)
        return 1
    
    # 2. 임계값 체크
    print("2️⃣ 임계값 체크 중...")
    passed, message = check_thresholds(report)
    
    if not passed:
        print(f"❌ 임계값 미달: {message}")
        send_alert(f"검색 품질 저하 감지: {message}", is_critical=True)
    else:
        print(f"✅ 임계값 통과: {message}")
    
    # 3. 일일 리포트 저장
    print("3️⃣ 일일 리포트 저장 중...")
    report_file = save_daily_report(report)
    
    # 4. 트렌드 분석
    print("4️⃣ 트렌드 분석 중...")
    trend_data = get_trend_data()
    print_trend_summary(trend_data)
    
    # 5. 요약 출력
    print("\n" + "="*60)
    print("📊 일일 품질 체크 완료")
    print("="*60)
    print(f"📅 날짜: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📈 Recall@10:  {report['recall_at_10']:.3f} (목표: ≥{ALERT_THRESHOLDS['recall_at_10']}) {'✅' if report['recall_at_10'] >= ALERT_THRESHOLDS['recall_at_10'] else '❌'}")
    print(f"📈 nDCG@10:    {report['ndcg_at_10']:.3f} (목표: ≥{ALERT_THRESHOLDS['ndcg_at_10']}) {'✅' if report['ndcg_at_10'] >= ALERT_THRESHOLDS['ndcg_at_10'] else '❌'}")
    print(f"📈 MRR:         {report['mrr']:.3f} (목표: ≥{ALERT_THRESHOLDS['mrr']}) {'✅' if report['mrr'] >= ALERT_THRESHOLDS['mrr'] else '❌'}")
    print(f"🎯 전체 상태: {'✅ PASS' if passed else '❌ FAIL'}")
    print(f"📁 리포트: {report_file}")
    
    return 0 if passed else 1

if __name__ == "__main__":
    exit(main())
