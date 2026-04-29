"""Phase tracker context manager — wraps a phase, records start/finish/payload."""
from contextlib import contextmanager

from kms import db


class PhaseHandle:
    def __init__(self, phase_id: int):
        self.phase_id = phase_id
        self._payload: dict | None = None

    def progress(self, text: str) -> None:
        db.update_sub_progress(self.phase_id, text)

    def payload(self, data: dict) -> None:
        self._payload = data


class RunTracker:
    def __init__(self, run_id: int):
        self.run_id = run_id

    @contextmanager
    def phase(self, num: int, name: str):
        phase_id = db.start_phase(self.run_id, num, name)
        handle = PhaseHandle(phase_id)
        try:
            yield handle
        except Exception as e:
            db.finish_phase(phase_id, "failed", {"error": str(e)})
            raise
        else:
            db.finish_phase(phase_id, "completed", handle._payload)

    def finish(self, notion_url: str | None = None, error: str | None = None) -> None:
        status = "failed" if error else "completed"
        db.finish_run(self.run_id, status, notion_url=notion_url, error=error)


def start(topic: str) -> RunTracker:
    return RunTracker(db.start_run(topic))
