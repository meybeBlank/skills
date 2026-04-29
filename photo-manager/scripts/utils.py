"""
utils.py - 工具函数
"""
import hashlib
import os
import re
import subprocess
from pathlib import Path
from datetime import datetime
from PIL import Image


def compute_file_hash(file_path):
    """计算文件的 MD5 哈希"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_exif_date(file_path):
    """从 EXIF 中提取拍摄日期"""
    try:
        img = Image.open(file_path)
        exif = img._getexif()
        if not exif:
            return None

        for tag_id, value in exif.items():
            from PIL.ExifTags import TAGS
            tag = TAGS.get(tag_id, tag_id)
            if tag == "DateTimeOriginal":
                return value
        return None
    except Exception:
        return None


def parse_exif_date(date_str):
    """解析 EXIF 日期字符串"""
    if not date_str:
        return None
    try:
        # EXIF 格式: "2015:01:09 16:11:30"
        date_str = date_str.replace(":", "-", 2)
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def get_video_date(file_path):
    """从视频中提取拍摄日期（使用 FFprobe）"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-show_entries', 'format_tags=creation_time',
            '-of', 'csv=p=0',
            str(file_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and result.stdout.strip():
            date_str = result.stdout.strip()
            match = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_str)
            if match:
                return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except Exception:
        pass

    return None


def ensure_filename_unique(dest_dir, filename):
    """确保文件名不冲突"""
    dest_path = Path(dest_dir) / filename
    if not dest_path.exists():
        return filename

    stem = Path(filename).stem
    ext = Path(filename).suffix
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{ext}"
        new_path = Path(dest_dir) / new_name
        if not new_path.exists():
            return new_name
        counter += 1


def ensure_dir(path):
    """确保目录存在"""
    Path(path).mkdir(parents=True, exist_ok=True)


def parse_filename_date(filename):
    """
    从文件名中解析日期

    支持格式:
    - IMG_20230213_191650.jpg (标准日期格式)
    - wx_camera_1698475744144.jpg (Unix时间戳，13位)
    - JPEG_20210607_153606.jpg
    - Screenshot_2024-07-13-20-11-56-651_com.tencent.mm.jpg
    - YYYYMMDD_HHmmss.jpg
    - IMG_YYYYMMDD.jpg

    Returns:
        datetime 或 None
    """
    name = Path(filename).stem

    # 检查是否是 Unix 时间戳格式 (13位数字，如 wx_camera_1698475744144)
    timestamp_match = re.match(r'^([A-Za-z_]+)?(\d{13})$', name)
    if timestamp_match:
        try:
            timestamp_ms = int(timestamp_match.group(2))
            # 毫秒转秒，只接受合理的时间戳范围 (2000-2100年)
            timestamp_s = timestamp_ms / 1000
            if 946684800 <= timestamp_s <= 4102444800:
                return datetime.fromtimestamp(timestamp_s)
        except (ValueError, OSError):
            pass

    # 标准日期格式模式
    patterns = [
        # IMG_20230213_191650.jpg
        (r'^IMG_(\d{8})_(\d{6})$', '%Y%m%d%H%M%S'),
        # JPEG_20210607_153606.jpg 或 YYYYMMDD_HHmmss
        (r'^([A-Za-z_]+)?(\d{8})_(\d{6})$', '%Y%m%d%H%M%S'),
        # Screenshot_2024-07-13-20-11-56-651_com.tencent.mm
        (r'^Screenshot_(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})', 'screenshot'),
        # IMG_20230213.jpg (无时间)
        (r'^IMG_(\d{8})$', '%Y%m%d'),
        # 纯日期 YYYYMMDD
        (r'^(\d{8})$', '%Y%m%d'),
    ]

    for pattern, fmt in patterns:
        match = re.match(pattern, name)
        if match:
            try:
                if fmt == '%Y%m%d%H%M%S':
                    date_str = f"{match.group(2 if len(match.groups()) == 3 else 1)}{match.group(3 if len(match.groups()) == 3 else 2)}"
                    return datetime.strptime(date_str, '%Y%m%d%H%M%S')
                elif fmt == '%Y%m%d':
                    if len(match.groups()) >= 2 and match.group(2):
                        date_str = f"{match.group(1)}{match.group(2)}"
                        return datetime.strptime(date_str, '%Y%m%d%H%M%S')
                    else:
                        return datetime.strptime(match.group(1), '%Y%m%d')
                elif fmt == 'screenshot':
                    return datetime.strptime(
                        f"{match.group(1)}-{match.group(2)}-{match.group(3)} "
                        f"{match.group(4)}-{match.group(5)}-{match.group(6)}",
                        '%Y-%m-%d %H-%M-%S'
                    )
            except ValueError:
                continue

    return None


def create_thumbnail(file_path, size=(300, 300)):
    """创建缩略图"""
    try:
        img = Image.open(file_path)
        img.thumbnail(size, Image.LANCZOS)
        return img
    except Exception:
        return None
