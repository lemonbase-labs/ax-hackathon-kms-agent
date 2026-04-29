import { useEffect, useState } from "react";
import { api } from "../lib/api";

export default function Feeds() {
  const [original, setOriginal] = useState<string | null>(null);
  const [draft, setDraft] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getFeeds()
      .then((d) => {
        setOriginal(d.content);
        setDraft(d.content);
      })
      .catch((e) => setError((e as Error).message));
  }, []);

  const dirty = original !== null && draft !== original;

  const save = async () => {
    if (!dirty || saving) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.saveFeeds(draft);
      setOriginal(updated.content);
      setDraft(updated.content);
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
          피드
        </h1>
        <p className="text-sm text-muted">
          RSS 화이트리스트.{" "}
          <code className="text-[12px] font-mono">{"<name> <url>"}</code> 한
          줄씩. <code className="font-mono">#</code>로 시작하는 줄은 비활성화.
          저장 즉시 다음 실행부터 적용.
        </p>
      </div>

      <div className="space-y-3">
        {original === null ? (
          <div className="text-sm text-subtle">불러오는 중…</div>
        ) : (
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
                  onClick={() => original !== null && setDraft(original)}
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
        )}
      </div>
    </div>
  );
}
