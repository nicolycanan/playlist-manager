import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .schemas import UrlRequest, DownloadRequest, InfoResponse, DownloadResponse, JobResponse
from .validators import validate_youtube_url
from .services.youtube import extract_info
from .services.downloader import download

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI(title="Playlist Manager")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
executor = ThreadPoolExecutor(max_workers=2)
jobs: dict[str, dict] = {}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request})


@app.post("/api/youtube/info", response_model=InfoResponse)
async def youtube_info(payload: UrlRequest):
    try:
        preview, entries = extract_info(validate_youtube_url(payload.url))
        return {"preview": preview, "entries": entries}
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except RuntimeError as exc:
        raise HTTPException(400, str(exc))


def _run_job(job_id: str, payload: DownloadRequest):
    def update(status, progress, message):
        jobs[job_id].update(status=status, progress=progress, message=message)
    jobs[job_id]["status"] = "Obtendo informações"
    try:
        files = download(payload.url, payload.format.value, payload.quality.value, update, payload.entries)
        jobs[job_id].update(status="Concluído", progress=100, files=files)
    except Exception as exc:
        message = str(exc) if isinstance(exc, RuntimeError) else (
            "Não foi possível concluir a extração. Verifique a URL, o FFmpeg e o espaço em disco."
        )
        jobs[job_id].update(status="error", progress=0, message=message)
        logger.info("Job %s falhou: %s", job_id, type(exc).__name__)


@app.post("/api/youtube/download", response_model=DownloadResponse, status_code=202)
async def youtube_download(payload: DownloadRequest, background_tasks: BackgroundTasks):
    try:
        payload.url = validate_youtube_url(payload.url)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    job_id = uuid4().hex
    jobs[job_id] = {"status": "Obtendo informações", "progress": 0, "message": None, "files": []}
    background_tasks.add_task(executor.submit, _run_job, job_id, payload)
    return {"job_id": job_id, "status": jobs[job_id]["status"]}


@app.get("/api/downloads")
async def list_downloads():
    from .config import settings
    return {"files": [p.name for p in settings.downloads_dir.iterdir() if p.is_file() and p.name != ".gitkeep"]}


@app.get("/api/downloads/{job_id}", response_model=JobResponse)
async def job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job não encontrado")
    return {"job_id": job_id, **jobs[job_id]}
