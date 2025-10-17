import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { task, options } = body;

    // 파이프라인 태스크별 처리
    let endpoint = "";
    let payload = {};

    switch (task) {
      case "preprocess_embed":
        // 전처리 + 임베딩을 순차 실행
        endpoint = "/api/v1/pipeline/preprocess-embed";
        payload = {
          chunk_size: options?.chunk_size || 1000,
          chunk_overlap: options?.chunk_overlap || 200,
          batch_size: options?.batch_size || 32
        };
        break;
      case "preprocess":
        endpoint = "/api/v1/index/preprocess";
        payload = {
          chunk_size: options?.chunk_size || 1000,
          chunk_overlap: options?.chunk_overlap || 200
        };
        break;
      case "embed":
        endpoint = "/api/v1/index/embed";
        payload = {
          batch_size: options?.batch_size || 32,
          model_name: options?.model_name || "jhgan/ko-sroberta-multitask"
        };
        break;
      default:
        return NextResponse.json(
          { success: false, error: `알 수 없는 태스크: ${task}` },
          { status: 400 }
        );
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { success: false, error: errorData.error || errorData.detail || "파이프라인 실행 실패" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json({
      success: true,
      task,
      result: data,
      message: getSuccessMessage(task, data)
    });
  } catch (error) {
    console.error("파이프라인 API 오류:", error);
    return NextResponse.json(
      { success: false, error: "서버 오류가 발생했습니다" },
      { status: 500 }
    );
  }
}

function getSuccessMessage(task: string, data: any): string {
  switch (task) {
    case "preprocess_embed":
      return "전처리 및 임베딩이 완료되었습니다. 이제 검색할 수 있어요!";
    case "preprocess":
      return `전처리가 완료되었습니다. ${data.chunks_created || 0}개 청크가 생성되었어요.`;
    case "embed":
      return `임베딩이 완료되었습니다. ${data.embeddings_added || 0}개 벡터가 저장되었어요.`;
    default:
      return "작업이 완료되었습니다.";
  }
}
