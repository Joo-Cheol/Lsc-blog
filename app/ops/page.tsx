"use client";
import { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { api } from "@/lib/api";
import { SchedulerRes } from "@/lib/types";
import { Loader2, Globe, History } from "lucide-react";

export default function Page() {
  const [status, setStatus] = useState<SchedulerRes | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onStatus() {
    setErr(null); setLoading(true);
    try { setStatus(await api<SchedulerRes>("/api/scheduler/status")); }
    catch(e:any){ setErr(e.message || String(e)); }
    finally { setLoading(false); }
  }

  const metricsUrl = `${process.env.NEXT_PUBLIC_LSC_API_BASE || ""}/metrics`;

  return (
    <div className="mx-auto max-w-3xl p-6 space-y-4">
      <Card>
        <CardHeader><CardTitle>운영 도구</CardTitle></CardHeader>
        <CardContent className="grid gap-4">
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={onStatus} disabled={loading}>
              {loading ? <Loader2 className="w-4 h-4 mr-1 animate-spin"/> : <History className="w-4 h-4 mr-1"/>}
              스케줄러 상태 확인
            </Button>
            <a href={metricsUrl} target="_blank" className="text-sm text-blue-600 hover:underline inline-flex items-center gap-1">
              <Globe className="w-4 h-4"/> /metrics 열기(보호 필요)
            </a>
          </div>
          {err && <div className="text-sm text-red-600">{err}</div>}

          {status && (
            <div className="text-sm grid gap-1">
              <div><b>Running:</b> {String(status.running)}</div>
              <div><b>Last:</b> added {status.last_result?.added ?? 0}, updated {status.last_result?.updated ?? 0}, failed {status.last_result?.failed ?? 0}</div>
              <Separator className="my-2"/>
              <div className="text-neutral-500 text-xs">* /metrics는 사설망/Ingress BasicAuth/방화벽으로 보호</div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}