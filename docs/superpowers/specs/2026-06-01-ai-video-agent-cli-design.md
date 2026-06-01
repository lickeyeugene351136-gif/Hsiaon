# AI Video Agent CLI Prototype Design

## Goal

Build a Python command-line prototype for an AI short-video generation Agent. The prototype turns a user request into structured task data, fills in sensible defaults, collects local reference-file metadata, creates a storyboard, generates video prompts and API parameters, runs through a mock video provider, validates outputs, and saves all artifacts to the resolved output directory.

## Scope

The first version focuses on the Agent workflow and artifact generation, not real video synthesis. The video provider will be an interface with a mock implementation that returns deterministic video bytes and provider metadata. `artifact_writer.py` writes those bytes to `video_001.mp4` and writes the final artifact set. The mock video file is a placeholder artifact and is not guaranteed to be a playable MP4 in V1. This keeps the prototype useful immediately while leaving a clean replacement point for a real video-generation API.

## User Experience

The user runs a CLI command with a natural-language request and optional paths:

```powershell
python -m ai_video_agent.cli "帮我生成一条 9:16 竖屏护肤成分动画，主题是胶原成分精准渗透，输出到 output/skincare_video"
```

The CLI also supports explicit arguments that override natural-language extraction:

```powershell
python -m ai_video_agent.cli "帮我生成一条护肤成分动画" --output-dir output/skincare_video --reference input/ref.png --duration 6 --aspect-ratio 9:16
```

Output directory resolution has this priority:

1. Explicit `--output-dir`.
2. A path extracted from natural language, such as `输出到 output/skincare_video`.
3. A timestamped run directory under `runs/{timestamp}` when no path is provided.

The command prints progress states and returns the final artifact paths:

- `video_001.mp4`
- `storyboard.md`
- `prompt.txt`
- `config.json`
- `generation_record.json`
- `manifest.json`
- `log.jsonl`

If the request omits common production details, the Agent fills them in:

- Aspect ratio defaults to `9:16`.
- Duration defaults to 6 seconds.
- Style defaults to structured commercial advertising fields: `style = "commercial advertising"`, `visual_quality = "realistic photographic quality"`, `tone = "clean, premium, high-end"`, and `render_type = "realistic"`.
- Short videos from 5-8 seconds default to 2 shots, with a maximum of 3.
- Negative prompts default to no text, subtitles, logo, watermark, malformed people, product deformation, flicker, low resolution, or cluttered backgrounds.

## Architecture

The codebase will be a small Python package named `ai_video_agent` with focused modules:

- `cli.py` parses command-line input and prints progress.
- `agent.py` orchestrates the workflow.
- `models.py` defines dataclasses for requests, generation plans, prompt bundles, storyboards, provider results, and saved artifacts.
- `planner.py` extracts known fields from the raw request and applies defaults.
- `prompt_builder.py` turns the plan into a full video prompt, negative prompt, and optional first/last-frame prompts.
- `providers/video_provider.py` defines the provider protocol and mock provider. Providers return generated video bytes or a temporary file path plus provider metadata; they do not manage the final artifact directory.
- `validators.py` checks output files and metadata.
- `artifact_writer.py` writes all final artifacts into the resolved output directory: storyboard, prompt, config, generation record, manifest, structured log, and video artifact when available.

The Agent flow is:

1. Parse the user request.
2. Resolve the output directory.
3. Collect metadata for provided reference paths that exist locally, such as filename, extension, size, and file type. V1 does not perform visual content analysis.
4. Build a generation plan with defaults.
5. Create storyboard shots.
6. Build prompts and API-style config.
7. Call the video provider.
8. Save artifacts.
9. Validate that expected files exist and are non-empty.
10. Print final paths.

The CLI prints stable progress states:

- `RECEIVED_REQUEST`
- `RESOLVED_OUTPUT_DIR`
- `COLLECTED_REFERENCES`
- `BUILT_PLAN`
- `CREATED_STORYBOARD`
- `BUILT_PROMPTS`
- `CALLED_PROVIDER`
- `WROTE_ARTIFACTS`
- `VALIDATED_OUTPUTS`
- `DONE`
- `FAILED`

## Additional V1 Decisions

### Output Paths

Natural-language output paths are extracted only from these trigger phrases:

- `输出到`
- `保存到`
- `放到`
- `生成到`
- `导出到`
- `输出路径为`
- `保存路径为`

