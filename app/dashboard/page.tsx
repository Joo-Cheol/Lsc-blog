"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import Link from 'next/link';
import { 
  Search, 
  FileText, 
  Download, 
  Upload, 
  BarChart3, 
  Settings,
  ArrowRight,
  Zap,
  Activity,
  Database,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle
} from 'lucide-react';
import { useState, useEffect } from 'react';

interface SystemStats {
  total_posts: number;
  total_chunks: number;
  total_searches: number;
  total_generations: number;
  last_crawl: string | null;
  last_index: string | null;
  crawler_stats: any;
  chroma_stats: any;
  cache_stats: any;
}

interface HealthStatus {
  status: string;
  uptime_seconds: number;
  database: any;
  chroma: any;
  embedding_cache: any;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, healthRes] = await Promise.all([
          fetch('/api/v1/stats'),
          fetch('/api/v1/health')
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
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000); // 30초마다 업데이트
    
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'degraded':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case 'unhealthy':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <Activity className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">대시보드 로딩 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* 헤더 */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
              <BarChart3 className="h-8 w-8 text-blue-600" />
              시스템 대시보드
            </h1>
            <p className="text-gray-600 mt-2">실시간 시스템 상태와 성능 지표</p>
          </div>
          <Link href="/">
            <Button variant="outline">
              <ArrowRight className="mr-2 h-4 w-4" />
              홈으로
            </Button>
          </Link>
        </div>

        {/* 시스템 상태 */}
        {health && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">전체 상태</p>
                    <div className="flex items-center gap-2 mt-1">
                      {getStatusIcon(health.status)}
                      <Badge variant={health.status === 'healthy' ? 'default' : 'destructive'}>
                        {health.status}
                      </Badge>
                    </div>
                  </div>
                  <Activity className="h-8 w-8 text-blue-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">가동 시간</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {formatUptime(health.uptime_seconds)}
                    </p>
                  </div>
                  <Clock className="h-8 w-8 text-green-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">데이터베이스</p>
                    <div className="flex items-center gap-2 mt-1">
                      {getStatusIcon(health.database?.status)}
                      <span className="text-sm">{health.database?.status}</span>
                    </div>
                  </div>
                  <Database className="h-8 w-8 text-purple-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">ChromaDB</p>
                    <div className="flex items-center gap-2 mt-1">
                      {getStatusIcon(health.chroma?.status)}
                      <span className="text-sm">{health.chroma?.status}</span>
                    </div>
                  </div>
                  <Database className="h-8 w-8 text-orange-600" />
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* 통계 카드 */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">수집된 포스트</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {stats.total_posts.toLocaleString()}
                    </p>
                  </div>
                  <Download className="h-8 w-8 text-blue-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">인덱스된 청크</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {stats.total_chunks.toLocaleString()}
                    </p>
                  </div>
                  <Search className="h-8 w-8 text-green-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">검색 횟수</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {stats.total_searches.toLocaleString()}
                    </p>
                  </div>
                  <Search className="h-8 w-8 text-purple-600" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">생성된 포스트</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {stats.total_generations.toLocaleString()}
                    </p>
                  </div>
                  <FileText className="h-8 w-8 text-orange-600" />
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* 상세 정보 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 크롤러 통계 */}
          {stats?.crawler_stats && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Download className="h-5 w-5" />
                  크롤러 통계
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">총 포스트</span>
                    <span className="font-medium">{stats.crawler_stats.total_posts}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">업데이트된 포스트</span>
                    <span className="font-medium">{stats.crawler_stats.updated_posts || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">마지막 크롤</span>
                    <span className="font-medium text-sm">
                      {stats.crawler_stats.last_crawl ? 
                        new Date(stats.crawler_stats.last_crawl).toLocaleString() : 
                        '없음'
                      }
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">마지막 logno</span>
                    <span className="font-medium">{stats.crawler_stats.last_logno || 0}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* ChromaDB 통계 */}
          {stats?.chroma_stats && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  ChromaDB 통계
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">총 문서</span>
                    <span className="font-medium">{stats.chroma_stats.total_documents}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">마지막 업데이트</span>
                    <span className="font-medium text-sm">
                      {stats.chroma_stats.last_updated ? 
                        new Date(stats.chroma_stats.last_updated).toLocaleString() : 
                        '없음'
                      }
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">소스 수</span>
                    <span className="font-medium">{Object.keys(stats.chroma_stats.sources || {}).length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">주제 수</span>
                    <span className="font-medium">{Object.keys(stats.chroma_stats.topics || {}).length}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* 임베딩 캐시 통계 */}
          {stats?.cache_stats && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5" />
                  임베딩 캐시
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">총 임베딩</span>
                    <span className="font-medium">{stats.cache_stats.total_embeddings}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">총 접근</span>
                    <span className="font-medium">{stats.cache_stats.total_accesses}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">평균 접근</span>
                    <span className="font-medium">{stats.cache_stats.avg_accesses?.toFixed(1) || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">오늘 접근</span>
                    <span className="font-medium">{stats.cache_stats.accessed_today}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* 빠른 액션 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                빠른 액션
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <Link href="/crawl" className="block">
                  <Button variant="outline" className="w-full justify-start">
                    <Download className="mr-2 h-4 w-4" />
                    크롤링 시작
                  </Button>
                </Link>
                <Link href="/search" className="block">
                  <Button variant="outline" className="w-full justify-start">
                    <Search className="mr-2 h-4 w-4" />
                    문서 검색
                  </Button>
                </Link>
                <Link href="/generate" className="block">
                  <Button variant="outline" className="w-full justify-start">
                    <FileText className="mr-2 h-4 w-4" />
                    포스트 생성
                  </Button>
                </Link>
                <Link href="/health" className="block">
                  <Button variant="outline" className="w-full justify-start">
                    <Activity className="mr-2 h-4 w-4" />
                    상태 확인
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
