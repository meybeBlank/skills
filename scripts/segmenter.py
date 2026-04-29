"""
segmenter.py - 智能聚类分段

功能：
- 根据 AI 理解结果进行智能聚类
- 支持多种聚类规则配置
- 输出聚类预览供用户确认

使用方式：
  python scripts/segmenter.py library/photos/2023/10

  或在 Claude Code 中通过 Skill 对话调用
"""
import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import difflib

sys.path.insert(0, str(Path(__file__).parent))

from config import load_config


def compute_similarity(text1, text2):
    """
    计算两个文本的相似度

    Args:
        text1: 文本1
        text2: 文本2

    Returns:
        float: 0-1 相似度
    """
    if not text1 or not text2:
        return 0.0
    return difflib.SequenceMatcher(None, text1, text2).ratio()


def compute_tags_similarity(tags1, tags2):
    """
    计算标签列表的相似度

    Args:
        tags1: 标签列表1
        tags2: 标签列表2

    Returns:
        float: 0-1 相似度
    """
    if not tags1 or not tags2:
        return 0.0
    set1, set2 = set(tags1), set(tags2)
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)


def cluster_by_scene(media_list, threshold=0.6):
    """
    按场景相似度聚类

    Args:
        media_list: 媒体列表
        threshold: 相似度阈值

    Returns:
        list: 聚类结果
    """
    clusters = []

    for media in media_list:
        understanding = media.get("ai_understanding", {})
        scene = understanding.get("scene", "")

        best_match_idx = -1
        best_similarity = 0

        for idx, cluster in enumerate(clusters):
            cluster_scene = cluster.get("representative_scene", "")
            similarity = compute_similarity(scene, cluster_scene)

            if similarity > best_similarity and similarity >= threshold:
                best_similarity = similarity
                best_match_idx = idx

        if best_match_idx >= 0:
            clusters[best_match_idx]["media"].append(media)
            # 更新代表场景（取最长）
            if len(scene) > len(clusters[best_match_idx].get("representative_scene", "")):
                clusters[best_match_idx]["representative_scene"] = scene
        else:
            clusters.append({
                "media": [media],
                "representative_scene": scene,
                "scene": scene,
                "name": generate_cluster_name(scene)
            })

    return clusters


def cluster_by_emotion(media_list, threshold=0.5):
    """
    按情绪聚类

    Args:
        media_list: 媒体列表
        threshold: 相似度阈值

    Returns:
        list: 聚类结果
    """
    emotion_map = defaultdict(list)

    for media in media_list:
        understanding = media.get("ai_understanding", {})
        emotion = understanding.get("emotion", "")

        # 提取主要情绪词
        emotion_keywords = ["温馨", "快乐", "好奇", "宁静", "兴奋", "平静", "欢快", "活泼"]
        matched = [kw for kw in emotion_keywords if kw in emotion]

        if matched:
            key = matched[0]
        else:
            key = "其他情绪"

        emotion_map[key].append(media)

    clusters = []
    for emotion, media_list in emotion_map.items():
        clusters.append({
            "media": media_list,
            "emotion": emotion,
            "name": emotion
        })

    return clusters


def cluster_by_tags(media_list, threshold=0.3):
    """
    按标签聚类

    Args:
        media_list: 媒体列表
        threshold: 标签相似度阈值

    Returns:
        list: 聚类结果
    """
    clusters = []

    for media in media_list:
        understanding = media.get("ai_understanding", {})
        tags = understanding.get("tags", [])

        best_match_idx = -1
        best_similarity = 0

        for idx, cluster in enumerate(clusters):
            cluster_tags = cluster.get("tags", [])
            similarity = compute_tags_similarity(tags, cluster_tags)

            if similarity > best_similarity and similarity >= threshold:
                best_similarity = similarity
                best_match_idx = idx

        if best_match_idx >= 0:
            clusters[best_match_idx]["media"].append(media)
            # 更新标签集合
            cluster_tags = set(clusters[best_match_idx].get("tags", []))
            cluster_tags.update(tags)
            clusters[best_match_idx]["tags"] = list(cluster_tags)
        else:
            clusters.append({
                "media": [media],
                "tags": tags,
                "name": generate_cluster_name_from_tags(tags)
            })

    return clusters


