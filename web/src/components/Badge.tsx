import type { RunStatus } from "../types";

const styles: Record<RunStatus | "pending", string> = {
  running: "bg-warning-soft text-warning",
  completed: "bg-success-soft text-success",
  failed: "bg-danger-soft text-danger",
  cancelled: "bg-bg text-muted",
  pending: "bg-bg text-subtle",
};

const labels: Record<RunStatus | "pending", string> = {
  running: "진행 중",
  completed: "완료",
  failed: "실패",
  cancelled: "취소됨",
  pending: "대기",
};

export function Badge({ status }: { status: RunStatus | "pending" }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${styles[status]}`}
    >
      {status === "running" && (
        <span className="w-1.5 h-1.5 rounded-full bg-warning pulse-dot" />
      )}
      {labels[status]}
    </span>
  );
}
