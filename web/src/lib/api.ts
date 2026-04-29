import type { Prompt, RunDetail, RunSummary } from "../types";

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
  listPrompts: () => req<{ prompts: Prompt[] }>("/api/prompts"),
  savePrompt: (name: string, content: string) =>
    req<Prompt>(`/api/prompts/${name}`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    }),
};
