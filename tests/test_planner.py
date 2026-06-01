import tempfile
import unittest
from pathlib import Path

from ai_video_agent.models import AgentInput, AgentError
from ai_video_agent.planner import (
    build_generation_plan,
    collect_reference_metadata,
    create_storyboard,
    duration_to_shot_count,
    extract_natural_output_dir,
    normalize_aspect_ratio,
    resolve_output_dir,
)


class PlannerTests(unittest.TestCase):
    def test_sparse_chinese_request_uses_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent_input = AgentInput(
                raw_request="生成一条护肤成分科技感视频",
                cwd=Path(tmp),
            )

            plan = build_generation_plan(agent_input)

            self.assertEqual(plan.aspect_ratio, "9:16")
            self.assertEqual(plan.duration, 6)
            self.assertEqual(plan.style, "commercial advertising")
            self.assertEqual(plan.visual_quality, "realistic photographic quality")
            self.assertEqual(plan.tone, "clean, premium, high-end")
            self.assertEqual(plan.render_type, "realistic")
            self.assertEqual(plan.shot_count, 2)
            self.assertTrue(str(plan.output_dir).startswith(str((Path(tmp) / "runs").resolve())))
            self.assertEqual(len(plan.run_id), 12)
            self.assertEqual(len(plan.request_hash), 64)

    def test_explicit_output_dir_takes_priority_over_natural_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            agent_input = AgentInput(
                raw_request="生成一条视频，输出到 natural/out",
                output_dir=Path("cli/out"),
                cwd=cwd,
            )

            output_dir = resolve_output_dir(agent_input)

            self.assertEqual(output_dir, (cwd / "cli" / "out").resolve())

    def test_extracts_natural_output_paths_from_supported_triggers(self):
        cases = [
            ("输出到 output/a，风格高级", Path("output/a")),
            ("保存到 output/b。", Path("output/b")),
            ("放到 output/c; ok", Path("output/c")),
            ("生成到 output/d\n下一行", Path("output/d")),
            ("导出到 output/e more", Path("output/e")),
            ("输出路径为 output/f", Path("output/f")),
            ("保存路径为 output/g", Path("output/g")),
        ]

        for raw_request, expected in cases:
            with self.subTest(raw_request=raw_request):
                self.assertEqual(extract_natural_output_dir(raw_request), expected)

    def test_normalizes_supported_aspect_ratios_and_rejects_unknown(self):
        self.assertEqual(normalize_aspect_ratio(None, "竖屏视频"), "9:16")
        self.assertEqual(normalize_aspect_ratio(None, "横屏视频"), "16:9")
        self.assertEqual(normalize_aspect_ratio(None, "方形视频"), "1:1")
        self.assertEqual(normalize_aspect_ratio("4:5", ""), "4:5")

        with self.assertRaises(AgentError) as ctx:
            normalize_aspect_ratio("3:2", "")

        self.assertEqual(ctx.exception.exit_code, 1)

    def test_duration_rules_are_explicit(self):
        self.assertEqual(duration_to_shot_count(4), 1)
        self.assertEqual(duration_to_shot_count(6), 2)
        self.assertEqual(duration_to_shot_count(12), 3)
        self.assertEqual(duration_to_shot_count(20), 5)

        with self.assertRaises(AgentError) as ctx:
            duration_to_shot_count(31)

        self.assertEqual(ctx.exception.exit_code, 1)

    def test_unsafe_output_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(AgentError) as ctx:
                resolve_output_dir(
                    AgentInput(
                        raw_request="生成视频",
                        output_dir=Path("..") / "outside",
                        cwd=Path(tmp),
                    )
                )

        self.assertEqual(ctx.exception.exit_code, 2)

    def test_explicit_missing_reference_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent_input = AgentInput(
                raw_request="生成视频",
                reference_paths=[Path("missing.png")],
                cwd=Path(tmp),
            )

            with self.assertRaises(AgentError) as ctx:
                collect_reference_metadata(agent_input)

        self.assertEqual(ctx.exception.exit_code, 1)

    def test_weak_natural_reference_missing_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent_input = AgentInput(
                raw_request="参考图在 missing.png，输出到 out",
                cwd=Path(tmp),
            )

            metadata, warnings = collect_reference_metadata(agent_input)

            self.assertEqual(metadata, [])
            self.assertTrue(any("missing.png" in warning for warning in warnings))

    def test_reference_metadata_records_file_facts(self):
        with tempfile.TemporaryDirectory() as tmp:
            ref = Path(tmp) / "ref.png"
            ref.write_bytes(b"abc")

            metadata, warnings = collect_reference_metadata(
                AgentInput(
                    raw_request="生成视频",
                    reference_paths=[ref],
                    cwd=Path(tmp),
                )
            )

            self.assertEqual(warnings, [])
            self.assertEqual(metadata[0].filename, "ref.png")
            self.assertEqual(metadata[0].extension, ".png")
            self.assertEqual(metadata[0].size_bytes, 3)
            self.assertEqual(metadata[0].file_type, "image")

    def test_storyboard_uses_fixed_shot_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_generation_plan(
                AgentInput(
                    raw_request="生成一条 9:16 护肤成分动画",
                    duration=6,
                    cwd=Path(tmp),
                )
            )

            shots = create_storyboard(plan)

            self.assertEqual(len(shots), 2)
            self.assertEqual(shots[0].index, 1)
            self.assertGreater(shots[0].duration, 0)
            self.assertTrue(shots[0].scene)
            self.assertTrue(shots[0].subject)
            self.assertTrue(shots[0].action)
            self.assertTrue(shots[0].shot_size)
            self.assertTrue(shots[0].composition)
            self.assertTrue(shots[0].camera_motion)
            self.assertTrue(shots[0].transition)
            self.assertTrue(shots[0].lighting)
            self.assertTrue(shots[0].purpose)
            self.assertTrue(shots[0].prompt)


if __name__ == "__main__":
    unittest.main()
