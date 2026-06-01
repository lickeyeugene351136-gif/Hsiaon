# AI Video Agent CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the V1 Python CLI prototype specified in `docs/superpowers/specs/2026-06-01-ai-video-agent-cli-design.md`.

**Architecture:** Implement a dependency-free Python package named `ai_video_agent`. The package separates planning, prompt building, provider calls, artifact writing, validation, and CLI orchestration. The mock provider returns deterministic bytes and metadata; the writer owns all final filesystem artifacts.

**Tech Stack:** Python standard library, `argparse`, `dataclasses`, `json`, `hashlib`, `pathlib`, `unittest`.

---

## File Structure

- Create `ai_video_agent/__init__.py`: package marker and version.
- Create `ai_video_agent/models.py`: dataclasses and progress/exit-code constants.
- Create `ai_video_agent/planner.py`: natural-language extraction, defaults, path safety, reference metadata, hashes, storyboard creation.
- Create `ai_video_agent/prompt_builder.py`: `PromptBundle`, prompt text, config dict.
- Create `ai_video_agent/providers/__init__.py`: provider package marker.
- Create `ai_video_agent/providers/video_provider.py`: provider protocol, mock provider, failure provider for tests.
- Create `ai_video_agent/artifact_writer.py`: writes `video_001.mp4`, `storyboard.md`, `prompt.txt`, `config.json`, `generation_record.json`, `manifest.json`, `log.jsonl`.
- Create `ai_video_agent/validators.py`: success and provider-failure validation.
- Create `ai_video_agent/agent.py`: orchestration and progress events.
- Create `ai_video_agent/cli.py`: command-line interface and exit-code mapping.
- Create `tests/test_planner.py`: planner/path/metadata/rules tests.
- Create `tests/test_prompt_and_artifacts.py`: prompt, config, manifest, writer tests.
- Create `tests/test_agent_cli.py`: end-to-end success/failure/CLI tests.

---

### Task 1: Planning Rules And Data Models

**Files:**
- Create: `ai_video_agent/__init__.py`
- Create: `ai_video_agent/models.py`
- Create: `ai_video_agent/planner.py`
- Test: `tests/test_planner.py`

- [ ] **Step 1: Write failing planner tests**

Create tests that assert sparse Chinese requests default to 9:16, 6 seconds, structured style fields, 2 shots, and safe output resolution. Include extraction tests for `--output-dir` priority, natural-language output triggers, aspect ratio normalization, duration rejection over 30 seconds, unsafe path rejection, explicit reference failure, weak reference warning, and reference metadata.

Run: `python -m unittest tests.test_planner -v`
Expected: FAIL because `ai_video_agent` modules do not exist.

- [ ] **Step 2: Implement minimal models and planner**

Implement dataclasses: `AgentInput`, `ReferenceMetadata`, `GenerationPlan`, `Shot`, `ProgressEvent`, and `AgentError`. Implement `build_generation_plan`, `create_storyboard`, `resolve_output_dir`, `extract_natural_output_dir`, `normalize_aspect_ratio`, `duration_to_shot_count`, `collect_reference_metadata`, `compute_request_hash`, and `compute_run_id`.

- [ ] **Step 3: Verify planner tests pass**

Run: `python -m unittest tests.test_planner -v`
Expected: PASS.

---

### Task 2: Prompts, Provider Result, Artifacts, And Validation

**Files:**
- Create: `ai_video_agent/prompt_builder.py`
- Create: `ai_video_agent/providers/__init__.py`
- Create: `ai_video_agent/providers/video_provider.py`
- Create: `ai_video_agent/artifact_writer.py`
- Create: `ai_video_agent/validators.py`
- Test: `tests/test_prompt_and_artifacts.py`

- [ ] **Step 1: Write failing prompt and artifact tests**

