"""CRUD for seen_sources — cross-run dedupe + per-source status tracking.

Status transitions: discovered → extracted | extract_failed
                                  → scored (after filter, with score)
"""
from kms import db
from kms.url_canonical import canonicalize


def insert_discovered(
    topic: str,
    url: str,
    title: str | None,
    source: str | None,
    run_id: int,
) -> bool:
    """Idempotent. Returns True if newly inserted, False if (topic, canonical) exists."""
    canon = canonicalize(url)
    if not canon:
        return False
    with db.connect() as c:
        cur = c.execute(
            "INSERT OR IGNORE INTO seen_sources "
            "(topic, url_canonical, url_original, title, source, first_seen_at, status, run_id) "
            "VALUES (?, ?, ?, ?, ?, ?, 'discovered', ?)",
            (topic, canon, url, title, source, db.now(), run_id),
        )
        return cur.rowcount > 0


def get_existing_canonicals(topic: str, urls: list[str]) -> set[str]:
    """Return the subset of canonical(url) already present for topic."""
    canons = [canonicalize(u) for u in urls if u]
    canons = [c for c in canons if c]
    if not canons:
        return set()
    placeholders = ",".join("?" * len(canons))
    with db.connect() as c:
        rows = c.execute(
            f"SELECT url_canonical FROM seen_sources "
            f"WHERE topic=? AND url_canonical IN ({placeholders})",
            (topic, *canons),
        ).fetchall()
    return {r["url_canonical"] for r in rows}


def filter_new(
    topic: str, candidates: list[dict]
) -> list[dict]:
    """Return only candidates whose canonical URL is not yet in seen_sources for topic."""
    if not candidates:
        return []
    existing = get_existing_canonicals(topic, [c.get("url", "") for c in candidates])
    out: list[dict] = []
    seen_in_batch: set[str] = set()
    for c in candidates:
        canon = canonicalize(c.get("url", ""))
        if not canon or canon in existing or canon in seen_in_batch:
            continue
        seen_in_batch.add(canon)
        out.append(c)
    return out


def mark_status(
    topic: str,
    url: str,
    status: str,
    score: int | None = None,
) -> None:
    canon = canonicalize(url)
    if not canon:
        return
    with db.connect() as c:
        if score is not None:
            c.execute(
                "UPDATE seen_sources SET status=?, score=? WHERE topic=? AND url_canonical=?",
                (status, score, topic, canon),
            )
        else:
            c.execute(
                "UPDATE seen_sources SET status=? WHERE topic=? AND url_canonical=?",
                (status, topic, canon),
            )


def attach_notion_page(topic: str, url: str, notion_page_id: str) -> None:
    canon = canonicalize(url)
    if not canon:
        return
    with db.connect() as c:
        c.execute(
            "UPDATE seen_sources SET notion_page_id=? WHERE topic=? AND url_canonical=?",
            (notion_page_id, topic, canon),
        )


def list_by_min_score(topic: str, min_score: int) -> list[dict]:
    """Return all rows for topic with score >= min_score, ordered by first_seen_at."""
    with db.connect() as c:
        rows = c.execute(
            "SELECT * FROM seen_sources "
            "WHERE topic=? AND score IS NOT NULL AND score >= ? "
            "ORDER BY first_seen_at",
            (topic, min_score),
        ).fetchall()
    return [dict(r) for r in rows]