The extracted path ends at whitespace, a Chinese comma, a Chinese period, a semicolon, or a newline. V1 supports relative paths and explicit absolute paths. Unsafe paths are rejected, including path traversal such as `../`, repository-parent writes through relative paths, and system-sensitive absolute directories such as `/`, `/bin`, `/etc`, `/usr`, `C:\Windows`, and `C:\Program Files`. If the resolved output directory already exists, V1 overwrites the known artifact filenames in that directory. The fallback `runs/{timestamp}` path prevents accidental collisions when no output path is provided.

Explicit `--reference` paths must exist or the run fails with an input error. Weakly extracted natural-language paths that look like references but do not exist are recorded as warnings and do not fail the run, because phrases such as `参考某某风格` may not be file paths.

### Supported Aspect Ratios

V1 supports these aspect ratios:

- `9:16`
- `16:9`
- `1:1`
- `4:5`

Chinese terms are normalized as:

- `竖屏` -> `9:16`
- `横屏` -> `16:9`
- `方图` or `方形` -> `1:1`

Unsupported ratios fail clearly.

### Duration And Shot Count

V1 maps duration to storyboard shot count as follows:

- `0-4s`: 1 shot.
- `5-8s`: 2 shots by default, with a maximum of 3.
- `9-15s`: 3 shots by default, with a maximum of 5.
- `16-30s`: 5 shots by default, with a maximum of 8.
- `>30s`: rejected in V1.

Each `Shot` has this schema:

- `index`
- `duration`
- `scene`
- `subject`
- `action`
- `shot_size`
- `composition`
- `camera_motion`
- `transition`
- `lighting`
- `purpose`
- `prompt`

### Logs And Exit Codes

V1 writes `log.jsonl`, one JSON object per progress event:

```json
{"time":"2026-06-01T12:00:00+08:00","state":"BUILT_PLAN","message":"Plan created","data":{"duration":6,"aspect_ratio":"9:16"}}
```

CLI exit codes are:

- `0`: success.
- `1`: user input error.
- `2`: output, path, or file error.
- `3`: provider error.
- `4`: validation error.

### Failure Artifact Policy

If the provider fails, the Agent keeps already available debugging artifacts:

- `storyboard.md`
- `prompt.txt`
- `config.json`
- `generation_record.json` with `status = "failed"`
- `manifest.json`
- `log.jsonl`

It does not write `video_001.mp4` on provider failure. The CLI prints `FAILED` and exits with code `3`.

## Data Flow

The CLI creates an `AgentInput` with:

- `raw_request`
- optional `output_dir`
- optional `reference_paths`
- optional explicit `duration`
- optional explicit `aspect_ratio`

`planner.py` creates a `GenerationPlan` with:

- `topic`
- `purpose`
- `aspect_ratio`
- `duration`
- `style`
- `visual_quality`
- `tone`
- `render_type`
- `shot_count`
- `motion_strength`
- `camera_motion`
- `output_dir`
- `reference_metadata`
- `negative_prompt_terms`
- `request_hash`

`prompt_builder.py` creates a `PromptBundle` with:

- `main_prompt`
- `negative_prompt`
- `negative_prompt_terms`
- optional `first_frame_prompt`
- optional `last_frame_prompt`
- `prompt_hash`

`VideoAgent.run()` returns an `AgentRunResult` containing:

- generation plan fields
- storyboard shots
- prompts
- provider result
- saved artifact paths
- validation results

Artifacts are written as plain text, JSON, and deterministic mock MP4 bytes so the prototype can be inspected without special tooling.

`prompt.txt` stores the complete natural-language prompt intended for the generation model, including the main prompt, negative prompt, and optional first/last-frame prompts.

`config.json` stores structured API-style parameters, not the full prose prompt:

```json
{
  "aspect_ratio": "9:16",
  "duration": 6,
  "resolution": "1080p",
  "style": "commercial advertising",
  "visual_quality": "realistic photographic quality",
  "tone": "clean, premium, high-end",
  "render_type": "realistic",
  "motion_strength": "medium",
  "camera_motion": "slow push in",
  "prompt_file": "prompt.txt",
  "negative_prompt_file": "prompt.txt",
  "negative_prompt_terms": [
    "不要文字",
    "不要字幕",
    "不要 logo",
    "不要水印"
  ]
}
```

`generation_record.json` stores provider-facing run metadata:

```json
{
  "provider": "mock",
  "request_id": "mock-{run_id}",
  "run_id": "abc123def456",
  "request_hash": "sha256(raw request + explicit overrides)",
  "prompt_hash": "sha256(prompt bundle)",
  "duration": 6,
  "aspect_ratio": "9:16",
  "status": "succeeded",
  "error_message": "",
  "output_file": "video_001.mp4"
}
```

