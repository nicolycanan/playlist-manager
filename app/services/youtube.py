import logging
from typing import Any
import yt_dlp
from ..validators import validate_youtube_url

logger = logging.getLogger(__name__)


def _preview(data: dict[str, Any], status: str = "disponível") -> dict[str, Any]:
    return {"title": data.get("title"), "thumbnail": data.get("thumbnail"),
            "duration": data.get("duration"), "channel": data.get("channel") or data.get("uploader"),
            "webpage_url": data.get("webpage_url") or data.get("original_url") or "", "status": status}


def extract_info(url: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    url = validate_youtube_url(url)
    options = {"quiet": True, "no_warnings": True, "skip_download": True,
               "extract_flat": "in_playlist"}
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            data = ydl.extract_info(url, download=False)
    except Exception as exc:
        logger.warning("Falha ao obter informações do YouTube: %s", type(exc).__name__)
        raise RuntimeError("Não foi possível obter informações. O vídeo pode ser privado, indisponível ou a rede falhou.") from exc
    entries = []
    for item in data.get("entries") or []:
        if not item:
            continue
        entries.append({**_preview(item), "id": item.get("id")})
    return _preview(data), entries
