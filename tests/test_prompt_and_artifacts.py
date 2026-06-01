import json
import tempfile
import unittest
from pathlib import Path

from ai_video_agent.artifact_writer import ArtifactWriter
from ai_video_agent.models import AgentInput
from ai_video_agent.planner import build_generation_plan, create_storyboard
from ai_video_agent.prompt_builder import build_config, build_prompt_bundle
from ai_video_agent.providers.video_provider import FailingVideoProvider, MockVideoProvider
from ai_video_agent.validators import (
    validate_provider_failure_artifacts,
    validate_success_artifacts,
)


class PromptAndArtifactTests(unittest.TestCase):
    def test_prompt_bundle_and_config_keep_separate_responsibilities(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_generation_plan(
                AgentInput(raw_request="生成一条护肤成分动画", cwd=Path(tmp))
            )
            shots = create_storyboard(plan)

            bundle = build_prompt_bundle(plan, shots)
            config = build_config(plan, bundle)

            self.assertIn("【视频主题】", bundle.main_prompt)
            self.assertIn("【负面提示词】", bundle.negative_prompt)
            self.assertIn("不要文字", bundle.negative_prompt)
            self.assertEqual(len(bundle.prompt_hash), 64)
            self.assertEqual(config["prompt_file"], "prompt.txt")
            self.assertEqual(config["negative_prompt_file"], "prompt.txt")
            self.assertEqual(config["negative_prompt_terms"], plan.negative_prompt_terms)
            self.assertNotIn("main_prompt", config)

    def test_success_artifacts_include_manifest_without_recursive_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan, shots, bundle, config = self._build_plan_parts(tmp)
            provider_result = MockVideoProvider().generate(plan, bundle, config)

            paths = ArtifactWriter(plan.output_dir).write_success(
                plan=plan,
                shots=shots,
                prompts=bundle,
                config=config,
                provider_result=provider_result,
                progress_events=[],
            )

            self.assertTrue(paths.video.exists())
            self.assertEqual(validate_success_artifacts(paths), [])

            manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
            self.assertIn("video_001.mp4", manifest["files"])
            self.assertIsNone(manifest["files"]["manifest.json"]["sha256"])
            self.assertEqual(
                manifest["files"]["manifest.json"]["hash_policy"],
                "omitted-for-self-to-avoid-recursive-hash",
            )
            self.assertEqual(len(manifest["files"]["prompt.txt"]["sha256"]), 64)

            record = json.loads(paths.generation_record.read_text(encoding="utf-8"))
            self.assertEqual(record["status"], "succeeded")
            self.assertEqual(record["output_file"], "video_001.mp4")

    def test_provider_failure_artifacts_omit_video_and_validate_failure_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan, shots, bundle, config = self._build_plan_parts(tmp)
            provider_result = FailingVideoProvider("network unavailable").generate(
                plan, bundle, config
            )

            paths = ArtifactWriter(plan.output_dir).write_provider_failure(
                plan=plan,
                shots=shots,
                prompts=bundle,
                config=config,
                provider_result=provider_result,
                progress_events=[],
            )

            self.assertIsNone(paths.video)
            self.assertFalse((plan.output_dir / "video_001.mp4").exists())
            self.assertEqual(validate_provider_failure_artifacts(paths), [])

            manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
            self.assertNotIn("video_001.mp4", manifest["files"])
            self.assertIsNone(manifest["files"]["manifest.json"]["sha256"])

            record = json.loads(paths.generation_record.read_text(encoding="utf-8"))
            self.assertEqual(record["status"], "failed")
            self.assertEqual(record["error_message"], "network unavailable")

    def test_success_validation_rejects_missing_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan, shots, bundle, config = self._build_plan_parts(tmp)
            provider_result = MockVideoProvider().generate(plan, bundle, config)
            paths = ArtifactWriter(plan.output_dir).write_success(
                plan, shots, bundle, config, provider_result, []
            )
            paths.video.unlink()

            errors = validate_success_artifacts(paths)

            self.assertTrue(any("video_001.mp4" in error for error in errors))

    def test_failure_validation_rejects_unexpected_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan, shots, bundle, config = self._build_plan_parts(tmp)
            provider_result = FailingVideoProvider("failed").generate(plan, bundle, config)
            paths = ArtifactWriter(plan.output_dir).write_provider_failure(
                plan, shots, bundle, config, provider_result, []
            )
            (plan.output_dir / "video_001.mp4").write_bytes(b"unexpected")

            errors = validate_provider_failure_artifacts(paths)

            self.assertTrue(any("must not exist" in error for error in errors))

    def _build_plan_parts(self, tmp):
        plan = build_generation_plan(
            AgentInput(
                raw_request="生成一条 9:16 护肤成分动画，主题是胶原成分精准渗透",
                output_dir=Path("out"),
                duration=6,
                aspect_ratio="9:16",
                cwd=Path(tmp),
            )
        )
        shots = create_storyboard(plan)
        bundle = build_prompt_bundle(plan, shots)
        config = build_config(plan, bundle)
        return plan, shots, bundle, config


if __name__ == "__main__":
    unittest.main()
