import SearchForm from '@/components/search-form';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Search, Info, Zap } from 'lucide-react';

export default function SearchPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* 헤더 */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Search className="h-8 w-8 text-green-600" />
            <h1 className="text-3xl font-bold text-gray-900">
              법률 문서 검색
            </h1>
          </div>
          <p className="text-lg text-gray-600">
            RAG 기반 검색으로 관련 법률 문서를 정확하게 찾아보세요
          </p>
        </div>

        {/* 정보 카드 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                RAG 검색
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                <div>
                  <h4 className="font-medium mb-1">벡터 검색</h4>
                  <p className="text-gray-600">
                    의미 기반 벡터 검색으로 관련성 높은 문서를 찾습니다.
                  </p>
                </div>
                <div>
                  <h4 className="font-medium mb-1">리랭킹</h4>
                  <p className="text-gray-600">
                    Cross-encoder를 사용해 검색 결과의 정확도를 향상시킵니다.
                  </p>
                </div>
                <div>
                  <h4 className="font-medium mb-1">컨텍스트 제공</h4>
                  <p className="text-gray-600">
                    검색된 문서를 AI 생성 시 컨텍스트로 활용합니다.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Info className="h-5 w-5" />
                검색 옵션
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                <div>
                  <h4 className="font-medium mb-1">결과 수 조절</h4>
                  <p className="text-gray-600">
                    1-20개 범위에서 원하는 결과 수를 설정할 수 있습니다.
                  </p>
                </div>
                <div>
                  <h4 className="font-medium mb-1">법률 주제 필터</h4>
                  <p className="text-gray-600">
                    특정 법률 분야로 검색 범위를 제한할 수 있습니다.
                  </p>
                </div>
                <div>
                  <h4 className="font-medium mb-1">리랭킹 토글</h4>
                  <p className="text-gray-600">
                    필요에 따라 리랭킹 기능을 켜거나 끌 수 있습니다.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 검색 폼 */}
        <SearchForm />
      </div>
    </div>
  );
}
