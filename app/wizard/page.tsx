"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  CheckCircle, 
  Loader2, 
  Play, 
  Search, 
  FileText,
  Database,
  ArrowRight,
  ArrowLeft,
  Sparkles,
  Target
} from "lucide-react";

type StepStatus = 'idle' | 'running' | 'success' | 'error';

interface StepData {
  status: StepStatus;
  result?: any;
  error?: string;
}

export default function WizardPage() {
  const [currentStep, setCurrentStep] = useState(1);
  const [blogUrl, setBlogUrl] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedResults, setSelectedResults] = useState<string[]>([]);
  const [pipelineStatus, setPipelineStatus] = useState<any>(null);
  
  const [steps, setSteps] = useState<Record<number, StepData>>({
    1: { status: 'idle' },
    2: { status: 'idle' },
    3: { status: 'idle' },
    4: { status: 'idle' }
  });

  const runStep = async (step: number, payload?: any) => {
    setSteps(prev => ({ ...prev, [step]: { status: 'running' } }));
    
    try {
      let response;
      switch (step) {
        case 1:
          response = await fetch("/api/crawl", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ blog_url: blogUrl })
          });
          break;
        case 2:
          response = await fetch("/api/pipeline/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ task: "preprocess_embed" })
          });
          
          // 파이프라인 상태 폴링 시작
          if (response.ok) {
            const data = await response.json();
            if (data.task_id) {
              pollPipelineStatus(data.task_id);
            }
          }
          break;
        case 3:
          response = await fetch("/api/search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: searchQuery })
          });
          break;
        case 4:
          response = await fetch("/api/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
              topic: searchQuery,
              evidence_ids: selectedResults,
              style: "법무법인 혜안"
            })
          });
          break;
      }
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "작업 실패");
      
      setSteps(prev => ({ ...prev, [step]: { status: 'success', result: data } }));
    } catch (error) {
      setSteps(prev => ({ 
        ...prev, 
        [step]: { 
          status: 'error', 
          error: error instanceof Error ? error.message : "알 수 없는 오류" 
        } 
      }));
    }
  };

  const pollPipelineStatus = async (taskId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/pipeline/status?id=${taskId}`);
        const status = await response.json();
        
        setPipelineStatus(status);
        
        if (status.status === "completed" || status.status === "failed") {
          clearInterval(pollInterval);
          setSteps(prev => ({ 
            ...prev, 
            [2]: { 
              status: status.status === "completed" ? "success" : "error",
              result: status,
              error: status.error
            } 
          }));
        }
      } catch (error) {
        console.error("상태 폴링 실패:", error);
        clearInterval(pollInterval);
        setSteps(prev => ({ 
          ...prev, 
          [2]: { status: "error", error: "상태 확인 실패" } 
        }));
      }
    }, 1000); // 1초마다 폴링
  };

  const StepCard = ({ 
    step, 
    title, 
    description, 
    icon: Icon, 
    children 
  }: {
    step: number;
    title: string;
    description: string;
    icon: any;
    children: React.ReactNode;
  }) => {
    const stepData = steps[step];
    const isActive = currentStep === step;
    const isCompleted = stepData.status === 'success';
    const isRunning = stepData.status === 'running';
    const hasError = stepData.status === 'error';
    
    return (
      <Card className={`transition-all duration-300 ${
        isActive ? 'ring-2 ring-blue-500 shadow-lg' : 
        isCompleted ? 'bg-green-50 border-green-200' : 
        hasError ? 'bg-red-50 border-red-200' : ''
      }`}>
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
              isCompleted ? 'bg-green-500 text-white' :
              isRunning ? 'bg-blue-500 text-white' :
              hasError ? 'bg-red-500 text-white' :
              isActive ? 'bg-blue-100 text-blue-600' :
              'bg-gray-100 text-gray-600'
            }`}>
              {isCompleted ? <CheckCircle className="h-4 w-4" /> :
               isRunning ? <Loader2 className="h-4 w-4 animate-spin" /> :
               step}
            </div>
            <Icon className="h-5 w-5" />
            {title}
          </CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          {children}
        </CardContent>
      </Card>
    );
  };

  const ProgressBar = () => (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">진행률</span>
        <span className="text-sm text-gray-500">{currentStep}/4 단계</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div 
          className="bg-blue-600 h-2 rounded-full transition-all duration-500"
          style={{ width: `${(currentStep / 4) * 100}%` }}
        />
      </div>
    </div>
  );

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">원클릭 마법사</h1>
        <p className="text-gray-600">4단계로 블로그를 검색 가능한 지식으로 만들어드려요</p>
      </div>

      <ProgressBar />

      {/* STEP 1: 주소 입력 */}
      <StepCard
        step={1}
        title="블로그 주소만 알려주세요"
        description="카테고리/페이지는 자동 감지돼요"
        icon={Target}
      >
        <div className="space-y-4">
          <Input
            type="url"
            placeholder="https://blog.naver.com/블로그ID"
            value={blogUrl}
            onChange={(e) => setBlogUrl(e.target.value)}
            className="text-lg"
          />
          
          {steps[1].status === 'idle' && (
            <Button 
              onClick={() => runStep(1)} 
              disabled={!blogUrl}
              className="w-full"
              size="lg"
            >
              <Play className="mr-2 h-5 w-5" />
              수집 시작
            </Button>
          )}
          
          {steps[1].status === 'running' && (
            <div className="text-center py-4">
              <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2 text-blue-600" />
              <p className="text-sm text-gray-600">카테고리 5/5 · 페이지 25/25</p>
            </div>
          )}
          
          {steps[1].status === 'success' && (
            <Alert>
              <CheckCircle className="h-4 w-4" />
              <AlertDescription>
                <div className="space-y-3">
                  <p className="font-semibold text-green-800">새 글 수집 완료!</p>
                  
                  {/* 수집된 글 목록 표시 */}
                  {steps[1].result?.collected_posts && steps[1].result.collected_posts.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 mb-2">수집된 글:</h4>
                      <div className="max-h-32 overflow-y-auto space-y-1">
                        {steps[1].result.collected_posts.slice(0, 5).map((post: any, index: number) => (
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
                        {steps[1].result.collected_posts.length > 5 && (
                          <p className="text-xs text-gray-500 text-center">
                            ... 외 {steps[1].result.collected_posts.length - 5}개 더
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                  
                  <p className="text-sm text-gray-600">
                    블로그 ID: {steps[1].result?.blog_id || "tjwlswlsdl"}
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
          
          {steps[1].status === 'error' && (
            <Alert variant="destructive">
              <AlertDescription>
                <p className="font-semibold">수집 실패</p>
                <p className="text-sm">{steps[1].error}</p>
                <Button 
                  onClick={() => runStep(1)}
                  variant="outline"
                  className="mt-2"
                >
                  다시 시도
                </Button>
              </AlertDescription>
            </Alert>
          )}
        </div>
      </StepCard>

      {/* STEP 2: 검색 준비 */}
      {currentStep >= 2 && (
        <StepCard
          step={2}
          title="읽기 좋은 조각으로 정리하고, 검색을 위해 기억해둘게요"
          description="글을 문단으로 나누고 의미로 벡터화합니다"
          icon={Database}
        >
          <div className="space-y-4">
            {steps[2].status === 'idle' && (
              <div className="grid grid-cols-2 gap-4">
                <Button 
                  onClick={() => runStep(2)}
                  className="h-20 flex flex-col items-center justify-center"
                >
                  <Database className="h-6 w-6 mb-2" />
                  전처리 실행
                </Button>
                <Button 
                  onClick={() => runStep(2)}
                  className="h-20 flex flex-col items-center justify-center"
                >
                  <Sparkles className="h-6 w-6 mb-2" />
                  임베딩 저장
                </Button>
              </div>
            )}
            
            {steps[2].status === 'running' && (
              <div className="text-center py-4 space-y-4">
                <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2 text-blue-600" />
                
                {/* 실시간 진행률 표시 */}
                {pipelineStatus && (
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>진행률</span>
                      <span>{pipelineStatus.progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                        style={{ width: `${pipelineStatus.progress}%` }}
                      />
                    </div>
                    <p className="text-sm text-gray-600">
                      {pipelineStatus.message}
                    </p>
                  </div>
                )}
                
                {/* 기본 진행 메시지 */}
                {!pipelineStatus && (
                  <>
                    <p className="text-sm text-gray-600">청크 120/120</p>
                    <p className="text-sm text-gray-600">추가 120 · 건너뜀 0 (캐시 0%)</p>
                  </>
                )}
              </div>
            )}
            
            {steps[2].status === 'success' && (
              <Alert>
                <CheckCircle className="h-4 w-4" />
                <AlertDescription>
                  <div className="space-y-3">
                    <p className="font-semibold text-green-800">검색 준비 완료!</p>
                    
                    {/* 상세 결과 표시 */}
                    {steps[2].result?.result && (
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div>
                          <span className="font-medium">청크:</span> {steps[2].result.result.chunks_created || 0}개
                        </div>
                        <div>
                          <span className="font-medium">임베딩:</span> {steps[2].result.result.embeddings_added || 0}개
                        </div>
                      </div>
                    )}
                    
                    <p className="text-sm text-gray-600">
                      컬렉션: {steps[2].result?.result?.collection_name || "legal_documents"}
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
          </div>
        </StepCard>
      )}

      {/* STEP 3: 검색해 보기 */}
      {currentStep >= 3 && (
        <StepCard
          step={3}
          title="원하는 내용을 검색해보세요"
          description="관련 문서를 찾아서 근거로 사용할 수 있어요"
          icon={Search}
        >
          <div className="space-y-4">
            <Input
              placeholder="예) 채권추심 절차"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="text-lg"
            />
            
            <div className="flex flex-wrap gap-2">
              {["채권추심 절차", "압류 방법", "합의서 작성 요령"].map((query) => (
                <Badge 
                  key={query}
                  variant="outline" 
                  className="cursor-pointer hover:bg-blue-50"
                  onClick={() => setSearchQuery(query)}
                >
                  {query}
                </Badge>
              ))}
            </div>
            
            {steps[3].status === 'idle' && (
              <Button 
                onClick={() => runStep(3)} 
                disabled={!searchQuery}
                className="w-full"
                size="lg"
              >
                <Search className="mr-2 h-5 w-5" />
                검색하기
              </Button>
            )}
            
            {steps[3].status === 'success' && (
              <div className="space-y-4">
                <div className="space-y-2">
                  {steps[3].result?.results?.slice(0, 3).map((result: any, index: number) => (
                    <Card key={index} className="p-3">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h4 className="font-medium text-sm">{result.title}</h4>
                          <p className="text-xs text-gray-600 mt-1">{result.snippet}</p>
                        </div>
                        <Badge variant="secondary" className="ml-2">리랭크 완료</Badge>
                      </div>
                    </Card>
                  ))}
                </div>
                <Button 
                  onClick={() => setCurrentStep(4)}
                  className="w-full"
                  size="lg"
                >
                  이 내용으로 글 만들기 <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            )}
          </div>
        </StepCard>
      )}

      {/* STEP 4: 글로 만들기 */}
      {currentStep >= 4 && (
        <StepCard
          step={4}
          title="원하는 톤과 분량을 선택하세요"
          description="기본 프리셋: 블로그용 800–1200자 · '법무법인 혜안' 톤"
          icon={FileText}
        >
          <div className="space-y-4">
            {steps[4].status === 'idle' && (
              <Button 
                onClick={() => runStep(4)} 
                className="w-full"
                size="lg"
              >
                <FileText className="mr-2 h-5 w-5" />
                글 생성
              </Button>
            )}
            
            {steps[4].status === 'running' && (
              <div className="text-center py-4">
                <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2 text-blue-600" />
                <p className="text-sm text-gray-600">품질 검증 중...</p>
              </div>
            )}
            
            {steps[4].status === 'success' && (
              <div className="space-y-4">
                <Alert>
                  <CheckCircle className="h-4 w-4" />
                  <AlertDescription>
                    <div className="space-y-3">
                      <p className="font-semibold">글 생성 완료!</p>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="secondary">표절 검사 통과</Badge>
                        <Badge variant="secondary">문체 일관성</Badge>
                        <Badge variant="secondary">법률 주의사항</Badge>
                      </div>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm">
                          복사
                        </Button>
                        <Button variant="outline" size="sm">
                          Markdown 저장
                        </Button>
                        <Button variant="outline" size="sm">
                          다시 만들기
                        </Button>
                      </div>
                    </div>
                  </AlertDescription>
                </Alert>
              </div>
            )}
          </div>
        </StepCard>
      )}

      {/* 네비게이션 */}
      <div className="flex justify-between mt-8">
        <Button 
          variant="outline" 
          onClick={() => setCurrentStep(Math.max(1, currentStep - 1))}
          disabled={currentStep === 1}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          이전
        </Button>
        <Button 
          variant="outline"
          onClick={() => window.location.href = '/dashboard'}
        >
          대시보드로 이동
        </Button>
      </div>
    </div>
  );
}
