from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.models import BITRATES, FORMATS, OVERWRITE_VALUES, CancelJobResponse, CreateJobRequest
from app.services.jobs import JobManager


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app = FastAPI(title="SpotUI", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
manager = JobManager(settings)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "settings": settings.public(),
            "jobs": manager.list_jobs(),
            "formats": sorted(FORMATS),
            "bitrates": sorted(BITRATES, key=lambda item: (item == "disable", item)),
            "overwrite_values": sorted(OVERWRITE_VALUES),
        },
    )


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/jobs")
async def list_jobs() -> dict[str, object]:
    return {"jobs": manager.list_jobs()}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, object]:
    job = manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.post("/api/jobs", status_code=201)
async def create_job(payload: CreateJobRequest) -> dict[str, object]:
    return manager.create_job(payload)


@app.post("/api/jobs/{job_id}/cancel", response_model=CancelJobResponse)
async def cancel_job(job_id: str) -> CancelJobResponse:
    cancelled, message = manager.cancel_job(job_id)
    if not cancelled:
        raise HTTPException(status_code=400, detail=message)

    job = manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found after cancellation.")

    return CancelJobResponse(job_id=job_id, status=str(job["status"]), message=message)


def main() -> None:
    import uvicorn

    settings.ensure_directories()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    main()
