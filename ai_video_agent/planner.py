from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .models import (
    AgentError,
    AgentInput,
    EXIT_INPUT_ERROR,
    EXIT_PATH_ERROR,
    GenerationPlan,
    ReferenceMetadata,
    Shot,
)


OUTPUT_TRIGGERS = [
    "输出路径为",
    "保存路径为",
    "输出到",
    "保存到",
    "放到",
    "生成到",
    "导出到",
]
SUPPORTED_ASPECT_RATIOS = {"9:16", "16:9", "1:1", "4:5"}
NEGATIVE_PROMPT_TERMS = [
    "不要文字",
    "不要字幕",
    "不要 logo",
    "不要水印",
    "不要畸形人物",
    "不要多余手指",
    "不要产品变形",
    "不要画面闪烁",
    "不要低清画质",
    "不要杂乱背景",
]
REFERENCE_PATTERN = re.compile(r"参考(?:图|图片|视频|文件)?(?:在|见|为)?\s*([^\s，。；;\n]+)")


def extract_natural_output_dir(raw_request: str) -> Path | None:
    for trigger in OUTPUT_TRIGGERS:
        index = raw_request.find(trigger)
        if index == -1:
            continue
        start = index + len(trigger)
        remainder = raw_request[start:].lstrip(" ：:")
        match = re.match(r"([^\s，。；;\n]+)", remainder)
        if match:
            return Path(match.group(1))
    return None


def normalize_aspect_ratio(explicit: str | None, raw_request: str) -> str:
    if explicit:
        if explicit not in SUPPORTED_ASPECT_RATIOS:
            raise AgentError(f"Unsupported aspect ratio: {explicit}", EXIT_INPUT_ERROR)
        return explicit
    for ratio in SUPPORTED_ASPECT_RATIOS:
        if ratio in raw_request:
            return ratio
    if "竖屏" in raw_request:
        return "9:16"
    if "横屏" in raw_request:
        return "16:9"
    if "方图" in raw_request or "方形" in raw_request:
        return "1:1"
    return "9:16"


def duration_to_shot_count(duration: int) -> int:
    if duration <= 0:
        raise AgentError("Duration must be greater than 0 seconds", EXIT_INPUT_ERROR)
    if duration <= 4:
        return 1
    if duration <= 8:
        return 2
    if duration <= 15:
        return 3
    if duration <= 30:
        return 5
    raise AgentError("Durations above 30 seconds are not supported in V1", EXIT_INPUT_ERROR)


def resolve_output_dir(agent_input: AgentInput) -> Path:
    cwd = agent_input.cwd.resolve()
    output = agent_input.output_dir or extract_natural_output_dir(agent_input.raw_request)
    if output is None:
        output = Path("runs") / "latest"
    if ".." in output.parts:
        raise AgentError(f"Unsafe output directory: {output}", EXIT_PATH_ERROR)
    resolved = output if output.is_absolute() else cwd / output
    resolved = resolved.resolve()
    _ensure_safe_output_dir(cwd, resolved)
    return resolved


def collect_reference_metadata(agent_input: AgentInput) -> tuple[list[ReferenceMetadata], list[str]]:
    metadata: list[ReferenceMetadata] = []
    warnings: list[str] = []
    cwd = agent_input.cwd.resolve()

    for raw_path in agent_input.reference_paths:
        path = raw_path if raw_path.is_absolute() else cwd / raw_path
        if not path.exists():
            raise AgentError(f"Reference path does not exist: {raw_path}", EXIT_INPUT_ERROR)
        metadata.append(_metadata_for(path))

    for raw_path in _extract_weak_reference_paths(agent_input.raw_request):
        path = raw_path if raw_path.is_absolute() else cwd / raw_path
        if path.exists():
            if not any(item.path == path.resolve() for item in metadata):
                metadata.append(_metadata_for(path))
        else:
            warnings.append(f"Weak reference path not found: {raw_path}")

    return metadata, warnings


def build_generation_plan(agent_input: AgentInput) -> GenerationPlan:
    if not agent_input.raw_request.strip():
        raise AgentError("Request cannot be empty", EXIT_INPUT_ERROR)
    output_dir = resolve_output_dir(agent_input)
    references, warnings = collect_reference_metadata(agent_input)
    duration = agent_input.duration or _extract_duration(agent_input.raw_request) or 6
    shot_count = duration_to_shot_count(duration)
    aspect_ratio = normalize_aspect_ratio(agent_input.aspect_ratio, agent_input.raw_request)
    topic = _extract_topic(agent_input.raw_request)
    request_hash = compute_request_hash(agent_input)
    run_id = compute_run_id(
        {
            "topic": topic,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "style": "commercial advertising",
            "motion_strength": "medium",
            "camera_motion": "slow push in",
        }
    )
    return GenerationPlan(
        topic=topic,
        purpose="short video generation",
        aspect_ratio=aspect_ratio,
        duration=duration,
        style="commercial advertising",
        visual_quality="realistic photographic quality",
        tone="clean, premium, high-end",
        render_type="realistic",
        shot_count=shot_count,
        motion_strength="medium",
        camera_motion="slow push in",
        output_dir=output_dir,
        reference_metadata=references,
        reference_warnings=warnings,
        negative_prompt_terms=NEGATIVE_PROMPT_TERMS.copy(),
        request_hash=request_hash,
        run_id=run_id,
    )


