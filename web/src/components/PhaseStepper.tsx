import type { PhaseRecord, PhaseStatus } from "../types";
import { CONDITIONAL_PHASES, PHASE_LABELS, TOTAL_PHASES } from "../types";

type DerivedStatus = PhaseStatus | "skipped" | null;

interface Props {
  phases: PhaseRecord[];
  currentPhase: number | null;
  runStatus: "running" | "completed" | "failed";
  onSelect?: (n: number) => void;
  selected?: number | null;
  executedPhases?: number[];
}

function derivedStatus(
  n: number,
  currentPhase: number | null,
  runStatus: Props["runStatus"],
  phaseExists: boolean,
): DerivedStatus {
  if (runStatus === "completed") {
    // Conditional phases that never recorded a row → skipped, not completed.
    if (!phaseExists && CONDITIONAL_PHASES.has(n)) return "skipped";
    return "completed";
  }
  if (currentPhase == null) return null;
  if (n < currentPhase) {
    if (!phaseExists && CONDITIONAL_PHASES.has(n)) return "skipped";
    return "completed";
  }
  if (n === currentPhase) {
    return runStatus === "failed" ? "failed" : "running";
  }
  return null;
}

export function PhaseStepper({
  phases,
  currentPhase,
  runStatus,
  onSelect,
  selected,
  executedPhases,
}: Props) {
  const byNum = new Map(phases.map((p) => [p.phase_num, p]));
  const executed = new Set(executedPhases ?? []);

  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: TOTAL_PHASES }, (_, i) => i + 1).map((n) => {
        const p = byNum.get(n);
        const phaseExists = !!p || executed.has(n);
        const status: DerivedStatus =
          p?.status ?? derivedStatus(n, currentPhase, runStatus, phaseExists);
        const isCurrent = runStatus === "running" && status === "running";
        const isCompleted = status === "completed";
        const isFailed = status === "failed";
        const isSkipped = status === "skipped";
        const isPending = status == null;
        const isSelected = selected === n;
        const isClickable = !!p && !isPending;

        return (
          <button
            key={n}
            type="button"
            onClick={() => isClickable && onSelect?.(n)}
            disabled={!isClickable}
            className={[
              "group flex-1 min-w-0 text-left transition",
              onSelect && isClickable ? "cursor-pointer" : "cursor-default",
            ].join(" ")}
          >
            <div className="relative h-1 rounded-full overflow-hidden bg-border">
              <div
                className={[
                  "absolute inset-0 rounded-full transition-all",
                  isCompleted ? "bg-accent" : "",
                  isFailed ? "bg-danger" : "",
                  isCurrent ? "bg-accent shimmer-bar" : "",
                  isSkipped ? "bg-border" : "",
                ].join(" ")}
              />
            </div>
            <div className="mt-1.5 flex items-center gap-1">
              <span
                className={[
                  "text-[10px] font-mono tabular-nums",
                  isCompleted || isCurrent ? "text-muted" : "text-subtle",
                ].join(" ")}
              >
                {String(n).padStart(2, "0")}
              </span>
              <span
                className={[
                  "text-[11px] truncate transition",
                  isCurrent ? "text-ink font-semibold" : "",
                  isCompleted ? "text-muted" : "",
                  isPending ? "text-subtle" : "",
                  isFailed ? "text-danger font-medium" : "",
                  isSkipped ? "text-subtle line-through" : "",
                  isSelected ? "underline underline-offset-2" : "",
                ].join(" ")}
                title={isSkipped ? "조건 미충족으로 스킵됨" : undefined}
              >
                {PHASE_LABELS[n]}
              </span>
              {isCurrent && p?.sub_progress && (
                <span className="text-[10px] text-accent font-mono">
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
