import HealthStatus from '@/components/health-status';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Server, Activity, Clock } from 'lucide-react';

export default function HealthPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* 헤더 */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Server className="h-8 w-8 text-blue-600" />
            <h1 className="text-3xl font-bold text-gray-900">
              시스템 모니터링
            </h1>
          </div>
          <p className="text-lg text-gray-600">
            API 서버와 관련 서비스들의 실시간 상태를 확인하세요
          </p>
        </div>

        {/* 모니터링 정보 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                실시간 모니터링
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                <div>
                  <h4 className="font-medium mb-1">자동 새로고침</h4>
                  <p className="text-gray-600">
                    30초마다 자동으로 상태를 확인합니다.
                  </p>
                </div>
                <div>
                  <h4 className="font-medium mb-1">상태 표시</h4>
                  <p className="text-gray-600">
                    Healthy, Degraded, Unhealthy 상태를 색상으로 구분합니다.
                  </p>
                </div>
                <div>
                  <h4 className="font-medium mb-1">상세 정보</h4>
                  <p className="text-gray-600">
                    각 서비스의 상세한 상태 정보를 제공합니다.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Server className="h-5 w-5" />
                서비스 상태
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                <div>
                  <h4 className="font-medium mb-1">API 서버</h4>
                  <p className="text-gray-600">
                    FastAPI 백엔드 서버의 상태를 확인합니다.
                  </p>
                </div>
                <div>
                  <h4 className="font-medium mb-1">데이터베이스</h4>
                  <p className="text-gray-600">
                    SQLite 데이터베이스 연결 상태를 모니터링합니다.
                  </p>
                </div>
                <div>
                  <h4 className="font-medium mb-1">LLM Provider</h4>
                  <p className="text-gray-600">
                    Ollama, Gemini 등 LLM 서비스 상태를 확인합니다.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                성능 지표
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                <div>
                  <h4 className="font-medium mb-1">가동 시간</h4>
                  <p className="text-gray-600">
                    서버의 총 가동 시간을 표시합니다.
                  </p>
                </div>
                <div>
                  <h4 className="font-medium mb-1">마지막 체크</h4>
                  <p className="text-gray-600">
                    가장 최근 상태 확인 시간을 기록합니다.
                  </p>
                </div>
                <div>
                  <h4 className="font-medium mb-1">버전 정보</h4>
                  <p className="text-gray-600">
                    현재 실행 중인 시스템 버전을 표시합니다.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 상태 모니터 */}
        <HealthStatus />
      </div>
    </div>
  );
}
