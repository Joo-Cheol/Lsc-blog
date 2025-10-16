import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // API 서버로 요청 전달
    const response = await fetch(`${API_BASE_URL}/api/v1/upload`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { success: false, error: errorData.detail || '업로드 요청 실패' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('업로드 API 오류:', error);
    return NextResponse.json(
      { success: false, error: '서버 오류가 발생했습니다' },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const uploadId = searchParams.get('uploadId');
    const type = searchParams.get('type') || 'status';
    
    if (type === 'status' && uploadId) {
      const response = await fetch(`${API_BASE_URL}/api/v1/upload/status/${uploadId}`);
      
      if (!response.ok) {
        const errorData = await response.json();
        return NextResponse.json(
          { success: false, error: errorData.detail || '상태 조회 실패' },
          { status: response.status }
        );
      }

      const data = await response.json();
      return NextResponse.json(data);
    } else if (type === 'history') {
      const limit = searchParams.get('limit') || '10';
      const response = await fetch(`${API_BASE_URL}/api/v1/upload/history?limit=${limit}`);
      
      if (!response.ok) {
        const errorData = await response.json();
        return NextResponse.json(
          { success: false, error: errorData.detail || '히스토리 조회 실패' },
          { status: response.status }
        );
      }

      const data = await response.json();
      return NextResponse.json(data);
    } else {
      return NextResponse.json(
        { success: false, error: '잘못된 요청입니다' },
        { status: 400 }
      );
    }
  } catch (error) {
    console.error('업로드 API 오류:', error);
    return NextResponse.json(
      { success: false, error: '서버 오류가 발생했습니다' },
      { status: 500 }
    );
  }
}
