import type { Prompt, RunDetail, RunSummary, ThresholdConfig } from "../types";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    throw new Error(`${r.status} ${text || r.statusText}`);
  }
  return r.json();
}

export const api = {
  listRuns: () => req<{ runs: RunSummary[] }>("/api/runs?limit=30"),
  activeRun: () => req<{ run: RunSummary | null }>("/api/runs/active"),
  getRun: (id: number) => req<RunDetail>(`/api/runs/${id}`),
  startRun: (topic: string, top_k = 5) =>
    req<{ status: string }>("/api/runs", {
      method: "POST",
      body: JSON.stringify({ topic, top_k }),
    }),
  deleteRun: (id: number) =>
    req<{ status: string }>(`/api/runs/${id}`, { method: "DELETE" }),
  cancelRun: (id: number) =>
    req<{ status: string; run_id: number }>(`/api/runs/${id}/cancel`, {
      method: "POST",
    }),
  listPrompts: () => req<{ prompts: Prompt[] }>("/api/prompts"),
  savePrompt: (name: string, content: string) =>
    req<Prompt>(`/api/prompts/${name}`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    }),
  rerunStep: (runId: number, step: string) =>
    req<{ step: string; phase_num: number; output: Record<string, unknown> }>(
      `/api/runs/${runId}/steps/${step}/rerun`,
      { method: "POST" },
    ),
  getFeeds: () => req<{ content: string }>("/api/feeds"),
  saveFeeds: (content: string) =>
    req<{ content: string }>("/api/feeds", {
      method: "PUT",
      body: JSON.stringify({ content }),
    }),
  getConfig: () => req<ThresholdConfig>("/api/config"),
  saveConfig: (cfg: ThresholdConfig) =>
    req<ThresholdConfig>("/api/config", {
      method: "PUT",
      body: JSON.stringify(cfg),
    }),
};