Create tests that assert `prompt.txt` contains model-facing prose and negative prompt text; `config.json` contains structured fields and `negative_prompt_terms` but not duplicated full prompt prose; `generation_record.json` contains provider metadata; `manifest.json` records hashes for other files but `manifest.json.files["manifest.json"].sha256 is None`; success validation requires video; provider-failure validation requires no video and failed record.

Run: `python -m unittest tests.test_prompt_and_artifacts -v`
Expected: FAIL because prompt/artifact/validator modules do not exist.

- [ ] **Step 2: Implement prompts, provider, writer, validators**

Implement `build_prompt_bundle`, `build_config`, `MockVideoProvider.generate`, `FailingVideoProvider.generate`, `ArtifactWriter.write_success`, `ArtifactWriter.write_provider_failure`, `validate_success_artifacts`, and `validate_provider_failure_artifacts`.

- [ ] **Step 3: Verify prompt and artifact tests pass**

Run: `python -m unittest tests.test_prompt_and_artifacts -v`
Expected: PASS.

---

### Task 3: Agent Orchestration And CLI

**Files:**
- Create: `ai_video_agent/agent.py`
- Create: `ai_video_agent/cli.py`
- Test: `tests/test_agent_cli.py`

- [ ] **Step 1: Write failing Agent and CLI tests**

Create tests that assert successful runs emit ordered states ending in `DONE`, write all success artifacts, return exit code `0`, and print final artifact paths. Add provider-failure tests that assert `FAILED`, exit code `3`, no `video_001.mp4`, and available debug artifacts. Add CLI parser tests for `--output-dir`, `--reference`, `--duration`, and `--aspect-ratio`.

Run: `python -m unittest tests.test_agent_cli -v`
Expected: FAIL because `agent.py` and `cli.py` do not exist.

- [ ] **Step 2: Implement Agent and CLI**

Implement `VideoAgent.run`, progress logging, provider failure handling, and `main(argv=None)`. CLI maps input/path/provider/validation errors to exit codes `1/2/3/4`.

- [ ] **Step 3: Verify Agent and CLI tests pass**

Run: `python -m unittest tests.test_agent_cli -v`
Expected: PASS.

---

### Task 4: Full Verification And Demo Run

**Files:**
- Modify as needed: `ai_video_agent/*.py`
- Modify as needed: `tests/*.py`

- [ ] **Step 1: Run the full test suite**

Run: `python -m unittest discover -v`
Expected: PASS.

- [ ] **Step 2: Run a real CLI demo**

Run: `python -m ai_video_agent.cli "帮我生成一条 9:16 竖屏护肤成分动画，主题是胶原成分精准渗透" --output-dir output/skincare_video --duration 6 --aspect-ratio 9:16`
Expected: Exit code `0`; output directory contains `video_001.mp4`, `storyboard.md`, `prompt.txt`, `config.json`, `generation_record.json`, `manifest.json`, and `log.jsonl`.

- [ ] **Step 3: Inspect generated JSON artifacts**

Run: `python -m json.tool output/skincare_video/config.json`
Expected: Valid JSON with structured generation fields.

Run: `python -m json.tool output/skincare_video/generation_record.json`
Expected: Valid JSON with `status` set to `succeeded`.

Run: `python -m json.tool output/skincare_video/manifest.json`
Expected: Valid JSON with `manifest.json.files["manifest.json"].sha256` set to `null`.

- [ ] **Step 4: Check git status**

Run: `git status --short`
Expected: Only intentional implementation and generated demo files are present. Do not stage generated demo output unless explicitly requested.

---

## Self-Review Notes

- Spec coverage: tasks cover output-dir priority, path safety, reference metadata, aspect ratios, duration-to-shot mapping, structured style, shot schema, prompt/config separation, provider/writer separation, manifest self-hash, success/failure validation, progress states, exit codes, and mock provider behavior.
- Marker scan: no unresolved implementation markers remain in this plan.
- Type consistency: `GenerationPlan`, `PromptBundle`, `ProviderResult`, `ArtifactPaths`, `AgentRunResult`, and validation functions are named consistently across tasks.
