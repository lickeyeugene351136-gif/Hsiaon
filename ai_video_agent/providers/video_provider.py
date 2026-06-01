from __future__ import annotations

from ..models import GenerationPlan, PromptBundle, ProviderResult


class MockVideoProvider:
    provider_name = "mock"

    def generate(
        self,
        plan: GenerationPlan,
        prompts: PromptBundle,
        config: dict[str, object],
    ) -> ProviderResult:
        video_bytes = (
            f"mock-video\nrun_id={plan.run_id}\nprompt_hash={prompts.prompt_hash}\n"
        ).encode("utf-8")
        return ProviderResult(
            provider=self.provider_name,
            request_id=f"mock-{plan.run_id}",
            run_id=plan.run_id,
            status="succeeded",
            error_message="",
            video_bytes=video_bytes,
            metadata={
                "duration": plan.duration,
                "aspect_ratio": plan.aspect_ratio,
            },
        )


class FailingVideoProvider:
    provider_name = "mock"

    def __init__(self, error_message: str = "provider failed") -> None:
        self.error_message = error_message

    def generate(
        self,
        plan: GenerationPlan,
        prompts: PromptBundle,
        config: dict[str, object],
    ) -> ProviderResult:
        return ProviderResult(
            provider=self.provider_name,
            request_id=f"mock-{plan.run_id}",
            run_id=plan.run_id,
            status="failed",
            error_message=self.error_message,
            metadata={
                "duration": plan.duration,
                "aspect_ratio": plan.aspect_ratio,
            },
        )
