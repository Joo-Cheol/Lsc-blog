import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { 
  Search, 
  FileText, 
  Download, 
  Upload, 
  BarChart3, 
  Settings,
  ArrowRight,
  Zap
} from 'lucide-react';

export default function HomePage() {
  const features = [
    {
      icon: <Download className="h-6 w-6" />,
      title: "증분 크롤링",
      description: "네이버 블로그에서 새로운 포스트만 자동으로 수집합니다.",
      href: "/crawl",
      color: "text-blue-600"
    },
    {
      icon: <Search className="h-6 w-6" />,
      title: "RAG 검색",
      description: "벡터 검색과 리랭킹으로 정확한 법률 문서를 찾습니다.",
      href: "/search",
      color: "text-green-600"
    },
    {
      icon: <FileText className="h-6 w-6" />,
      title: "AI 생성",
      description: "혜안 톤앤매너로 전문적인 블로그 포스트를 생성합니다.",
      href: "/generate",
      color: "text-purple-600"
    },
    {
      icon: <Upload className="h-6 w-6" />,
      title: "자동 업로드",
      description: "생성된 포스트를 네이버 블로그에 자동으로 업로드합니다.",
      href: "/upload",
      color: "text-orange-600"
    }
  ];

  const stats = [
    { label: "수집된 포스트", value: "1,234", icon: <Download className="h-4 w-4" /> },
    { label: "검색된 문서", value: "5,678", icon: <Search className="h-4 w-4" /> },
    { label: "생성된 포스트", value: "89", icon: <FileText className="h-4 w-4" /> },
    { label: "업로드된 포스트", value: "45", icon: <Upload className="h-4 w-4" /> }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* 헤더 */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Zap className="h-8 w-8 text-blue-600" />
            <h1 className="text-4xl font-bold text-gray-900">
              LSC Blog Automation
            </h1>
          </div>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            AI 기반 네이버 블로그 자동화 시스템으로 법률 콘텐츠를 효율적으로 관리하세요
          </p>
        </div>

        {/* 통계 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
          {stats.map((stat, index) => (
            <Card key={index} className="text-center">
              <CardContent className="pt-6">
                <div className="flex items-center justify-center gap-2 mb-2">
                  {stat.icon}
                  <span className="text-2xl font-bold text-gray-900">
                    {stat.value}
                  </span>
                </div>
                <p className="text-sm text-gray-600">{stat.label}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* 주요 기능 */}
        <div className="mb-12">
          <h2 className="text-2xl font-bold text-center mb-8 text-gray-900">
            주요 기능
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <Card key={index} className="hover:shadow-lg transition-shadow cursor-pointer group">
                <CardHeader>
                  <div className={`${feature.color} mb-2`}>
                    {feature.icon}
                  </div>
                  <CardTitle className="text-lg">{feature.title}</CardTitle>
                  <CardDescription>{feature.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <Link href={feature.href}>
                    <Button variant="outline" className="w-full group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                      시작하기
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* 추가 기능 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-blue-600" />
                <CardTitle>시스템 모니터링</CardTitle>
              </div>
              <CardDescription>
                실시간 시스템 상태와 성능 지표를 확인하세요
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link href="/dashboard">
                <Button variant="outline" className="w-full">
                  대시보드 보기
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Settings className="h-5 w-5 text-gray-600" />
                <CardTitle>시스템 설정</CardTitle>
              </div>
              <CardDescription>
                API 설정과 시스템 구성을 관리하세요
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link href="/config">
                <Button variant="outline" className="w-full">
                  설정 관리
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>

        {/* 워크플로우 */}
        <Card className="mb-12">
          <CardHeader>
            <CardTitle className="text-center">자동화 워크플로우</CardTitle>
            <CardDescription className="text-center">
              크롤링부터 업로드까지 완전 자동화된 프로세스
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <span className="text-blue-600 font-bold">1</span>
                </div>
                <span className="font-medium">크롤링</span>
              </div>
              <ArrowRight className="h-4 w-4 text-gray-400" />
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                  <span className="text-green-600 font-bold">2</span>
                </div>
                <span className="font-medium">검색</span>
              </div>
              <ArrowRight className="h-4 w-4 text-gray-400" />
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                  <span className="text-purple-600 font-bold">3</span>
                </div>
                <span className="font-medium">생성</span>
              </div>
              <ArrowRight className="h-4 w-4 text-gray-400" />
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center">
                  <span className="text-orange-600 font-bold">4</span>
                </div>
                <span className="font-medium">업로드</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* CTA */}
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-4 text-gray-900">
            지금 시작해보세요
          </h2>
          <p className="text-gray-600 mb-6">
            AI 기반 블로그 자동화로 콘텐츠 제작 시간을 단축하고 품질을 향상시키세요
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/crawl">
              <Button size="lg" className="w-full sm:w-auto">
                <Download className="mr-2 h-5 w-5" />
                크롤링 시작
              </Button>
            </Link>
            <Link href="/generate">
              <Button size="lg" variant="outline" className="w-full sm:w-auto">
                <FileText className="mr-2 h-5 w-5" />
                포스트 생성
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}