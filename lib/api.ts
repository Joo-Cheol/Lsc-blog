export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string,string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string,string> || {}),
  };
  if (process.env.NEXT_PUBLIC_LSC_API_KEY) {
    headers["X-API-Key"] = process.env.NEXT_PUBLIC_LSC_API_KEY!;
  }
  
  // 프록시 모드: 같은 출처로 호출
  const base = process.env.NEXT_PUBLIC_LSC_API_BASE || "";
  const url = base ? `${base}${path}` : path;
  
  const res = await fetch(url, {
    ...init, headers, cache: "no-store",
  });
  if (!res.ok) {
    const msg = await res.text().catch(()=> res.statusText);
    throw new Error(`${res.status} ${res.statusText}: ${msg}`);
  }
  return res.json();
}