`manifest.json` stores the run-level artifact index:

```json
{
  "run_id": "abc123def456",
  "artifacts": {
    "video": "video_001.mp4",
    "storyboard": "storyboard.md",
    "prompt": "prompt.txt",
    "config": "config.json",
    "generation_record": "generation_record.json",
    "manifest": "manifest.json",
    "log": "log.jsonl"
  },
  "files": {
    "video_001.mp4": {
      "purpose": "Mock video bytes returned by provider",
      "size": 128,
      "sha256": "64-character lowercase sha256 hex"
    },
    "storyboard.md": {
      "purpose": "Human-readable storyboard",
      "size": 1024,
      "sha256": "64-character lowercase sha256 hex"
    },
    "prompt.txt": {
      "purpose": "Complete model-facing prompt text",
      "size": 2048,
      "sha256": "64-character lowercase sha256 hex"
    },
    "config.json": {
      "purpose": "Structured API-style generation parameters",
      "size": 512,
      "sha256": "64-character lowercase sha256 hex"
    },
    "generation_record.json": {
      "purpose": "Provider-facing run metadata",
      "size": 512,
      "sha256": "64-character lowercase sha256 hex"
    },
    "manifest.json": {
      "purpose": "Run-level artifact index",
      "size": 768,
      "sha256": "64-character lowercase sha256 hex"
    },
    "log.jsonl": {
      "purpose": "Structured progress events",
      "size": 1024,
      "sha256": "64-character lowercase sha256 hex"
    }
  },
  "created_at": "2026-06-01T12:00:00+08:00"
}
```

For reproducibility, the Agent computes:

- `request_hash` from the raw request plus explicit CLI overrides.
- `prompt_hash` from `PromptBundle`.
- `run_id = sha256(normalized_request_fields + explicit_generation_parameters).hexdigest()[:12]`.

`run_id` must not include timestamped output paths, log timestamps, or other time-varying values. This keeps the run identifier stable for the same normalized request and generation parameters, even when the default output directory changes.

## Error Handling

The CLI should fail clearly when:

- The request is empty.
- The output directory cannot be created.
- An explicit `--reference` path does not exist.
- The resolved output path is unsafe.
- The duration is above 30 seconds.
- The aspect ratio is unsupported.
- The provider fails.
- Expected artifacts are missing or empty.

The mock provider should be deterministic and not require network access. V1 does not retry provider failures. It records the error in `generation_record.json` when possible, writes available non-video artifacts, prints `FAILED`, and exits with code `3`. Real provider errors will later be mapped to retry actions such as shortening prompts, adjusting unsupported duration or aspect ratio, and lowering motion strength.

## Testing

Use Python's built-in `unittest` so the empty repository does not need dependency installation. Tests will cover:

- Default planning values for sparse requests.
- Extraction of aspect ratio, duration, output path, and topic hints from Chinese requests.
- `--output-dir` takes priority over natural-language output paths.
- Explicit `--duration` and `--aspect-ratio` override natural-language extraction.
- Natural-language output extraction supports the documented Chinese trigger phrases and stop rules.
- Unsafe output paths and path traversal are rejected.
- Missing explicit `--reference` paths fail, while missing weak natural-language reference paths produce warnings.
- Reference metadata collection records filename, extension, size, and file type without visual analysis.
- Supported aspect ratio normalization and rejection behavior.
- Duration validation and storyboard shot count selection by duration.
- Storyboard shots use the fixed `Shot` schema.
- Prompt generation includes concrete visual, motion, parameter, and negative-prompt sections.
- `prompt.txt`, `config.json`, `generation_record.json`, `manifest.json`, and `log.jsonl` keep separate responsibilities.
- `run_id` ignores timestamps and timestamped output paths.
- End-to-end CLI/Agent run writes all expected success artifacts.
- Progress states are emitted in the expected order for a successful run.
- Provider failure emits `FAILED`, writes the available error artifacts, does not write `video_001.mp4`, and does not retry.
- CLI exit codes match success, input, path/file, provider, and validation outcomes.
- Validation fails for missing or empty files.

## Out Of Scope For V1

- Real AI video generation API integration.
- Browser or web chat interface.
- Image/video computer vision analysis.
- Web search and external trend research.
- Real MP4 encoding.
- Multi-turn conversation memory.
- Concurrent runs.
- Job queues.
- Batch generation.
- User accounts or permission management.

These are intentionally excluded from the first prototype so the Agent control flow and artifact contracts can be proven first.