def cluster_by_time_content(media_list, time_window_hours=2, content_threshold=0.5):
    """
    按时间邻近 + 内容相似聚类

    Args:
        media_list: 媒体列表
        time_window_hours: 时间窗口（小时）
        content_threshold: 内容相似度阈值

    Returns:
        list: 聚类结果
    """
    # 按时间排序
    sorted_media = sorted(media_list, key=lambda m: m.get("date_taken") or "")

    clusters = []
    current_cluster = None

    for media in sorted_media:
        date_taken = media.get("date_taken")
        if not date_taken:
            date_taken = "unknown"
        else:
            try:
                date_taken = datetime.fromisoformat(date_taken.replace("Z", "+00:00"))
            except:
                date_taken = None

        understanding = media.get("ai_understanding", {})
        scene = understanding.get("scene", "")

        if current_cluster is None:
            current_cluster = {
                "media": [media],
                "representative_scene": scene,
                "start_time": date_taken,
                "end_time": date_taken,
                "name": generate_cluster_name(scene)
            }
            continue

        # 检查时间间隔
        time_diff = float('inf')
        if date_taken and current_cluster.get("end_time"):
            time_diff = abs((date_taken - current_cluster["end_time"]).total_seconds() / 3600)

        # 检查内容相似度
        similarity = compute_similarity(scene, current_cluster["representative_scene"])

        if time_diff <= time_window_hours and similarity >= content_threshold:
            # 合并到当前集群
            current_cluster["media"].append(media)
            if date_taken:
                current_cluster["end_time"] = date_taken
            if len(scene) > len(current_cluster["representative_scene"]):
                current_cluster["representative_scene"] = scene
        else:
            # 保存当前集群，开始新集群
            clusters.append(current_cluster)
            current_cluster = {
                "media": [media],
                "representative_scene": scene,
                "start_time": date_taken,
                "end_time": date_taken,
                "name": generate_cluster_name(scene)
            }

    # 添加最后一个集群
    if current_cluster:
        clusters.append(current_cluster)

    return clusters


def generate_cluster_name(scene):
    """从场景描述生成聚类名称"""
    if not scene:
        return "未分类"

    # 提取关键名词
    keywords = [
        "水族馆", "白鲸", "海洋", "宝宝", "孩子", "气球",
        "户外", "公园", "游乐场", "家庭", "聚会", "生日",
        "旅行", "海边", "山", "城市", "街道", "室内",
        "餐厅", "商场", "学校", "节日", "春节", "国庆"
    ]

    for keyword in keywords:
        if keyword in scene:
            return keyword

    # 取前5个字
    return scene[:5] if len(scene) >= 5 else scene


def generate_cluster_name_from_tags(tags):
    """从标签生成聚类名称"""
    if not tags:
        return "未分类"

    priority_tags = ["水族馆", "户外", "家庭", "聚会", "生日", "旅行", "宝宝", "孩子"]
    for tag in tags:
        for priority in priority_tags:
            if priority in tag:
                return priority

    return tags[0] if tags else "未分类"


def analyze_cluster(clusters):
    """
    分析聚类结果，生成概览

    Args:
        clusters: 聚类列表

    Returns:
        dict: 概览信息
    """
    total_media = sum(len(c["media"]) for c in clusters)

    overview = {
        "total": total_media,
        "cluster_count": len(clusters),
        "clusters": []
    }

    for idx, cluster in enumerate(clusters, 1):
        media_count = len(cluster["media"])
        emotions = []
        all_tags = []
        scenes = []

        for media in cluster["media"]:
            u = media.get("ai_understanding", {})
            if u.get("emotion"):
                emotions.append(u["emotion"])
            if u.get("tags"):
                all_tags.extend(u["tags"])
            if u.get("scene"):
                scenes.append(u["scene"][:50])

        # 去重
        emotions = list(dict.fromkeys(emotions))[:3]
        all_tags = list(dict.fromkeys(all_tags))[:10]

        cluster_info = {
            "id": idx,
            "name": cluster.get("name", "未分类"),
            "media_count": media_count,
            "percentage": round(media_count / total_media * 100, 1) if total_media > 0 else 0,
            "emotions": emotions,
            "tags": all_tags,
            "preview_scene": scenes[0] if scenes else ""
        }

        overview["clusters"].append(cluster_info)

    return overview


def generate_preview_text(overview):
    """
    生成聚类预览文本

    Args:
        overview: 聚类概览

    Returns:
        str: 预览文本
    """
    lines = [
        f"📊 聚类分析结果（共 {overview['cluster_count']} 个分段，{overview['total']} 张媒体）：",
        ""
    ]

    for cluster in overview["clusters"]:
        lines.append(f"{cluster['id']}️⃣ 【{cluster['name']}】{cluster['media_count']}张 ({cluster['percentage']}%)")

        if cluster["emotions"]:
            lines.append(f"   情绪: {', '.join(cluster['emotions'][:2])}")

        if cluster["tags"]:
            lines.append(f"   标签: {', '.join(cluster['tags'][:5])}")

        if cluster["preview_scene"]:
            lines.append(f"   示例: {cluster['preview_scene'][:30]}...")

        lines.append("")

    return "\n".join(lines)


