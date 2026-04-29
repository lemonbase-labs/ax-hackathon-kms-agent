import { useState } from "react";
import { api } from "../lib/api";
import type { PhaseRecord } from "../types";

const RERUN_STEP_BY_PHASE: Record<number, string> = {
  1: "keyword_extract",
  4: "filter",
  5: "draft",
};

export function PhaseDetail({
  phase,
  runId,
  runStatus,
}: {
  phase: PhaseRecord;
  runId: number;
  runStatus: string;
}) {
  const p = phase.payload ?? {};
  const step = RERUN_STEP_BY_PHASE[phase.phase_num];
  const canRerun =
    !!step && phase.status === "completed" && runStatus !== "running";

  const [rerunOutput, setRerunOutput] = useState<Record<string, unknown> | null>(
    null,
  );
  const [rerunning, setRerunning] = useState(false);
  const [rerunError, setRerunError] = useState<string | null>(null);

  const doRerun = async () => {
    if (!step || rerunning) return;
    setRerunning(true);
    setRerunError(null);
    try {
      const res = await api.rerunStep(runId, step);
      setRerunOutput(res.output);
    } catch (e) {
      setRerunError((e as Error).message);
    } finally {
      setRerunning(false);
    }
  };

  return (
    <div className="rounded-xl bg-bg border border-border p-5 space-y-3">
      <div className="flex items-center justify-between text-xs text-muted">
        <span className="font-mono">
          phase {String(phase.phase_num).padStart(2, "0")} · {phase.phase_name}
        </span>
        <span>
          {phase.status} {phase.sub_progress ? `· ${phase.sub_progress}` : ""}
        </span>
      </div>
      <PayloadView phaseNum={phase.phase_num} payload={p} status={phase.status} />

      {canRerun && (
        <div className="pt-3 border-t border-border space-y-3">
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs text-subtle">
              {step}.md를 수정한 뒤 같은 입력으로 이 단계만 재실행 (원본 무변경)
            </span>
            <button
              onClick={doRerun}
              disabled={rerunning}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-accent-soft text-accent hover:bg-accent hover:text-white disabled:opacity-40 transition"
            >
              {rerunning ? "실행 중…" : "↻ 현재 프롬프트로 재실행"}
            </button>
          </div>
          {rerunError && (
            <div className="text-xs text-danger font-mono whitespace-pre-wrap">
              {rerunError}
            </div>
          )}
          {rerunOutput && (
            <div className="rounded-lg bg-surface border border-accent/30 p-4 space-y-2">
              <div className="text-[11px] font-mono text-accent">
                현재 프롬프트 결과 · 휘발 (새로고침 시 사라짐)
              </div>
              <PayloadView
                phaseNum={phase.phase_num}
                payload={rerunOutput}
                status="completed"
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function PayloadView({
  phaseNum,
  payload,
  status,
}: {
  phaseNum: number;
  payload: Record<string, unknown>;
  status: string;
}) {
  if (status === "running" && Object.keys(payload).length === 0) {
    return <div className="text-sm text-subtle italic">처리 중…</div>;
  }
  if (status === "failed") {
    return (
      <div className="text-sm text-danger font-mono whitespace-pre-wrap">
        {String(payload.error ?? "failed")}
      </div>
    );
  }

  switch (phaseNum) {
    case 1:
      return <Keywords en={payload.en as string[]} ko={payload.ko as string[]} />;
    case 2:
      return (
        <Candidates
          rss={payload.rss_count as number}
          en={payload.serper_en_count as number}
          ko={payload.serper_ko_count as number}
          total={payload.total as number}
          list={payload.candidates as { title: string; url: string; source: string }[]}
        />
      );
    case 3:
      return (
        <Stat label="추출 성공/실패">
          {payload.extracted as number} / {payload.failed as number}
        </Stat>
      );
    case 4:
      return (
        <Selected
          items={
            payload.selected as {
              url: string;
              title: string;
              score: number;
              score_detail?: { reason?: string };
            }[]
          }
        />
      );
    case 5:
      return (
        <DraftPreview
          chars={payload.chars as number}
          draft={payload.draft as string}
        />
      );
    case 6:
      return (
        <a
          href={payload.page_url as string}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 text-accent hover:underline text-sm"
        >
          {payload.page_url as string}
          <span aria-hidden>↗</span>
        </a>
      );
    default:
      return null;
  }
}

function Keywords({ en, ko }: { en: string[]; ko: string[] }) {
  return (
    <div className="space-y-2">
      <KwRow label="EN" items={en} />
      <KwRow label="KO" items={ko} />
    </div>
  );
}

function KwRow({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="flex items-baseline gap-3">
      <span className="text-xs font-mono text-subtle w-6">{label}</span>
      <div className="flex flex-wrap gap-1.5">
        {items?.map((k) => (
          <span
            key={k}
            className="px-2 py-0.5 rounded-md bg-accent-soft text-accent text-xs"
          >
            {k}
          </span>
        ))}
      </div>
    </div>
  );
}

function Candidates({
  rss,
  en,
  ko,
  total,
  list,
}: {
  rss: number;
  en: number;
  ko: number;
  total: number;
  list: { title: string; url: string; source: string }[];
}) {
  return (
    <div className="space-y-3">
      <div className="flex gap-4 text-xs text-muted font-mono">
        <span>RSS {rss}</span>
        <span>Serper(en) {en}</span>
        <span>Serper(ko) {ko}</span>
        <span className="text-ink">→ {total}</span>
      </div>
      <ul className="space-y-1 max-h-48 overflow-auto pr-1">
        {list?.slice(0, 30).map((c, i) => (
          <li key={i} className="text-sm flex gap-2 items-baseline">
            <span className="text-[10px] font-mono text-subtle w-12 shrink-0">
              {c.source}
            </span>
            <a
              href={c.url}
              target="_blank"
              rel="noreferrer"
              className="text-ink hover:text-accent truncate"
            >
              {c.title || c.url}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline gap-3">
      <span className="text-xs text-subtle">{label}</span>
      <span className="font-mono text-ink">{children}</span>
    </div>
  );
}

function Selected({
  items,
}: {
  items: {
    url: string;
    title: string;
    score: number;
    score_detail?: { reason?: string };
  }[];
}) {
  return (
    <ul className="space-y-2">
      {items?.map((s, i) => (
        <li key={i} className="rounded-lg bg-surface border border-border p-3">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-accent-soft text-accent">
              {s.score}
            </span>
            <a
              href={s.url}
              target="_blank"
              rel="noreferrer"
              className="text-sm text-ink hover:text-accent truncate"
            >
              {s.title || s.url}
            </a>
          </div>
          {s.score_detail?.reason && (
            <p className="text-xs text-muted ml-1">{s.score_detail.reason}</p>
          )}
        </li>
      ))}
    </ul>
  );
}

function DraftPreview({ chars, draft }: { chars: number; draft: string }) {
  return (
    <div className="space-y-2">
      <div className="text-xs text-muted font-mono">{chars} chars</div>
      <pre className="text-sm whitespace-pre-wrap font-sans bg-surface border border-border rounded-lg p-4 max-h-80 overflow-auto leading-relaxed">
        {draft}
      </pre>
    </div>
  );
}
