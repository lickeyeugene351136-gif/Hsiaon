from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


EXIT_SUCCESS = 0
EXIT_INPUT_ERROR = 1
EXIT_PATH_ERROR = 2
EXIT_PROVIDER_ERROR = 3
EXIT_VALIDATION_ERROR = 4


PROGRESS_STATES = [
    "RECEIVED_REQUEST",
    "RESOLVED_OUTPUT_DIR",
    "COLLECTED_REFERENCES",
    "BUILT_PLAN",
    "CREATED_STORYBOARD",
    "BUILT_PROMPTS",
    "CALLED_PROVIDER",
    "WROTE_ARTIFACTS",
    "VALIDATED_OUTPUTS",
    "DONE",
    "FAILED",
]


class AgentError(Exception):
    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


@dataclass(frozen=True)
class AgentInput:
    raw_request: str
    output_dir: Path | None = None
    reference_paths: list[Path] = field(default_factory=list)
    duration: int | None = None
    aspect_ratio: str | None = None
    cwd: Path = field(default_factory=Path.cwd)


@dataclass(frozen=True)
class ReferenceMetadata:
    path: Path
    filename: str
    extension: str
    size_bytes: int
    file_type: str


@dataclass(frozen=True)
class GenerationPlan:
    topic: str
    purpose: str
    aspect_ratio: str
    duration: int
    style: str
    visual_quality: str
    tone: str
    render_type: str
    shot_count: int
    motion_strength: str
    camera_motion: str
    output_dir: Path
    reference_metadata: list[ReferenceMetadata]
    reference_warnings: list[str]
    negative_prompt_terms: list[str]
    request_hash: str
    run_id: str


@dataclass(frozen=True)
class Shot:
    index: int
    duration: float
    scene: str
    subject: str
    action: str
    shot_size: str
    composition: str
    camera_motion: str
    transition: str
    lighting: str
    purpose: str
    prompt: str


@dataclass(frozen=True)
class PromptBundle:
    main_prompt: str
    negative_prompt: str
    negative_prompt_terms: list[str]
    prompt_hash: str
    first_frame_prompt: str | None = None
    last_frame_prompt: str | None = None


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    request_id: str
    run_id: str
    status: str
    error_message: str
    video_bytes: bytes | None = None
    temporary_video_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ArtifactPaths:
    output_dir: Path
    video: Path | None
    storyboard: Path
    prompt: Path
    config: Path
    generation_record: Path
    manifest: Path
    log: Path


@dataclass(frozen=True)
class ProgressEvent:
    state: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    time: str | None = None


@dataclass(frozen=True)
class AgentRunResult:
    plan: GenerationPlan | None
    shots: list[Shot]
    prompts: PromptBundle | None
    provider_result: ProviderResult | None
    artifact_paths: ArtifactPaths | None
    validation_errors: list[str]
    progress_events: list[ProgressEvent]
    exit_code: int
