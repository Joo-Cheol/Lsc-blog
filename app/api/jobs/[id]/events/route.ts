import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${params.id}/events`, {
      method: "GET",
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    });

    if (!response.ok) {
      return new NextResponse("Job 이벤트 조회 실패", { status: response.status });
    }

    // SSE 스트림을 그대로 전달
    return new NextResponse(response.body, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    });
  } catch (error) {
    console.error("Job 이벤트 API 오류:", error);
    return new NextResponse("서버 오류가 발생했습니다", { status: 500 });
  }
}
