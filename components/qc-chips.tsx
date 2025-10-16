"use client";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, AlertTriangle } from "lucide-react";
import { QC } from "@/lib/types";

export function QCChips({ qc }: { qc?: QC }) {
  const items = [
    { k: "passed",      label: "QC" },
    { k: "length_ok",   label: "길이" },
    { k: "h2_ok",       label: "H2" },
    { k: "checklist_ok",label: "체크리스트" },
    { k: "formal_ok",   label: "격식형" },
    { k: "forbidden_ok",label: "금칙어" },
    { k: "numeric_ok",  label: "숫자" },
  ] as const;
  return (
    <div className="flex flex-wrap gap-1">
      {items.map(({k,label}) => {
        const ok = (qc as any)?.[k];
        const Icon = ok ? CheckCircle2 : AlertTriangle;
        return (
          <Badge key={k} className={ok ? "bg-emerald-600" : "bg-neutral-600"}>
            <Icon className="w-3 h-3 mr-1"/>{label}
          </Badge>
        );
      })}
    </div>
  );
}