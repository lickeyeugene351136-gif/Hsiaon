from __future__ import annotations

import json
from pathlib import Path

from .models import ArtifactPaths


def validate_success_artifacts(paths: ArtifactPaths) -> list[str]:
    errors = _required_non_empty(
        [
            paths.storyboard,
            paths.prompt,
            paths.config,
            paths.generation_record,
            paths.manifest,
            paths.log,
        ]
    )
    if paths.video is None or not paths.video.exists() or paths.video.stat().st_size == 0:
        errors.append("video_001.mp4 must exist and be non-empty for success")
    record = _read_json(paths.generation_record, errors)
    manifest = _read_json(paths.manifest, errors)
    if record:
        if record.get("status") != "succeeded":
            errors.append("generation_record.json status must be succeeded")
        if record.get("output_file") != "video_001.mp4":
            errors.append("generation_record.json output_file must be video_001.mp4")
    if manifest:
        files = manifest.get("files", {})
        if "video_001.mp4" not in files:
            errors.append("manifest.json must include video_001.mp4 for success")
        if files.get("manifest.json", {}).get("sha256", "missing") is not None:
            errors.append("manifest.json self sha256 must be null")
    if paths.log.exists():
        log_text = paths.log.read_text(encoding="utf-8")
        if "FAILED" in log_text.splitlines()[-1:]:
            errors.append("log.jsonl must not end in FAILED for success")
    return errors


def validate_provider_failure_artifacts(paths: ArtifactPaths) -> list[str]:
    errors = _required_non_empty(
        [
            paths.storyboard,
            paths.prompt,
            paths.config,
            paths.generation_record,
            paths.manifest,
            paths.log,
        ]
    )
    unexpected_video = paths.output_dir / "video_001.mp4"
    if unexpected_video.exists():
        errors.append("video_001.mp4 must not exist for provider failure")
    record = _read_json(paths.generation_record, errors)
    manifest = _read_json(paths.manifest, errors)
    if record:
        if record.get("status") != "failed":
            errors.append("generation_record.json status must be failed")
        if not record.get("error_message"):
            errors.append("generation_record.json error_message must be non-empty")
    if manifest:
        files = manifest.get("files", {})
        if "video_001.mp4" in files:
            errors.append("manifest.json must omit video_001.mp4 for provider failure")
        if files.get("manifest.json", {}).get("sha256", "missing") is not None:
            errors.append("manifest.json self sha256 must be null")
    if paths.log.exists() and "FAILED" not in paths.log.read_text(encoding="utf-8"):
        errors.append("log.jsonl must contain FAILED for provider failure")
    return errors


def _required_non_empty(paths: list[Path]) -> list[str]:
    errors = []
    for path in paths:
        if not path.exists():
            errors.append(f"{path.name} is missing")
        elif path.stat().st_size == 0:
            errors.append(f"{path.name} is empty")
    return errors


def _read_json(path: Path, errors: list[str]) -> dict[str, object] | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path.name} is invalid JSON: {exc}")
        return None
