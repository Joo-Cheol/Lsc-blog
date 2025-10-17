"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  X, 
  AlertTriangle, 
  RefreshCw, 
  ExternalLink, 
  HelpCircle,
  CheckCircle,
  XCircle,
  Clock
} from "lucide-react";

interface ErrorGuideModalProps {
  isOpen: boolean;
  onClose: () => void;
  errorCode?: string;
  errorMessage?: string;
  suggestion?: string;
}

const errorGuides = {
  INVALID_INPUT: {
    title: "잘못된 블로그 주소",
    description: "입력하신 주소가 올바르지 않습니다.",
    solutions: [
      {
        icon: <CheckCircle className="h-4 w-4 text-green-600" />,
        title: "올바른 형식 확인",
        description: "https://blog.naver.com/블로그ID 형식으로 입력해주세요",
        example: "예: https://blog.naver.com/example123"
      },
      {
        icon: <ExternalLink className="h-4 w-4 text-blue-600" />,
        title: "블로그 주소 복사",
        description: "네이버 블로그에서 주소창의 URL을 복사해서 붙여넣기",
        action: "네이버 블로그로 이동"
      }
    ]
  },
  CRAWL_FAILED: {
    title: "크롤링 실패",
    description: "블로그에서 글을 가져오는 중 문제가 발생했습니다.",
    solutions: [
      {
        icon: <RefreshCw className="h-4 w-4 text-blue-600" />,
        title: "다시 시도",
        description: "일시적인 네트워크 문제일 수 있습니다",
        action: "다시 시도하기"
      },
      {
        icon: <AlertTriangle className="h-4 w-4 text-yellow-600" />,
        title: "블로그 설정 확인",
        description: "블로그가 비공개이거나 접근이 제한되어 있을 수 있습니다",
        action: "블로그 설정 확인"
      },
      {
        icon: <Clock className="h-4 w-4 text-gray-600" />,
        title: "잠시 후 시도",
        description: "서버 부하로 인한 일시적 문제일 수 있습니다",
        action: "5분 후 다시 시도"
      }
    ]
  },
  PIPELINE_FAILED: {
    title: "검색 준비 실패",
    description: "데이터 처리 중 문제가 발생했습니다.",
    solutions: [
      {
        icon: <RefreshCw className="h-4 w-4 text-blue-600" />,
        title: "다시 시도",
        description: "처리 과정에서 일시적 오류가 발생했을 수 있습니다",
        action: "다시 시도하기"
      },
      {
        icon: <AlertTriangle className="h-4 w-4 text-yellow-600" />,
        title: "데이터 확인",
        description: "수집된 데이터가 충분하지 않을 수 있습니다",
        action: "크롤링 다시 실행"
      }
    ]
  },
  NO_DATA: {
    title: "처리할 데이터 없음",
    description: "먼저 블로그를 크롤링해야 합니다.",
    solutions: [
      {
        icon: <ExternalLink className="h-4 w-4 text-blue-600" />,
        title: "블로그 크롤링",
        description: "STEP 1에서 블로그를 먼저 수집해주세요",
        action: "크롤링 페이지로 이동"
      }
    ]
  }
};

export default function ErrorGuideModal({ 
  isOpen, 
  onClose, 
  errorCode, 
  errorMessage, 
  suggestion 
}: ErrorGuideModalProps) {
  if (!isOpen) return null;

  const guide = errorCode ? errorGuides[errorCode as keyof typeof errorGuides] : null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-red-600">
              <XCircle className="h-5 w-5" />
              {guide?.title || "오류 발생"}
            </CardTitle>
            <CardDescription>
              {guide?.description || "작업 중 문제가 발생했습니다."}
            </CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {/* 에러 메시지 */}
          {errorMessage && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <strong>오류 내용:</strong> {errorMessage}
              </AlertDescription>
            </Alert>
          )}

          {/* 제안사항 */}
          {suggestion && (
            <Alert>
              <HelpCircle className="h-4 w-4" />
              <AlertDescription>
                <strong>해결 방법:</strong> {suggestion}
              </AlertDescription>
            </Alert>
          )}

          {/* 가이드 솔루션 */}
          {guide && (
            <div className="space-y-3">
              <h3 className="font-medium text-gray-900">해결 방법</h3>
              {guide.solutions.map((solution, index) => (
                <div key={index} className="p-3 border border-gray-200 rounded-lg">
                  <div className="flex items-start gap-3">
                    {solution.icon}
                    <div className="flex-1">
                      <h4 className="font-medium text-gray-900 mb-1">
                        {solution.title}
                      </h4>
                      <p className="text-sm text-gray-600 mb-2">
                        {solution.description}
                      </p>
                      {solution.example && (
                        <p className="text-xs text-gray-500 bg-gray-50 p-2 rounded">
                          {solution.example}
                        </p>
                      )}
                      {solution.action && (
                        <Button 
                          size="sm" 
                          variant="outline" 
                          className="mt-2"
                          onClick={() => {
                            if (solution.action === "다시 시도하기") {
                              window.location.reload();
                            } else if (solution.action === "크롤링 페이지로 이동") {
                              window.location.href = "/crawl";
                            } else if (solution.action === "네이버 블로그로 이동") {
                              window.open("https://blog.naver.com", "_blank");
                            } else if (solution.action === "블로그 설정 확인") {
                              window.open("https://blog.naver.com/PostList.naver", "_blank");
                            }
                          }}
                        >
                          {solution.action}
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 일반적인 도움말 */}
          <div className="border-t pt-4">
            <h3 className="font-medium text-gray-900 mb-2">추가 도움말</h3>
            <div className="text-sm text-gray-600 space-y-1">
              <p>• 문제가 지속되면 브라우저를 새로고침해보세요</p>
              <p>• 네트워크 연결 상태를 확인해주세요</p>
              <p>• 다른 블로그 주소로 시도해보세요</p>
            </div>
          </div>

          {/* 닫기 버튼 */}
          <div className="flex justify-end pt-4">
            <Button onClick={onClose} variant="outline">
              닫기
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

