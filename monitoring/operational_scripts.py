#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
운영 스크립트
"""
import os
import sys
import time
import json
import shutil
import sqlite3
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class OperationalScripts:
    """운영 스크립트 모음"""
    
    def __init__(self):
        self.backup_dir = "backups"
        self.logs_dir = "logs"
        self.data_dir = "src/data"
        
        # 디렉토리 생성
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
    
    def backup_database(self, backup_name: Optional[str] = None) -> str:
        """데이터베이스 백업"""
        try:
            if not backup_name:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            backup_path = os.path.join(self.backup_dir, f"{backup_name}.db")
            
            # seen.sqlite 백업
            seen_db = "src/data/meta/seen.sqlite"
            if os.path.exists(seen_db):
                shutil.copy2(seen_db, backup_path)
                logger.info(f"데이터베이스 백업 완료: {backup_path}")
            else:
                logger.warning(f"백업할 데이터베이스가 없습니다: {seen_db}")
                return ""
            
            return backup_path
            
        except Exception as e:
            logger.error(f"데이터베이스 백업 실패: {e}")
            return ""
    
    def restore_database(self, backup_path: str) -> bool:
        """데이터베이스 복원"""
        try:
            if not os.path.exists(backup_path):
                logger.error(f"백업 파일이 없습니다: {backup_path}")
                return False
            
            seen_db = "src/data/meta/seen.sqlite"
            
            # 기존 파일 백업
            if os.path.exists(seen_db):
                shutil.copy2(seen_db, f"{seen_db}.backup_{int(time.time())}")
            
            # 복원
            shutil.copy2(backup_path, seen_db)
            logger.info(f"데이터베이스 복원 완료: {backup_path} -> {seen_db}")
            
            return True
            
        except Exception as e:
            logger.error(f"데이터베이스 복원 실패: {e}")
            return False
    
    def cleanup_old_backups(self, days: int = 30) -> int:
        """오래된 백업 파일 정리"""
        try:
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            removed_count = 0
            
            for filename in os.listdir(self.backup_dir):
                file_path = os.path.join(self.backup_dir, filename)
                if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)
                    removed_count += 1
                    logger.info(f"오래된 백업 파일 삭제: {filename}")
            
            logger.info(f"백업 정리 완료: {removed_count}개 파일 삭제")
            return removed_count
            
        except Exception as e:
            logger.error(f"백업 정리 실패: {e}")
            return 0
    
    def cleanup_logs(self, days: int = 7) -> int:
        """로그 파일 정리"""
        try:
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            removed_count = 0
            
            for filename in os.listdir(self.logs_dir):
                file_path = os.path.join(self.logs_dir, filename)
                if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)
                    removed_count += 1
                    logger.info(f"오래된 로그 파일 삭제: {filename}")
            
            logger.info(f"로그 정리 완료: {removed_count}개 파일 삭제")
            return removed_count
            
        except Exception as e:
            logger.error(f"로그 정리 실패: {e}")
            return 0
    
    def cleanup_temp_files(self) -> int:
        """임시 파일 정리"""
        try:
            temp_dirs = [
                "src/data/indexes",
                "monitoring",
                "__pycache__",
                ".pytest_cache"
            ]
            
            removed_count = 0
            
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            if file.endswith(('.tmp', '.temp', '.log', '.cache')):
                                file_path = os.path.join(root, file)
                                try:
                                    os.remove(file_path)
                                    removed_count += 1
                                except:
                                    pass
            
            logger.info(f"임시 파일 정리 완료: {removed_count}개 파일 삭제")
            return removed_count
            
        except Exception as e:
            logger.error(f"임시 파일 정리 실패: {e}")
            return 0
    
    def check_disk_space(self) -> Dict[str, Any]:
        """디스크 공간 확인"""
        try:
            import shutil
            
            total, used, free = shutil.disk_usage("/")
            
            return {
                "total_gb": total / (1024**3),
                "used_gb": used / (1024**3),
                "free_gb": free / (1024**3),
                "usage_percent": (used / total) * 100,
                "status": "warning" if (used / total) > 0.9 else "ok"
            }
            
        except Exception as e:
            logger.error(f"디스크 공간 확인 실패: {e}")
            return {"error": str(e)}
    
    def check_database_integrity(self) -> Dict[str, Any]:
        """데이터베이스 무결성 확인"""
        try:
            seen_db = "src/data/meta/seen.sqlite"
            
            if not os.path.exists(seen_db):
                return {"status": "error", "message": "데이터베이스 파일이 없습니다"}
            
            conn = sqlite3.connect(seen_db)
            
            # 무결성 체크
            result = conn.execute("PRAGMA integrity_check").fetchone()
            integrity_ok = result[0] == "ok"
            
            # 테이블 정보
            tables = conn.execute("""
                SELECT name FROM sqlite_master WHERE type='table'
            """).fetchall()
            
            # 레코드 수
            record_counts = {}
            for table in tables:
                table_name = table[0]
                count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                record_counts[table_name] = count
            
            conn.close()
            
            return {
                "status": "ok" if integrity_ok else "error",
                "integrity_check": result[0],
                "tables": [t[0] for t in tables],
                "record_counts": record_counts
            }
            
        except Exception as e:
            logger.error(f"데이터베이스 무결성 확인 실패: {e}")
            return {"status": "error", "error": str(e)}
    
    def optimize_database(self) -> bool:
        """데이터베이스 최적화"""
        try:
            seen_db = "src/data/meta/seen.sqlite"
            
            if not os.path.exists(seen_db):
                logger.error("데이터베이스 파일이 없습니다")
                return False
            
            conn = sqlite3.connect(seen_db)
            
            # VACUUM 실행
            conn.execute("VACUUM")
            
            # 인덱스 재구성
            conn.execute("REINDEX")
            
            # 통계 업데이트
            conn.execute("ANALYZE")
            
            conn.close()
            
            logger.info("데이터베이스 최적화 완료")
            return True
            
        except Exception as e:
            logger.error(f"데이터베이스 최적화 실패: {e}")
            return False
    
    def restart_services(self) -> Dict[str, Any]:
        """서비스 재시작"""
        try:
            results = {}
            
            # FastAPI 서버 재시작 (실제 구현에서는 systemd, docker 등 사용)
            try:
                # 프로세스 찾기 및 재시작 로직
                results["fastapi"] = "restart_attempted"
            except Exception as e:
                results["fastapi"] = f"restart_failed: {e}"
            
            # Next.js 서버 재시작
            try:
                # 프로세스 찾기 및 재시작 로직
                results["nextjs"] = "restart_attempted"
            except Exception as e:
                results["nextjs"] = f"restart_failed: {e}"
            
            logger.info("서비스 재시작 시도 완료")
            return results
            
        except Exception as e:
            logger.error(f"서비스 재시작 실패: {e}")
            return {"error": str(e)}
    
    def health_check_all(self) -> Dict[str, Any]:
        """전체 헬스 체크"""
        try:
            from monitoring.dashboard import get_dashboard
            
            dashboard = get_dashboard()
            health_summary = dashboard.get_health_summary()
            
            # 추가 체크
            disk_space = self.check_disk_space()
            db_integrity = self.check_database_integrity()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_status": health_summary.get("overall_status", "unknown"),
                "system_health": health_summary,
                "disk_space": disk_space,
                "database_integrity": db_integrity,
                "recommendations": self._get_recommendations(health_summary, disk_space, db_integrity)
            }
            
        except Exception as e:
            logger.error(f"전체 헬스 체크 실패: {e}")
            return {"error": str(e)}
    
    def _get_recommendations(self, health_summary: Dict[str, Any], 
                           disk_space: Dict[str, Any], 
                           db_integrity: Dict[str, Any]) -> List[str]:
        """권장사항 생성"""
        recommendations = []
        
        # 디스크 공간 체크
        if disk_space.get("usage_percent", 0) > 90:
            recommendations.append("디스크 공간이 부족합니다. 백업 정리나 로그 정리를 수행하세요.")
        
        # 데이터베이스 무결성 체크
        if db_integrity.get("status") == "error":
            recommendations.append("데이터베이스 무결성에 문제가 있습니다. 백업에서 복원을 고려하세요.")
        
        # 시스템 상태 체크
        overall_status = health_summary.get("overall_status", "unknown")
        if overall_status in ["critical", "warning"]:
            recommendations.append("시스템 상태가 좋지 않습니다. 서비스 재시작을 고려하세요.")
        
        # 활성 알림 체크
        if health_summary.get("active_alerts_count", 0) > 5:
            recommendations.append("활성 알림이 많습니다. 알림 규칙을 검토하세요.")
        
        return recommendations
    
    def generate_operational_report(self) -> str:
        """운영 보고서 생성"""
        try:
            report_data = {
                "timestamp": datetime.now().isoformat(),
                "health_check": self.health_check_all(),
                "disk_space": self.check_disk_space(),
                "database_integrity": self.check_database_integrity(),
                "backup_info": self._get_backup_info(),
                "log_info": self._get_log_info()
            }
            
            report_path = os.path.join(self.logs_dir, f"operational_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"운영 보고서 생성 완료: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"운영 보고서 생성 실패: {e}")
            return ""
    
    def _get_backup_info(self) -> Dict[str, Any]:
        """백업 정보 조회"""
        try:
            backups = []
            for filename in os.listdir(self.backup_dir):
                file_path = os.path.join(self.backup_dir, filename)
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    backups.append({
                        "filename": filename,
                        "size_mb": stat.st_size / (1024 * 1024),
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
            
            return {
                "backup_count": len(backups),
                "total_size_mb": sum(b["size_mb"] for b in backups),
                "backups": sorted(backups, key=lambda x: x["modified"], reverse=True)[:10]
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_log_info(self) -> Dict[str, Any]:
        """로그 정보 조회"""
        try:
            logs = []
            for filename in os.listdir(self.logs_dir):
                file_path = os.path.join(self.logs_dir, filename)
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    logs.append({
                        "filename": filename,
                        "size_mb": stat.st_size / (1024 * 1024),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
            
            return {
                "log_count": len(logs),
                "total_size_mb": sum(l["size_mb"] for l in logs),
                "logs": sorted(logs, key=lambda x: x["modified"], reverse=True)[:10]
            }
            
        except Exception as e:
            return {"error": str(e)}


# 전역 운영 스크립트 인스턴스
_ops_scripts: Optional[OperationalScripts] = None


def get_operational_scripts() -> OperationalScripts:
    """운영 스크립트 인스턴스 조회"""
    global _ops_scripts
    if _ops_scripts is None:
        _ops_scripts = OperationalScripts()
    return _ops_scripts


if __name__ == "__main__":
    # 테스트 실행
    ops = OperationalScripts()
    
    # 헬스 체크
    health = ops.health_check_all()
    print("헬스 체크 결과:")
    print(json.dumps(health, indent=2, ensure_ascii=False))
    
    # 운영 보고서 생성
    report_path = ops.generate_operational_report()
    if report_path:
        print(f"\n운영 보고서 생성: {report_path}")
