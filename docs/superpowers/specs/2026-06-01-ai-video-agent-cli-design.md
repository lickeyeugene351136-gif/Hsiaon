# AI Video Agent CLI Prototype Design

## Goal

Build a Python command-line prototype for an AI short-video generation Agent. The prototype turns a user request into structured task data, fills in sensible defaults, creates a storyboard, generates video prompts and API parameters, runs through a mock video provider, validates outputs, and saves all artifacts to the requested output directory.

## Scope

The first version focuses on the Agent workflow and artifact generation, not real video synthesis. The video provider will be an interface with a mock implementation that writes a deterministic `video_001.mp4` test artifact and a generation record. This keeps the prototype useful immediately while leaving a clean replacement point for a real video-generation API.

## User Experience

The user runs a CLI command with a natural-language request and optional paths:

```powershell
python -m ai_video_agent.cli "帮我生成一条 9:16 竖屏护肤成分动画，主题是胶原成分精准渗透，输出到 output/skincare_video"
```

The command prints progress states and returns the final artifact paths:

- `video_001.mp4`
- `storyboard.md`
- `prompt.txt`
- `config.json`
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
- `models.py` defines dataclasses for requests, storyboards, prompts, provider results, and saved artifacts.
- `planner.py` extracts known fields from the raw request and applies defaults.
- `prompt_builder.py` turns the plan into a full video prompt, negative prompt, and optional first/last-frame prompts.
- `providers/video_provider.py` defines the provider protocol and mock provider.
- `validators.py` checks output files and metadata.
- `artifact_writer.py` writes storyboard, prompt, config, log, and video artifacts.

The Agent flow is:

1. Parse the user request.
2. Resolve the output directory.
3. Analyze any provided reference paths that exist locally.
4. Build a generation plan with defaults.
5. Create storyboard shots.
6. Build prompts and API-style config.
7. Call the video provider.
8. Save artifacts.
9. Validate that expected files exist and are non-empty.
10. Print final paths.

## Data Flow

The CLI creates an `AgentInput` with:

- `raw_request`
- optional `output_dir`
- optional `reference_paths`

`VideoAgent.run()` returns an `AgentRunResult` containing:

- extracted plan fields
- storyboard shots
- prompts
- provider result
- saved artifact paths
- validation results

Artifacts are written as plain text, JSON, and deterministic mock MP4 bytes so the prototype can be inspected without special tooling.

## Error Handling

The CLI should fail clearly when:

- The request is empty.
- The output directory cannot be created.
- A provided reference path does not exist.
- The provider fails.
- Expected artifacts are missing or empty.

The mock provider should be deterministic and not require network access. Real provider errors will later be mapped to retry actions such as shortening prompts, adjusting unsupported duration or aspect ratio, and lowering motion strength.

## Testing

Use Python's built-in `unittest` so the empty repository does not need dependency installation. Tests will cover:

- Default planning values for sparse requests.
- Extraction of aspect ratio, duration, output path, and topic hints from Chinese requests.
- Storyboard shot count selection by duration.
- Prompt generation includes concrete visual, motion, parameter, and negative-prompt sections.
- End-to-end CLI/Agent run writes all expected artifacts.
- Validation fails for missing or empty files.

## Out Of Scope For V1

- Real AI video generation API integration.
- Browser or web chat interface.
- Image/video computer vision analysis.
- Web search and external trend research.
- Real MP4 encoding.
- Multi-turn conversation memory.

These are intentionally excluded from the first prototype so the Agent control flow and artifact contracts can be proven first.
