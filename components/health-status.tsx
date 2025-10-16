'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, CheckCircle, XCircle, RefreshCw, Server, Database, Cpu } from 'lucide-react';

interface ProviderStatus {
  available: boolean;
  model_info?: {
    provider: string;
    model_name: string;
  };
  error?: string;
}

interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
  providers: Record<string, ProviderStatus>;
  database: {
    status: string;
    error?: string;
  };
  uptime_seconds: number;
}

export default function HealthStatus() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const checkHealth = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/health');
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || '헬스 체크 실패');
      }

      setHealth(data);
      setLastChecked(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : '서버 연결 실패');
      setHealth(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
    // 30초마다 자동 체크
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy': return 'bg-green-100 text-green-800';
      case 'degraded': return 'bg-yellow-100 text-yellow-800';
      case 'unhealthy': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy': return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'degraded': return <XCircle className="h-4 w-4 text-yellow-600" />;
      case 'unhealthy': return <XCircle className="h-4 w-4 text-red-600" />;
      default: return <XCircle className="h-4 w-4 text-gray-600" />;
    }
  };

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours}h ${minutes}m ${secs}s`;
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              시스템 상태
            </div>
            <div className="flex items-center gap-2">
              {lastChecked && (
                <span className="text-sm text-muted-foreground">
                  마지막 확인: {lastChecked.toLocaleTimeString()}
                </span>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={checkHealth}
                disabled={isLoading}
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
              </Button>
            </div>
          </CardTitle>
          <CardDescription>
            API 서버와 관련 서비스들의 상태를 실시간으로 모니터링합니다.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <XCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {health && (
            <div className="space-y-6">
              {/* 전체 상태 */}
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  {getStatusIcon(health.status)}
                  <div>
                    <h3 className="font-medium">전체 상태</h3>
                    <p className="text-sm text-muted-foreground">
                      버전 {health.version} • 가동시간 {formatUptime(health.uptime_seconds)}
                    </p>
                  </div>
                </div>
                <Badge className={getStatusColor(health.status)}>
                  {health.status.toUpperCase()}
                </Badge>
              </div>

              {/* 데이터베이스 상태 */}
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  <Database className="h-4 w-4" />
                  <div>
                    <h3 className="font-medium">데이터베이스</h3>
                    <p className="text-sm text-muted-foreground">
                      {health.database.error || '정상 작동 중'}
                    </p>
                  </div>
                </div>
                <Badge className={getStatusColor(health.database.status)}>
                  {health.database.status.toUpperCase()}
                </Badge>
              </div>

              {/* Provider 상태 */}
              <div>
                <h3 className="font-medium mb-3 flex items-center gap-2">
                  <Cpu className="h-4 w-4" />
                  LLM Provider
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {Object.entries(health.providers).map(([name, provider]) => (
                    <div key={name} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center gap-3">
                        {provider.available ? (
                          <CheckCircle className="h-4 w-4 text-green-600" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-600" />
                        )}
                        <div>
                          <h4 className="font-medium capitalize">{name}</h4>
                          {provider.model_info && (
                            <p className="text-sm text-muted-foreground">
                              {provider.model_info.model_name}
                            </p>
                          )}
                          {provider.error && (
                            <p className="text-sm text-red-600">{provider.error}</p>
                          )}
                        </div>
                      </div>
                      <Badge 
                        className={provider.available ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}
                      >
                        {provider.available ? 'ONLINE' : 'OFFLINE'}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>

              {/* 시스템 정보 */}
              <div className="pt-4 border-t">
                <h3 className="font-medium mb-3">시스템 정보</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">버전</span>
                    <p className="font-medium">{health.version}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">가동시간</span>
                    <p className="font-medium">{formatUptime(health.uptime_seconds)}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">마지막 체크</span>
                    <p className="font-medium">
                      {new Date(health.timestamp).toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Provider 수</span>
                    <p className="font-medium">
                      {Object.keys(health.providers).length}개
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
