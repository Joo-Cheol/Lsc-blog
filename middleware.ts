import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(req: NextRequest) {
  const url = req.nextUrl;
  const isApi = url.pathname.startsWith("/api/");
  const isBrowserGet = req.method === "GET" && !req.headers.get("x-requested-with");

  // 브라우저가 주소창에 직접 /api/* 입력한 경우만 리다이렉트
  if (isApi && isBrowserGet) {
    url.pathname = "/";
    url.search = "";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
}




