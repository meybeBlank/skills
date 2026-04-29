"""
music_generator.py - MiniMax Music API 背景音乐生成

功能：
- 根据图片理解结果生成匹配的背景音乐
- 先调用歌词生成 API 生成歌词
- 再调用音乐生成 API 生成音乐

API Endpoints:
- POST https://api.minimaxi.com/v1/lyrics_generation
- POST https://api.minimaxi.com/v1/music_generation
"""
import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from config import load_config


def generate_lyrics(prompt, timeout=60):
    """
    调用 MiniMax 歌词生成 API

    Args:
        prompt: 歌词主题描述
        timeout: 超时时间

    Returns:
        dict: {song_title, style_tags, lyrics}
    """
    api_key = os.getenv("ANTHROPIC_AUTH_TOKEN", "")
    if not api_key:
        config = load_config()
        api_key = config.get("minimax", {}).get("api_key", "")

    if not api_key:
        raise ValueError("请设置 ANTHROPIC_AUTH_TOKEN 环境变量")

    url = "https://api.minimaxi.com/v1/lyrics_generation"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "mode": "write_full_song",
        "prompt": prompt
    }

    print(f"调用歌词生成 API...")
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        data = resp.json()
    except requests.exceptions.Timeout:
        raise Exception(f"歌词生成超时 ({timeout}s)，请稍后重试")
    except requests.exceptions.RequestException as e:
        raise Exception(f"歌词生成请求失败: {e}")

    if data.get("base_resp", {}).get("status_code") != 0:
        raise Exception(f"歌词 API 错误: {data.get('base_resp', {}).get('status_msg')}")

    return {
        "song_title": data.get("song_title", ""),
        "style_tags": data.get("style_tags", ""),
        "lyrics": data.get("lyrics", "")
    }


def get_music_prompt_from_segment(segment_info):
    """
    从 segment 信息生成歌词提示词（整合所有 scene）

    Args:
        segment_info: segment info.json 内容

    Returns:
        str: 歌词提示词
    """
    name = segment_info.get("name", "")
    media_list = segment_info.get("media", [])

    if not media_list:
        return f"关于{name}的家庭温馨音乐"

    # 收集所有 scene 描述
    scenes = []
    emotions = []
    tags = set()

    for media in media_list:
        understanding = media.get("ai_understanding", {})
        if understanding:
            scene = understanding.get("scene", "")
            if scene:
                scenes.append(scene)
            emotion = understanding.get("emotion", "")
            if emotion:
                emotions.append(emotion)
            tag_list = understanding.get("tags", [])
            if tag_list:
                tags.update(tag_list)

    # 去重情绪
    unique_emotions = []
    seen = set()
    for e in emotions:
        # 分割逗号分隔的情绪
        for part in e.split("、"):
            part = part.strip()
            if part and part not in seen:
                seen.add(part)
                unique_emotions.append(part)

    emotion_str = "、".join(unique_emotions[:4]) if unique_emotions else "温馨、快乐"
    tags_str = "、".join(list(tags)[:8]) if tags else "家庭、孩子"

    # 构建一个综合描述
    scene_summary = "、".join([s[:30] for s in scenes[:3]])  # 每个scene取前30字

    # 生成贴合内容的歌词主题
    prompt = f"""主题：家庭亲子时刻
风格标签：{emotion_str}
内容描述：{tags_str}
场景概括：{scene_summary}...

请生成一首温馨的家庭歌曲，歌词要贴合上述场景，体现父母对孩子的爱、孩子的纯真童心、家庭生活的美好片段。"""

    return prompt



def generate_music(prompt, lyrics=None, model="music-2.6", timeout=300):
    """
    调用 MiniMax Music API 生成音乐

    Args:
        prompt: 音乐风格提示词
        lyrics: 可选歌词
        model: 模型名称
        timeout: 超时时间（秒）

    Returns:
        dict: API 响应
    """
    api_key = os.getenv("ANTHROPIC_AUTH_TOKEN", "")
    if not api_key:
        config = load_config()
        api_key = config.get("minimax", {}).get("api_key", "")

    if not api_key:
        raise ValueError("请设置 ANTHROPIC_AUTH_TOKEN 环境变量或在 settings.yaml 中配置 MiniMax API Key")

    url = "https://api.minimaxi.com/v1/music_generation"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "prompt": prompt,
        "audio_setting": {
            "sample_rate": 44100,
            "bitrate": 256000,
            "format": "mp3"
        },
        "output_format": "url"
    }

    if lyrics:
        payload["lyrics"] = lyrics

    print(f"调用 Music API (超时 {timeout}s)...")

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        data = resp.json()

        if data.get("base_resp", {}).get("status_code") != 0:
            error_msg = data.get("base_resp", {}).get("status_msg", "Unknown error")
            raise Exception(f"Music API 错误: {error_msg}")

        return data

    except requests.exceptions.Timeout:
        raise Exception(f"音乐生成超时 ({timeout}s)，请稍后重试")
    except requests.exceptions.RequestException as e:
        raise Exception(f"音乐生成请求失败: {e}")


