import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def find_ffmpeg(configured: str | None = None) -> str | None:
    if configured:
        candidate = Path(configured)
        if candidate.is_file():
            return str(candidate)
    return shutil.which("ffmpeg")


def require_ffmpeg(configured: str | None = None) -> str:
    path = find_ffmpeg(configured)
    if not path:
        raise RuntimeError("FFmpeg não foi encontrado no PATH. Instale o FFmpeg e adicione-o ao PATH.")
    return path


def postprocessor_options(fmt: str, quality: str, ffmpeg: str) -> dict:
    codec = {"mp3": "mp3", "m4a": "m4a", "wav": "wav"}[fmt]
    options = {"key": "FFmpegExtractAudio", "preferredcodec": codec}
    if fmt == "mp3":
        options["preferredquality"] = quality
    return {"postprocessors": [options], "ffmpeg_location": ffmpeg}
