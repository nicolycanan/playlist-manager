from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseModel):
    downloads_dir: Path = Field(default=BASE_DIR / "downloads")
    ffmpeg_path: str | None = None
    max_concurrent_downloads: int = 2

    @classmethod
    def from_env(cls) -> "Settings":
        raw_dir = os.getenv("DOWNLOADS_DIR", "downloads")
        directory = Path(raw_dir)
        if not directory.is_absolute():
            directory = BASE_DIR / directory
        ffmpeg = os.getenv("FFMPEG_PATH") or None
        try:
            concurrency = max(1, int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "2")))
        except ValueError:
            concurrency = 2
        directory.mkdir(parents=True, exist_ok=True)
        return cls(downloads_dir=directory.resolve(), ffmpeg_path=ffmpeg,
                   max_concurrent_downloads=concurrency)


settings = Settings.from_env()
