"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  Database, 
  RefreshCw, 
  Download, 
  Upload, 
  Settings,
  Play,
  CheckCircle,
  AlertTriangle,
  Loader2
} from "lucide-react";

export default function OpsPage() {
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [results, setResults] = useState<Record<string, any>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [confirmModal, setConfirmModal] = useState<{show: boolean, task: string, dangerWord: string}>({
    show: false, task: "", dangerWord: ""
  });
  const [confirmInput, setConfirmInput] = useState("");
  const [pipelineStatus, setPipelineStatus] = useState<Record<string, any>>({});

  const handleOperation = async (operation: string, payload?: any) => {
    setLoading(prev => ({ ...prev, [operation]: true }));
    setErrors(prev => ({ ...prev, [operation]: "" }));
    
    try {
      const response = await fetch(`/api/v1/${operation}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload || {})
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || data.detail || "작업 실패");
      }
      
      setResults(prev => ({ ...prev, [operation]: data }));
      
      // 파이프라인 작업인 경우 상태 폴링 시작
      if (data.task_id && (operation.includes("pipeline") || data.task === "preprocess_embed")) {
        pollPipelineStatus(data.task_id, operation);
      }
    } catch (error) {
      setErrors(prev => ({ 
        ...prev, 
        [operation]: error instanceof Error ? error.message : "알 수 없는 오류"
      }));
    } finally {
      setLoading(prev => ({ ...prev, [operation]: false }));
    }
  };

  const pollPipelineStatus = async (taskId: string, operation: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/pipeline/status?id=${taskId}`);
        const status = await response.json();
        
        setPipelineStatus(prev => ({ ...prev, [operation]: status }));
        
        if (status.status === "completed" || status.status === "failed") {
          clearInterval(pollInterval);
          setLoading(prev => ({ ...prev, [operation]: false }));
          
          if (status.status === "completed") {
            setResults(prev => ({ ...prev, [operation]: status }));
          } else {
            setErrors(prev => ({ ...prev, [operation]: status.error || "파이프라인 실패" }));
          }
        }
      } catch (error) {
        console.error("상태 폴링 실패:", error);
        clearInterval(pollInterval);
        setLoading(prev => ({ ...prev, [operation]: false }));
      }
    }, 1000); // 1초마다 폴링
  };

  const handleDangerousOperation = (task: string, dangerWord: string) => {
    setConfirmModal({ show: true, task, dangerWord });
    setConfirmInput("");
  };

  const confirmDangerousOperation = async () => {
    if (confirmInput === confirmModal.dangerWord) {
      setConfirmModal({ show: false, task: "", dangerWord: "" });
      await handleOperation(confirmModal.task);
    }
  };

  const OperationCard = ({ 
    title, 
    description, 
    operation, 
    payload, 
    icon: Icon, 
    variant = "default" 
  }: {
    title: string;
    description: string;
    operation: string;
    payload?: any;
    icon: any;
    variant?: "default" | "destructive";
  }) => {
    const isLoading = loading[operation];
    const result = results[operation];
    const error = errors[operation];
    
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Icon className="h-5 w-5" />
            {title}
          </CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button 
            onClick={() => handleOperation(operation, payload)}
            disabled={isLoading}
            variant={variant === "destructive" ? "destructive" : "default"}
            className="w-full"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                실행 중...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                실행
              </>
            )}
          </Button>
          
          {result && (
            <Alert>
              <CheckCircle className="h-4 w-4" />
              <AlertDescription>
                <pre className="text-sm whitespace-pre-wrap">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </AlertDescription>
            </Alert>
          )}
          
          {error && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">운영 도구</h1>
        <p className="text-gray-600">자주 하는 일부터 고급 설정까지</p>
      </div>

      {/* 시스템 상태 패널 */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5" />
            시스템 상태 확인
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <Badge variant="secondary">API OK</Badge>
            <Badge variant="secondary">DB OK</Badge>
            <Badge variant="secondary">AI OK</Badge>
            <span className="text-sm text-gray-500">마지막 업데이트: 13:38</span>
          </div>
        </CardContent>
      </Card>

      {/* 초심자 섹션 */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">자주 하는 일</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Play className="h-5 w-5" />
                원클릭 파이프라인
              </CardTitle>
              <CardDescription>
                최근 수집한 글을 자동으로 정리·저장하고 검색까지 준비합니다
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button 
                onClick={() => handleOperation("pipeline/run", { task: "preprocess_embed" })}
                disabled={loading["pipeline/run"]}
                className="w-full"
                size="lg"
              >
                {loading["pipeline/run"] ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    처리 중...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    지금 실행
                  </>
                )}
              </Button>
              
              {/* 실시간 진행률 표시 */}
              {pipelineStatus["pipeline/run"] && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>진행률</span>
                    <span>{pipelineStatus["pipeline/run"].progress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${pipelineStatus["pipeline/run"].progress}%` }}
                    />
                  </div>
                  <p className="text-sm text-gray-600 text-center">
                    {pipelineStatus["pipeline/run"].message}
                  </p>
                </div>
              )}
              
              {/* 완료 결과 표시 */}
              {results["pipeline/run"] && results["pipeline/run"].status === "completed" && (
                <Alert>
                  <CheckCircle className="h-4 w-4" />
                  <AlertDescription>
                    <div className="space-y-2">
                      <p className="font-semibold text-green-800">파이프라인 완료!</p>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div>
                          <span className="font-medium">청크:</span> {results["pipeline/run"].result?.chunks_created || 0}개
                        </div>
                        <div>
                          <span className="font-medium">임베딩:</span> {results["pipeline/run"].result?.embeddings_added || 0}개
                        </div>
                      </div>
                      <p className="text-xs text-gray-500">
                        컬렉션: {results["pipeline/run"].result?.collection_name || "legal_documents"}
                      </p>
                    </div>
                  </AlertDescription>
                </Alert>
              )}
              
              <p className="text-sm text-gray-500 text-center">보통 1–3분 소요</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <RefreshCw className="h-5 w-5" />
                새 글만 다시 수집
              </CardTitle>
              <CardDescription>
                이미 본 글은 건너뜁니다
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button 
                onClick={() => handleOperation("crawl", { blog_url: "https://blog.naver.com/tjwlswlsdl" })}
                disabled={loading["crawl"]}
                className="w-full"
                size="lg"
                variant="outline"
              >
                {loading["crawl"] ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    확인 중...
                  </>
                ) : (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4" />
                    새 글 확인
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 고급 설정 */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">고급 설정</h2>
          <Button 
            variant="outline" 
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            {showAdvanced ? "접기" : "펼치기"}
          </Button>
        </div>
        
        {showAdvanced && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* 전처리/청킹 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  전처리/청킹
                  <Badge variant="secondary">권장</Badge>
                </CardTitle>
                <CardDescription>원본 데이터를 정제하고 청크로 분할합니다</CardDescription>
              </CardHeader>
              <CardContent>
                <Button 
                  onClick={() => handleOperation("index/preprocess", { chunk_size: 1000, chunk_overlap: 200 })}
                  disabled={loading["index/preprocess"]}
                  className="w-full"
                >
                  {loading["index/preprocess"] ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      처리 중...
                    </>
                  ) : (
                    <>
                      <Settings className="mr-2 h-4 w-4" />
                      시작
                    </>
                  )}
                </Button>
                <p className="text-xs text-gray-500 mt-2">권장값: 1000/200</p>
              </CardContent>
            </Card>
            
            {/* 임베딩/업서트 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  임베딩/업서트
                  <Badge variant="secondary">권장</Badge>
                </CardTitle>
                <CardDescription>텍스트를 벡터화하고 ChromaDB에 저장합니다</CardDescription>
              </CardHeader>
              <CardContent>
                <Button 
                  onClick={() => handleOperation("index/embed", { batch_size: 32 })}
                  disabled={loading["index/embed"]}
                  className="w-full"
                >
                  {loading["index/embed"] ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      저장 중...
                    </>
                  ) : (
                    <>
                      <Database className="mr-2 h-4 w-4" />
                      저장하기
                    </>
                  )}
                </Button>
                <p className="text-xs text-gray-500 mt-2">권장값: 32</p>
              </CardContent>
            </Card>
            
            {/* ChromaDB 재구축 */}
            <Card className="border-red-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-red-700">
                  <AlertTriangle className="h-5 w-5" />
                  ChromaDB 재구축
                  <Badge variant="destructive">위험</Badge>
                </CardTitle>
                <CardDescription>벡터 데이터베이스를 완전히 재구축합니다</CardDescription>
              </CardHeader>
              <CardContent>
                <Button 
                  onClick={() => handleDangerousOperation("index/rebuild", "REBUILD")}
                  disabled={loading["index/rebuild"]}
                  variant="destructive"
                  className="w-full"
                >
                  {loading["index/rebuild"] ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      재구축 중...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="mr-2 h-4 w-4" />
                      재구축
                    </>
                  )}
                </Button>
                <p className="text-xs text-red-500 mt-2">⚠️ 모든 데이터가 삭제됩니다</p>
              </CardContent>
            </Card>
            
            {/* 백업 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Download className="h-5 w-5" />
                  데이터 백업
                </CardTitle>
                <CardDescription>현재 데이터를 백업 파일로 저장합니다</CardDescription>
              </CardHeader>
              <CardContent>
                <Button 
                  onClick={() => handleOperation("backup")}
                  disabled={loading["backup"]}
                  className="w-full"
                >
                  {loading["backup"] ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      백업 중...
                    </>
                  ) : (
                    <>
                      <Download className="mr-2 h-4 w-4" />
                      백업하기
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
            
            {/* 복원 */}
            <Card className="border-red-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-red-700">
                  <AlertTriangle className="h-5 w-5" />
                  데이터 복원
                  <Badge variant="destructive">위험</Badge>
                </CardTitle>
                <CardDescription>백업 파일에서 데이터를 복원합니다</CardDescription>
              </CardHeader>
              <CardContent>
                <Button 
                  onClick={() => handleDangerousOperation("restore", "RESTORE")}
                  disabled={loading["restore"]}
                  variant="destructive"
                  className="w-full"
                >
                  {loading["restore"] ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      복원 중...
                    </>
                  ) : (
                    <>
                      <Upload className="mr-2 h-4 w-4" />
                      복원
                    </>
                  )}
                </Button>
                <p className="text-xs text-red-500 mt-2">⚠️ 현재 데이터가 덮어씌워집니다</p>
              </CardContent>
            </Card>
            
            {/* 시스템 상태 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5" />
                  시스템 상태
                </CardTitle>
                <CardDescription>전체 시스템의 상태를 확인합니다</CardDescription>
              </CardHeader>
              <CardContent>
                <Button 
                  onClick={() => handleOperation("health")}
                  disabled={loading["health"]}
                  className="w-full"
                >
                  {loading["health"] ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      확인 중...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="mr-2 h-4 w-4" />
                      확인하기
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          </div>
        )}
      </div>

      {/* 위험 작업 확인 모달 */}
      {confirmModal.show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-96">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-red-700">
                <AlertTriangle className="h-5 w-5" />
                위험한 작업 확인
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-gray-600">
                이 작업은 데이터를 삭제할 수 있습니다. 계속하려면 <strong>{confirmModal.dangerWord}</strong>를 입력하세요.
              </p>
              <Input
                placeholder={confirmModal.dangerWord}
                value={confirmInput}
                onChange={(e) => setConfirmInput(e.target.value)}
              />
              <div className="flex gap-2">
                <Button 
                  onClick={confirmDangerousOperation}
                  disabled={confirmInput !== confirmModal.dangerWord}
                  variant="destructive"
                  className="flex-1"
                >
                  확인
                </Button>
                <Button 
                  onClick={() => setConfirmModal({ show: false, task: "", dangerWord: "" })}
                  variant="outline"
                  className="flex-1"
                >
                  취소
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 주의사항 */}
      <Alert className="mt-8">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          <strong>주의:</strong> 파괴적 작업(재구축, 복원)은 데이터 손실을 일으킬 수 있습니다. 
          실행 전 반드시 백업을 수행하세요.
        </AlertDescription>
      </Alert>
    </div>
  );
}