from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default

    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(slots=True)
class Settings:
    host: str = os.getenv("SPOTUI_HOST", "0.0.0.0")
    port: int = _env_int("SPOTUI_PORT", 8080)
    output_dir: Path = Path(os.getenv("SPOTUI_OUTPUT_DIR", "/music"))
    config_dir: Path = Path(os.getenv("SPOTUI_CONFIG_DIR", "/config"))
    cookie_file: Path = Path(os.getenv("SPOTUI_COOKIE_FILE", "/config/cookies.txt"))
    output_template: str = os.getenv(
        "SPOTUI_OUTPUT_TEMPLATE",
        "{artist}/{album}/{track-number} - {title}.{output-ext}",
    )
    default_format: str = os.getenv("SPOTUI_DEFAULT_FORMAT", "mp3")
    default_bitrate: str = os.getenv("SPOTUI_DEFAULT_BITRATE", "128k")
    max_log_lines: int = _env_int("SPOTUI_MAX_LOG_LINES", 400)

    @property
    def jobs_file(self) -> Path:
        return self.config_dir / "jobs.json"

    def ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.cookie_file.parent.mkdir(parents=True, exist_ok=True)

    def public(self) -> dict[str, str | int | bool]:
        return {
            "host": self.host,
            "port": self.port,
            "output_dir": str(self.output_dir),
            "config_dir": str(self.config_dir),
            "cookie_file": str(self.cookie_file),
            "cookie_file_exists": self.cookie_file.exists(),
            "output_template": self.output_template,
            "default_format": self.default_format,
            "default_bitrate": self.default_bitrate,
        }


settings = Settings()

