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
  const [lastEventId, setLastEventId] = useState<number>(0);
  const [isConnected, setIsConnected] = useState(false);

  console.log("useJob 호출됨:", { jobId, job: job?.status, eventsCount: events.length });

  useEffect(() => {
    if (!jobId) return;
    let es: EventSource | undefined;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = (since: number = 0) => {
      // Next.js 프록시 대신 직접 백엔드에 연결
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const url = since > 0 
        ? `${baseUrl}/api/v1/jobs/${jobId}/events?since=${since}` 
        : `${baseUrl}/api/v1/jobs/${jobId}/events`;
      
      console.log("SSE 연결 시도:", url);
      es = new EventSource(url);
      setIsConnected(true);

      // 1) 즉시 스냅샷 (첫 연결시만)
      if (since === 0) {
        fetch(`${baseUrl}/api/v1/jobs/${jobId}`)
          .then((r) => r.json())
          .then((d) => {
            console.log("Job 스냅샷:", d);
            if (d.ok) setJob(d.job);
          })
          .catch((e) => console.error("Job 스냅샷 오류:", e));
      }

      es.addEventListener("snapshot", (e: any) => {
        try {
          if (!e.data || e.data === "undefined" || e.data.trim() === "") {
            console.warn("SSE snapshot event received with empty data:", e.data);
            return;
          }
          
          const d = JSON.parse(e.data);
          setJob(d.job);
        } catch (error) {
          console.error("Failed to parse SSE snapshot event:", e.data, error);
        }
      });

      es.addEventListener("ping", (e: any) => {
        // Heartbeat - 연결 유지 확인
        console.log("SSE heartbeat received");
      });

      ["progress", "info", "warning", "error", "done"].forEach((t) => {
        es!.addEventListener(t, (e: any) => {
          try {
            // e.data가 "undefined" 문자열이거나 빈 값인 경우 처리
            if (!e.data || e.data === "undefined" || e.data.trim() === "") {
              console.warn(`SSE event ${t} received with empty data:`, e.data);
              return;
            }
            
            const d = JSON.parse(e.data);
            setEvents((prev) => [...prev, { type: t, ...d }]);
            setLastEventId(d.event_id || 0);
            
            if (t === "done") {
              es?.close();
              setIsConnected(false);
            }
          } catch (error) {
            console.error(`Failed to parse SSE event ${t}:`, e.data, error);
          }
        });
      });

      es.onerror = () => {
        setIsConnected(false);
        es?.close();
        
        // 재연결 시도 (3초 후)
        reconnectTimeout = setTimeout(() => {
          if (job?.status === "running") {
            connect(lastEventId);
          }
        }, 3000);
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectTimeout);
      es?.close();
      setIsConnected(false);
    };
  }, [jobId, lastEventId]);

  return { job, events, isConnected };
}
