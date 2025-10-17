"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Play, CheckCircle, XCircle, ArrowRight, Database } from "lucide-react";
import { useJob } from "@/components/useJob";
import JobResultPosts from "@/components/JobResultPosts";


export default function CrawlForm() {
  const [blogUrl, setBlogUrl] = useState("");
  const [jobId, setJobId] = useState<string>();
  const [error, setError] = useState<string | null>(null);
  
  const { job, events, isConnected } = useJob(jobId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setJobId(undefined);

    try {
      // 간단 유효성: naver 블로그/모바일 블로그 허용
      const isValidUrl = /^https?:\/\/(m\.)?blog\.naver\.com\//i.test(blogUrl) || 
                        /^https?:\/\/(m\.)?blog\.naver\.com\/PostList\.naver\?/i.test(blogUrl);
      
      if (!isValidUrl) {
        setError("네이버 블로그 주소를 입력해 주세요 (예: https://blog.naver.com/<id>)");
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
        throw new Error(data.detail || data.error || "크롤링 요청 실패");
      }

      if (data.ok && data.job_id) {
        setJobId(data.job_id);
      } else {
        throw new Error("Job ID를 받지 못했습니다");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다");
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

          <Button type="submit" disabled={job?.status === "running"} className="w-full">
            {job?.status === "running" ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                블로그에서 새 글 찾는 중...
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

        {/* Job 진행상황 표시 */}
        {job && (
          <div className="mt-4 space-y-4">
            {/* 진행률 표시 */}
            <div className="space-y-2">
              <div className="text-sm text-gray-600">
                상태: {job.status === "running" ? "진행 중" : job.status} · 진행률: {Math.round((job.progress || 0) * 100)}%
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${Math.round((job.progress || 0) * 100)}%` }}
                />
              </div>
              <div className="text-sm flex gap-4">
                <span className="text-blue-600">발견 {job.counters?.found ?? 0}</span>
                <span className="text-green-600">신규 {job.counters?.new ?? 0}</span>
                <span className="text-gray-500">스킵 {job.counters?.skipped ?? 0}</span>
                <span className="text-red-600">실패 {job.counters?.failed ?? 0}</span>
              </div>
            </div>

            {/* 수집된 글 목록 */}
            <JobResultPosts posts={job.results?.posts} />

            {/* 완료 상태 */}
            {job.status === "succeeded" && (
              <Alert>
                <CheckCircle className="h-4 w-4" />
                <AlertDescription>
                  <div className="space-y-3">
                    <p className="font-semibold text-green-800">크롤링 완료! 🎉</p>
                    <p className="text-sm text-gray-600">
                      {job.results?.posts?.length || 0}개의 새 글을 수집했습니다.
                    </p>
                    <div className="flex gap-2">
                      <Link href="/ops" className="flex-1">
                        <Button className="w-full" size="sm">
                          <Database className="mr-2 h-4 w-4" />
                          인덱싱 시작하기
                        </Button>
                      </Link>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={() => {
                          setJobId(undefined);
                          setBlogUrl("");
                        }}
                      >
                        같은 주소로 다시 크롤
                      </Button>
                    </div>
                  </div>
                </AlertDescription>
              </Alert>
            )}

            {/* 실패 상태 */}
            {job.status === "failed" && (
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertDescription>
                  <p className="font-semibold">크롤링 실패</p>
                  <p className="text-sm">{job.errors?.[0]?.message || "알 수 없는 오류"}</p>
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}