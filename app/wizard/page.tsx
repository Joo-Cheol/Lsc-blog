"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Play, CheckCircle, XCircle, ArrowRight, Search, Database } from "lucide-react";
import ProgressHeader from "@/components/ProgressHeader";
import { useJob } from "@/components/useJob";
import JobResultPosts from "@/components/JobResultPosts";

export default function WizardPage() {
  const [currentStep, setCurrentStep] = useState(1);
  const [blogUrl, setBlogUrl] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [crawlJobId, setCrawlJobId] = useState<string>();
  const [pipelineJobId, setPipelineJobId] = useState<string>();
  
  const { job: crawlJob, events: crawlEvents } = useJob(crawlJobId);
  const { job: pipelineJob, events: pipelineEvents } = useJob(pipelineJobId);

  const startCrawl = async () => {
    const res = await fetch("/api/crawl", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ blog_url: blogUrl }),
    }).then((r) => r.json());
    
    if (res.ok) {
      setCrawlJobId(res.job_id);
    }
  };

  const startPipeline = async () => {
    const res = await fetch("/api/pipeline/preprocess-embed", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task: "preprocess_embed" }),
    }).then((r) => r.json());
    
    if (res.ok) {
      setPipelineJobId(res.job_id);
    }
  };

  const canProceedToStep2 = crawlJob?.status === "succeeded";
  const canProceedToStep3 = pipelineJob?.status === "succeeded";

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <ProgressHeader title="원클릭 마법사" step={currentStep} total={4} />
      
      <div className="text-center mb-8">
        <p className="text-lg text-gray-600">
          블로그 주소만 입력하면, 자동으로 모든 카테고리에서 새 글을 모아 검색 가능한 지식으로 바꿉니다.
        </p>
      </div>

      {/* STEP 1: 블로그 수집 */}
      {currentStep === 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Play className="h-5 w-5" />
              STEP 1: 블로그 수집
            </CardTitle>
            <CardDescription>
              네이버 블로그 주소를 입력하면 자동으로 새 글을 수집합니다
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">블로그 주소</label>
              <Input
                placeholder="https://blog.naver.com/블로그ID"
                value={blogUrl}
                onChange={(e) => setBlogUrl(e.target.value)}
                disabled={crawlJob?.status === "running"}
              />
            </div>
            
            <Button 
              onClick={startCrawl} 
              disabled={!blogUrl || crawlJob?.status === "running"}
              className="w-full"
              size="lg"
            >
              {crawlJob?.status === "running" ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  수집 중...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  수집 시작
                </>
              )}
            </Button>

            {/* 크롤링 진행상황 */}
            {crawlJob && (
              <div className="space-y-4">
                <div className="text-sm text-gray-600">
                  상태: {crawlJob.status} · 진행률: {Math.round((crawlJob.progress || 0) * 100)}%
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${Math.round((crawlJob.progress || 0) * 100)}%` }}
                  />
                </div>
                <div className="text-sm">
                  발견 {crawlJob.counters?.found ?? 0} · 신규 {crawlJob.counters?.new ?? 0} · 스킵 {crawlJob.counters?.skipped ?? 0} · 실패 {crawlJob.counters?.failed ?? 0}
                </div>

                {/* 이번에 추가된 글 제목 리스트 */}
                <JobResultPosts posts={crawlJob.results?.posts} />
              </div>
            )}

            {/* 완료 후 다음 단계 버튼 */}
            {canProceedToStep2 && (
              <Alert>
                <CheckCircle className="h-4 w-4" />
                <AlertDescription>
                  <div className="space-y-3">
                    <p className="font-semibold text-green-800">수집 완료!</p>
                    <p className="text-sm text-gray-600">
                      {crawlJob.results?.posts?.length || 0}개의 새 글을 수집했습니다.
                    </p>
                    <Button 
                      onClick={() => setCurrentStep(2)}
                      className="w-full"
                      size="lg"
                    >
                      다음: 검색 준비 <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </div>
                </AlertDescription>
              </Alert>
            )}

            {/* 에러 표시 */}
            {crawlJob?.status === "failed" && (
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertDescription>
                  <p className="font-semibold">수집 실패</p>
                  <p className="text-sm">{crawlJob.errors?.[0] || "알 수 없는 오류"}</p>
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {/* STEP 2: 검색 준비 */}
      {currentStep === 2 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              STEP 2: 검색 준비
            </CardTitle>
            <CardDescription>
              수집한 글을 정리하고 검색 가능한 형태로 저장합니다
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button 
              onClick={startPipeline} 
              disabled={pipelineJob?.status === "running"}
              className="w-full"
              size="lg"
            >
              {pipelineJob?.status === "running" ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  처리 중...
                </>
              ) : (
                <>
                  <Database className="mr-2 h-4 w-4" />
                  검색 준비 시작
                </>
              )}
            </Button>

            {/* 파이프라인 진행상황 */}
            {pipelineJob && (
              <div className="space-y-4">
                <div className="text-sm text-gray-600">
                  상태: {pipelineJob.status} · 진행률: {Math.round((pipelineJob.progress || 0) * 100)}%
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${Math.round((pipelineJob.progress || 0) * 100)}%` }}
                  />
                </div>
                <div className="text-sm">
                  청크: {pipelineJob.results?.chunks_created || 0}개 · 임베딩: {pipelineJob.results?.embeddings_added || 0}개
                </div>
              </div>
            )}

            {/* 완료 후 다음 단계 버튼 */}
            {canProceedToStep3 && (
              <Alert>
                <CheckCircle className="h-4 w-4" />
                <AlertDescription>
                  <div className="space-y-3">
                    <p className="font-semibold text-green-800">검색 준비 완료!</p>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="font-medium">청크:</span> {pipelineJob.results?.chunks_created || 0}개
                      </div>
                      <div>
                        <span className="font-medium">임베딩:</span> {pipelineJob.results?.embeddings_added || 0}개
                      </div>
                    </div>
                    <p className="text-sm text-gray-600">
                      컬렉션: {pipelineJob.results?.collection_name || "legal_documents"}
                    </p>
                    <Button 
                      onClick={() => setCurrentStep(3)}
                      className="w-full"
                      size="lg"
                    >
                      다음: 검색해 보기 <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </div>
                </AlertDescription>
              </Alert>
            )}

            {/* 에러 표시 */}
            {pipelineJob?.status === "failed" && (
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertDescription>
                  <p className="font-semibold">검색 준비 실패</p>
                  <p className="text-sm">{pipelineJob.errors?.[0] || "알 수 없는 오류"}</p>
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {/* STEP 3: 검색 체험 */}
      {currentStep === 3 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5" />
              STEP 3: 검색 체험
            </CardTitle>
            <CardDescription>
              준비된 데이터로 검색을 체험해보세요
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">검색어</label>
              <Input
                placeholder="예: 채권추심, 소액대출, 법적절차"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            
            <Button 
              onClick={() => setCurrentStep(4)}
              disabled={!searchQuery}
              className="w-full"
              size="lg"
            >
              <Search className="mr-2 h-4 w-4" />
              검색해 보기
            </Button>
          </CardContent>
        </Card>
      )}

      {/* STEP 4: 완료 */}
      {currentStep === 4 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5" />
              STEP 4: 완료
            </CardTitle>
            <CardDescription>
              마법사가 완료되었습니다!
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert>
              <CheckCircle className="h-4 w-4" />
              <AlertDescription>
                <div className="space-y-3">
                  <p className="font-semibold text-green-800">축하합니다!</p>
                  <p className="text-sm text-gray-600">
                    블로그 자동화 시스템이 준비되었습니다. 이제 언제든지 검색과 글 생성을 사용할 수 있습니다.
                  </p>
                  <div className="flex gap-2">
                    <Button 
                      onClick={() => window.location.href = "/search"}
                      className="flex-1"
                    >
                      <Search className="mr-2 h-4 w-4" />
                      검색 페이지
                    </Button>
                    <Button 
                      onClick={() => window.location.href = "/generate"}
                      className="flex-1"
                      variant="outline"
                    >
                      글 생성하기
                    </Button>
                  </div>
                </div>
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      )}

      {/* 네비게이션 */}
      <div className="mt-8 flex justify-between">
        <Button 
          variant="outline" 
          onClick={() => setCurrentStep(Math.max(1, currentStep - 1))}
          disabled={currentStep === 1}
        >
          이전
        </Button>
        <Button 
          variant="outline" 
          onClick={() => window.location.href = "/dashboard"}
        >
          대시보드로 이동
        </Button>
      </div>
    </div>
  );
}