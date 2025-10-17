import GenerateForm from '@/components/generate-form';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { FileText, Info, Shield, Sparkles } from 'lucide-react';

export default function GeneratePage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* 헤더 */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <FileText className="h-8 w-8 text-purple-600" />
            <h1 className="text-3xl font-bold text-gray-900">
              AI 블로그 포스트 생성
            </h1>
          </div>
          <p className="text-lg text-gray-600">
            혜안 톤앤매너로 전문적인 법률 블로그 포스트를 자동 생성합니다
          </p>
          <div className="mt-4 flex items-center justify-center gap-4">
            <div className="text-sm text-gray-500">
              품질 가드: 길이/소제목/체크리스트/디스클레이머 자동 검증
            </div>
          </div>
        </div>

        {/* 정보 카드 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5" />
                혜안 톤앤매너
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                <div>
                  <h4 className="font-medium mb-1">공감적 접근</h4>
                  <p className="text-gray-600">
                    독자의 어려움에 공감하며 시작합니다.
                  </p>
                </div>
                <div>
                  <h4 className="font-medium mb-1">희망 제시</h4>
                  <p className="text-gray-600">
                    해결책이 있음을 암시하며 긍정적인 기대를 심어줍니다.
                  </p>
                </div>
                <div>
                  <h4 className="font-medium mb-1">전문성 강조</h4>
                  <p className="text-gray-600">
                    법무법인 혜안의 전문성을 자연스럽게 어필합니다.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                품질 가드
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                <div>
                  <h4 className="font-medium mb-1">구조 검증</h4>
                  <p className="text-gray-600">
                    필수 섹션과 소제목 수를 자동으로 검증합니다.
                  </p>
                </div>
                <div>
                  <h4 className="font-medium mb-1">길이 제한</h4>
                  <p className="text-gray-600">
                    1600-1900자 범위 내에서 적절한 길이를 유지합니다.
                  </p>
                </div>
                <div>
                  <h4 className="font-medium mb-1">자동 재생성</h4>
                  <p className="text-gray-600">
                    품질 기준 미달 시 자동으로 재생성합니다.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Info className="h-5 w-5" />
                생성 옵션
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                <div>
                  <h4 className="font-medium mb-1">RAG 통합</h4>
                  <p className="text-gray-600">
                    검색된 관련 문서를 컨텍스트로 활용합니다.
                  </p>
                </div>
                <div>
                  <h4 className="font-medium mb-1">다중 Provider</h4>
                  <p className="text-gray-600">
                    Ollama, Gemini 등 다양한 LLM을 지원합니다.
                  </p>
                </div>
                <div>
                  <h4 className="font-medium mb-1">커스터마이징</h4>
                  <p className="text-gray-600">
                    토큰 수, 온도, 재시도 횟수를 조절할 수 있습니다.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 생성 폼 */}
        <GenerateForm />
      </div>
    </div>
  );
}