import CrawlForm from '@/components/crawl-form';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Download, Info } from 'lucide-react';

export default function CrawlPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* 헤더 */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Download className="h-8 w-8 text-blue-600" />
            <h1 className="text-3xl font-bold text-gray-900">
              네이버 블로그 크롤링
            </h1>
          </div>
          <p className="text-lg text-gray-600">
            네이버 블로그에서 새로운 포스트를 자동으로 수집합니다
          </p>
        </div>

        {/* 정보 카드 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Info className="h-5 w-5" />
              크롤링 정보
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <h4 className="font-medium mb-2">증분 크롤링</h4>
                <p className="text-gray-600">
                  이전에 수집한 포스트는 자동으로 스킵하여 중복을 방지합니다.
                </p>
              </div>
              <div>
                <h4 className="font-medium mb-2">중복 제거</h4>
                <p className="text-gray-600">
                  내용 해시를 기반으로 중복된 포스트를 자동으로 제거합니다.
                </p>
              </div>
              <div>
                <h4 className="font-medium mb-2">체크포인트</h4>
                <p className="text-gray-600">
                  마지막 수집 위치를 저장하여 다음 크롤링 시 이어서 진행합니다.
                </p>
              </div>
              <div>
                <h4 className="font-medium mb-2">안전한 지연</h4>
                <p className="text-gray-600">
                  서버 부하를 방지하기 위해 요청 간 적절한 지연 시간을 적용합니다.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 크롤링 폼 */}
        <CrawlForm />
      </div>
    </div>
  );
}
