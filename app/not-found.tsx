export default function NotFound() {
  return (
    <main className="min-h-[60vh] grid place-items-center p-8 text-center">
      <div>
        <h2 className="text-2xl font-bold mb-2">페이지를 찾을 수 없어요 (404)</h2>
        <p className="text-sm text-neutral-600 mb-4">
          상단의 <b>검색/생성/운영</b> 메뉴로 이동해 주세요.
          <br/>API 주소(<code>/api/*</code>)는 브라우저에서 직접 여는 경로가 아닙니다.
        </p>
        <div className="space-y-2">
          <a href="/" className="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            검색 페이지로 이동
          </a>
          <br/>
          <a href="/generate" className="inline-block bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
            생성 페이지로 이동
          </a>
        </div>
      </div>
    </main>
  );
}




