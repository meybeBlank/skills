"""
video_maker.py - 纪念视频生成

功能：
- 读取 segment info.json 获取所有图片 AI 理解
- 调用 LLM 决定图片排序和转场
- FFmpeg xfade 合成视频 + segment 自带 bgm.mp3

工作流程：
1. 读取 segment info.json
2. 构建提示词调用 LLM 排序+转场
3. 按排序顺序 + 转场 FFmpeg 合成视频
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from config import load_config, get_videos_dir, ensure_dir


LLM_SYSTEM_PROMPT = """你是一个专业的家庭纪念视频剪辑师。

任务：根据照片内容，合理排序，并选择合适的转场效果，讲述一个流畅的故事。

原则：
- 考虑时间逻辑（白天→夜晚，或具体时间顺序）
- 考虑情绪节奏（开头-发展-高潮）
- 考虑场景连贯性（同类场景集中）
- 考虑叙事逻辑（事件发展顺序）
- 转场选择要符合场景转换的情感

转场类型说明：
- fade：淡入淡出，适合温馨平静的场景切换
- slideright/slideleft：滑入/滑出，适合空间位置变化
- slideup/slidedown：向上/下滑入
- wipeup/wipedown/wipeleft/wiperight：刮擦式切换
- circleclose/circleopen：圆形收缩/展开
- rectcrop：矩形裁切

转场选择要符合场景转换的情感，优先选择更动感、明显的转场效果。"""

LLM_USER_PROMPT_TEMPLATE = """请为以下照片给出最佳排序和转场。

Segment 名称：{segment_name}
照片数量：{media_count}

照片信息：
{media_list}

输出格式（必须严格遵循）：
说明：{{排序理由}}
顺序：{{filename1}} →[转场] {{filename2}} →[转场] {{filename3}} →[转场] {{filename4}} ...

转场选择规则：
- 同一类场景内切换用 slideright/slideleft/slideup/slidedown（动感流畅）
- 不同场景切换用 wipeup/wipedown/wiperight/wipeleft（叙事感强）
- 情绪高潮或强调时刻用 circleclose/circleopen（戏剧性）
- fade 只在情绪转折点使用，不要连续用多个 fade
- 尽量让转场多样化，不要重复同样的转场

注意：
- 使用 →[转场] 符号连接相邻照片
- 转场数量 = 照片数量 - 1
- 只输出这两行，不要输出其他内容

