import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import type { Prompt } from "../types";

const PROMPT_LABELS: Record<string, string> = {
  keyword_extract: "1. 키워드 추출",
  filter: "2. 스코어링",
  curate: "3. 앵글 제안",
  draft: "4. 드래프트 생성",
};

export default function Prompts() {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [activeName, setActiveName] = useState<string | null>(null);
  const [draft, setDraft] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listPrompts()
      .then((d) => {
        setPrompts(d.prompts);
        if (d.prompts.length > 0) {
          setActiveName(d.prompts[0].name);
        }
      })
      .catch((e) => setError((e as Error).message));
  }, []);

  const active = useMemo(
    () => prompts.find((p) => p.name === activeName) ?? null,
    [prompts, activeName],
  );

  useEffect(() => {
    if (active) setDraft(active.content);
  }, [active]);

  const dirty = !!active && draft !== active.content;

  const save = async () => {
    if (!active || !dirty || saving) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.savePrompt(active.name, draft);
      setPrompts((ps) =>
        ps.map((p) => (p.name === updated.name ? updated : p)),
      );
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
        <h1
          className="text-4xl mb-2"
          style={{ fontFamily: "var(--font-display)" }}
        >
          프롬프트
        </h1>
        <p className="text-sm text-muted">
          저장 즉시 다음 실행부터 적용됩니다. 실행 중인 파이프라인엔 영향 없음.
        </p>
      </div>

      <div className="grid grid-cols-[220px_1fr] gap-6">
        <aside className="space-y-1">
          {prompts.map((p) => (
            <button
              key={p.name}
              onClick={() => setActiveName(p.name)}
              className={[
                "w-full text-left px-4 py-3 rounded-xl text-sm transition border",
                p.name === activeName
                  ? "bg-accent-soft border-accent text-accent font-semibold"
                  : "bg-surface border-border text-muted hover:text-ink hover:border-border-strong",
              ].join(" ")}
            >
              <div>{PROMPT_LABELS[p.name] ?? p.name}</div>
              <div className="text-[11px] mt-0.5 font-mono opacity-70">
                {p.name}.md
              </div>
            </button>
          ))}
        </aside>

        <div className="space-y-3">
          {active ? (
            <>
              <div className="rounded-2xl border border-border bg-surface overflow-hidden">
                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  spellCheck={false}
                  className="w-full p-5 text-sm leading-relaxed resize-none focus:outline-none bg-surface"
                  style={{ fontFamily: "var(--font-mono)", minHeight: 460 }}
                />
              </div>
              <div className="flex items-center justify-between">
                <div className="text-xs text-subtle">
                  {dirty ? (
                    <span className="text-warning">● 저장되지 않음</span>
                  ) : savedAt ? (
                    <span>저장됨 · {savedAt.toLocaleTimeString()}</span>
                  ) : (
                    <span>편집 시 즉시 다음 실행에 반영</span>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => active && setDraft(active.content)}
                    disabled={!dirty || saving}
                    className="px-4 py-2 text-sm rounded-xl bg-bg border border-border text-muted hover:text-ink disabled:opacity-40 transition"
                  >
                    되돌리기
                  </button>
                  <button
                    onClick={save}
                    disabled={!dirty || saving}
                    className="px-5 py-2 text-sm font-semibold rounded-xl bg-accent text-white hover:bg-accent-hover disabled:opacity-40 transition"
                  >
                    {saving ? "저장 중…" : "저장"}
                  </button>
                </div>
              </div>
              {error && <div className="text-sm text-danger">{error}</div>}
            </>
          ) : (
            <div className="text-sm text-subtle">프롬프트를 선택하세요.</div>
          )}
        </div>
      </div>
    </div>
  );
}
