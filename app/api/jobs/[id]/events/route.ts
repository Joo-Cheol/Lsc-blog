import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const url = new URL(request.url);
    const since = url.searchParams.get('since');
    const eventsUrl = since 
      ? `${API_BASE_URL}/api/v1/jobs/${params.id}/events?since=${since}`
      : `${API_BASE_URL}/api/v1/jobs/${params.id}/events`;

    console.log("SSE 프록시 요청:", eventsUrl);

    const response = await fetch(eventsUrl, {
      method: "GET",
      headers: {
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
      },
    });

    if (!response.ok) {
      console.error("SSE 응답 오류:", response.status, response.statusText);
      return new NextResponse("Job 이벤트 조회 실패", { status: response.status });
    }

    // SSE 스트림을 그대로 전달
    const stream = new ReadableStream({
      start(controller) {
        const reader = response.body?.getReader();
        if (!reader) {
          controller.close();
          return;
        }

        function pump(): Promise<void> {
          return reader.read().then(({ done, value }) => {
            if (done) {
              controller.close();
              return;
            }
            controller.enqueue(value);
            return pump();
          });
        }

        return pump();
      }
    });

    return new NextResponse(stream, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Cache-Control",
      },
    });
  } catch (error) {
    console.error("Job 이벤트 API 오류:", error);
    return new NextResponse("서버 오류가 발생했습니다", { status: 500 });
  }
}
