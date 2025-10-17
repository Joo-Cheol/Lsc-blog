"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Play, CheckCircle, XCircle, ArrowRight, Database } from "lucide-react";

interface CrawlResult {
  success: boolean;
  run_id: string;
  crawled_count: number;
  skipped_count: number;
  failed_count: number;
  last_logno_updated?: string;
  duration_ms: number;
  message?: string;
  blog_id?: string;
  collected_posts?: Array<{
    title: string;
    url: string;
    logno: string;
    status: 'new' | 'duplicate' | 'updated';
  }>;
}

export default function CrawlForm() {
  const [blogUrl, setBlogUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CrawlResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string>("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      // 간단 유효성: naver 블로그/모바일 블로그 허용
      const isValidUrl = /^https?:\/\/(m\.)?blog\.naver\.com\//i.test(blogUrl) || 
                        /^https?:\/\/(m\.)?blog\.naver\.com\/PostList\.naver\?/i.test(blogUrl);
      
      if (!isValidUrl) {
        setError("네이버 블로그 주소를 입력해 주세요 (예: https://blog.naver.com/<id>)");
        setLoading(false);
        return;
      }

      setProgress("카테고리 탐색 중...");
      const response = await fetch("/api/crawl", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          blog_url: blogUrl,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "크롤링 요청 실패");
      }

      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Play className="h-5 w-5" />
          블로그 크롤링
        </CardTitle>
        <CardDescription>
          네이버 블로그 주소만 입력하면 자동으로 모든 포스트를 수집합니다
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="blogUrl">블로그 주소</Label>
            <Input
              id="blogUrl"
              type="url"
              placeholder="https://blog.naver.com/<blogId>"
              value={blogUrl}
              onChange={(e) => setBlogUrl(e.target.value)}
              required
            />
            <p className="text-xs text-muted-foreground">
              예: https://blog.naver.com/tjwlswlsdl
            </p>
          </div>

          <Button type="submit" disabled={loading} className="w-full">
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {progress || "크롤링 중..."}
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                크롤링 시작
              </>
            )}
          </Button>
          
          {progress && (
            <p className="text-sm text-blue-600 text-center mt-2">
              {progress}
            </p>
          )}
        </form>

        {error && (
          <Alert className="mt-4" variant="destructive">
            <XCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {result && (
          <Alert className="mt-4">
            <CheckCircle className="h-4 w-4" />
            <AlertDescription>
              <div className="space-y-3">
                <div>
                  <p className="font-semibold text-green-800">크롤링 완료!</p>
                  <p className="text-sm text-gray-600">블로그 ID: {result.blog_id}</p>
                </div>
                
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div className="text-center">
                    <p className="font-semibold text-blue-600">{result.crawled_count}</p>
                    <p className="text-gray-600">수집</p>
                  </div>
                  <div className="text-center">
                    <p className="font-semibold text-yellow-600">{result.skipped_count}</p>
                    <p className="text-gray-600">스킵</p>
                  </div>
                  <div className="text-center">
                    <p className="font-semibold text-red-600">{result.failed_count}</p>
                    <p className="text-gray-600">실패</p>
                  </div>
                </div>
                
                    <p className="text-sm text-gray-500">소요시간: {(result.duration_ms / 1000).toFixed(1)}초</p>
                    
                    {/* 수집된 글 목록 표시 */}
                    {result.collected_posts && result.collected_posts.length > 0 && (
                      <div className="mt-4">
                        <h4 className="text-sm font-semibold text-gray-700 mb-2">수집된 글 목록:</h4>
                        <div className="max-h-40 overflow-y-auto space-y-1">
                          {result.collected_posts.map((post, index) => (
                            <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded text-xs">
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-gray-900 truncate" title={post.title}>
                                  {post.title}
                                </p>
                                <p className="text-gray-500">#{post.logno}</p>
                              </div>
                              <div className="ml-2">
                                {post.status === 'new' && (
                                  <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">
                                    새글
                                  </span>
                                )}
                                {post.status === 'updated' && (
                                  <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs">
                                    업데이트
                                  </span>
                                )}
                                {post.status === 'duplicate' && (
                                  <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full text-xs">
                                    중복
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    <div className="flex gap-2 pt-2">
                      <Link href="/ops">
                        <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
                          <Database className="mr-1 h-3 w-3" />
                          인덱싱 시작하기
                        </Button>
                      </Link>
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => {
                          setResult(null);
                          setError(null);
                          setProgress("");
                        }}
                      >
                        같은 주소로 다시 크롤
                      </Button>
                    </div>
              </div>
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}