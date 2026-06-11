from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


FORMATS = {"mp3", "m4a", "opus", "flac", "ogg", "wav"}
OVERWRITE_VALUES = {"skip", "force"}
BITRATES = {"disable", "64k", "96k", "128k", "160k", "192k", "256k", "320k"}


class CreateJobRequest(BaseModel):
    query: str = Field(min_length=1, max_length=600)
    format: str = Field(default="mp3")
    bitrate: str = Field(default="128k")
    subdir: str = Field(default="", max_length=200)
    overwrite: Literal["skip", "force"] = "skip"
    threads: int = Field(default=4, ge=1, le=8)

    @field_validator("query")
    @classmethod
    def clean_query(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Query cannot be empty.")
        return cleaned

    @field_validator("format")
    @classmethod
    def validate_format(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in FORMATS:
            raise ValueError(f"Format must be one of: {', '.join(sorted(FORMATS))}")
        return normalized

    @field_validator("bitrate")
    @classmethod
    def validate_bitrate(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in BITRATES:
            raise ValueError(f"Bitrate must be one of: {', '.join(sorted(BITRATES))}")
        return normalized

    @field_validator("subdir")
    @classmethod
    def clean_subdir(cls, value: str) -> str:
        cleaned = value.strip().strip("/")
        if ".." in cleaned.split("/"):
            raise ValueError("Subfolder cannot contain '..'")
        return cleaned


class CancelJobResponse(BaseModel):
    job_id: str
    status: str
    message: str

