"use client";
import { useEffect, useState } from "react";

export default function HealthBadge() {
  const [ok, setOk] = useState<boolean | null>(null);

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_LSC_API_BASE || "";
    // 프록시 모드면 같은 출처로 호출
    const url = base ? `${base}/health/ready` : `/api/health/ready`;
    fetch(url, { cache: "no-store" })
      .then(r => setOk(r.ok))
      .catch(() => setOk(false));
  }, []);

  const cls = ok === null ? "bg-gray-400" : ok ? "bg-emerald-600" : "bg-red-600";
  const text = ok === null ? "CHECK" : ok ? "API OK" : "API DOWN";
  return <span className={`text-white text-xs px-2 py-1 rounded ${cls}`}>{text}</span>;
}




