# AI Video Agent CLI Prototype Design

## Goal

Build a Python command-line prototype for an AI short-video generation Agent. The prototype turns a user request into structured task data, fills in sensible defaults, collects local reference-file metadata, creates a storyboard, generates video prompts and API parameters, runs through a mock video provider, validates outputs, and saves all artifacts to the resolved output directory.

## Scope

The first version focuses on the Agent workflow and artifact generation, not real video synthesis. The video provider will be an interface with a mock implementation that writes deterministic bytes to `video_001.mp4` as a test artifact and writes `generation_record.json`. The mock video file is a placeholder artifact and is not guaranteed to be a playable MP4 in V1. This keeps the prototype useful immediately while leaving a clean replacement point for a real video-generation API.

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
- `log.txt`

If the request omits common production details, the Agent fills them in:

- Aspect ratio defaults to `9:16`.
- Duration defaults to 6 seconds.
- Style defaults to commercial advertising with realistic photographic quality.
- Short videos default to 1-3 shots for 5-8 seconds.
- Negative prompts default to no text, subtitles, logo, watermark, malformed people, product deformation, flicker, low resolution, or cluttered backgrounds.

## Architecture

The codebase will be a small Python package named `ai_video_agent` with focused modules:

- `cli.py` parses command-line input and prints progress.
- `agent.py` orchestrates the workflow.
- `models.py` defines dataclasses for requests, generation plans, prompt bundles, storyboards, provider results, and saved artifacts.
- `planner.py` extracts known fields from the raw request and applies defaults.
- `prompt_builder.py` turns the plan into a full video prompt, negative prompt, and optional first/last-frame prompts.
- `providers/video_provider.py` defines the provider protocol and mock provider.
- `validators.py` checks output files and metadata.
- `artifact_writer.py` writes storyboard, prompt, config, log, and video artifacts.

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
  "motion_strength": "medium",
  "camera_motion": "slow push in",
  "prompt_file": "prompt.txt",
  "negative_prompt": "不要文字，不要字幕，不要 logo，不要水印"
}
```

`generation_record.json` stores provider-facing run metadata:

```json
{
  "provider": "mock",
  "request_id": "mock-{run_id}",
  "run_id": "12-character hash",
  "request_hash": "sha256(raw request + explicit overrides)",
  "prompt_hash": "sha256(prompt bundle)",
  "duration": 6,
  "aspect_ratio": "9:16",
  "status": "succeeded",
  "error_message": "",
  "output_file": "video_001.mp4"
}
```

For reproducibility, the Agent computes:

- `request_hash` from the raw request plus explicit CLI overrides.
- `prompt_hash` from `PromptBundle`.
- `run_id = sha256(raw_request + structured_config).hexdigest()[:12]`.

## Error Handling

The CLI should fail clearly when:

- The request is empty.
- The output directory cannot be created.
- A provided reference path does not exist.
- The provider fails.
- Expected artifacts are missing or empty.

The mock provider should be deterministic and not require network access. V1 does not retry provider failures. It records the error in `generation_record.json` when possible, prints `FAILED`, and exits with a non-zero status. Real provider errors will later be mapped to retry actions such as shortening prompts, adjusting unsupported duration or aspect ratio, and lowering motion strength.

## Testing

Use Python's built-in `unittest` so the empty repository does not need dependency installation. Tests will cover:

- Default planning values for sparse requests.
- Extraction of aspect ratio, duration, output path, and topic hints from Chinese requests.
- `--output-dir` takes priority over natural-language output paths.
- Explicit `--duration` and `--aspect-ratio` override natural-language extraction.
- Reference metadata collection records filename, extension, size, and file type without visual analysis.
- Storyboard shot count selection by duration.
- Prompt generation includes concrete visual, motion, parameter, and negative-prompt sections.
- `prompt.txt`, `config.json`, and `generation_record.json` keep separate responsibilities.
- End-to-end CLI/Agent run writes all expected artifacts.
- Progress states are emitted in the expected order for a successful run.
- Provider failure emits `FAILED`, writes the available error record, and does not retry.
- Validation fails for missing or empty files.

## Out Of Scope For V1

- Real AI video generation API integration.
- Browser or web chat interface.
- Image/video computer vision analysis.
- Web search and external trend research.
- Real MP4 encoding.
- Multi-turn conversation memory.

These are intentionally excluded from the first prototype so the Agent control flow and artifact contracts can be proven first.
