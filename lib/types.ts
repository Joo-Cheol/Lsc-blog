export type SearchReq = { query: string; cat?: string; date_from?: string; date_to?: string; hybrid?: boolean };
export type SearchHit = { id: string; title?: string; url?: string; snippet?: string; date?: string; cat?: string; sim?: number; bm25?: number; combo?: number; };
export type SearchRes = { hits: SearchHit[]; meta?: { took_ms?: number; cached?: boolean } };

export type GenerateReq = { topic: string; keywords: string };
export type QC = { passed: boolean; length_ok?: boolean; h2_ok?: boolean; checklist_ok?: boolean; formal_ok?: boolean; forbidden_ok?: boolean; numeric_ok?: boolean };
export type GenerateRes = { text: string; provider: string; success: boolean; plag_score: number; top_sources: Array<{title?: string; url?: string; sim?: number; combo?: number; date?: string}>; qc: QC; };

export type SchedulerRes = { running: boolean; next_runs?: any[]; last_result?: {added?: number; updated?: number; failed?: number} };