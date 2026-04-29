import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import type { ThresholdConfig } from "../types";

type Field = {
  key: keyof ThresholdConfig;
  label: string;
  hint: string;
};

const FIELDS: Field[] = [
  {
    key: "source_threshold",
    label: "Source 임계값",
    hint: "이 점수 이상이면 Notion Source 필드에 적재됩니다.",
  },
  {
    key: "draft_threshold",
    label: "Draft 임계값",
    hint: "이 점수 이상이면 초안 합성 후보로 누적됩니다. Source 임계값 이상이어야 합니다.",
  },
  {
    key: "draft_batch",
    label: "Draft 트리거 개수",
    hint: "마지막 갱신 이후 누적 초안 후보가 이 수에 도달하면 초안이 재생성됩니다.",
  },
];

export default function Settings() {
  const [original, setOriginal] = useState<ThresholdConfig | null>(null);
  const [draft, setDraft] = useState<ThresholdConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getConfig()
      .then((c) => {
        setOriginal(c);
        setDraft(c);
      })
      .catch((e) => setError((e as Error).message));
  }, []);

  const dirty = useMemo(() => {
    if (!original || !draft) return false;
    return FIELDS.some((f) => original[f.key] !== draft[f.key]);
  }, [original, draft]);

  const clientError = useMemo(() => {
    if (!draft) return null;
    for (const f of FIELDS) {
      const v = draft[f.key];
      if (!Number.isInteger(v)) return `${f.label}은(는) 정수여야 합니다.`;
    }
    if (draft.source_threshold < 1 || draft.source_threshold > 20)
      return "Source 임계값은 1~20 사이여야 합니다.";
    if (draft.draft_threshold < 1 || draft.draft_threshold > 20)
      return "Draft 임계값은 1~20 사이여야 합니다.";
    if (draft.source_threshold > draft.draft_threshold)
      return "Source 임계값은 Draft 임계값보다 크지 않아야 합니다.";
    if (draft.draft_batch < 1) return "Draft 트리거 개수는 1 이상이어야 합니다.";
    return null;
  }, [draft]);

  const update = (key: keyof ThresholdConfig, raw: string) => {
    if (!draft) return;
    const n = parseInt(raw, 10);
    setDraft({ ...draft, [key]: Number.isNaN(n) ? 0 : n });
  };

  const save = async () => {
    if (!draft || !dirty || saving || clientError) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.saveConfig(draft);
      setOriginal(updated);
      setDraft(updated);
      setSavedAt(new Date());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl mb-2 font-bold tracking-tight text-ink">
          설정
        </h1>
        <p className="text-sm text-muted">
          파이프라인 게이트 임계값. 점수 척도: relevance(1-10) +
          credibility(1-10) → 합산 2~20.
        </p>
      </div>

      {!draft || !original ? (
        <div className="text-sm text-subtle">불러오는 중…</div>
      ) : (
        <>
          <div className="space-y-4">
            {FIELDS.map((f) => (
              <div
                key={f.key}
                className="rounded-2xl border border-border bg-surface p-5"
              >
                <div className="flex items-center justify-between gap-6">
                  <div className="space-y-1">
                    <div className="text-sm font-semibold text-ink">
                      {f.label}
                    </div>
                    <div className="text-xs text-muted">{f.hint}</div>
                    <div className="text-[11px] font-mono text-subtle opacity-70">
                      {f.key}
                    </div>
                  </div>
                  <input
                    type="number"
                    inputMode="numeric"
                    value={draft[f.key]}
                    onChange={(e) => update(f.key, e.target.value)}
                    className="w-24 px-3 py-2 text-right text-sm rounded-xl border border-border bg-bg focus:outline-none focus:border-border-strong"
                    style={{ fontFamily: "var(--font-mono)" }}
                  />
                </div>
              </div>
            ))}
          </div>

          {clientError && (
            <div className="text-sm text-danger">{clientError}</div>
          )}

          <div className="flex items-center justify-between">
            <div className="text-xs text-subtle">
              {dirty ? (
                <span className="text-warning">● 저장되지 않음</span>
              ) : savedAt ? (
                <span>저장됨 · {savedAt.toLocaleTimeString()}</span>
              ) : (
                <span>저장 시 즉시 다음 실행에 반영</span>
              )}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => original && setDraft(original)}
                disabled={!dirty || saving}
                className="px-4 py-2 text-sm rounded-xl bg-bg border border-border text-muted hover:text-ink disabled:opacity-40 transition"
              >
                되돌리기
              </button>
              <button
                onClick={save}
                disabled={!dirty || saving || !!clientError}
                className="px-5 py-2 text-sm font-semibold rounded-xl bg-accent text-white hover:bg-accent-hover disabled:opacity-40 transition"
              >
                {saving ? "저장 중…" : "저장"}
              </button>
            </div>
          </div>

          {error && <div className="text-sm text-danger">{error}</div>}
        </>
      )}
    </div>
  );
}
