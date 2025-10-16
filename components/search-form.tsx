'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Loader2, Search, ExternalLink, Clock } from 'lucide-react';

interface SearchResult {
  text: string;
  score: number;
  metadata: {
    source_url?: string;
    published_at?: string;
    law_topic?: string;
  };
  source_url?: string;
  published_at?: string;
}

interface SearchResponse {
  success: boolean;
  query: string;
  results: SearchResult[];
  total_results: number;
  with_rerank: boolean;
  duration_ms: number;
  suggestions?: string[];
}

export default function SearchForm() {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(6);
  const [withRerank, setWithRerank] = useState(true);
  const [lawTopic, setLawTopic] = useState('채권추심');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query.trim(),
          top_k: topK,
          with_rerank: withRerank,
          law_topic: lawTopic
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || '검색 요청 실패');
      }

      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion);
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            법률 문서 검색
          </CardTitle>
          <CardDescription>
            RAG 기반 검색으로 관련 법률 문서를 찾아보세요. 리랭킹을 통해 더 정확한 결과를 제공합니다.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="query">검색 쿼리</Label>
              <Input
                id="query"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="채권추심 절차, 지급명령 신청 방법 등..."
                required
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="top_k">결과 수</Label>
                <Input
                  id="top_k"
                  type="number"
                  value={topK}
                  onChange={(e) => setTopK(parseInt(e.target.value))}
                  min="1"
                  max="20"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="law_topic">법률 주제</Label>
                <Input
                  id="law_topic"
                  type="text"
                  value={lawTopic}
                  onChange={(e) => setLawTopic(e.target.value)}
                  placeholder="채권추심"
                />
              </div>
              <div className="space-y-2">
                <Label>옵션</Label>
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="with_rerank"
                    checked={withRerank}
                    onChange={(e) => setWithRerank(e.target.checked)}
                    className="rounded"
                  />
                  <Label htmlFor="with_rerank" className="text-sm">
                    리랭킹 사용
                  </Label>
                </div>
              </div>
            </div>

            <Button type="submit" disabled={isLoading || !query.trim()} className="w-full">
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  검색 중...
                </>
              ) : (
                <>
                  <Search className="mr-2 h-4 w-4" />
                  검색
                </>
              )}
            </Button>
          </form>

          {error && (
            <Alert variant="destructive" className="mt-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>검색 결과</span>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Clock className="h-4 w-4" />
                {result.duration_ms}ms
                {result.with_rerank && (
                  <Badge variant="secondary">리랭킹 적용</Badge>
                )}
              </div>
            </CardTitle>
            <CardDescription>
              "{result.query}"에 대한 {result.total_results}개 결과
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {result.results.map((item, index) => (
                <div key={index} className="border rounded-lg p-4 space-y-2">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-sm text-muted-foreground mb-2">
                        유사도: {(item.score * 100).toFixed(1)}%
                      </p>
                      <p className="text-sm leading-relaxed">
                        {item.text}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <div className="flex items-center gap-4">
                      {item.published_at && (
                        <span>{item.published_at}</span>
                      )}
                      {item.metadata.law_topic && (
                        <Badge variant="outline" className="text-xs">
                          {item.metadata.law_topic}
                        </Badge>
                      )}
                    </div>
                    {item.source_url && (
                      <a
                        href={item.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 hover:text-primary"
                      >
                        <ExternalLink className="h-3 w-3" />
                        원문 보기
                      </a>
                    )}
                  </div>
                </div>
              ))}

              {result.suggestions && result.suggestions.length > 0 && (
                <div className="mt-6">
                  <h4 className="text-sm font-medium mb-2">검색 제안</h4>
                  <div className="flex flex-wrap gap-2">
                    {result.suggestions.map((suggestion, index) => (
                      <Button
                        key={index}
                        variant="outline"
                        size="sm"
                        onClick={() => handleSuggestionClick(suggestion)}
                        className="text-xs"
                      >
                        {suggestion}
                      </Button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
