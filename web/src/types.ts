export type RunStatus = "running" | "completed" | "failed" | "cancelled";
export type PhaseStatus = "running" | "completed" | "failed";

export interface RunSummary {
  id: number;
  topic: string;
  status: RunStatus;
  current_phase: number | null;
  notion_url: string | null;
  error: string | null;
  started_at: string;
  finished_at: string | null;
  executed_phases: number[];
}

export interface PhaseRecord {
  id: number;
  run_id: number;
  phase_num: number;
  phase_name: string;
  status: PhaseStatus;
  sub_progress: string | null;
  payload: Record<string, unknown> | null;
  payload_json: string | null;
  started_at: string;
  finished_at: string | null;
}

export interface RunDetail extends RunSummary {
  phases: PhaseRecord[];
}

export interface Prompt {
  name: string;
  content: string;
}

export interface ThresholdConfig {
  source_threshold: number;
  draft_threshold: number;
  draft_batch: number;
}

export const PHASE_LABELS: Record<number, string> = {
  1: "키워드 추출",
  2: "후보 수집",
  3: "본문 추출",
  4: "스코어링",
  5: "드래프트 생성",
  6: "Notion 저장",
};

// Phase 5 only runs when draft trigger fires (누적 score≥4 신규 ≥3개).
export const CONDITIONAL_PHASES = new Set([5]);

export const TOTAL_PHASES = 6;
