# Playlist Manager

Aplicação FastAPI modular para obter informações e baixar áudio autorizado de vídeos ou playlists públicas do YouTube, usando `yt-dlp` e FFmpeg via subprocess interno do yt-dlp.

## Executar

1. `python -m venv .venv` e ative o ambiente.
2. `pip install -r requirements.txt`
3. Copie `.env.example` para `.env`; instale FFmpeg e deixe-o no `PATH` (ou configure `FFMPEG_PATH`).
4. `python run.py`

Abra `http://127.0.0.1:8000`. Os endpoints são `POST /api/youtube/info`, `POST /api/youtube/download`, `GET /api/downloads` e `GET /api/downloads/{job_id}`.

Use somente conteúdo público/autorizado. O projeto não contorna DRM, paywalls ou controles de acesso.