def download_music(audio_url, output_path):
    """
    下载音乐文件

    Args:
        audio_url: 音乐 URL
        output_path: 保存路径

    Returns:
        str: 保存路径
    """
    import urllib.parse

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        resp = requests.get(audio_url, timeout=30)
    except requests.exceptions.RequestException as e:
        raise Exception(f"音乐文件下载请求失败: {e}")

    if resp.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(resp.content)
        print(f"音乐已下载: {output_path}")
        return str(output_path)
    elif resp.status_code == 403:
        raise Exception(f"音乐 URL 已过期 (403)，请重新生成音乐")
    else:
        raise Exception(f"音乐下载失败: HTTP {resp.status_code}")


def generate_for_segment(segment_dir, output_path=None):
    """
    为 segment 生成背景音乐（先歌词后音乐）

    Args:
        segment_dir: segment 目录
        output_path: 输出音乐路径

    Returns:
        str: 音乐文件路径
    """
    segment_dir = Path(segment_dir)
    info_path = segment_dir / "info.json"

    if not info_path.exists():
        raise FileNotFoundError(f"info.json 不存在: {info_path}")

    with open(info_path, "r", encoding="utf-8") as f:
        segment_info = json.load(f)

    segment_name = segment_info.get("name", "")

    # 1. 生成歌词
    theme = get_music_prompt_from_segment(segment_info)
    print(f"\nSegment: {segment_name}")
    print(f"歌词主题: {theme}")

    lyrics_result = generate_lyrics(theme)
    print(f"歌名: {lyrics_result['song_title']}")
    print(f"风格: {lyrics_result['style_tags']}")

    # 保存歌词
    lyrics_path = segment_dir / "lyrics.json"
    with open(lyrics_path, "w", encoding="utf-8") as f:
        json.dump(lyrics_result, f, ensure_ascii=False, indent=2)
    print(f"歌词已保存: {lyrics_path}")

    # 2. 生成音乐（使用生成的歌词）
    music_prompt = lyrics_result["style_tags"]
    music_lyrics = lyrics_result["lyrics"]

    print(f"\n开始生成音乐...")
    result = generate_music(music_prompt, music_lyrics)

    if result is None:
        raise Exception(f"音乐生成失败: API 返回 None，请检查账户配额或稍后重试")

    data = result.get("data")
    if not data:
        raise Exception(f"音乐生成失败: API 返回数据为空 {result}")

    audio_url = data.get("audio") or data.get("audio_url")
    if not audio_url:
        raise Exception(f"音乐生成失败: 未获取到 audio_url，API 返回: {result}")

    if output_path is None:
        output_path = segment_dir / "bgm.mp3"

    try:
        return download_music(audio_url, output_path)
    except Exception as e:
        raise Exception(f"音乐下载失败: {e}")


def process_library(library_path=None, segments_only=True):
    """
    处理整个媒体库，为每个 segment 生成音乐

    Args:
        library_path: 媒体库路径
        segments_only: 是否只处理 segments 目录
    """
    if library_path is None:
        from config import get_photos_dir
        library_path = get_photos_dir()

    library_path = Path(library_path)

    print(f"扫描媒体库: {library_path}")

    segment_count = 0

    for year_dir in sorted(library_path.iterdir()):
        if not year_dir.is_dir():
            continue

        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir():
                continue

            # 遍历月份目录下的 segment_* 目录
            for segment_dir in sorted(month_dir.iterdir()):
                if not segment_dir.is_dir():
                    continue
                if not segment_dir.name.startswith("segment_"):
                    continue

                print(f"\n处理: {year_dir.name}/{month_dir.name}/{segment_dir.name}")

                try:
                    music_path = generate_for_segment(segment_dir)
                    if music_path:
                        segment_count += 1
                        print(f"  ✓ 成功: {music_path}")
                except Exception as e:
                    print(f"  ✗ 失败: {e}")
                    raise  # 向上抛出，让调用方知道出了问题


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="生成背景音乐 (MiniMax Music API)")
    parser.add_argument("path", nargs="?", help="segment 目录路径或媒体库路径")
    parser.add_argument("--output", "-o", help="输出音乐文件路径")

    args = parser.parse_args()

    if args.path:
        path = Path(args.path)
        if (path / "info.json").exists():
            # 单个 segment
            generate_for_segment(path, args.output)
        else:
            # 媒体库
            process_library(args.path)
    else:
        process_library()
