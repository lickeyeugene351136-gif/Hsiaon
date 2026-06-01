import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from ai_video_agent.agent import VideoAgent
from ai_video_agent.cli import main
from ai_video_agent.models import AgentInput
from ai_video_agent.providers.video_provider import FailingVideoProvider, MockVideoProvider


class AgentCliTests(unittest.TestCase):
    def test_agent_success_emits_ordered_progress_and_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = VideoAgent(provider=MockVideoProvider()).run(
                AgentInput(
                    raw_request="生成一条 9:16 护肤成分动画，主题是胶原成分精准渗透",
                    output_dir=Path("out"),
                    duration=6,
                    aspect_ratio="9:16",
                    cwd=Path(tmp),
                )
            )

            states = [event.state for event in result.progress_events]

            self.assertEqual(result.exit_code, 0)
            self.assertEqual(states[0], "RECEIVED_REQUEST")
            self.assertIn("VALIDATED_OUTPUTS", states)
            self.assertEqual(states[-1], "DONE")
            self.assertTrue(result.artifact_paths.video.exists())
            self.assertTrue(result.artifact_paths.manifest.exists())

    def test_agent_provider_failure_writes_debug_artifacts_without_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = VideoAgent(provider=FailingVideoProvider("quota exceeded")).run(
                AgentInput(
                    raw_request="生成一条护肤成分动画",
                    output_dir=Path("out"),
                    cwd=Path(tmp),
                )
            )

            states = [event.state for event in result.progress_events]

            self.assertEqual(result.exit_code, 3)
            self.assertEqual(states[-1], "FAILED")
            self.assertIsNone(result.artifact_paths.video)
            self.assertFalse((Path(tmp) / "out" / "video_001.mp4").exists())
            self.assertTrue(result.artifact_paths.prompt.exists())
            record = json.loads(result.artifact_paths.generation_record.read_text(encoding="utf-8"))
            self.assertEqual(record["status"], "failed")
            self.assertEqual(record["error_message"], "quota exceeded")

    def test_cli_success_returns_zero_and_prints_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "cli_out"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "生成一条护肤成分动画",
                        "--output-dir",
                        str(output_dir),
                        "--duration",
                        "6",
                        "--aspect-ratio",
                        "9:16",
                    ]
                )

            printed = stdout.getvalue()

            self.assertEqual(exit_code, 0)
            self.assertIn("DONE", printed)
            self.assertIn("video_001.mp4", printed)
            self.assertTrue((output_dir / "manifest.json").exists())

    def test_cli_input_error_returns_one(self):
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(["", "--duration", "6"])

        self.assertEqual(exit_code, 1)
        self.assertIn("FAILED", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
