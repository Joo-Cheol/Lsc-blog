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
import ErrorGuideModal from "@/components/ErrorGuideModal";

export default function WizardPage() {
  const [currentStep, setCurrentStep] = useState(1);
  const [blogUrl, setBlogUrl] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [crawlJobId, setCrawlJobId] = useState<string>();
  const [pipelineJobId, setPipelineJobId] = useState<string>();
  const [errorModal, setErrorModal] = useState<{
    isOpen: boolean;
    errorCode?: string;
    errorMessage?: string;
    suggestion?: string;
  }>({ isOpen: false });
  
  const { job: crawlJob, events: crawlEvents } = useJob(crawlJobId);
  const { job: pipelineJob, events: pipelineEvents } = useJob(pipelineJobId);

  const startCrawl = async () => {
    try {
      console.log("크롤링 시작:", blogUrl);
      const res = await fetch("/api/crawl", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ blog_url: blogUrl }),
      }).then((r) => r.json());
      
      console.log("크롤링 응답:", res);
      
      if (res.ok) {
        console.log("Job ID 설정:", res.job_id);
        setCrawlJobId(res.job_id);
      } else {
        // API 에러 처리
        setErrorModal({
          isOpen: true,
          errorCode: "INVALID_INPUT",
          errorMessage: res.detail || "크롤링 요청에 실패했습니다.",
          suggestion: "블로그 주소를 다시 확인해주세요."
        });
      }
    } catch (error) {
      setErrorModal({
        isOpen: true,
        errorCode: "CRAWL_FAILED",
        errorMessage: "네트워크 오류가 발생했습니다.",
        suggestion: "인터넷 연결을 확인하고 다시 시도해주세요."
      });
    }
  };

  const startPipeline = async () => {
    try {
      const res = await fetch("/api/pipeline/preprocess-embed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: "preprocess_embed" }),
      }).then((r) => r.json());
      
      if (res.ok) {
        setPipelineJobId(res.job_id);
      } else {
        setErrorModal({
          isOpen: true,
          errorCode: "PIPELINE_FAILED",
          errorMessage: res.detail || "파이프라인 실행에 실패했습니다.",
          suggestion: "먼저 블로그를 크롤링했는지 확인해주세요."
        });
      }
    } catch (error) {
      setErrorModal({
        isOpen: true,
        errorCode: "PIPELINE_FAILED",
        errorMessage: "네트워크 오류가 발생했습니다.",
        suggestion: "인터넷 연결을 확인하고 다시 시도해주세요."
      });
    }
  };

  const canProceedToStep2 = crawlJob?.status === "succeeded";
  const canProceedToStep3 = pipelineJob?.status === "succeeded";

  // Job 실패 시 에러 모달 표시
  if (crawlJob?.status === "failed" && crawlJob.errors?.length > 0) {
    const error = crawlJob.errors[0];
    if (!errorModal.isOpen) {
      setErrorModal({
        isOpen: true,
        errorCode: "CRAWL_FAILED",
        errorMessage: error.message || error,
        suggestion: error.suggestion || "잠시 후 다시 시도해주세요."
      });
    }
  }

  if (pipelineJob?.status === "failed" && pipelineJob.errors?.length > 0) {
    const error = pipelineJob.errors[0];
    if (!errorModal.isOpen) {
      setErrorModal({
        isOpen: true,
        errorCode: "PIPELINE_FAILED",
        errorMessage: error.message || error,
        suggestion: error.suggestion || "데이터 처리 중 오류가 발생했습니다."
      });
    }
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <ProgressHeader title="원클릭 마법사" step={currentStep} total={4} />
      
      <div className="text-center mb-8">
        <p className="text-lg text-gray-600 mb-2">
          블로그 주소만 입력하면, 자동으로 모든 카테고리에서 새 글을 모아 검색 가능한 지식으로 바꿉니다.
        </p>
        <p className="text-sm text-gray-500">
          💡 처음 사용하시나요? 걱정 마세요! 단계별로 안내해드릴게요.
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
              네이버 블로그 주소를 입력하면 자동으로 모든 카테고리에서 새 글을 찾아 수집합니다
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
                  블로그에서 새 글 찾는 중...
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
                  상태: {crawlJob.status === "running" ? "진행 중" : crawlJob.status} · 진행률: {Math.round((crawlJob.progress || 0) * 100)}%
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${Math.round((crawlJob.progress || 0) * 100)}%` }}
                  />
                </div>
                <div className="text-sm flex gap-4">
                  <span className="text-blue-600">발견 {crawlJob.counters?.found ?? 0}</span>
                  <span className="text-green-600">신규 {crawlJob.counters?.new ?? 0}</span>
                  <span className="text-gray-500">스킵 {crawlJob.counters?.skipped ?? 0}</span>
                  <span className="text-red-600">실패 {crawlJob.counters?.failed ?? 0}</span>
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
                    <p className="font-semibold text-green-800">수집 완료! 🎉</p>
                    <p className="text-sm text-gray-600">
                      {crawlJob.results?.posts?.length || 0}개의 새 글을 수집했습니다. 이제 검색 준비를 시작할 수 있어요!
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
              수집한 글을 잘게 나누고 벡터화해서 검색 가능한 형태로 저장합니다
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
                  문서를 잘게 나누고 벡터화하는 중...
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
                <div className="text-sm flex gap-4">
                  <span className="text-blue-600">청크 {pipelineJob.results?.chunks_created || 0}개</span>
                  <span className="text-green-600">임베딩 {pipelineJob.results?.embeddings_added || 0}개</span>
                  {pipelineJob.results?.cache_hit_rate && (
                    <span className="text-purple-600">캐시 {pipelineJob.results.cache_hit_rate}%</span>
                  )}
                </div>
              </div>
            )}

            {/* 완료 후 다음 단계 버튼 */}
            {canProceedToStep3 && (
              <Alert>
                <CheckCircle className="h-4 w-4" />
                <AlertDescription>
                  <div className="space-y-3">
                    <p className="font-semibold text-green-800">검색 준비 완료! 🚀</p>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div className="bg-blue-50 p-2 rounded">
                        <span className="font-medium text-blue-800">청크:</span> {pipelineJob.results?.chunks_created || 0}개
                      </div>
                      <div className="bg-green-50 p-2 rounded">
                        <span className="font-medium text-green-800">임베딩:</span> {pipelineJob.results?.embeddings_added || 0}개
                      </div>
                    </div>
                    <p className="text-sm text-gray-600">
                      📚 컬렉션: {pipelineJob.results?.collection_name || "legal_documents"}
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
              준비된 데이터로 검색을 체험해보세요. 원하는 키워드로 관련 글을 찾아보세요!
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">검색어</label>
              <Input
                placeholder="예: 채권추심, 소액대출, 법적절차, 계약서 작성"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <div className="flex flex-wrap gap-2 mt-2">
                <span className="text-xs text-gray-500">추천 키워드:</span>
                {["채권추심", "소액대출", "법적절차"].map((keyword) => (
                  <button
                    key={keyword}
                    onClick={() => setSearchQuery(keyword)}
                    className="text-xs bg-gray-100 hover:bg-gray-200 px-2 py-1 rounded transition-colors"
                  >
                    {keyword}
                  </button>
                ))}
              </div>
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
                  <p className="font-semibold text-green-800">축하합니다! 🎊</p>
                  <p className="text-sm text-gray-600">
                    블로그 자동화 시스템이 준비되었습니다! 이제 언제든지 검색과 글 생성을 사용할 수 있어요.
                  </p>
                  <div className="bg-green-50 p-3 rounded-lg">
                    <p className="text-sm text-green-800 font-medium">✨ 다음에 할 수 있는 것들:</p>
                    <ul className="text-xs text-green-700 mt-1 space-y-1">
                      <li>• 검색 페이지에서 원하는 정보 찾기</li>
                      <li>• 글 생성 페이지에서 AI로 블로그 포스트 작성</li>
                      <li>• 새로운 블로그 추가로 데이터 확장</li>
                    </ul>
                  </div>
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

      {/* 에러 가이드 모달 */}
      <ErrorGuideModal
        isOpen={errorModal.isOpen}
        onClose={() => setErrorModal({ isOpen: false })}
        errorCode={errorModal.errorCode}
        errorMessage={errorModal.errorMessage}
        suggestion={errorModal.suggestion}
      />
    </div>
  );
}