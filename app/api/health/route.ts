import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { success: false, error: errorData.detail || '헬스 체크 실패' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('헬스 체크 API 오류:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: '서버 연결 실패',
        status: 'unhealthy',
        timestamp: new Date().toISOString()
      },
      { status: 503 }
    );
  }
}
