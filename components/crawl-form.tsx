'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Play, CheckCircle, XCircle } from 'lucide-react';

interface CrawlResult {
  success: boolean;
  run_id: string;
  crawled_count: number;
  skipped_count: number;
  failed_count: number;
  last_logno_updated?: string;
  duration_ms: number;
  message?: string;
}

export default function CrawlForm() {
  const [formData, setFormData] = useState({
    blog_id: 'tjwlswlsdl',
    category_no: 6,
    max_pages: 1
  });
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<CrawlResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('/api/crawl', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || '크롤링 요청 실패');
      }

      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다');
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (field: string, value: string | number) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Play className="h-5 w-5" />
          네이버 블로그 크롤링
        </CardTitle>
        <CardDescription>
          네이버 블로그에서 포스트를 수집합니다. 증분 크롤링과 중복 제거가 자동으로 적용됩니다.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="blog_id">블로그 ID</Label>
              <Input
                id="blog_id"
                type="text"
                value={formData.blog_id}
                onChange={(e) => handleInputChange('blog_id', e.target.value)}
                placeholder="tjwlswlsdl"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="category_no">카테고리 번호</Label>
              <Input
                id="category_no"
                type="number"
                value={formData.category_no}
                onChange={(e) => handleInputChange('category_no', parseInt(e.target.value))}
                min="0"
                required
              />
            </div>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="max_pages">최대 페이지 수</Label>
            <Input
              id="max_pages"
              type="number"
              value={formData.max_pages}
              onChange={(e) => handleInputChange('max_pages', parseInt(e.target.value))}
              min="1"
              max="10"
              required
            />
            <p className="text-sm text-muted-foreground">
              한 번에 크롤링할 최대 페이지 수입니다 (1-10)
            </p>
          </div>

          <Button type="submit" disabled={isLoading} className="w-full">
            {isLoading ? (
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
          <Alert variant="destructive" className="mt-4">
            <XCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {result && (
          <Alert className="mt-4">
            <CheckCircle className="h-4 w-4" />
            <AlertDescription>
              <div className="space-y-2">
                <p className="font-medium">크롤링 완료!</p>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>실행 ID: {result.run_id}</div>
                  <div>수집된 포스트: {result.crawled_count}개</div>
                  <div>스킵된 포스트: {result.skipped_count}개</div>
                  <div>실패한 포스트: {result.failed_count}개</div>
                  <div>실행 시간: {result.duration_ms}ms</div>
                  {result.last_logno_updated && (
                    <div>마지막 logno: {result.last_logno_updated}</div>
                  )}
                </div>
                {result.message && (
                  <p className="text-sm text-muted-foreground mt-2">
                    {result.message}
                  </p>
                )}
              </div>
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
