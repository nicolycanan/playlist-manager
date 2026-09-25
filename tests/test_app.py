from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.main import jobs
from app.validators import validate_youtube_url
from app.services.downloader import download, sanitize_filename
from app.services.converter import find_ffmpeg


def test_url_validation():
    assert validate_youtube_url("https://www.youtube.com/watch?v=x").startswith("https")
    for url in ("https://example.com/video", "javascript:alert(1)", "https://youtu.be/"):
        try:
            validate_youtube_url(url)
            assert False
        except ValueError:
            pass


def test_sanitize_filename():
    assert "/" not in sanitize_filename('canal: título?/x')
    assert sanitize_filename("") == "audio"


def test_ffmpeg_detection(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.converter.shutil.which", lambda _: None)
    assert find_ffmpeg(str(tmp_path / "missing")) is None
    executable = tmp_path / "ffmpeg.exe"
    executable.write_text("")
    assert find_ffmpeg(str(executable)) == str(executable)


def test_info_validation():
    client = TestClient(app)
    response = client.post("/api/youtube/info", json={"url": "https://example.com"})
    assert response.status_code == 422


def test_info_with_mocked_ytdlp(monkeypatch):
    monkeypatch.setattr(
        "app.main.extract_info",
        lambda url: (
            {"title": "Demo", "thumbnail": None, "duration": 10,
             "channel": "Canal", "webpage_url": url, "status": "disponível"},
            [],
        ),
    )
    response = TestClient(app).post(
        "/api/youtube/info", json={"url": "https://www.youtube.com/watch?v=demo"}
    )
    assert response.status_code == 200
    assert response.json()["preview"]["title"] == "Demo"


def test_download_rejects_missing_physical_conversion(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.downloader.settings.downloads_dir", tmp_path)
    monkeypatch.setattr("app.services.downloader.require_ffmpeg", lambda _: "ffmpeg")

    class FakeYDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def download(self, urls):
            (tmp_path / "source.webm").write_bytes(b"source")

    monkeypatch.setattr("app.services.downloader.yt_dlp.YoutubeDL", FakeYDL)
    try:
        download("https://www.youtube.com/watch?v=test", "mp3", "192", lambda *args: None)
        assert False
    except RuntimeError as exc:
        assert "arquivo final" in str(exc)


def test_download_file_endpoint_and_traversal_protection(monkeypatch, tmp_path):
    monkeypatch.setattr("app.config.settings.downloads_dir", tmp_path)
    output = tmp_path / "demo.mp3"
    output.write_bytes(b"audio")
    jobs["job-file"] = {
        "status": "completed", "progress": 100, "message": None,
        "files": [{"filename": output.name, "format": "mp3", "size": output.stat().st_size}],
    }
    response = TestClient(app).get("/api/downloads/job-file/file")
    assert response.status_code == 200
    assert response.content == b"audio"

    jobs["job-traversal"] = {
        "status": "completed", "progress": 100, "message": None,
        "files": [{"filename": "../secret.mp3", "format": "mp3", "size": 1}],
    }
    assert TestClient(app).get("/api/downloads/job-traversal/file").status_code == 404


def test_job_does_not_complete_without_physical_file(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.downloader.settings.downloads_dir", tmp_path)
    monkeypatch.setattr("app.services.downloader.require_ffmpeg", lambda _: "ffmpeg")

    class FakeYDL:
        def __init__(self, options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def download(self, urls):
            return None

    monkeypatch.setattr("app.services.downloader.yt_dlp.YoutubeDL", FakeYDL)
    with TestClient(app) as client:
        response = client.post(
            "/api/youtube/download",
            json={"url": "https://www.youtube.com/watch?v=test", "format": "mp3", "quality": "192"},
        )
        job_id = response.json()["job_id"]
        for _ in range(20):
            status = client.get(f"/api/downloads/{job_id}").json()
            if status["status"] == "error":
                break
        assert status["status"] == "error"
        assert "arquivo final" in status["message"].lower()
