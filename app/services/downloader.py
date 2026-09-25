import logging
import re
from pathlib import Path
from threading import Lock
from typing import Callable
import yt_dlp
from .converter import require_ffmpeg, postprocessor_options
from ..config import settings

logger = logging.getLogger(__name__)
_lock = Lock()


def sanitize_filename(value: str, fallback: str = "audio") -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", value or "")
    value = re.sub(r"\s+", " ", value).strip(" .")
    return (value[:180] or fallback)


def _safe_template() -> str:
    # yt-dlp must never resolve its template relative to the process cwd.
    return str(settings.downloads_dir.resolve() / "%(uploader)s - %(title)s.%(ext)s")


def download(url: str, fmt: str, quality: str, update: Callable[[str, float, str | None], None],
             entries: list[str] | None = None) -> list[dict[str, str | int]]:
    ffmpeg = require_ffmpeg(settings.ffmpeg_path)
    settings.downloads_dir.mkdir(parents=True, exist_ok=True)
    update("Baixando áudio", 15, None)
    options = {"format": "bestaudio/best", "outtmpl": _safe_template(),
               "noplaylist": False if entries is None else True,
               "ignoreerrors": False, "quiet": True, "no_warnings": True,
               "restrictfilenames": False, "overwrites": False,
               "continuedl": True, "postprocessors": postprocessor_options(fmt, quality, ffmpeg)["postprocessors"],
               "ffmpeg_location": ffmpeg,
               "progress_hooks": [lambda p: _hook(p, update)]}
    if entries:
        options["playlist_items"] = ",".join(entries)
    before = {p.resolve() for p in settings.downloads_dir.rglob("*") if p.is_file()}
    final_paths: list[Path] = []

    def postprocessor_hook(event: dict):
        if event.get("status") != "finished":
            return
        info = event.get("info_dict") or {}
        candidates = [info.get("filepath")]
        candidates.extend(
            item.get("filepath")
            for item in info.get("requested_downloads") or []
            if isinstance(item, dict)
        )
        for candidate in candidates:
            if candidate:
                path = Path(candidate).resolve()
                if path not in final_paths:
                    final_paths.append(path)

    options["postprocessor_hooks"] = [postprocessor_hook]
    try:
        with _lock, yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
    except Exception as exc:
        logger.warning("Download falhou: %s", type(exc).__name__)
        raise RuntimeError("Não foi possível baixar ou converter o áudio. Verifique a URL, permissões e espaço em disco.") from exc
    update("Finalizando", 95, None)
    after = final_paths
    root = settings.downloads_dir.resolve()
    valid_paths = []
    for path in after:
        print(f"[DEBUG] Tentando validar a existência do arquivo em: {path}")
        exists = path.exists()
        print(f"[DEBUG] O arquivo existe? {exists}")
        try:
            path.relative_to(root)
        except ValueError:
            logger.warning("Ignorando arquivo final fora da pasta de downloads")
            continue
        if exists and path.stat().st_size > 0:
            valid_paths.append(path)
    if not valid_paths:
        raise RuntimeError(
            "O áudio não foi convertido corretamente: o arquivo final não foi encontrado "
            "ou está vazio. Verifique o FFmpeg e tente novamente."
        )
    result = []
    for path in valid_paths:
        # Keep yt-dlp output confined to the configured directory and normalize
        # metadata-derived names before exposing them to the UI.
        safe = sanitize_filename(path.stem) + path.suffix.lower()
        target = settings.downloads_dir / safe
        counter = 1
        while target.exists() and target.resolve() != path.resolve():
            target = settings.downloads_dir / f"{sanitize_filename(path.stem)} ({counter}){path.suffix.lower()}"
            counter += 1
        if target.resolve() != path.resolve():
            path.rename(target)
        if not target.is_file() or target.stat().st_size <= 0:
            raise RuntimeError(
                "O áudio não foi convertido corretamente: o arquivo final não foi encontrado "
                "ou está vazio. Verifique o FFmpeg e tente novamente."
            )
        result.append({
            "filename": target.name,
            "format": target.suffix.lstrip(".").lower(),
            "size": target.stat().st_size,
        })
    return result


def _hook(progress: dict, update: Callable):
    if progress.get("status") == "finished":
        update("Convertendo", 75, None)
    elif progress.get("status") == "downloading":
        total = progress.get("total_bytes") or progress.get("total_bytes_estimate")
        percent = (progress.get("downloaded_bytes", 0) / total * 60) if total else 20
        update("Baixando áudio", min(70, percent), None)
