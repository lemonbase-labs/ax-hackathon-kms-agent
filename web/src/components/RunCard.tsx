import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { RunDetail, RunSummary } from "../types";
import { Badge } from "./Badge";
import { PhaseStepper } from "./PhaseStepper";
import { PhaseDetail } from "./PhaseDetail";

interface Props {
  run: RunSummary;
  defaultExpanded?: boolean;
  pollMs?: number;
}

export function RunCard({ run, defaultExpanded, pollMs }: Props) {
  const [expanded, setExpanded] = useState(!!defaultExpanded);
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [selectedPhase, setSelectedPhase] = useState<number | null>(null);

  useEffect(() => {
    if (!expanded && run.status !== "running") return;
    let alive = true;
    const tick = async () => {
      try {
        const d = await api.getRun(run.id);
        if (alive) setDetail(d);
      } catch {
        // ignore
      }
    };
    tick();
    if (run.status === "running" && pollMs) {
      const id = setInterval(tick, pollMs);
      return () => {
        alive = false;
        clearInterval(id);
      };
    }
    return () => {
      alive = false;
    };
  }, [run.id, run.status, run.current_phase, expanded, pollMs]);

  const elapsed = elapsedString(run.started_at, run.finished_at);
  const phases = detail?.phases ?? [];
  const focusPhase =
    selectedPhase !== null
      ? phases.find((p) => p.phase_num === selectedPhase)
      : phases.find((p) => p.status === "running") ??
        phases[phases.length - 1];

  return (
    <article className="rounded-2xl bg-surface border border-border overflow-hidden">
      <header
        className="px-6 py-4 flex items-start gap-4 cursor-pointer hover:bg-bg/50 transition"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge status={run.status} />
            <span className="text-xs text-subtle font-mono">
              #{String(run.id).padStart(3, "0")}
            </span>
            <span className="text-xs text-subtle">{elapsed}</span>
          </div>
          <h3
            className="text-xl truncate"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {run.topic}
          </h3>
        </div>
        <div className="flex items-center gap-3">
          {run.notion_url && (
            <a
              href={run.notion_url}
              target="_blank"
              rel="noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-xs text-accent hover:underline"
            >
              Notion ↗
            </a>
          )}
          <span className="text-subtle text-sm">{expanded ? "▴" : "▾"}</span>
        </div>
      </header>

      <div className="px-6 pb-4">
        <PhaseStepper
          phases={phases}
          currentPhase={run.current_phase}
          runStatus={run.status}
          onSelect={(n) => {
            setExpanded(true);
            setSelectedPhase(n);
          }}
          selected={selectedPhase}
        />
      </div>

      {expanded && (
        <div className="px-6 pb-6 space-y-3">
          {run.error && (
            <div className="rounded-lg bg-danger-soft text-danger px-4 py-3 text-sm font-mono whitespace-pre-wrap">
              {run.error}
            </div>
          )}
          {focusPhase ? (
            <PhaseDetail phase={focusPhase} />
          ) : (
            <div className="text-sm text-subtle italic">phase 데이터 없음</div>
          )}
        </div>
      )}
    </article>
  );
}

function elapsedString(start: string, end: string | null): string {
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  const sec = Math.max(0, Math.round((e - s) / 1000));
  if (sec < 60) return `${sec}s`;
  const m = Math.floor(sec / 60);
  const r = sec % 60;
  return `${m}m ${r}s`;
}
