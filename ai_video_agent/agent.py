from __future__ import annotations

from .artifact_writer import ArtifactWriter
from .models import (
    AgentError,
    AgentInput,
    AgentRunResult,
    EXIT_PROVIDER_ERROR,
    EXIT_SUCCESS,
    EXIT_VALIDATION_ERROR,
    ProgressEvent,
)
from .planner import build_generation_plan, create_storyboard
from .prompt_builder import build_config, build_prompt_bundle
from .providers.video_provider import MockVideoProvider
from .validators import validate_provider_failure_artifacts, validate_success_artifacts


class VideoAgent:
    def __init__(self, provider: object | None = None) -> None:
        self.provider = provider or MockVideoProvider()

    def run(self, agent_input: AgentInput) -> AgentRunResult:
        events: list[ProgressEvent] = []

        def emit(state: str, message: str, **data: object) -> None:
            events.append(ProgressEvent(state=state, message=message, data=data))

        emit("RECEIVED_REQUEST", "Received request")
        try:
            plan = build_generation_plan(agent_input)
            emit("RESOLVED_OUTPUT_DIR", "Resolved output directory", output_dir=str(plan.output_dir))
            emit(
                "COLLECTED_REFERENCES",
                "Collected reference metadata",
                count=len(plan.reference_metadata),
                warnings=plan.reference_warnings,
            )
            emit(
                "BUILT_PLAN",
                "Built generation plan",
                duration=plan.duration,
                aspect_ratio=plan.aspect_ratio,
                run_id=plan.run_id,
            )
            shots = create_storyboard(plan)
            emit("CREATED_STORYBOARD", "Created storyboard", shot_count=len(shots))
            prompts = build_prompt_bundle(plan, shots)
            config = build_config(plan, prompts)
            emit("BUILT_PROMPTS", "Built prompts", prompt_hash=prompts.prompt_hash)
        except AgentError as exc:
            emit("FAILED", exc.message, exit_code=exc.exit_code)
            return AgentRunResult(
                plan=None,
                shots=[],
                prompts=None,
                provider_result=None,
                artifact_paths=None,
                validation_errors=[exc.message],
                progress_events=events,
                exit_code=exc.exit_code,
            )

        provider_result = self.provider.generate(plan, prompts, config)
        emit("CALLED_PROVIDER", "Called video provider", status=provider_result.status)
        writer = ArtifactWriter(plan.output_dir)

        if provider_result.status != "succeeded":
            emit("FAILED", provider_result.error_message or "Provider failed")
            artifact_paths = writer.write_provider_failure(
                plan, shots, prompts, config, provider_result, events
            )
            validation_errors = validate_provider_failure_artifacts(artifact_paths)
            exit_code = EXIT_PROVIDER_ERROR if not validation_errors else EXIT_VALIDATION_ERROR
            return AgentRunResult(
                plan=plan,
                shots=shots,
                prompts=prompts,
                provider_result=provider_result,
                artifact_paths=artifact_paths,
                validation_errors=validation_errors,
                progress_events=events,
                exit_code=exit_code,
            )

        emit("WROTE_ARTIFACTS", "Writing artifacts")
        emit("VALIDATED_OUTPUTS", "Validating outputs")
        emit("DONE", "Short video generation prototype completed")
        artifact_paths = writer.write_success(plan, shots, prompts, config, provider_result, events)
        validation_errors = validate_success_artifacts(artifact_paths)
        if validation_errors:
            events.append(
                ProgressEvent(
                    state="FAILED",
                    message="Validation failed",
                    data={"errors": validation_errors},
                )
            )
            return AgentRunResult(
                plan=plan,
                shots=shots,
                prompts=prompts,
                provider_result=provider_result,
                artifact_paths=artifact_paths,
                validation_errors=validation_errors,
                progress_events=events,
                exit_code=EXIT_VALIDATION_ERROR,
            )
        return AgentRunResult(
            plan=plan,
            shots=shots,
            prompts=prompts,
            provider_result=provider_result,
            artifact_paths=artifact_paths,
            validation_errors=[],
            progress_events=events,
            exit_code=EXIT_SUCCESS,
        )
