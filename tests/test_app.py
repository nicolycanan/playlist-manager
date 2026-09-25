from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.validators import validate_youtube_url
from app.services.downloader import sanitize_filename
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
