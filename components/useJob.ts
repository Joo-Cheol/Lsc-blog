import { useEffect, useState } from "react";

export type Job = {
  id: string;
  status: "queued" | "running" | "succeeded" | "failed";
  progress: number;
  counters: Record<string, number>;
  results?: {
    posts?: { title: string; url: string; logno?: string }[];
    chunks_created?: number;
    embeddings_added?: number;
    cache_hit_rate?: number;
    collection_name?: string;
    total_items?: number;
    [k: string]: any;
  };
  errors?: string[];
  events?: Array<{
    ts: string;
    type: string;
    message: string;
    data: Record<string, any>;
  }>;
};

export function useJob(jobId?: string) {
  const [job, setJob] = useState<Job | undefined>();
  const [events, setEvents] = useState<any[]>([]);

  useEffect(() => {
    if (!jobId) return;
    let es: EventSource | undefined;

    // 1) 즉시 스냅샷
    fetch(`/api/jobs/${jobId}`)
      .then((r) => r.json())
      .then((d) => d.ok && setJob(d.job));

    // 2) SSE
    es = new EventSource(`/api/jobs/${jobId}/events`);
    es.onmessage = () => {}; // not used
    es.addEventListener("snapshot", (e: any) => {
      const d = JSON.parse(e.data);
      setJob(d.job);
    });
    ["progress", "info", "warning", "error", "done"].forEach((t) => {
      es!.addEventListener(t, (e: any) => {
        const d = JSON.parse(e.data);
        setEvents((prev) => [...prev, { type: t, ...d }]);
        if (t === "done") es?.close();
      });
    });
    es.onerror = () => es?.close();
    return () => es?.close();
  }, [jobId]);

  return { job, events };
}
