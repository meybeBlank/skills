"""
image_understanding_batch.py - 批量图片理解

功能：
- 使用 MiniMax VLM API 分析每张照片
- 将理解结果写入 metadata

依赖：
- requests
- ANTHROPIC_AUTH_TOKEN 环境变量（或在 settings.yaml 中配置）
"""
import os
import sys
import json
import base64
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from config import load_config


def analyze_image_api(image_path, prompt=None):
    """
    使用 MiniMax VLM API 分析单张照片

    Args:
        image_path: 图片路径
        prompt: 可选的提示词

    Returns:
        dict: 分析结果
    """
    if prompt is None:
        prompt = """分析这张照片，返回 JSON 格式：
{
    "scene": "场景描述",
    "emotion": "情绪",
    "tags": ["标签1", "标签2"],
    "suitable_music": "适合的背景音乐风格"
}"""

    # 读取图片并转为 base64
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    # 获取 API Key
    api_key = os.getenv("ANTHROPIC_AUTH_TOKEN", "")
    if not api_key:
        config = load_config()
        api_key = config.get("minimax", {}).get("api_key", "")

    if not api_key:
        raise ValueError("请设置 ANTHROPIC_AUTH_TOKEN 环境变量或在 settings.yaml 中配置 MiniMax API Key")

    url = "https://api.minimaxi.com/v1/coding_plan/vlm"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "MM-API-Source": "MinMax-MCP",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": prompt,
        "image_url": f"data:image/jpeg;base64,{img_b64}"
    }

    import requests
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise Exception(f"API 错误: {resp.status_code} - {resp.text}")

    data = resp.json()
    if data.get("base_resp", {}).get("status_code") != 0:
        raise Exception(f"API 错误: {data.get('base_resp', {}).get('status_msg')}")

    # 解析返回内容
    content = data.get("content", "")

    # 尝试解析 JSON（API 返回的是带 markdown 代码块的 JSON）
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        result = json.loads(content.strip())
        return result
    except json.JSONDecodeError:
        # 如果不是 JSON，返回为 scene
        return {"scene": content}


def process_month(month_dir, dry_run=False):
    """
    处理一个月份目录的所有图片

    Args:
        month_dir: 月份目录路径
        dry_run: 是否仅测试不实际调用 API
    """
    month_dir = Path(month_dir)
    metadata_path = month_dir / "metadata.json"

    if not metadata_path.exists():
        print(f"跳过 (无 metadata): {month_dir}")
        return

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # 检查是否已全部理解
    if metadata.get("ai_understood"):
        print(f"已理解，跳过: {month_dir.name}")
        return

    # 获取需要处理的图片
    image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
    to_process = []

    for media in metadata.get("media", []):
        if media.get("type") != "image":
            continue
        if "ai_understanding" in media:
            continue  # 已理解
        to_process.append(media)

    if not to_process:
        print(f"没有需要处理的图片: {month_dir.name}")
        metadata["ai_understood"] = True
        metadata["ai_understood_at"] = datetime.now().isoformat()
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        return

    print(f"处理 {len(to_process)} 张图片: {month_dir.name}")

    for i, media in enumerate(to_process, 1):
        filename = media["filename"]
        file_path = month_dir / filename

        if not file_path.exists():
            continue

        print(f"  [{i}/{len(to_process)}] {filename}")

        if dry_run:
            media["ai_understanding"] = {
                "scene": "待分析",
                "emotion": "待分析",
                "tags": ["待分析"],
                "suitable_music": "待分析"
            }
        else:
            try:
                result = analyze_image_api(file_path)
                media["ai_understanding"] = result
            except Exception as e:
                print(f"  分析错误: {e}")
                media["ai_understanding"] = {"scene": f"错误: {str(e)}"}

        # 保存进度
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        # 避免限流
        time.sleep(0.3)

    # 标记完成
    metadata["ai_understood"] = True
    metadata["ai_understood_at"] = datetime.now().isoformat()
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"完成: {month_dir.name}")


def process_library(library_path=None, dry_run=False):
    """
    处理整个媒体库的图片理解

    Args:
        library_path: 媒体库路径
        dry_run: 是否仅测试
    """
    if library_path is None:
        from config import get_photos_dir
        library_path = get_photos_dir()

    library_path = Path(library_path)

    print(f"开始图片理解: {library_path}")

    for year_dir in sorted(library_path.iterdir()):
        if not year_dir.is_dir():
            continue

        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir():
                continue

            print(f"\n处理目录: {year_dir.name}/{month_dir.name}")
            process_month(month_dir, dry_run)

    print("\n图片理解完成!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="批量图片理解 (MiniMax VLM API)")
    parser.add_argument("path", nargs="?", help="媒体库路径或月份目录")
    parser.add_argument("--dry-run", action="store_true", help="仅测试不实际调用 API")

    args = parser.parse_args()

    if args.path:
        path = Path(args.path)
        if (path / "metadata.json").exists():
            process_month(path, args.dry_run)
        else:
            process_library(args.path, args.dry_run)
    else:
        process_library(None, args.dry_run)
