"use client";
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { SearchRes } from "@/lib/types";
import { ResultCard } from "@/components/result-card";
import { Loader2, Search } from "lucide-react";

export default function Page() {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("채권추심");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [hybrid, setHybrid] = useState(true);
  const [hits, setHits] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSearch() {
    setErr(null); setLoading(true);
    try {
      const payload:any = { query: q.trim() };
      if (cat) payload.cat = cat;
      if (dateFrom) payload.date_from = dateFrom;
      if (dateTo) payload.date_to = dateTo;
      if (hybrid) payload.hybrid = true;
      const res = await api<SearchRes>("/api/search", { method:"POST", body: JSON.stringify(payload) });
      setHits(res.hits || []);
    } catch(e:any) {
      setErr(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl p-6 space-y-4">
      <Card>
        <CardHeader><CardTitle>RAG 검색</CardTitle></CardHeader>
        <CardContent className="grid md:grid-cols-4 gap-4">
          <div className="md:col-span-3 grid gap-3">
            <div className="flex gap-2">
              <Input value={q} onChange={e=>setQ(e.target.value)} placeholder="예: 지급명령 핵심 절차"/>
              <Button onClick={onSearch} disabled={!q.trim() || loading}>
                {loading ? <Loader2 className="w-4 h-4 mr-1 animate-spin"/> : <Search className="w-4 h-4 mr-1"/>}
                검색
              </Button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div><Label>카테고리</Label><Input value={cat} onChange={e=>setCat(e.target.value)}/></div>
              <div><Label>시작일</Label><Input type="date" value={dateFrom} onChange={e=>setDateFrom(e.target.value)}/></div>
              <div><Label>종료일</Label><Input type="date" value={dateTo} onChange={e=>setDateTo(e.target.value)}/></div>
            </div>
          </div>
          <div className="md:col-span-1 flex items-center justify-between border rounded-lg p-3">
            <div>
              <div className="text-sm font-medium">하이브리드</div>
              <div className="text-xs text-neutral-500">BM25 + 벡터</div>
            </div>
            <Switch checked={hybrid} onCheckedChange={setHybrid}/>
          </div>
          {err && <div className="md:col-span-4 text-sm text-red-600">{err}</div>}
        </CardContent>
      </Card>

      {!!hits.length && (
        <Card>
          <CardHeader><CardTitle>검색 결과 ({hits.length})</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {hits.map((h, i)=> <ResultCard key={i} h={h}/>)}
          </CardContent>
        </Card>
      )}
    </div>
  );
}