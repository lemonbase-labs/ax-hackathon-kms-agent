"""FastAPI server for the KMS dashboard. Local-only (127.0.0.1)."""
import sys
import threading
import traceback
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from kms import _config, _feeds, _prompts, db
from kms.draft import synthesize
from kms.filter import score_and_select
from kms.keyword_extract import extract_keywords
from kms.pipeline import run_pipeline
from kms.slack import notify_draft

# step name → (loader, runner returning a phase-payload-shaped dict)
STEP_PHASE_NUM = {"keyword_extract": 1, "filter": 4, "draft": 5}

load_dotenv()

app = FastAPI(title="KMS Dashboard")

# Vite dev server (localhost:5173) needs CORS during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_run_lock = threading.Lock()


class RunRequest(BaseModel):
    topic: str
    top_k: int = 5


class PromptUpdate(BaseModel):
    content: str


class FeedsUpdate(BaseModel):
    content: str


class ConfigUpdate(BaseModel):
    source_threshold: int
    draft_threshold: int
    draft_batch: int


def _execute(topic: str, top_k: int) -> None:
    try:
        result = run_pipeline(topic, top_k=top_k)
        action = result.get("notion_action")
        if action:
            notify_draft(topic, action, result["notion_url"])
    except Exception:
        traceback.print_exc(file=sys.stderr)
    finally:
        if _run_lock.locked():
            _run_lock.release()


@app.post("/api/runs")
def create_run(req: RunRequest):
    if not req.topic.strip():
        raise HTTPException(400, "topic is required")
    if not _run_lock.acquire(blocking=False):
        raise HTTPException(409, "another run is in progress")
    if db.get_active_run() is not None:
        _run_lock.release()
        raise HTTPException(409, "another run is in progress")
    threading.Thread(
        target=_execute, args=(req.topic.strip(), req.top_k), daemon=True
    ).start()
    return {"status": "started"}


@app.get("/api/runs")
def list_runs(limit: int = 50):
    return {"runs": db.list_runs(limit=limit)}


@app.get("/api/runs/active")
def active_run():
    return {"run": db.get_active_run()}


@app.get("/api/runs/{run_id}")
def run_detail(run_id: int):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run


@app.delete("/api/runs/{run_id}")
def delete_run(run_id: int):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    if run["status"] == "running":
        raise HTTPException(409, "cannot delete a running run")
    db.delete_run(run_id)
    return {"status": "deleted"}


def _run_step(step: str, data: dict) -> dict:
    """Dispatch step to its function. Returns a phase-payload-shaped dict."""
    if step == "keyword_extract":
        kws = extract_keywords(data["topic"])
        return {"en": kws["en"], "ko": kws["ko"]}
    if step == "filter":
        top = score_and_select(data["topic"], data["docs"], top_k=data["top_k"])
        return {
            "scored": [
                {
                    "url": d["url"],
                    "title": d.get("title", ""),
                    "score": d.get("score"),
                    "score_detail": d.get("score_detail", {}),
                }
                for d in top
            ],
        }
    if step == "draft":
        text = synthesize(data["topic"], data["docs"])
        return {"chars": len(text), "draft": text}
    raise HTTPException(400, f"unknown step: {step}")


@app.post("/api/runs/{run_id}/steps/{step}/rerun")
def rerun_step(run_id: int, step: str):
    if step not in STEP_PHASE_NUM:
        raise HTTPException(400, f"step must be one of {list(STEP_PHASE_NUM)}")
    if not db.get_run(run_id):
        raise HTTPException(404, "run not found")
    data = db.get_step_input(run_id, step)
    if data is None:
        raise HTTPException(
            404,
            "no saved input for this step (only runs started after this feature shipped have snapshots)",
        )
    output = _run_step(step, data)
    return {"step": step, "phase_num": STEP_PHASE_NUM[step], "output": output}


@app.get("/api/runs/{run_id}/steps")
def list_run_steps(run_id: int):
    if not db.get_run(run_id):
        raise HTTPException(404, "run not found")
    return {"steps": db.list_step_inputs(run_id)}


@app.get("/api/prompts")
def list_prompts():
    return {
        "prompts": [
            {"name": n, "content": _prompts.load(n)} for n in _prompts.list_names()
        ]
    }


@app.get("/api/prompts/{name}")
def get_prompt(name: str):
    if name not in _prompts.list_names():
        raise HTTPException(404, "prompt not found")
    return {"name": name, "content": _prompts.load(name)}


@app.put("/api/prompts/{name}")
def update_prompt(name: str, body: PromptUpdate):
    try:
        _prompts.save(name, body.content)
    except ValueError:
        raise HTTPException(404, "prompt not found")
    return {"name": name, "content": _prompts.load(name)}


@app.get("/api/feeds")
def get_feeds():
    return {"content": _feeds.load_raw()}


@app.put("/api/feeds")
def update_feeds(body: FeedsUpdate):
    try:
        _feeds.save(body.content)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"content": _feeds.load_raw()}


@app.get("/api/config")
def get_config():
    return _config.load()


@app.put("/api/config")
def update_config(body: ConfigUpdate):
    try:
        return _config.save(body.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


# Serve built frontend if present
_DIST = Path(__file__).parent.parent / "web" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="frontend")
