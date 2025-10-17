"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  CheckCircle, 
  AlertCircle, 
  XCircle, 
  RefreshCw,
  Database,
  Cpu,
  HardDrive,
  Network
} from "lucide-react";

interface HealthData {
  status: string;
  timestamp: string;
  version: string;
  debug: boolean;
  uptime_seconds: number;
  providers: Record<string, any>;
  database: Record<string, any>;
  chroma: Record<string, any>;
  embedding_cache: Record<string, any>;
}

export default function HealthPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const fetchHealth = async () => {
    try {
      const response = await fetch("/api/health");
      if (response.ok) {
        const data = await response.json();
        setHealth(data);
        setLastUpdate(new Date());
      }
    } catch (error) {
      console.error("헬스 체크 실패:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 10000); // 10초마다 업데이트
    return () => clearInterval(interval);
  }, []);

  const StatusBadge = ({ status }: { status: string }) => {
    const colors = {
      healthy: 'bg-green-100 text-green-800 border-green-200',
      degraded: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      unhealthy: 'bg-red-100 text-red-800 border-red-200'
    }
    const icons = {
      healthy: <CheckCircle className="h-3 w-3" />,
      degraded: <AlertCircle className="h-3 w-3" />,
      unhealthy: <XCircle className="h-3 w-3" />
    }
    
    return (
      <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs border ${colors[status as keyof typeof colors] || colors.unhealthy}`}>
        {icons[status as keyof typeof icons] || icons.unhealthy}
        {status}
      </div>
    )
  };

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours}시간 ${minutes}분 ${secs}초`;
  };

  if (loading && !health) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
          <span className="ml-2">헬스 체크 중...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">시스템 헬스 체크</h1>
          <p className="text-gray-600">실시간 시스템 상태 모니터링</p>
        </div>
        <div className="flex items-center gap-4">
          {lastUpdate && (
            <span className="text-sm text-gray-500">
              마지막 업데이트: {lastUpdate.toLocaleTimeString()}
            </span>
          )}
          <Button onClick={fetchHealth} variant="outline" disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            새로고침
          </Button>
        </div>
      </div>

      {health && (
        <>
          {/* 전체 상태 */}
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5" />
                전체 시스템 상태
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4 mb-4">
                <StatusBadge status={health.status} />
                <span className="text-sm text-gray-600">
                  버전: {health.version} | 디버그: {health.debug ? 'ON' : 'OFF'}
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <p className="text-sm font-medium">업타임</p>
                  <p className="text-lg font-semibold">{formatUptime(health.uptime_seconds)}</p>
                </div>
                <div>
                  <p className="text-sm font-medium">마지막 체크</p>
                  <p className="text-lg font-semibold">
                    {new Date(health.timestamp).toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium">상태</p>
                  <p className="text-lg font-semibold capitalize">{health.status}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 컴포넌트별 상태 */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* LLM Provider */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Cpu className="h-4 w-4" />
                  LLM Provider
                </CardTitle>
              </CardHeader>
              <CardContent>
                <StatusBadge status={Object.keys(health.providers).length > 0 ? "healthy" : "unhealthy"} />
                <div className="mt-2 space-y-1">
                  {Object.entries(health.providers).map(([name, config]) => (
                    <div key={name} className="text-xs">
                      <p className="font-medium">{name}</p>
                      <p className="text-gray-500">{config.model || "N/A"}</p>
                    </div>
                  ))}
                  {Object.keys(health.providers).length === 0 && (
                    <p className="text-xs text-gray-500">등록된 프로바이더 없음</p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* 데이터베이스 */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Database className="h-4 w-4" />
                  데이터베이스
                </CardTitle>
              </CardHeader>
              <CardContent>
                <StatusBadge status={health.database.status} />
                <div className="mt-2 space-y-1">
                  <div className="text-xs">
                    <p className="font-medium">Seen DB</p>
                    <p className="text-gray-500">{health.database.seen_posts || 0}개 포스트</p>
                  </div>
                  <div className="text-xs">
                    <p className="font-medium">Checkpoints</p>
                    <p className="text-gray-500">{health.database.checkpoints || 0}개</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* ChromaDB */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <HardDrive className="h-4 w-4" />
                  ChromaDB
                </CardTitle>
              </CardHeader>
              <CardContent>
                <StatusBadge status={health.chroma.status} />
                <div className="mt-2 space-y-1">
                  <div className="text-xs">
                    <p className="font-medium">컬렉션</p>
                    <p className="text-gray-500">{health.chroma.collections || 0}개</p>
                  </div>
                  <div className="text-xs">
                    <p className="font-medium">문서</p>
                    <p className="text-gray-500">{health.chroma.total_documents || 0}개</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 임베딩 캐시 */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Network className="h-4 w-4" />
                  임베딩 캐시
                </CardTitle>
              </CardHeader>
              <CardContent>
                <StatusBadge status={health.embedding_cache.status} />
                <div className="mt-2 space-y-1">
                  <div className="text-xs">
                    <p className="font-medium">캐시된 임베딩</p>
                    <p className="text-gray-500">{health.embedding_cache.total_embeddings || 0}개</p>
                  </div>
                  <div className="text-xs">
                    <p className="font-medium">히트율</p>
                    <p className="text-gray-500">{health.embedding_cache.hit_rate || "N/A"}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 상세 정보 */}
          <Card className="mt-8">
            <CardHeader>
              <CardTitle>상세 정보</CardTitle>
              <CardDescription>전체 헬스 체크 응답 데이터</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="bg-gray-100 p-4 rounded-lg text-sm overflow-auto">
                {JSON.stringify(health, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}