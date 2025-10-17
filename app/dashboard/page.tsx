"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  Activity, 
  Database, 
  Search, 
  FileText, 
  TrendingUp,
  CheckCircle,
  AlertCircle,
  XCircle,
  RefreshCw
} from "lucide-react";
import Link from "next/link";

interface SystemStats {
  total_posts: number;
  total_chunks: number;
  total_searches: number;
  total_generations: number;
  total_crawls: number;
  total_uploads: number;
  provider_stats: Record<string, any>;
  crawler_stats: Record<string, any>;
  chroma_stats: Record<string, any>;
  cache_stats: Record<string, any>;
  operation_metrics: Record<string, number>;
}

interface HealthStatus {
  status: string;
  timestamp: string;
  version: string;
  providers: Record<string, any>;
  database: Record<string, any>;
  chroma: Record<string, any>;
  embedding_cache: Record<string, any>;
  uptime_seconds: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [statsRes, healthRes] = await Promise.all([
        fetch("/api/stats"),
        fetch("/api/health")
      ]);
      
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }
      
      if (healthRes.ok) {
        const healthData = await healthRes.json();
        setHealth(healthData);
      }
    } catch (error) {
      console.error("데이터 로딩 실패:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // 30초마다 업데이트
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

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
          <span className="ml-2">데이터 로딩 중...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">시스템 대시보드</h1>
          <p className="text-gray-600">실시간 시스템 상태와 성능 지표</p>
        </div>
        <Button onClick={fetchData} variant="outline">
          <RefreshCw className="mr-2 h-4 w-4" />
          새로고침
        </Button>
      </div>

      {/* 헬스 상태 */}
      {health && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">전체 상태</CardTitle>
            </CardHeader>
            <CardContent>
              <StatusBadge status={health.status} />
              <p className="text-xs text-gray-500 mt-1">
                업타임: {Math.floor(health.uptime_seconds / 3600)}시간
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">ChromaDB</CardTitle>
            </CardHeader>
            <CardContent>
              <StatusBadge status={health.chroma.status} />
              <p className="text-xs text-gray-500 mt-1">
                문서: {health.chroma.total_documents || 0}개
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">임베딩 캐시</CardTitle>
            </CardHeader>
            <CardContent>
              <StatusBadge status={health.embedding_cache.status} />
              <p className="text-xs text-gray-500 mt-1">
                히트율: {health.embedding_cache.hit_rate || "N/A"}
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">LLM Provider</CardTitle>
            </CardHeader>
            <CardContent>
              <StatusBadge status={Object.keys(health.providers).length > 0 ? "healthy" : "unhealthy"} />
              <p className="text-xs text-gray-500 mt-1">
                {Object.keys(health.providers).join(", ") || "없음"}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 운영 메트릭 */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Database className="h-4 w-4" />
                크롤링
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_crawls}</div>
              <p className="text-xs text-gray-500">오늘 실행</p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Search className="h-4 w-4" />
                검색
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_searches}</div>
              <p className="text-xs text-gray-500">오늘 실행</p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <FileText className="h-4 w-4" />
                생성
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_generations}</div>
              <p className="text-xs text-gray-500">오늘 실행</p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Activity className="h-4 w-4" />
                업로드
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_uploads}</div>
              <p className="text-xs text-gray-500">오늘 실행</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 데이터 현황 */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                수집된 데이터
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm">포스트</span>
                  <span className="font-semibold">{stats.total_posts}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">청크</span>
                  <span className="font-semibold">{stats.total_chunks}</span>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                캐시 성능
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm">임베딩</span>
                  <span className="font-semibold">{stats.cache_stats?.total_embeddings || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">접근</span>
                  <span className="font-semibold">{stats.cache_stats?.total_accesses || 0}</span>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                최근 활동
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm">마지막 크롤</span>
                  <span className="font-semibold text-xs">
                    {stats.crawler_stats?.last_crawl ? 
                      new Date(stats.crawler_stats.last_crawl).toLocaleDateString() : 
                      "없음"
                    }
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">마지막 인덱싱</span>
                  <span className="font-semibold text-xs">
                    {stats.chroma_stats?.last_updated ? 
                      new Date(stats.chroma_stats.last_updated).toLocaleDateString() : 
                      "없음"
                    }
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 빈 상태 가이드 */}
      {(!stats || (stats.total_posts === 0 && stats.total_chunks === 0)) && (
        <Card className="bg-green-50 border-green-200 mb-8">
          <CardContent className="pt-6">
            <div className="text-center space-y-3">
              <div className="text-green-600">
                <Activity className="h-12 w-12 mx-auto" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-green-900">오늘 처리한 작업이 여기에 보여요</h3>
                <p className="text-green-700">
                  <a href="/wizard" className="underline font-medium">마법사</a>를 시작하거나 
                  <a href="/crawl" className="underline font-medium ml-1">크롤링</a>을 해보세요.
                </p>
              </div>
              <div className="flex justify-center gap-2">
                <Link href="/wizard">
                  <Button size="sm" className="bg-green-600 hover:bg-green-700">
                    마법사 시작하기
                  </Button>
                </Link>
                <Link href="/crawl">
                  <Button size="sm" variant="outline">
                    크롤링 시작
                  </Button>
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 빠른 액션 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>빠른 액션</CardTitle>
            <CardDescription>자주 사용하는 기능으로 바로 이동</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Link href="/wizard">
              <Button variant="outline" className="w-full justify-start">
                <Sparkles className="mr-2 h-4 w-4" />
                원클릭 마법사
              </Button>
            </Link>
            <Link href="/crawl">
              <Button variant="outline" className="w-full justify-start">
                <Database className="mr-2 h-4 w-4" />
                새 블로그 크롤링
              </Button>
            </Link>
            <Link href="/search">
              <Button variant="outline" className="w-full justify-start">
                <Search className="mr-2 h-4 w-4" />
                문서 검색
              </Button>
            </Link>
            <Link href="/generate">
              <Button variant="outline" className="w-full justify-start">
                <FileText className="mr-2 h-4 w-4" />
                콘텐츠 생성
              </Button>
            </Link>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>시스템 관리</CardTitle>
            <CardDescription>운영 및 유지보수 도구</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Link href="/ops">
              <Button variant="outline" className="w-full justify-start">
                <Activity className="mr-2 h-4 w-4" />
                운영 도구
              </Button>
            </Link>
            <Link href="/health">
              <Button variant="outline" className="w-full justify-start">
                <CheckCircle className="mr-2 h-4 w-4" />
                헬스 체크
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}