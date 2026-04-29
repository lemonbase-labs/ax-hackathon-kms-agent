import type { PhaseRecord } from "../types";
import { PHASE_LABELS, TOTAL_PHASES } from "../types";

interface Props {
  phases: PhaseRecord[];
  currentPhase: number | null;
  runStatus: "running" | "completed" | "failed";
  onSelect?: (n: number) => void;
  selected?: number | null;
}

export function PhaseStepper({
  phases,
  currentPhase,
  runStatus,
  onSelect,
  selected,
}: Props) {
  const byNum = new Map(phases.map((p) => [p.phase_num, p]));

  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: TOTAL_PHASES }, (_, i) => i + 1).map((n) => {
        const p = byNum.get(n);
        const isCurrent = runStatus === "running" && currentPhase === n;
        const isCompleted = p?.status === "completed";
        const isFailed = p?.status === "failed";
        const isPending = !p;
        const isSelected = selected === n;

        return (
          <button
            key={n}
            type="button"
            onClick={() => onSelect?.(n)}
            disabled={isPending}
            className={[
              "group flex-1 min-w-0 text-left transition",
              onSelect && !isPending ? "cursor-pointer" : "cursor-default",
            ].join(" ")}
          >
            <div className="relative h-1.5 rounded-full overflow-hidden bg-border">
              <div
                className={[
                  "absolute inset-0 rounded-full transition-all",
                  isCompleted ? "bg-accent" : "",
                  isFailed ? "bg-danger" : "",
                  isCurrent ? "bg-accent shimmer-bar" : "",
                ].join(" ")}
              />
            </div>
            <div className="mt-2 flex items-center gap-1.5">
              <span
                className={[
                  "text-[11px] font-mono tabular-nums",
                  isCompleted || isCurrent ? "text-ink" : "text-subtle",
                ].join(" ")}
              >
                {String(n).padStart(2, "0")}
              </span>
              <span
                className={[
                  "text-xs truncate transition",
                  isCurrent ? "text-ink font-semibold" : "",
                  isCompleted ? "text-muted" : "",
                  isPending ? "text-subtle" : "",
                  isFailed ? "text-danger font-medium" : "",
                  isSelected ? "underline underline-offset-2" : "",
                ].join(" ")}
              >
                {PHASE_LABELS[n]}
              </span>
              {isCurrent && p?.sub_progress && (
                <span className="text-[11px] text-accent font-mono">
                  {p.sub_progress}
                </span>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}
