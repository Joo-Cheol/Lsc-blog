import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    console.log('Generate API 요청 받음:', { body, API_BASE_URL });
    
    // API 서버로 요청 전달
    const response = await fetch(`${API_BASE_URL}/api/v1/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    console.log('백엔드 응답 상태:', response.status);

    if (!response.ok) {
      const errorData = await response.json();
      console.error('백엔드 오류:', errorData);
      return NextResponse.json(
        { success: false, error: errorData.detail || '생성 요청 실패' },
        { status: response.status }
      );
    }

    const data = await response.json();
    console.log('생성 성공:', { success: data.success, contentLength: data.content?.length });
    return NextResponse.json(data);
  } catch (error) {
    console.error('생성 API 오류:', error);
    return NextResponse.json(
      { success: false, error: '서버 오류가 발생했습니다' },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const type = searchParams.get('type') || 'templates';
    
    if (type === 'templates') {
      const response = await fetch(`${API_BASE_URL}/api/v1/generate/templates`);
      
      if (!response.ok) {
        const errorData = await response.json();
        return NextResponse.json(
          { success: false, error: errorData.detail || '템플릿 조회 실패' },
          { status: response.status }
        );
      }

      const data = await response.json();
      return NextResponse.json(data);
    } else {
      return NextResponse.json(
        { success: false, error: '잘못된 요청 타입입니다' },
        { status: 400 }
      );
    }
  } catch (error) {
    console.error('생성 API 오류:', error);
    return NextResponse.json(
      { success: false, error: '서버 오류가 발생했습니다' },
      { status: 500 }
    );
  }
}
