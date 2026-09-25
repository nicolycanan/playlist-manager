from enum import Enum
from pydantic import BaseModel, Field, field_validator


class Format(str, Enum):
    mp3 = "mp3"
    m4a = "m4a"
    wav = "wav"


class Quality(str, Enum):
    q128 = "128"
    q192 = "192"
    q256 = "256"
    q320 = "320"


class UrlRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class DownloadRequest(UrlRequest):
    format: Format = Format.mp3
    quality: Quality = Quality.q192
    entries: list[str] | None = None

    @field_validator("entries")
    @classmethod
    def valid_entries(cls, value):
        if value is not None and len(value) > 500:
            raise ValueError("Seleção de playlist muito grande")
        return value


class Preview(BaseModel):
    title: str | None = None
    thumbnail: str | None = None
    duration: int | None = None
    channel: str | None = None
    webpage_url: str
    status: str


class PlaylistEntry(Preview):
    id: str | None = None


class InfoResponse(BaseModel):
    preview: Preview
    entries: list[PlaylistEntry] = []


class DownloadResponse(BaseModel):
    job_id: str
    status: str


class FileMetadata(BaseModel):
    filename: str
    format: str
    size: int


class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: float = 0
    message: str | None = None
    files: list[FileMetadata] = []