def create_storyboard(plan: GenerationPlan) -> list[Shot]:
    base_duration = round(plan.duration / plan.shot_count, 2)
    shots: list[Shot] = []
    for index in range(1, plan.shot_count + 1):
        duration = base_duration
        if index == plan.shot_count:
            duration = round(plan.duration - base_duration * (plan.shot_count - 1), 2)
        scene = "clean premium commercial scene"
        subject = plan.topic
        action = "show ingredient transformation and visual delivery"
        shot_size = "macro close-up" if index == 1 else "close-up"
        composition = "center-weighted vertical composition"
        camera_motion = plan.camera_motion
        transition = "cut" if index == 1 else "soft dissolve"
        lighting = "bright translucent studio lighting"
        purpose = "establish subject" if index == 1 else "reinforce benefit"
        prompt = (
            f"Shot {index}: {shot_size}, {subject}, {action}, "
            f"{composition}, {camera_motion}, {lighting}."
        )
        shots.append(
            Shot(
                index=index,
                duration=duration,
                scene=scene,
                subject=subject,
                action=action,
                shot_size=shot_size,
                composition=composition,
                camera_motion=camera_motion,
                transition=transition,
                lighting=lighting,
                purpose=purpose,
                prompt=prompt,
            )
        )
    return shots


def compute_request_hash(agent_input: AgentInput) -> str:
    payload = {
        "raw_request": agent_input.raw_request,
        "duration": agent_input.duration,
        "aspect_ratio": agent_input.aspect_ratio,
        "output_dir": str(agent_input.output_dir) if agent_input.output_dir else None,
        "reference_paths": [str(path) for path in agent_input.reference_paths],
    }
    return _sha256_json(payload)


def compute_run_id(payload: dict[str, object]) -> str:
    return _sha256_json(payload)[:12]


def _ensure_safe_output_dir(cwd: Path, resolved: Path) -> None:
    sensitive = [
        Path("/"),
        Path("/bin"),
        Path("/etc"),
        Path("/usr"),
        Path("C:/Windows"),
        Path("C:/Program Files"),
    ]
    lowered = str(resolved).lower()
    if any(lowered == str(path.resolve()).lower() for path in sensitive if path.exists() or str(path).startswith("C:")):
        raise AgentError(f"Unsafe output directory: {resolved}", EXIT_PATH_ERROR)
    try:
        resolved.relative_to(cwd)
    except ValueError:
        # Explicit absolute paths are allowed unless they are sensitive.
        if not resolved.is_absolute():
            raise AgentError(f"Unsafe output directory: {resolved}", EXIT_PATH_ERROR)
    raw_parts = resolved.parts
    if ".." in raw_parts:
        raise AgentError(f"Unsafe output directory: {resolved}", EXIT_PATH_ERROR)


def _is_under_cwd(cwd: Path, path: Path) -> bool:
    try:
        path.relative_to(cwd)
        return True
    except ValueError:
        return False


def _metadata_for(path: Path) -> ReferenceMetadata:
    resolved = path.resolve()
    extension = resolved.suffix.lower()
    return ReferenceMetadata(
        path=resolved,
        filename=resolved.name,
        extension=extension,
        size_bytes=resolved.stat().st_size,
        file_type=_file_type(extension),
    )


def _file_type(extension: str) -> str:
    if extension in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        return "image"
    if extension in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
        return "video"
    if extension in {".txt", ".md", ".json", ".csv"}:
        return "document"
    return "unknown"


def _extract_weak_reference_paths(raw_request: str) -> list[Path]:
    paths: list[Path] = []
    for match in REFERENCE_PATTERN.finditer(raw_request):
        value = match.group(1).strip(" ：:")
        if Path(value).suffix:
            paths.append(Path(value))
    return paths


def _extract_duration(raw_request: str) -> int | None:
    match = re.search(r"(\d+)\s*(?:秒|s|S)", raw_request)
    if match:
        return int(match.group(1))
    return None


def _extract_topic(raw_request: str) -> str:
    match = re.search(r"主题(?:是|为)?([^，。；;\n]+)", raw_request)
    if match:
        return match.group(1).strip()
    cleaned = raw_request.strip()
    return cleaned[:40] or "AI short video"


def _sha256_json(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
