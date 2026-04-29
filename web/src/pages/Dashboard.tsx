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
      <section>
        <h1
          className="text-5xl mb-3 leading-tight"
          style={{ fontFamily: "var(--font-display)" }}
        >
          오늘의 <em className="text-accent not-italic">주제</em>는?
        </h1>
        <p className="text-muted mb-6">
          주제어를 입력하면 키워드 추출부터 Notion 저장까지 7단계를 자동 실행합니다.
        </p>
        <form onSubmit={submit} className="flex gap-2">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder='예: "수습 평가", "people analytics"'
            disabled={submitting || !!activeRun}
            className="flex-1 px-5 py-4 text-lg bg-surface border border-border rounded-2xl focus:outline-none focus:border-accent focus:ring-4 focus:ring-accent-soft transition disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!topic.trim() || submitting || !!activeRun}
            className="px-8 py-4 text-base font-semibold bg-accent text-white rounded-2xl hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed transition"
          >
            {submitting ? "시작 중…" : activeRun ? "다른 실행 진행 중" : "실행"}
          </button>
        </form>
        {submitError && (
          <div className="mt-3 text-sm text-danger">{submitError}</div>
        )}
      </section>

      {activeRun && (
        <section>
          <SectionTitle>지금 진행 중</SectionTitle>
          <RunCard run={activeRun} defaultExpanded pollMs={2000} />
        </section>
      )}

      <section>
        <SectionTitle>이력</SectionTitle>
        {pastRuns.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-3">
            {pastRuns.map((r) => (
              <RunCard key={r.id} run={r} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-xs uppercase tracking-[0.2em] text-subtle mb-4">
      {children}
    </h2>
  );
}

function EmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-border-strong px-6 py-16 text-center">
      <div
        className="text-4xl mb-3 opacity-30"
        style={{ fontFamily: "var(--font-display)" }}
      >
        ∅
      </div>
      <p className="text-sm text-muted">아직 실행 이력이 없습니다.</p>
    </div>
  );
}
