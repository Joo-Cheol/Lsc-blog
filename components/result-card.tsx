"use client";
import { Badge } from "@/components/ui/badge";
import { Globe } from "lucide-react";
import { SearchHit } from "@/lib/types";

export function ResultCard({ h }: { h: SearchHit }) {
  return (
    <div className="rounded-lg border p-3 bg-white">
      <div className="flex flex-wrap items-center gap-2 text-xs text-neutral-500">
        {typeof h.sim   !== "undefined" && <Badge variant="secondary">sim {h.sim?.toFixed?.(3)}</Badge>}
        {typeof h.bm25  !== "undefined" && <Badge variant="secondary">bm25 {h.bm25?.toFixed?.(3)}</Badge>}
        {typeof h.combo !== "undefined" && <Badge className="bg-indigo-600">combo {h.combo?.toFixed?.(3)}</Badge>}
        {h.date && <Badge variant="outline">{h.date}</Badge>}
        {h.cat  && <Badge variant="outline">{h.cat}</Badge>}
      </div>
      <div className="mt-1 font-medium line-clamp-1">{h.title || h.id}</div>
      {h.url && (
        <a href={h.url} target="_blank" className="text-xs text-blue-600 hover:underline inline-flex items-center gap-1">
          <Globe className="w-3 h-3"/> 원문 보기
        </a>
      )}
      {h.snippet && <p className="mt-2 text-sm text-neutral-700 line-clamp-3">{h.snippet}</p>}
    </div>
  );
}