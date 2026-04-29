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
  onDelete?: (id: number) => void;
}

export function RunCard({ run, defaultExpanded, pollMs, onDelete }: Props) {
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

  const isRunning = run.status === "running";

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!onDelete) return;
    if (!confirm(`"${run.topic}" 이력을 삭제할까요?`)) return;
    try {
      await api.deleteRun(run.id);
      onDelete(run.id);
    } catch (err) {
      alert(`삭제 실패: ${(err as Error).message}`);
    }
  };

  return (
    <article
      className={[
        "rounded-2xl bg-surface border overflow-hidden transition",
        isRunning
          ? "border-accent/30 shadow-[0_1px_2px_rgba(91,108,255,0.08),0_8px_24px_-12px_rgba(91,108,255,0.25)]"
          : "border-border shadow-[0_1px_2px_rgba(26,27,38,0.04)]",
      ].join(" ")}
    >
      <header
        className="px-5 py-3.5 flex items-center gap-3 cursor-pointer hover:bg-bg/40 transition"
        onClick={() => setExpanded((v) => !v)}
      >
        <Badge status={run.status} />
        <h3 className="flex-1 min-w-0 text-base font-semibold truncate text-ink">
          {run.topic}
        </h3>
        <span className="text-[11px] text-subtle font-mono tabular-nums">
          #{String(run.id).padStart(3, "0")}
        </span>
        <span className="text-[11px] text-subtle tabular-nums">{elapsed}</span>
        {run.notion_url && (
          <a
            href={run.notion_url}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="text-[11px] text-accent hover:underline whitespace-nowrap"
          >
            Notion ↗
          </a>
        )}
        {!isRunning && onDelete && (
          <button
            type="button"
            onClick={handleDelete}
            aria-label="이력 삭제"
            title="이력 삭제"
            className="text-subtle hover:text-danger p-1 -m-1 rounded transition"
          >
            <svg
              aria-hidden
              viewBox="0 0 20 20"
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M4 6h12M8 6V4h4v2m-6 0v10a1 1 0 001 1h6a1 1 0 001-1V6" />
            </svg>
          </button>
        )}
        <svg
          aria-hidden
          viewBox="0 0 20 20"
          className={[
            "w-4 h-4 text-subtle shrink-0 transition-transform",
            expanded ? "rotate-180" : "",
          ].join(" ")}
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M5 7.5l5 5 5-5" />
        </svg>
      </header>

      <div className="px-5 pb-3">
        <PhaseStepper
          phases={phases}
          currentPhase={run.current_phase}
          runStatus={run.status}
          executedPhases={run.executed_phases}
          onSelect={(n) => {
            setExpanded(true);
            setSelectedPhase(n);
          }}
          selected={selectedPhase}
        />
      </div>

      {expanded && (
        <div className="px-5 pb-5 pt-1 space-y-3">
          {run.error && (
            <div className="rounded-lg bg-danger-soft text-danger px-4 py-3 text-sm font-mono whitespace-pre-wrap">
              {run.error}
            </div>
          )}
          {focusPhase ? (
            <PhaseDetail
              phase={focusPhase}
              runId={run.id}
              runStatus={run.status}
            />
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
