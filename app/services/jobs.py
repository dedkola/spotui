from __future__ import annotations

import json
import queue
import subprocess
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings
from app.models import CreateJobRequest


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class DownloadJob:
    id: str
    query: str
    format: str
    bitrate: str
    subdir: str
    overwrite: str
    threads: int
    status: str = "queued"
    created_at: str = field(default_factory=utc_now)
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    output_directory: str = ""
    error: str | None = None
    command: list[str] = field(default_factory=list)
    log_lines: list[str] = field(default_factory=list)

    def append_log(self, line: str, max_lines: int) -> None:
        self.log_lines.append(line.rstrip())
        if len(self.log_lines) > max_lines:
            self.log_lines = self.log_lines[-max_lines:]

    def summary(self) -> dict[str, object]:
        data = asdict(self)
        data["log_tail"] = self.log_lines[-10:]
        data.pop("log_lines", None)
        return data


class JobManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.ensure_directories()
        self._lock = threading.RLock()
        self._queue: queue.Queue[str] = queue.Queue()
        self._jobs: dict[str, DownloadJob] = {}
        self._processes: dict[str, subprocess.Popen[str]] = {}
        self._load_state()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True, name="spotui-worker")
        self._worker.start()

    def list_jobs(self) -> list[dict[str, object]]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda item: item.created_at, reverse=True)
            return [job.summary() for job in jobs]

    def get_job(self, job_id: str) -> dict[str, object] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return asdict(job) if job else None

    def create_job(self, payload: CreateJobRequest) -> dict[str, object]:
        job = DownloadJob(
            id=uuid.uuid4().hex[:12],
            query=payload.query,
            format=payload.format,
            bitrate=payload.bitrate,
            subdir=payload.subdir,
            overwrite=payload.overwrite,
            threads=payload.threads,
        )

        with self._lock:
            self._jobs[job.id] = job
            self._queue.put(job.id)
            self._save_state()
            return asdict(job)

    def cancel_job(self, job_id: str) -> tuple[bool, str]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False, "Job not found."

            if job.status in {"completed", "failed", "cancelled"}:
                return False, f"Job is already {job.status}."

            if job.status == "queued":
                job.status = "cancelled"
                job.finished_at = utc_now()
                job.append_log("Job cancelled before starting.", self.settings.max_log_lines)
                self._save_state()
                return True, "Queued job cancelled."

            process = self._processes.get(job_id)
            if process is None:
                return False, "Process is no longer running."

            job.status = "cancelled"
            process.terminate()
            job.append_log("Cancellation requested. Waiting for spotDL to exit...", self.settings.max_log_lines)
            self._save_state()
            threading.Thread(
                target=self._kill_if_needed,
                args=(job_id, process),
                daemon=True,
                name=f"spotui-cancel-{job_id}",
            ).start()
            return True, "Running job cancellation requested."

    def _resolve_output_dir(self, subdir: str) -> Path:
        root = self.settings.output_dir.resolve()
        target = root / subdir if subdir else root
        resolved = target.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError("Resolved output directory is outside the configured output root.")
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    def _build_command(self, job: DownloadJob, output_directory: Path) -> list[str]:
        output_pattern = str(output_directory / self.settings.output_template)
        command = [
            "spotdl",
            "download",
            job.query,
            "--output",
            output_pattern,
            "--format",
            job.format,
            "--bitrate",
            job.bitrate,
            "--threads",
            str(job.threads),
            "--overwrite",
            job.overwrite,
            "--restrict",
            "ascii",
            "--print-errors",
        ]

        if self.settings.cookie_file.exists():
            command.extend(["--cookie-file", str(self.settings.cookie_file)])

        return command

    def _worker_loop(self) -> None:
        while True:
            job_id = self._queue.get()
            try:
                self._run_job(job_id)
            finally:
                self._queue.task_done()

    def _kill_if_needed(self, job_id: str, process: subprocess.Popen[str]) -> None:
        try:
            process.wait(timeout=10)
            return
        except subprocess.TimeoutExpired:
            process.kill()

        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.append_log("spotDL did not exit in time and was killed.", self.settings.max_log_lines)
                self._save_state()

    def _run_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status == "cancelled":
                return

            try:
                output_directory = self._resolve_output_dir(job.subdir)
            except ValueError as exc:
                job.status = "failed"
                job.error = str(exc)
                job.finished_at = utc_now()
                job.append_log(str(exc), self.settings.max_log_lines)
                self._save_state()
                return

            job.output_directory = str(output_directory)
            job.command = self._build_command(job, output_directory)
            job.status = "running"
            job.started_at = utc_now()
            self._save_state()

        try:
            process = subprocess.Popen(
                job.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as exc:
            with self._lock:
                job.status = "failed"
                job.error = str(exc)
                job.finished_at = utc_now()
                job.append_log(f"Failed to launch spotDL: {exc}", self.settings.max_log_lines)
                self._save_state()
            return

        with self._lock:
            self._processes[job_id] = process
            self._save_state()

        assert process.stdout is not None
        for line in process.stdout:
            with self._lock:
                job.append_log(line, self.settings.max_log_lines)
                self._save_state()

        exit_code = process.wait()

        with self._lock:
            self._processes.pop(job_id, None)
            job.exit_code = exit_code
            job.finished_at = utc_now()

            if job.status == "cancelled":
                job.append_log("spotDL process exited after cancellation.", self.settings.max_log_lines)
            elif exit_code == 0:
                job.status = "completed"
                job.append_log("Download finished successfully.", self.settings.max_log_lines)
            else:
                job.status = "failed"
                job.error = f"spotDL exited with code {exit_code}."
                job.append_log(job.error, self.settings.max_log_lines)

            self._save_state()

    def _load_state(self) -> None:
        jobs_file = self.settings.jobs_file
        if not jobs_file.exists():
            return

        try:
            data = json.loads(jobs_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return

        for raw_job in data.get("jobs", []):
            job = DownloadJob(**raw_job)
            if job.status == "running":
                job.status = "failed"
                job.finished_at = utc_now()
                job.error = "App restarted while this job was running."
                job.append_log(job.error, self.settings.max_log_lines)
            self._jobs[job.id] = job

    def _save_state(self) -> None:
        payload = {"jobs": [asdict(job) for job in self._jobs.values()]}
        self.settings.jobs_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
