from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import (
    ArtifactPaths,
    GenerationPlan,
    ProgressEvent,
    PromptBundle,
    ProviderResult,
    Shot,
)


class ArtifactWriter:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def write_success(
        self,
        plan: GenerationPlan,
        shots: list[Shot],
        prompts: PromptBundle,
        config: dict[str, object],
        provider_result: ProviderResult,
        progress_events: list[ProgressEvent],
    ) -> ArtifactPaths:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        video = self.output_dir / "video_001.mp4"
        video.write_bytes(provider_result.video_bytes or b"")
        paths = self._base_paths(video=video)
        self._write_common(paths, plan, shots, prompts, config, provider_result, progress_events)
        return paths

    def write_provider_failure(
        self,
        plan: GenerationPlan,
        shots: list[Shot],
        prompts: PromptBundle,
        config: dict[str, object],
        provider_result: ProviderResult,
        progress_events: list[ProgressEvent],
    ) -> ArtifactPaths:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        video_path = self.output_dir / "video_001.mp4"
        if video_path.exists():
            video_path.unlink()
        paths = self._base_paths(video=None)
        self._write_common(paths, plan, shots, prompts, config, provider_result, progress_events)
        return paths

    def _base_paths(self, video: Path | None) -> ArtifactPaths:
        return ArtifactPaths(
            output_dir=self.output_dir,
            video=video,
            storyboard=self.output_dir / "storyboard.md",
            prompt=self.output_dir / "prompt.txt",
            config=self.output_dir / "config.json",
            generation_record=self.output_dir / "generation_record.json",
            manifest=self.output_dir / "manifest.json",
            log=self.output_dir / "log.jsonl",
        )

    def _write_common(
        self,
        paths: ArtifactPaths,
        plan: GenerationPlan,
        shots: list[Shot],
        prompts: PromptBundle,
        config: dict[str, object],
        provider_result: ProviderResult,
        progress_events: list[ProgressEvent],
    ) -> None:
        paths.storyboard.write_text(_render_storyboard(shots), encoding="utf-8")
        paths.prompt.write_text(_render_prompt(prompts), encoding="utf-8")
        _write_json(paths.config, config)
        _write_json(paths.generation_record, _generation_record(plan, prompts, provider_result, paths.video))
        _write_log(paths.log, progress_events, provider_result.status)
        self._write_manifest(paths, plan.run_id)

    def _write_manifest(self, paths: ArtifactPaths, run_id: str) -> None:
        artifact_map = {
            "storyboard": "storyboard.md",
            "prompt": "prompt.txt",
            "config": "config.json",
            "generation_record": "generation_record.json",
            "manifest": "manifest.json",
            "log": "log.jsonl",
        }
        if paths.video is not None:
            artifact_map = {"video": "video_001.mp4", **artifact_map}

        files: dict[str, dict[str, Any]] = {}
        purposes = {
            "video_001.mp4": "Mock video bytes returned by provider",
            "storyboard.md": "Human-readable storyboard",
            "prompt.txt": "Complete model-facing prompt text",
            "config.json": "Structured API-style generation parameters",
            "generation_record.json": "Provider-facing run metadata",
            "manifest.json": "Run-level artifact index",
            "log.jsonl": "Structured progress events",
        }
        for filename in artifact_map.values():
            path = self.output_dir / filename
            if filename == "manifest.json":
                files[filename] = {
                    "purpose": purposes[filename],
                    "size": 0,
                    "sha256": None,
                    "hash_policy": "omitted-for-self-to-avoid-recursive-hash",
                }
            else:
                files[filename] = {
                    "purpose": purposes[filename],
                    "size": path.stat().st_size,
                    "sha256": _file_hash(path),
                }

        manifest = {
            "run_id": run_id,
            "artifacts": artifact_map,
            "files": files,
            "created_at": _now_iso(),
        }
        for _ in range(3):
            _write_json(paths.manifest, manifest)
            new_size = paths.manifest.stat().st_size
            if manifest["files"]["manifest.json"]["size"] == new_size:
                break
            manifest["files"]["manifest.json"]["size"] = new_size
        _write_json(paths.manifest, manifest)


def _render_storyboard(shots: list[Shot]) -> str:
    lines = ["# Storyboard", ""]
    for shot in shots:
        lines.extend(
            [
                f"## Shot {shot.index}",
                f"- Duration: {shot.duration}",
                f"- Scene: {shot.scene}",
                f"- Subject: {shot.subject}",
                f"- Action: {shot.action}",
                f"- Shot size: {shot.shot_size}",
                f"- Composition: {shot.composition}",
                f"- Camera motion: {shot.camera_motion}",
                f"- Transition: {shot.transition}",
                f"- Lighting: {shot.lighting}",
                f"- Purpose: {shot.purpose}",
                f"- Prompt: {shot.prompt}",
                "",
            ]
        )
    return "\n".join(lines)


def _render_prompt(prompts: PromptBundle) -> str:
    parts = [prompts.main_prompt, prompts.negative_prompt]
    if prompts.first_frame_prompt:
        parts.append("【首帧】\n" + prompts.first_frame_prompt)
    if prompts.last_frame_prompt:
        parts.append("【尾帧】\n" + prompts.last_frame_prompt)
    return "\n\n".join(parts) + "\n"


def _generation_record(
    plan: GenerationPlan,
    prompts: PromptBundle,
    provider_result: ProviderResult,
    video_path: Path | None,
) -> dict[str, object]:
    return {
        "provider": provider_result.provider,
        "request_id": provider_result.request_id,
        "run_id": plan.run_id,
        "request_hash": plan.request_hash,
        "prompt_hash": prompts.prompt_hash,
        "duration": plan.duration,
        "aspect_ratio": plan.aspect_ratio,
        "status": provider_result.status,
        "error_message": provider_result.error_message,
        "output_file": video_path.name if video_path else "",
    }


def _write_log(path: Path, progress_events: list[ProgressEvent], provider_status: str) -> None:
    default_state = "FAILED" if provider_status == "failed" else "DONE"
    events = progress_events or [ProgressEvent(state=default_state, message="Artifacts written")]
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            payload = _to_jsonable(event)
            payload["time"] = payload.get("time") or _now_iso()
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    return value
