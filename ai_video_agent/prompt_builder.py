from __future__ import annotations

import hashlib
import json

from .models import GenerationPlan, PromptBundle, Shot


def build_prompt_bundle(plan: GenerationPlan, shots: list[Shot]) -> PromptBundle:
    shot_lines = "\n".join(
        f"{shot.index}. {shot.prompt} 时长 {shot.duration} 秒，转场 {shot.transition}。"
        for shot in shots
    )
    main_prompt = (
        "【视频主题】\n"
        f"生成一条关于 {plan.topic} 的 AI 短视频。\n\n"
        "【画面内容】\n"
        f"画面主体为 {plan.topic}，场景为干净高级的商业广告环境，"
        "背景通透、留白充足，突出成分可视化和产品质感。\n\n"
        "【镜头语言】\n"
        f"视频比例 {plan.aspect_ratio}，总时长 {plan.duration} 秒，"
        f"镜头数量 {plan.shot_count}，运镜为 {plan.camera_motion}。\n"
        f"{shot_lines}\n\n"
        "【视觉风格】\n"
        f"风格为 {plan.style}，画质为 {plan.visual_quality}，"
        f"语气为 {plan.tone}，渲染类型为 {plan.render_type}，"
        "使用明亮通透光线、浅景深和稳定构图。\n\n"
        "【动态变化】\n"
        "主体从清晰展示过渡到成分渗透和效果强化，动态柔和，节奏干净。"
    )
    negative_prompt = "【负面提示词】\n" + "，".join(plan.negative_prompt_terms)
    prompt_hash = _hash_prompt(
        {
            "main_prompt": main_prompt,
            "negative_prompt": negative_prompt,
            "first_frame_prompt": None,
            "last_frame_prompt": None,
        }
    )
    return PromptBundle(
        main_prompt=main_prompt,
        negative_prompt=negative_prompt,
        negative_prompt_terms=plan.negative_prompt_terms.copy(),
        prompt_hash=prompt_hash,
    )


def build_config(plan: GenerationPlan, bundle: PromptBundle) -> dict[str, object]:
    return {
        "aspect_ratio": plan.aspect_ratio,
        "duration": plan.duration,
        "resolution": "1080p",
        "style": plan.style,
        "visual_quality": plan.visual_quality,
        "tone": plan.tone,
        "render_type": plan.render_type,
        "motion_strength": plan.motion_strength,
        "camera_motion": plan.camera_motion,
        "prompt_file": "prompt.txt",
        "negative_prompt_file": "prompt.txt",
        "negative_prompt_terms": bundle.negative_prompt_terms,
    }


def _hash_prompt(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
