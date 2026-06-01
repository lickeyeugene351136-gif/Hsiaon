from __future__ import annotations

import argparse
from pathlib import Path

from .agent import VideoAgent
from .models import AgentInput


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI short-video Agent CLI prototype")
    parser.add_argument("request", help="Natural-language video generation request")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--reference", type=Path, action="append", default=[])
    parser.add_argument("--duration", type=int, default=None)
    parser.add_argument("--aspect-ratio", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = VideoAgent().run(
        AgentInput(
            raw_request=args.request,
            output_dir=args.output_dir,
            reference_paths=args.reference,
            duration=args.duration,
            aspect_ratio=args.aspect_ratio,
            cwd=Path.cwd(),
        )
    )
    for event in result.progress_events:
        print(event.state)
    if result.artifact_paths:
        print(f"output_dir: {result.artifact_paths.output_dir}")
        if result.artifact_paths.video:
            print(f"video: {result.artifact_paths.video}")
        print(f"storyboard: {result.artifact_paths.storyboard}")
        print(f"prompt: {result.artifact_paths.prompt}")
        print(f"config: {result.artifact_paths.config}")
        print(f"generation_record: {result.artifact_paths.generation_record}")
        print(f"manifest: {result.artifact_paths.manifest}")
        print(f"log: {result.artifact_paths.log}")
    if result.validation_errors:
        for error in result.validation_errors:
            print(f"error: {error}")
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
