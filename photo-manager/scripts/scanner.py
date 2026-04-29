"""
scanner.py - 扫描照片和视频，提取元数据，按年月整理
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime
import shutil

sys.path.insert(0, str(Path(__file__).parent))

from utils import compute_file_hash, get_exif_date, parse_exif_date, get_video_date, ensure_filename_unique, ensure_dir, parse_filename_date
from config import get_photos_dir


def scan_directory(source_dir, output_dir=None):
    """
    扫描源目录下的所有照片和视频

    Args:
        source_dir: 原始媒体目录
        output_dir: 可选，指定输出目录（默认使用 library）
    """
    source_dir = Path(source_dir)
    if not source_dir.exists():
        print(f"错误: 目录不存在 {source_dir}")
        return

    if output_dir is None:
        output_dir = get_photos_dir()
    else:
        output_dir = Path(output_dir)

    # 支持的图片格式
    image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
    # 支持的视频格式
    video_extensions = {".mov", ".mp4", ".avi", ".mkv", ".m4v", ".3gp"}

    # 按年月分组媒体
    media_by_month = {}

    print(f"开始扫描目录: {source_dir}")

    for root, dirs, files in os.walk(source_dir):
        for filename in files:
            ext = Path(filename).suffix.lower()
            file_path = Path(root) / filename

            # 判断是图片还是视频
            is_image = ext in image_extensions
            is_video = ext in video_extensions

            if not is_image and not is_video:
                continue

            print(f"  扫描: {filename} ({'图片' if is_image else '视频'})")

            # 计算哈希
            file_hash = compute_file_hash(file_path)

            # 按优先级提取日期
            media_date = None
            date_source = None

            if is_image:
                exif_date_str = get_exif_date(file_path)
                media_date = parse_exif_date(exif_date_str)
                if media_date:
                    date_source = "exif"

            if media_date is None:
                # 尝试 FFprobe (视频)
                ffprobe_date = get_video_date(file_path)
                if ffprobe_date:
                    media_date = ffprobe_date
                    date_source = "ffprobe"

            if media_date is None:
                # 尝试从文件名解析
                filename_date = parse_filename_date(filename)
                if filename_date:
                    media_date = filename_date
                    date_source = "filename"

            # 最后 fallback: 无法解析时间，放到特殊月份 13 表示时间未知
            if media_date is None:
                year = "unknown"
                month = "13"
                date_source = "unknown"
            else:
                year = media_date.strftime("%Y")
                month = media_date.strftime("%m")

            # 目标目录结构: library/photos/{year}/{month}/
            dest_subdir = output_dir / year / month
            ensure_dir(dest_subdir)

            # 复制文件到目标目录
            unique_filename = ensure_filename_unique(dest_subdir, filename)
            dest_path = dest_subdir / unique_filename

            # 如果源文件和目标文件相同，跳过复制
            if file_path.resolve() != dest_path.resolve():
                shutil.copy2(file_path, dest_path)

            # 记录媒体信息
            media_info = {
                "filename": unique_filename,
                "original_name": filename,
                "source_path": str(file_path.resolve()),
                "stored_path": str(dest_path),
                "hash": file_hash,
                "date_taken": media_date.isoformat() if media_date else None,
                "date_source": date_source,
                "year": year,
                "month": month,
                "type": "image" if is_image else "video",
                "extension": ext
            }

            # 按年月分组
            key = (year, month)
            if key not in media_by_month:
                media_by_month[key] = []
            media_by_month[key].append(media_info)

    # 统计
    total_photos = sum(1 for m in media_by_month.values() for med in m if med["type"] == "image")
    total_videos = sum(1 for m in media_by_month.values() for med in m if med["type"] == "video")

    print(f"\n扫描完成! 共找到 {total_photos} 张照片, {total_videos} 个视频")

    # 为每个月份目录生成 metadata.json
    for (year, month), media_list in media_by_month.items():
        # 按日期排序 (None 放到最后)
        media_list.sort(key=lambda x: (x["date_taken"] is None, x["date_taken"] or ""))

        metadata_path = output_dir / year / month
        metadata = {
            "year": year,
            "month": month,
            "media_count": len(media_list),
            "photo_count": len([m for m in media_list if m["type"] == "image"]),
            "video_count": len([m for m in media_list if m["type"] == "video"]),
            "created_at": datetime.now().isoformat(),
            "media": media_list
        }

        with open(metadata_path / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print(f"  {year}/{month}/metadata.json ({len(media_list)} 个媒体)")

    return media_by_month


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scanner.py <源目录> [输出目录]")
        print("示例: python scanner.py ~/Pictures/输入")
        sys.exit(1)

    source = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else None

    scan_directory(source, output)
