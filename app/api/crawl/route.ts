import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // 호환성: 구버전에서 blog_id/category_no/max_pages가 올 수도 있음
    // → 있으면 그대로 유지, 없으면 blog_url만 사용
    const payload = body?.blog_id || body?.category_no || body?.max_pages
      ? body
      : { blog_url: body?.blog_url };
    
    // API 서버로 요청 전달
    const response = await fetch(`${API_BASE_URL}/api/v1/crawl`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { success: false, error: errorData.error || errorData.detail || '크롤링 요청 실패' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('크롤링 API 오류:', error);
    return NextResponse.json(
      { success: false, error: '서버 오류가 발생했습니다' },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const runId = searchParams.get('runId');
    
    if (!runId) {
      return NextResponse.json(
        { success: false, error: 'runId가 필요합니다' },
        { status: 400 }
      );
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/crawl/status/${runId}`);
    
    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { success: false, error: errorData.detail || '상태 조회 실패' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('크롤링 상태 조회 오류:', error);
    return NextResponse.json(
      { success: false, error: '서버 오류가 발생했습니다' },
      { status: 500 }
    );
  }
}
