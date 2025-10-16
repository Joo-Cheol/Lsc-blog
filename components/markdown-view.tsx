"use client";
import { Separator } from "@/components/ui/separator";

export function MarkdownView({ text }: { text?: string }) {
  const lines = (text || "").split(/\n+/);
  return (
    <div className="prose prose-neutral max-w-none">
      {lines.map((ln, i) => {
        if (ln.startsWith("# "))  return <h1 key={i} className="text-2xl font-bold mt-2">{ln.replace(/^#\s+/,"")}</h1>;
        if (ln.startsWith("## ")) return <h2 key={i} className="text-xl font-semibold mt-4">{ln.replace(/^##\s+/,"")}</h2>;
        if (/^\s*[-*]\s+/.test(ln)) return <li key={i} className="ml-4 list-disc">{ln.replace(/^\s*[-*]\s+/,"")}</li>;
        if (/^\d+\.\s+/.test(ln))  return <li key={i} className="ml-4 list-decimal">{ln.replace(/^\d+\.\s+/,"")}</li>;
        if (!ln.trim()) return <Separator key={i} className="my-2"/>;
        return <p key={i} className="leading-relaxed">{ln}</p>;
      })}
    </div>
  );
}