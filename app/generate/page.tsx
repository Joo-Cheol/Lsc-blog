"use client";
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { api } from "@/lib/api";
import { GenerateRes } from "@/lib/types";
import { QCChips } from "@/components/qc-chips";
import { MarkdownView } from "@/components/markdown-view";
import { Loader2, Sparkles, Download, ClipboardList } from "lucide-react";

export default function Page() {
  const [topic, setTopic] = useState("채권추심 지급명령 절차");
  const [keywords, setKeywords] = useState("지급명령, 독촉, 집행권원, 소액사건");
  const [res, setRes] = useState<GenerateRes | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onGenerate() {
    setErr(null); setLoading(true); setRes(null);
    try {
      const out = await api<GenerateRes>("/api/generate", { method:"POST", body: JSON.stringify({ topic: topic.trim(), keywords: keywords.trim() }) });
      setRes(out);
    } catch(e:any) {
      setErr(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  function downloadMarkdown(text?: string) {
    if (!text) return;
    const blob = new Blob([text], { type:"text/markdown;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = `lsc_${Date.now()}.md`;
    document.body.appendChild(a); a.click(); a.remove();
  }

  return (
    <div className="mx-auto max-w-5xl p-6 space-y-4">
      <Card>
        <CardHeader><CardTitle>블로그 글 생성</CardTitle></CardHeader>
        <CardContent className="grid md:grid-cols-3 gap-4">
          <div className="md:col-span-2 grid gap-3">
            <div><Label>주제</Label><Input value={topic} onChange={e=>setTopic(e.target.value)}/></div>
            <div><Label>키워드</Label><Input value={keywords} onChange={e=>setKeywords(e.target.value)} placeholder="쉼표로 구분"/></div>
            <div className="flex gap-2">
              <Button onClick={onGenerate} disabled={!topic.trim() || loading}>
                {loading ? <Loader2 className="w-4 h-4 mr-1 animate-spin"/> : <Sparkles className="w-4 h-4 mr-1"/>}
                생성하기
              </Button>
              {res?.text && (
                <Button variant="outline" onClick={() => downloadMarkdown(res.text)}>
                  <Download className="w-4 h-4 mr-1"/> Markdown 저장
                </Button>
              )}
            </div>
            {err && <div className="text-sm text-red-600">{err}</div>}
          </div>
          <div className="md:col-span-1 rounded-lg border p-3 bg-neutral-50 text-xs text-neutral-600">
            <div className="font-medium mb-1">가이드</div>
            <ul className="list-disc pl-4 space-y-1">
              <li>길이 1600–1900자, H2≥3, 체크리스트≥5</li>
              <li>격식형 80%+, 금칙어 0회</li>
              <li>표절 ≤ 0.18, 사실은 RAG 근거</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {res && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <ClipboardList className="w-4 h-4"/> 품질 메타
              </CardTitle>
              <QCChips qc={res.qc}/>
            </div>
          </CardHeader>
          <CardContent className="grid md:grid-cols-3 gap-6">
            <div className="md:col-span-2">
              <MarkdownView text={res.text}/>
            </div>
            <div className="md:col-span-1">
              <div className="text-sm grid gap-1">
                <div className="text-neutral-500 text-xs">Provider</div>
                <div className="font-medium">{res.provider}</div>
                <Separator className="my-2"/>
                <div className="text-neutral-500 text-xs">Top Sources</div>
                <div className="grid gap-2">
                  {(res.top_sources || []).map((s, i) => (
                    <div key={i} className="rounded border p-2">
                      <div className="text-xs font-medium line-clamp-1">{s.title || s.url || s.date || "-"}</div>
                      <div className="text-[11px] text-neutral-500 flex flex-wrap gap-2">
                        {typeof s.sim   !== "undefined" && <span>sim {s.sim?.toFixed?.(3)}</span>}
                        {typeof s.combo !== "undefined" && <span>combo {s.combo?.toFixed?.(3)}</span>}
                        {s.date && <span>{s.date}</span>}
                      </div>
                      {s.url && <a href={s.url} target="_blank" className="text-[11px] text-blue-600 hover:underline">원문</a>}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}