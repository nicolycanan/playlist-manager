from urllib.parse import urlparse

OFFICIAL_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}


def validate_youtube_url(value: str) -> str:
    try:
        parsed = urlparse(value.strip())
    except ValueError as exc:
        raise ValueError("URL inválida") from exc
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Use uma URL oficial do YouTube")
    host = parsed.hostname.lower().rstrip(".")
    if host not in OFFICIAL_HOSTS:
        raise ValueError("Use uma URL oficial do YouTube")
    if host == "youtu.be" and not parsed.path.strip("/"):
        raise ValueError("URL do YouTube sem vídeo")
    if host != "youtu.be" and parsed.path in {"", "/"} and not parsed.query:
        raise ValueError("URL do YouTube sem vídeo ou playlist")
    return value.strip()
