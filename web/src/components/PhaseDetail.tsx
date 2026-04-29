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
          totalCandidates={
            (payload.total_candidates ?? payload.total) as number
          }
          newCount={payload.new_count as number | undefined}
          list={payload.candidates as { title: string; url: string; source: string }[]}
        />
      );
    case 3:
      return (
        <Stat label="신규 후보 추출 성공/실패">
          {payload.extracted as number} / {payload.failed as number}
        </Stat>
      );
    case 4:
      return (
        <Scored
          items={
            (payload.scored ?? payload.selected) as {
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
          docCount={payload.doc_count as number | undefined}
          trigger={
            payload.trigger as
              | { delta?: number; draft_eligible_total?: number; last_drafted?: number }
              | undefined
          }
        />
      );
    case 6:
      return (
        <NotionLink
          pageUrl={payload.page_url as string}
          draftReplaced={payload.draft_replaced as boolean | undefined}
        />
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
  totalCandidates,
  newCount,
  list,
}: {
  rss: number;
  en: number;
  ko: number;
  totalCandidates: number;
  newCount?: number;
  list: { title: string; url: string; source: string }[];
}) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-4 text-xs text-muted font-mono">
        <span>RSS {rss}</span>
        <span>Serper(en) {en}</span>
        <span>Serper(ko) {ko}</span>
        <span className="text-ink">→ {totalCandidates}</span>
        {typeof newCount === "number" && (
          <span className="text-accent">신규 {newCount}</span>
        )}
      </div>
      {typeof newCount === "number" && newCount === 0 && (
        <p className="text-xs text-subtle italic">
          모두 이전 회차에서 본 URL — 다음 단계 SKIP
        </p>
      )}
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

// Score gates (mirrors kms/pipeline.py)
const SOURCE_THRESHOLD = 3;
const DRAFT_THRESHOLD = 4;

function Scored({
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
      {items?.map((s, i) => {
        const tier =
          s.score >= DRAFT_THRESHOLD
            ? "draft"
            : s.score >= SOURCE_THRESHOLD
              ? "source"
              : "below";
        return (
          <li
            key={i}
            className={[
              "rounded-lg border p-3",
              tier === "below"
                ? "bg-bg border-border opacity-60"
                : "bg-surface border-border",
            ].join(" ")}
          >
            <div className="flex items-center gap-2 mb-1">
              <span
                className={[
                  "font-mono text-xs px-2 py-0.5 rounded",
                  tier === "draft"
                    ? "bg-accent text-white"
                    : tier === "source"
                      ? "bg-accent-soft text-accent"
                      : "bg-border text-subtle",
                ].join(" ")}
                title={
                  tier === "draft"
                    ? `≥${DRAFT_THRESHOLD}: 초안 합성 대상`
                    : tier === "source"
                      ? `≥${SOURCE_THRESHOLD}: Notion Source 적재`
                      : `<${SOURCE_THRESHOLD}: 탈락`
                }
              >
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
        );
      })}
    </ul>
  );
}

function DraftPreview({
  chars,
  draft,
  docCount,
  trigger,
}: {
  chars: number;
  draft: string;
  docCount?: number;
  trigger?: { delta?: number; draft_eligible_total?: number; last_drafted?: number };
}) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-4 text-xs text-muted font-mono">
        <span>{chars} chars</span>
        {typeof docCount === "number" && <span>자료 {docCount}건</span>}
        {trigger && (
          <span className="text-accent">
            트리거 +{trigger.delta} (누적 {trigger.draft_eligible_total} / 마지막 갱신{" "}
            {trigger.last_drafted})
          </span>
        )}
      </div>
      <pre className="text-sm whitespace-pre-wrap font-sans bg-surface border border-border rounded-lg p-4 max-h-80 overflow-auto leading-relaxed">
        {draft}
      </pre>
    </div>
  );
}

function NotionLink({
  pageUrl,
  draftReplaced,
}: {
  pageUrl: string;
  draftReplaced?: boolean;
}) {
  return (
    <div className="space-y-2">
      <a
        href={pageUrl}
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center gap-2 text-accent hover:underline text-sm"
      >
        {pageUrl}
        <span aria-hidden>↗</span>
      </a>
      {typeof draftReplaced === "boolean" && (
        <div className="text-xs text-subtle">
          {draftReplaced
            ? "초안 본문 교체됨"
            : "Source/키워드만 누적 (초안 미갱신)"}
        </div>
      )}
    </div>
  );
}