可选转场：slideright, slideleft, slideup, slidedown, wipeup, wipedown, wipeleft, wiperight, circleclose, circleopen, rectcrop, fade"""


def get_api_key():
    """获取 API Key"""
    api_key = os.getenv("ANTHROPIC_AUTH_TOKEN", "")
    if not api_key:
        config = load_config()
        api_key = config.get("minimax", {}).get("api_key", "")
    return api_key


def call_llm_sort(segment_info):
    """
    调用 LLM 获取图片排序和转场

    Args:
        segment_info: segment info.json 内容

    Returns:
        tuple: (ordered_filenames, explanation, transitions)
    """
    import requests

    api_key = get_api_key()
    if not api_key:
        raise ValueError("请设置 ANTHROPIC_AUTH_TOKEN 环境变量")

    segment_name = segment_info.get("name", "")
    media_list = segment_info.get("media", [])

    # 构建媒体列表文本
    media_texts = []
    for i, media in enumerate(media_list):
        filename = media.get("filename", "")
        understanding = media.get("ai_understanding", {})
        scene = understanding.get("scene", "无描述")
        emotion = understanding.get("emotion", "无")
        tags = understanding.get("tags", [])

        media_texts.append(
            f"{i+1}. {filename}\n"
            f"   场景：{scene}\n"
            f"   情绪：{emotion}\n"
            f"   标签：{', '.join(tags)}"
        )

    media_list_str = "\n".join(media_texts)

    user_prompt = LLM_USER_PROMPT_TEMPLATE.format(
        segment_name=segment_name,
        media_count=len(media_list),
        media_list=media_list_str
    )

    # 调用 MiniMax Text API
    url = "https://api.minimaxi.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "MiniMax-M2.7",
        "messages": [
            {"role": "system", "content": LLM_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3,
        "max_completion_tokens": 1024
    }

    print(f"调用 LLM 排序 ({len(media_list)} 张照片)...")

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        data = resp.json()

        if data.get("base_resp", {}).get("status_code") != 0:
            raise Exception(f"LLM API 错误: {data.get('base_resp', {}).get('status_msg')}")

        # 解析响应
        choices = data.get("choices", [])
        if not choices:
            raise Exception(f"LLM 返回为空: {data}")
        content = choices[0].get("message", {}).get("content", "")
        return parse_llm_response(content, media_list)

    except requests.exceptions.Timeout:
        raise Exception("LLM 排序超时，请重试")
    except Exception as e:
        raise Exception(f"LLM 排序失败: {e}")


def parse_llm_response(content, media_list):
    """
    解析 LLM 返回的排序和转场结果

    Args:
        content: LLM 返回内容
        media_list: 原始媒体列表

    Returns:
        tuple: (ordered_filenames, explanation, transitions)
    """
    # 去掉思考过程标签内容
    import re
    content_clean = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
    content_clean = re.sub(r'<THOUGHT>.*?</THOUGHT>', '', content_clean, flags=re.DOTALL)
    content_clean = re.sub(r'\[RESULT\]', '', content_clean)  # 去掉 [RESULT] 标签

    lines = content_clean.strip().split("\n")

    explanation = ""
    ordered_filenames = []
    transitions = []

    for line in lines:
        line = line.strip()
        if line.startswith("说明："):
            explanation = line[3:].strip()
        elif line.startswith("顺序："):
            order_str = line[3:].strip()
            # 格式: filename1 →[fade] filename2 →[slideright] filename3
            import re
            # 匹配 "filename →[transition]"
            pattern = r'(\S+?)\s*→\[(\w+)\]'
            matches = re.findall(pattern, order_str)

            if matches:
                # 如果包含 →[transition] 格式
                ordered_filenames = [m[0] for m in matches]
                transitions = [m[1] for m in matches]
            else:
                # 回退：逗号分隔
                filenames = [f.strip() for f in order_str.split(",")]
                ordered_filenames = [f for f in filenames if f]

    # 验证所有文件名都存在
    available_filenames = {m.get("filename") for m in media_list}
    valid_filenames = [f for f in ordered_filenames if f in available_filenames]

    # 如果解析失败或遗漏太多，使用时间排序作为后备
    if len(valid_filenames) < len(media_list) * 0.5:
        print("警告: LLM 排序解析失败，使用时间排序作为后备")
        media_list.sort(key=lambda x: x.get("date_taken", ""))
        return [m.get("filename") for m in media_list], "时间排序（LLM 解析失败）", []

    # 补充遗漏的文件（按时间顺序添加到末尾）
    missing = [m.get("filename") for m in media_list if m.get("filename") not in valid_filenames]
    if missing:
        missing.sort()
        valid_filenames.extend(missing)

    # 调整转场数量与文件数量匹配
    expected_transitions = len(valid_filenames) - 1
    if len(transitions) < expected_transitions:
        # 用 fade 填充不足的转场
        transitions.extend(["fade"] * (expected_transitions - len(transitions)))
    elif len(transitions) > expected_transitions:
        transitions = transitions[:expected_transitions]

    return valid_filenames, explanation, transitions


def create_video_from_segment(segment_dir, output_path=None):
    """
    从 segment 目录创建纪念视频

    Args:
        segment_dir: segment 目录路径
        output_path: 输出视频路径

    Returns:
        str: 视频路径
    """
    segment_dir = Path(segment_dir)
    info_path = segment_dir / "info.json"

    if not info_path.exists():
        raise FileNotFoundError(f"info.json 不存在: {info_path}")

    with open(info_path, "r", encoding="utf-8") as f:
        segment_info = json.load(f)

    segment_name = segment_info.get("name", "")

    # 检查背景音乐
    bgm_path = segment_dir / "bgm.mp3"
    if not bgm_path.exists():
        raise FileNotFoundError(f"segment 缺少背景音乐: {bgm_path}")

    print(f"\n处理 Segment: {segment_name}")

    # 获取媒体列表
    media_list = segment_info.get("media", [])
    print(f"媒体数量: {len(media_list)}")

    # LLM 排序+转场
    ordered_filenames, explanation, transitions = call_llm_sort(segment_info)
    print(f"排序说明: {explanation}")
    print(f"排序结果: {' → '.join(ordered_filenames[:5])}...")
    if transitions:
        print(f"转场: {' → '.join(transitions[:5])}...")

    # 构建有序媒体路径（图片从 month_dir 读取）
    month_dir = segment_dir.parent
    filename_to_media = {m.get("filename"): m for m in media_list}
    ordered_media = []
    for filename in ordered_filenames:
        if filename in filename_to_media:
            media = filename_to_media[filename]
            filepath = month_dir / filename  # 从月份目录读取原图
            if filepath.exists():
                media["path"] = str(filepath.absolute())  # 使用绝对路径
                media["segment_bgm"] = str(bgm_path.absolute())
                ordered_media.append(media)
            else:
                print(f"警告: 文件不存在: {filepath}")

    if not ordered_media:
        raise Exception("没有有效的媒体文件")

    # 确定输出路径（默认保存到 videos/{year}/{month}/ 目录）
    if output_path is None:
        # 从路径解析年月: library/photos/2024/07/segment_01_居家日常
        parts = segment_dir.parts
        year = parts[-3]  # 2024
        month = parts[-2]  # 07

        videos_dir = get_videos_dir()
        month_videos_dir = videos_dir / year / month
        ensure_dir(month_videos_dir)
        output_path = month_videos_dir / f"{segment_name}.mp4"

    output_path = Path(output_path)

    # 生成视频（带转场）
    generate_video_with_xfade(ordered_media, output_path, str(bgm_path), transitions)

    return str(output_path)


def generate_video_with_xfade(media_list, output_path, bgm_path, transitions):
    """
    使用 FFmpeg xfade 生成带转场的视频

    Args:
        media_list: 有序媒体列表
        output_path: 输出路径
        bgm_path: 背景音乐路径
        transitions: 转场类型列表
    """
    config = load_config()
    temp_dir = Path(config["paths"]["temp"])
    ensure_dir(temp_dir)

    duration_per_photo = config["video"].get("duration_per_photo", 3)
    xfade_duration = 1.5  # 转场持续时间

    fps = config["video"].get("fps", 24)
    crf = config["video"].get("crf", 23)
    resolution = config["video"].get("resolution", "1920x1080")

    # 解析分辨率
    target_w, target_h = map(int, resolution.split("x"))

    media_count = len(media_list)

    if media_count == 1:
        # 只有一张图片，单独处理
        filepath = media_list[0]["path"]
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", filepath,
            "-t", str(duration_per_photo),
            "-vf", f"scale=-2:{target_h}:force_original_aspect_ratio=decrease,fps={fps}",
            "-c:v", "libx264",
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            str(output_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"FFmpeg 执行失败: {result.stderr}")
        print(f"视频已生成: {output_path}")
        return

    # 构建 filter_complex
    # 策略：
    # 1. 每张图片缩放到目标分辨率
    # 2. 使用 xfade 链式连接：第一张和第二张 xfade，结果再和第三张 xfade，依次类推
    filter_parts = []
    input_args = []

    # 准备输入
    for i, media in enumerate(media_list):
        input_args.extend(["-i", media["path"]])

    # 缩放所有图片并延长显示时间
    # 输入图片只有 1 帧 (duration=0.04s)，需要填充到 duration_per_photo 秒
    for i in range(media_count):
        # scale 缩放，tpad 填充持续时间，fps 设置帧率
        filter_parts.append(
            f"[{i}:v]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease"
            f",pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2"
            f",tpad=stop_mode=clone:stop_duration={duration_per_photo}"
            f",fps={fps}[v{i}]"
        )

    # 构建 xfade 链式操作
    # 例如 6 张图片: [v0][v1] → v01, [v01][v2] → v012, [v012][v3] → v0123, ...
    prev_label = "v0"
    for i in range(1, media_count):
        trans = transitions[i - 1] if i - 1 < len(transitions) else "fade"
        # offset: 第 i 张图片开始替换前一组合的时刻
        # 第 1 张在 offset=2 开始被第 2 张替换 (3-1=2)
        # 第 2 张在 offset=5 开始被第 3 张替换 (2×3-1=5)
        # ...
        offset = i * duration_per_photo - xfade_duration
        # 当前 xfade 结果的标签: v01, v012, v0123, ...
        cur_label = "v0" + "".join(str(j) for j in range(1, i + 1))
        filter_parts.append(
            f"[{prev_label}][v{i}]xfade=transition={trans}:duration={xfade_duration}:offset={offset}[{cur_label}]"
        )
        prev_label = cur_label

    # 最终输出标签
    final_label = prev_label
    filter_complex = ";".join(filter_parts)

    # 生成临时视频（无音频）
    temp_video = output_path.with_suffix(".temp.mp4")

    cmd = [
        "ffmpeg", "-y"
    ] + input_args + [
        "-filter_complex", filter_complex,
        "-map", f"[{final_label}]",
        "-c:v", "libx264",
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-t", str(media_count * duration_per_photo - xfade_duration),
        str(temp_video)
    ]

    print("执行 FFmpeg 合成视频（带转场）...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"FFmpeg 执行失败: {result.stderr}")

    # 添加音频
    print(f"添加背景音乐: {Path(bgm_path).name}")

    cmd_audio = [
        "ffmpeg", "-y",
        "-i", str(temp_video),
        "-i", str(bgm_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(output_path)
    ]

    result = subprocess.run(cmd_audio, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"添加音频失败: {result.stderr}")

    # 删除临时文件
    temp_video.unlink()

    print(f"视频已生成: {output_path}")


def generate_video(media_list, output_path, bgm_path):
    """
    使用 FFmpeg 生成视频（使用 image2 demuxer，无转场）

    Args:
        media_list: 有序媒体列表
        output_path: 输出路径
        bgm_path: 背景音乐路径
    """
    config = load_config()
    temp_dir = Path(config["paths"]["temp"])
    ensure_dir(temp_dir)

    duration_per_photo = config["video"].get("duration_per_photo", 3)

    fps = config["video"].get("fps", 24)
    crf = config["video"].get("crf", 23)
    resolution = config["video"].get("resolution", "1920x1080")

    # 解析分辨率
    target_w, target_h = map(int, resolution.split("x"))

    # 生成临时视频（无音频）
    temp_video = output_path.with_suffix(".temp.mp4")

    # 使用 image2 demuxer 直接读取图片文件列表
    filelist_path = temp_dir / "filelist.txt"
    with open(filelist_path, "w", encoding="utf-8") as f:
        for media in media_list:
            filepath = media["path"].replace("'", "'\\''")
            f.write(f"file '{filepath}'\n")
            f.write(f"duration {duration_per_photo}\n")
        # 最后一个文件重复以确保结束
        if media_list:
            last_path = media_list[-1]["path"].replace("'", "'\\''")
            f.write(f"file '{last_path}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(filelist_path),
        "-vf", f"scale=-2:{target_h}:force_original_aspect_ratio=decrease,fps={fps}",
        "-c:v", "libx264",
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        str(temp_video)
    ]

    print("执行 FFmpeg 合成视频...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"FFmpeg 执行失败: {result.stderr}")

    # 添加音频
    print(f"添加背景音乐: {Path(bgm_path).name}")

    cmd_audio = [
        "ffmpeg", "-y",
        "-i", str(temp_video),
        "-i", str(bgm_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(output_path)
    ]

    result = subprocess.run(cmd_audio, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"添加音频失败: {result.stderr}")

    # 删除临时文件
    temp_video.unlink()

    print(f"视频已生成: {output_path}")


def process_segment(segment_dir, output_path=None):
    """
    处理单个 segment

    Args:
        segment_dir: segment 目录路径
        output_path: 输出视频路径
    """
    segment_dir = Path(segment_dir)
    return create_video_from_segment(segment_dir, output_path)


def process_month(month_dir, output_dir=None):
    """
    处理整个月份目录，为每个 segment 生成独立视频

    Args:
        month_dir: 月份目录路径
        output_dir: 输出目录（可选）
    """
    month_dir = Path(month_dir)

    if output_dir:
        output_dir = Path(output_dir)
        ensure_dir(output_dir)
    else:
        videos_dir = get_videos_dir()
        ensure_dir(videos_dir)
        output_dir = videos_dir

    # 获取月份元数据
    metadata_path = month_dir / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        year = metadata.get("year", "")
        month = metadata.get("month", "")
        print(f"处理月份: {year}-{month}")

    # 遍历月份目录下的 segment_* 目录
    segment_count = 0
    for seg_dir in sorted(month_dir.iterdir()):
        if not seg_dir.is_dir():
            continue
        if not seg_dir.name.startswith("segment_"):
            continue

        info_path = seg_dir / "info.json"
        if not info_path.exists():
            continue

        # 检查是否有背景音乐
        bgm_path = seg_dir / "bgm.mp3"
        if not bgm_path.exists():
            print(f"跳过 (无背景音乐): {seg_dir.name}")
            continue

        try:
            # 从 seg_dir 路径解析年月
            parts = seg_dir.parts
            year = parts[-3]  # 2024
            month = parts[-2]  # 07
            output_path = output_dir / year / month / f"{seg_dir.name}.mp4"
            result = process_segment(seg_dir, output_path)
            segment_count += 1
            print(f"✓ 完成: {result}")
        except Exception as e:
            print(f"✗ 失败: {seg_dir.name} - {e}")

    print(f"\n完成！共生成 {segment_count} 个视频")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="生成纪念视频")
    parser.add_argument("path", nargs="?", help="segment 目录或月份目录")
    parser.add_argument("--output", "-o", help="输出视频路径（用于单个 segment）")
    parser.add_argument("--segment", action="store_true", help="强制作为 segment 处理")

    args = parser.parse_args()

    if not args.path:
        print("用法:")
        print("  单个 segment: python video_maker.py <segment_dir> [--output <path>]")
        print("  月份目录: python video_maker.py <month_dir>")
        sys.exit(1)

    path = Path(args.path)

    if not path.exists():
        print(f"错误: 路径不存在: {path}")
        sys.exit(1)

    if args.segment or (path / "info.json").exists():
        # 作为 segment 处理
        process_segment(path, args.output)
    elif (path / "segments").exists() or any(p.name.startswith("segment_") for p in path.iterdir()):
        # 作为月份处理
        process_month(path, args.output)
    else:
        print(f"错误: 无法识别的路径类型: {path}")
        sys.exit(1)
