"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Play, CheckCircle, XCircle } from "lucide-react";

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
}

export default function CrawlForm() {
  const [blogUrl, setBlogUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CrawlResult | null>(null);
  const [error, setError] = useState<string | null>(null);

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
                크롤링 중...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                크롤링 시작
              </>
            )}
          </Button>
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
              <div className="space-y-1">
                <p><strong>크롤링 완료!</strong></p>
                <p>블로그 ID: {result.blog_id}</p>
                <p>수집: {result.crawled_count}개</p>
                <p>스킵: {result.skipped_count}개</p>
                <p>실패: {result.failed_count}개</p>
                <p>소요시간: {result.duration_ms}ms</p>
                {result.message && <p>{result.message}</p>}
              </div>
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}