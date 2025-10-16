import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // API 서버로 요청 전달
    const response = await fetch(`${API_BASE_URL}/api/v1/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { success: false, error: errorData.detail || '검색 요청 실패' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('검색 API 오류:', error);
    return NextResponse.json(
      { success: false, error: '서버 오류가 발생했습니다' },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const q = searchParams.get('q') || '';
    const type = searchParams.get('type') || 'suggestions';
    
    let endpoint = '';
    if (type === 'suggestions') {
      endpoint = `/api/v1/search/suggestions?q=${encodeURIComponent(q)}`;
    } else if (type === 'popular') {
      const limit = searchParams.get('limit') || '10';
      endpoint = `/api/v1/search/popular?limit=${limit}`;
    } else {
      return NextResponse.json(
        { success: false, error: '잘못된 요청 타입입니다' },
        { status: 400 }
      );
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`);
    
    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { success: false, error: errorData.detail || '검색 요청 실패' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('검색 API 오류:', error);
    return NextResponse.json(
      { success: false, error: '서버 오류가 발생했습니다' },
      { status: 500 }
    );
  }
}
