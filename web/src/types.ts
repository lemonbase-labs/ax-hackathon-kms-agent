export type RunStatus = "running" | "completed" | "failed";
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

export const PHASE_LABELS: Record<number, string> = {
  1: "키워드 추출",
  2: "후보 수집",
  3: "본문 추출",
  4: "스코어링",
  5: "앵글 제안",
  6: "드래프트 생성",
  7: "Notion 저장",
};

export const TOTAL_PHASES = 7;
