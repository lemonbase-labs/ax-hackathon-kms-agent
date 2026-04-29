"""FastAPI server for the KMS dashboard. Local-only (127.0.0.1)."""
import threading
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from kms import _prompts, db
from kms.pipeline import run_pipeline

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


def _execute(topic: str, top_k: int) -> None:
    try:
        run_pipeline(topic, top_k=top_k)
    except Exception:
        pass
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


# Serve built frontend if present
_DIST = Path(__file__).parent.parent / "web" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="frontend")
