import { useState } from "react";
import { api } from "../lib/api";
import { usePolling } from "../lib/usePolling";
import type { RunSummary } from "../types";
import { RunCard } from "../components/RunCard";

export default function Dashboard() {
  const [topic, setTopic] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const active = usePolling(api.activeRun, 2000);
  const runs = usePolling(api.listRuns, 5000);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim() || submitting) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await api.startRun(topic.trim());
      setTopic("");
      active.refetch();
      runs.refetch();
    } catch (e) {
      setSubmitError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  const activeRun = active.data?.run ?? null;
  const allRuns: RunSummary[] = runs.data?.runs ?? [];
  const pastRuns = allRuns.filter((r) => r.id !== activeRun?.id);

  return (
    <div className="space-y-10">
      {activeRun ? (
        <section>
          <SectionTitle count={1}>지금 진행 중</SectionTitle>
          <RunCard run={activeRun} defaultExpanded pollMs={2000} />
          <p className="mt-3 text-xs text-subtle">
            현재 실행이 끝나면 다음 주제를 시작할 수 있어요.
          </p>
        </section>
      ) : (
        <section>
          <h1 className="text-4xl mb-2 leading-tight font-bold tracking-tight text-ink">
            오늘의 <span className="text-accent">주제</span>는?
          </h1>
          <p className="text-sm text-muted mb-5">
            주제어를 입력하면 키워드 추출부터 Notion 저장까지 6단계를 자동 실행합니다.
            같은 주제 재실행 시 신규 후보만 평가합니다.
          </p>
          <form onSubmit={submit} className="flex gap-2">
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder='예: "수습 평가", "people analytics"'
              disabled={submitting}
              className="flex-1 px-4 py-3 text-base bg-surface border border-border rounded-xl focus:outline-none focus:border-accent focus:ring-4 focus:ring-accent-soft transition disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!topic.trim() || submitting}
              className="px-6 py-3 text-sm font-semibold bg-accent text-white rounded-xl hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              {submitting ? "시작 중…" : "실행"}
            </button>
          </form>
          {submitError && (
            <div className="mt-3 text-sm text-danger">{submitError}</div>
          )}
        </section>
      )}

      <section>
        <SectionTitle count={pastRuns.length}>이력</SectionTitle>
        {pastRuns.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-2.5">
            {pastRuns.map((r) => (
              <RunCard key={r.id} run={r} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function SectionTitle({
  children,
  count,
}: {
  children: React.ReactNode;
  count?: number;
}) {
  return (
    <h2 className="mb-4 flex items-baseline gap-2">
      <span className="text-lg font-semibold text-ink">{children}</span>
      {typeof count === "number" && (
        <span className="text-xs font-mono tabular-nums text-subtle">
          {count}
        </span>
      )}
    </h2>
  );
}

function EmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-border-strong px-6 py-16 text-center">
      <div className="text-3xl mb-3 opacity-30 font-light">∅</div>
      <p className="text-sm text-muted">아직 실행 이력이 없습니다.</p>
    </div>
  );
}
