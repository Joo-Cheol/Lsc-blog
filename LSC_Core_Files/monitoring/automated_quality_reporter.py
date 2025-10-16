#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
자동화된 품질 리포트 시스템
"""
import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timedelta
import schedule
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

# ===== 환경 가드 설정 =====
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

class AutomatedQualityReporter:
    """자동화된 품질 리포트 클래스"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.reports_dir = Path("quality_reports")
        self.reports_dir.mkdir(exist_ok=True)
        
        # 알림 설정
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        self.email_config = {
            "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
            "smtp_port": int(os.getenv("SMTP_PORT", "587")),
            "username": os.getenv("SMTP_USERNAME"),
            "password": os.getenv("SMTP_PASSWORD"),
            "from_email": os.getenv("FROM_EMAIL"),
            "to_emails": os.getenv("TO_EMAILS", "").split(",")
        }
        
        # SLO 임계값
        self.slo_thresholds = {
            "recall@10": 0.7,
            "ndcg@10": 0.6,
            "mrr": 0.5,
            "p95_latency_ms": 200,
            "error_rate": 0.005,
            "cache_hit_rate": 0.6
        }
    
    def fetch_quality_metrics(self) -> Dict[str, Any]:
        """API에서 품질 메트릭 가져오기"""
        try:
            response = requests.get(f"{self.api_base_url}/metrics/quality", timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch quality metrics: {e}")
            return {}
    
    def fetch_performance_metrics(self) -> Dict[str, Any]:
        """API에서 성능 메트릭 가져오기"""
        try:
            response = requests.get(f"{self.api_base_url}/metrics", timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch performance metrics: {e}")
            return {}
    
    def generate_quality_report(self) -> Dict[str, Any]:
        """품질 리포트 생성"""
        logger.info("Generating automated quality report...")
        
        # 메트릭 수집
        quality_metrics = self.fetch_quality_metrics()
        performance_metrics = self.fetch_performance_metrics()
        
        # 리포트 생성
        report = {
            "timestamp": datetime.now().isoformat(),
            "report_type": "automated_quality_report",
            "quality_metrics": quality_metrics.get("quality_metrics", {}),
            "performance_metrics": performance_metrics.get("metrics", {}),
            "slo_status": quality_metrics.get("slo_status", {}),
            "alerts": [],
            "trends": self._calculate_trends(),
            "recommendations": []
        }
        
        # 알림 생성
        report["alerts"] = self._generate_alerts(report)
        
        # 권장사항 생성
        report["recommendations"] = self._generate_recommendations(report)
        
        return report
    
    def _calculate_trends(self) -> Dict[str, Any]:
        """트렌드 계산 (최근 7일 리포트 비교)"""
        trends = {}
        
        try:
            # 최근 리포트 파일들 찾기
            report_files = list(self.reports_dir.glob("quality_report_*.json"))
            report_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            if len(report_files) < 2:
                return {"status": "insufficient_data"}
            
            # 최근 2개 리포트 비교
            with open(report_files[0], "r", encoding="utf-8") as f:
                current_report = json.load(f)
            
            with open(report_files[1], "r", encoding="utf-8") as f:
                previous_report = json.load(f)
            
            # 메트릭 변화 계산
            current_quality = current_report.get("quality_metrics", {})
            previous_quality = previous_report.get("quality_metrics", {})
            
            for metric in ["recall@10", "ndcg@10", "mrr"]:
                if metric in current_quality and metric in previous_quality:
                    current_val = current_quality[metric].get(metric, 0)
                    previous_val = previous_quality[metric].get(metric, 0)
                    change = current_val - previous_val
                    change_pct = (change / previous_val * 100) if previous_val > 0 else 0
                    
                    trends[metric] = {
                        "current": current_val,
                        "previous": previous_val,
                        "change": change,
                        "change_percentage": change_pct,
                        "trend": "up" if change > 0 else "down" if change < 0 else "stable"
                    }
            
        except Exception as e:
            logger.error(f"Failed to calculate trends: {e}")
            trends["error"] = str(e)
        
        return trends
    
    def _generate_alerts(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """알림 생성"""
        alerts = []
        
        # 품질 메트릭 알림
        quality_metrics = report.get("quality_metrics", {})
        slo_status = report.get("slo_status", {})
        
        for metric, threshold in self.slo_thresholds.items():
            if metric in quality_metrics:
                value = quality_metrics[metric]
                if isinstance(value, dict):
                    value = value.get(metric, 0)
                
                if value < threshold:
                    alerts.append({
                        "type": "slo_violation",
                        "metric": metric,
                        "value": value,
                        "threshold": threshold,
                        "severity": "critical" if value < threshold * 0.8 else "warning",
                        "message": f"{metric} is {value:.3f}, below threshold {threshold}"
                    })
        
        # 성능 메트릭 알림
        performance_metrics = report.get("performance_metrics", {})
        latency = performance_metrics.get("latency", {})
        
        if "p95" in latency and latency["p95"] > self.slo_thresholds["p95_latency_ms"]:
            alerts.append({
                "type": "performance_degradation",
                "metric": "p95_latency",
                "value": latency["p95"],
                "threshold": self.slo_thresholds["p95_latency_ms"],
                "severity": "warning",
                "message": f"P95 latency is {latency['p95']:.2f}ms, above threshold {self.slo_thresholds['p95_latency_ms']}ms"
            })
        
        return alerts
    
    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """권장사항 생성"""
        recommendations = []
        
        # 품질 기반 권장사항
        quality_metrics = report.get("quality_metrics", {})
        
        recall_10 = quality_metrics.get("recall@10", {}).get("recall@10", 0)
        if recall_10 < 0.7:
            recommendations.append("Consider enabling hybrid search (BM25 + vector) to improve recall")
        
        ndcg_10 = quality_metrics.get("ndcg@10", {}).get("ndcg@10", 0)
        if ndcg_10 < 0.6:
            recommendations.append("Consider enabling reranker to improve ranking quality")
        
        # 성능 기반 권장사항
        performance_metrics = report.get("performance_metrics", {})
        cache_hit_rate = performance_metrics.get("cache_hit_rate", 0)
        
        if cache_hit_rate < 0.6:
            recommendations.append("Consider increasing cache size or optimizing cache strategy")
        
        # 트렌드 기반 권장사항
        trends = report.get("trends", {})
        for metric, trend_data in trends.items():
            if isinstance(trend_data, dict) and trend_data.get("trend") == "down":
                change_pct = trend_data.get("change_percentage", 0)
                if abs(change_pct) > 5:  # 5% 이상 하락
                    recommendations.append(f"{metric} is declining ({change_pct:.1f}%), investigate recent changes")
        
        return recommendations
    
    def save_report(self, report: Dict[str, Any]) -> str:
        """리포트 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.reports_dir / f"quality_report_{timestamp}.json"
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Quality report saved to: {report_path}")
        return str(report_path)
    
    def send_slack_notification(self, report: Dict[str, Any]):
        """Slack 알림 전송"""
        if not self.slack_webhook:
            return
        
        try:
            # 알림 메시지 구성
            alerts = report.get("alerts", [])
            if not alerts:
                return  # 알림이 없으면 전송하지 않음
            
            # 메시지 구성
            message = {
                "text": "🚨 Search Quality Alert",
                "attachments": []
            }
            
            for alert in alerts:
                color = "danger" if alert["severity"] == "critical" else "warning"
                attachment = {
                    "color": color,
                    "title": f"{alert['metric']} Alert",
                    "text": alert["message"],
                    "fields": [
                        {"title": "Current Value", "value": str(alert["value"]), "short": True},
                        {"title": "Threshold", "value": str(alert["threshold"]), "short": True}
                    ]
                }
                message["attachments"].append(attachment)
            
            # Slack 전송
            response = requests.post(self.slack_webhook, json=message, timeout=10)
            response.raise_for_status()
            
            logger.info("Slack notification sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
    
    def send_email_report(self, report: Dict[str, Any]):
        """이메일 리포트 전송"""
        if not self.email_config["username"] or not self.email_config["to_emails"]:
            return
        
        try:
            # 이메일 구성
            msg = MIMEMultipart()
            msg['From'] = self.email_config["from_email"]
            msg['To'] = ", ".join(self.email_config["to_emails"])
            msg['Subject'] = f"Search Quality Report - {datetime.now().strftime('%Y-%m-%d')}"
            
            # 리포트 내용 구성
            body = self._format_email_report(report)
            msg.attach(MIMEText(body, 'html'))
            
            # 이메일 전송
            server = smtplib.SMTP(self.email_config["smtp_server"], self.email_config["smtp_port"])
            server.starttls()
            server.login(self.email_config["username"], self.email_config["password"])
            server.send_message(msg)
            server.quit()
            
            logger.info("Email report sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send email report: {e}")
    
    def _format_email_report(self, report: Dict[str, Any]) -> str:
        """이메일 리포트 HTML 포맷팅"""
        quality_metrics = report.get("quality_metrics", {})
        performance_metrics = report.get("performance_metrics", {})
        alerts = report.get("alerts", [])
        recommendations = report.get("recommendations", [])
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .metric {{ margin: 10px 0; padding: 10px; border-left: 4px solid #007cba; }}
                .alert {{ margin: 10px 0; padding: 10px; border-left: 4px solid #dc3545; background-color: #f8d7da; }}
                .recommendation {{ margin: 10px 0; padding: 10px; border-left: 4px solid #28a745; background-color: #d4edda; }}
                .trend-up {{ color: #28a745; }}
                .trend-down {{ color: #dc3545; }}
                .trend-stable {{ color: #6c757d; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔍 Search Quality Report</h1>
                <p>Generated: {report['timestamp']}</p>
            </div>
            
            <h2>📊 Quality Metrics</h2>
            <div class="metric">
                <strong>Recall@10:</strong> {quality_metrics.get('recall@10', {}).get('recall@10', 'N/A'):.3f}
            </div>
            <div class="metric">
                <strong>nDCG@10:</strong> {quality_metrics.get('ndcg@10', {}).get('ndcg@10', 'N/A'):.3f}
            </div>
            <div class="metric">
                <strong>MRR:</strong> {quality_metrics.get('mrr', {}).get('mrr', 'N/A'):.3f}
            </div>
            
            <h2>⚡ Performance Metrics</h2>
            <div class="metric">
                <strong>P95 Latency:</strong> {performance_metrics.get('latency', {}).get('p95', 'N/A'):.2f}ms
            </div>
            <div class="metric">
                <strong>Cache Hit Rate:</strong> {performance_metrics.get('cache_hit_rate', 'N/A'):.1%}
            </div>
            <div class="metric">
                <strong>QPS:</strong> {performance_metrics.get('qps', 'N/A'):.2f}
            </div>
        """
        
        if alerts:
            html += "<h2>🚨 Alerts</h2>"
            for alert in alerts:
                html += f"""
                <div class="alert">
                    <strong>{alert['metric']}:</strong> {alert['message']}
                </div>
                """
        
        if recommendations:
            html += "<h2>💡 Recommendations</h2>"
            for rec in recommendations:
                html += f"""
                <div class="recommendation">
                    {rec}
                </div>
                """
        
        html += """
        </body>
        </html>
        """
        
        return html
    
    def run_daily_report(self):
        """일일 리포트 실행"""
        logger.info("Running daily quality report...")
        
        try:
            # 리포트 생성
            report = self.generate_quality_report()
            
            # 리포트 저장
            report_path = self.save_report(report)
            
            # 알림 전송
            self.send_slack_notification(report)
            self.send_email_report(report)
            
            logger.info("Daily quality report completed successfully")
            
        except Exception as e:
            logger.error(f"Daily quality report failed: {e}")
    
    def run_post_deployment_report(self):
        """배포 후 리포트 실행"""
        logger.info("Running post-deployment quality report...")
        
        try:
            # 리포트 생성
            report = self.generate_quality_report()
            
            # 리포트 저장
            report_path = self.save_report(report)
            
            # 알림 전송 (배포 후에는 항상 전송)
            self.send_slack_notification(report)
            self.send_email_report(report)
            
            logger.info("Post-deployment quality report completed successfully")
            
        except Exception as e:
            logger.error(f"Post-deployment quality report failed: {e}")

def setup_scheduler():
    """스케줄러 설정"""
    reporter = AutomatedQualityReporter()
    
    # 일일 리포트 (매일 오전 9시)
    schedule.every().day.at("09:00").do(reporter.run_daily_report)
    
    # 주간 리포트 (매주 월요일 오전 10시)
    schedule.every().monday.at("10:00").do(reporter.run_daily_report)
    
    logger.info("Quality report scheduler configured")
    
    # 스케줄러 실행
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 체크

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "scheduler":
        # 스케줄러 모드
        setup_scheduler()
    else:
        # 일회성 실행
        reporter = AutomatedQualityReporter()
        reporter.run_daily_report()




