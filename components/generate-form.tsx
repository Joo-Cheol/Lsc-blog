'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Loader2, FileText, CheckCircle, XCircle, RefreshCw } from 'lucide-react';

interface QualityResult {
  passed: boolean;
  reasons: string[];
  scores: Record<string, string>;
  retries: number;
}

interface GenerateResponse {
  success: boolean;
  content: string;
  quality_result: QualityResult;
  provider_used: string;
  context_docs_count: number;
  duration_ms: number;
  message?: string;
}

export default function GenerateForm() {
  const [query, setQuery] = useState('');
  const [withRag, setWithRag] = useState(true);
  const [provider, setProvider] = useState('');
  const [maxTokens, setMaxTokens] = useState(2000);
  const [temperature, setTemperature] = useState(0.7);
  const [maxRetries, setMaxRetries] = useState(2);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query.trim(),
          with_rag: withRag,
          provider: provider || undefined,
          max_tokens: maxTokens,
          temperature: temperature,
          max_retries: maxRetries
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || '생성 요청 실패');
      }

      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegenerate = () => {
    if (result) {
      handleSubmit(new Event('submit') as any);
    }
  };

  const getScoreColor = (score: string) => {
    switch (score) {
      case '통과': return 'bg-green-100 text-green-800';
      case '실패': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            블로그 포스트 생성
          </CardTitle>
          <CardDescription>
            혜안 톤앤매너로 전문적인 법률 블로그 포스트를 생성합니다. 품질 가드가 자동으로 검증합니다.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="query">생성 주제</Label>
              <Textarea
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="채권추심 절차, 지급명령 신청 방법, 소액사건 절차 등..."
                rows={3}
                required
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="max_tokens">최대 토큰 수</Label>
                <Input
                  id="max_tokens"
                  type="number"
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                  min="100"
                  max="4000"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="temperature">생성 온도</Label>
                <Input
                  id="temperature"
                  type="number"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  min="0.0"
                  max="2.0"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="max_retries">최대 재시도</Label>
                <Input
                  id="max_retries"
                  type="number"
                  value={maxRetries}
                  onChange={(e) => setMaxRetries(parseInt(e.target.value))}
                  min="0"
                  max="5"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="provider">LLM Provider</Label>
                <Input
                  id="provider"
                  type="text"
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  placeholder="ollama, gemini (선택사항)"
                />
              </div>
              <div className="space-y-2">
                <Label>옵션</Label>
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="with_rag"
                    checked={withRag}
                    onChange={(e) => setWithRag(e.target.checked)}
                    className="rounded"
                  />
                  <Label htmlFor="with_rag" className="text-sm">
                    RAG 사용 (관련 문서 참조)
                  </Label>
                </div>
              </div>
            </div>

            <div className="flex gap-2">
              <Button type="submit" disabled={isLoading || !query.trim()} className="flex-1">
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    생성 중...
                  </>
                ) : (
                  <>
                    <FileText className="mr-2 h-4 w-4" />
                    포스트 생성
                  </>
                )}
              </Button>
              {result && (
                <Button type="button" variant="outline" onClick={handleRegenerate} disabled={isLoading}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  재생성
                </Button>
              )}
            </div>
          </form>

          {error && (
            <Alert variant="destructive" className="mt-4">
              <XCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 품질 검증 결과 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {result.quality_result.passed ? (
                  <CheckCircle className="h-5 w-5 text-green-600" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-600" />
                )}
                품질 검증
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm">재시도 횟수</span>
                <Badge variant="outline">{result.quality_result.retries}</Badge>
              </div>
              
              <div className="space-y-2">
                <span className="text-sm font-medium">검증 항목</span>
                {Object.entries(result.quality_result.scores).map(([key, score]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-xs capitalize">{key}</span>
                    <Badge className={getScoreColor(score)}>
                      {score}
                    </Badge>
                  </div>
                ))}
              </div>

              {result.quality_result.reasons.length > 0 && (
                <div className="space-y-1">
                  <span className="text-sm font-medium text-red-600">실패 이유</span>
                  {result.quality_result.reasons.map((reason, index) => (
                    <p key={index} className="text-xs text-red-600">• {reason}</p>
                  ))}
                </div>
              )}

              <div className="pt-2 border-t space-y-1 text-xs text-muted-foreground">
                <div>Provider: {result.provider_used}</div>
                <div>컨텍스트 문서: {result.context_docs_count}개</div>
                <div>실행 시간: {result.duration_ms}ms</div>
              </div>
            </CardContent>
          </Card>

          {/* 생성된 콘텐츠 */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>생성된 포스트</CardTitle>
              {result.message && (
                <CardDescription>{result.message}</CardDescription>
              )}
            </CardHeader>
            <CardContent>
              <div className="prose prose-sm max-w-none">
                <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
                  {result.content}
                </pre>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