def apply_user_adjustments(clusters, adjustments):
    """
    应用用户调整

    Args:
        clusters: 原始聚类
        adjustments: 调整指令

    Returns:
        list: 调整后的聚类
    """
    # TODO: 实现用户调整逻辑
    return clusters


def generate_segments(month_dir, clusters, output_dir=None):
    """
    生成 segments 目录

    Args:
        month_dir: 月份目录
        clusters: 聚类结果
        output_dir: 输出目录

    Returns:
        list: 生成的 segment 信息
    """
    output_dir = month_dir

    segment_info = []

    for idx, cluster in enumerate(clusters, 1):
        segment_name = f"segment_{idx:02d}_{cluster.get('name', 'unknown')}"
        segment_dir = output_dir / segment_name

        segment_dir.mkdir(parents=True, exist_ok=True)

        # 写入 segment 信息（只包含 filename 引用，不拷贝图片）
        info = {
            "id": idx,
            "name": cluster.get("name", "未分类"),
            "media_count": len(cluster["media"]),
            "representative_scene": cluster.get("representative_scene", ""),
            "emotion": cluster.get("emotion", ""),
            "tags": list(set(cluster.get("tags", []))),
            "media": []
        }

        # 只记录 filename，不拷贝图片
        for media in cluster["media"]:
            info["media"].append({
                "filename": media["filename"],
                "ai_understanding": media.get("ai_understanding", {})
            })

        # 保存 info.json
        with open(segment_dir / "info.json", "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

        segment_info.append({
            "id": idx,
            "name": cluster.get("name", "未分类"),
            "path": str(segment_dir),
            "media_count": len(cluster["media"])
        })

        print(f"  ✅ 已生成: {segment_name} ({len(cluster['media'])}张)")

    return segment_info


def segment_month(month_dir, method="scene", threshold=0.6, user_adjustments=None):
    """
    对月份目录进行聚类分段

    Args:
        month_dir: 月份目录
        method: 聚类方法 (scene/emotion/tags/time_content)
        threshold: 相似度阈值
        user_adjustments: 用户调整

    Returns:
        dict: 聚类结果
    """
    month_dir = Path(month_dir)
    metadata_path = month_dir / "metadata.json"

    if not metadata_path.exists():
        raise FileNotFoundError(f"metadata.json 不存在: {metadata_path}")

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # 获取有 AI 理解的媒体
    media_list = [
        m for m in metadata.get("media", [])
        if m.get("type") == "image" and m.get("ai_understanding")
    ]

    if not media_list:
        raise ValueError("没有找到带有 AI 理解的媒体，请先运行 image_understanding_batch.py")

    # 根据方法聚类
    if method == "scene":
        clusters = cluster_by_scene(media_list, threshold)
    elif method == "emotion":
        clusters = cluster_by_emotion(media_list, threshold)
    elif method == "tags":
        clusters = cluster_by_tags(media_list, threshold)
    elif method == "time_content":
        clusters = cluster_by_time_content(media_list, time_window_hours=2, content_threshold=threshold)
    else:
        raise ValueError(f"未知的聚类方法: {method}")

    # 应用用户调整
    if user_adjustments:
        clusters = apply_user_adjustments(clusters, user_adjustments)

    # 分析聚类结果
    overview = analyze_cluster(clusters)

    return {
        "month_dir": str(month_dir),
        "method": method,
        "threshold": threshold,
        "clusters": clusters,
        "overview": overview
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="智能聚类分段")
    parser.add_argument("path", nargs="?", help="月份目录路径")
    parser.add_argument("--method", "-m", choices=["scene", "emotion", "tags", "time_content"],
                        default="scene", help="聚类方法")
    parser.add_argument("--threshold", "-t", type=float, default=0.6,
                        help="相似度阈值 (0-1)")
    parser.add_argument("--preview", "-p", action="store_true",
                        help="仅预览不生成")
    parser.add_argument("--generate", "-g", action="store_true",
                        help="生成 segments 目录")

    args = parser.parse_args()

    if not args.path:
        print("用法: python segmenter.py <月份目录> [--method scene] [--threshold 0.6]")
        sys.exit(1)

    path = Path(args.path)
    if not (path / "metadata.json").exists():
        print(f"错误: {path} 下没有 metadata.json")
        sys.exit(1)

    # 执行聚类
    result = segment_month(path, method=args.method, threshold=args.threshold)

    # 输出预览
    preview = generate_preview_text(result["overview"])
    print(preview)

    if args.preview:
        print("\n💡 使用 --generate 参数生成 segments 目录")
        return

    if args.generate:
        print("\n正在生成 segments...")
        segments = generate_segments(path, result["clusters"])
        print(f"\n✅ 完成！生成了 {len(segments)} 个分段")


if __name__ == "__main__":
    main()
