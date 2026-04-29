"""
config.py - 配置加载模块
"""
import os
import yaml
from pathlib import Path


def load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 展开路径中的 ~
    for key in ["input", "library", "temp"]:
        if key in config.get("paths", {}):
            config["paths"][key] = os.path.expanduser(config["paths"][key])

    return config


def get_library_dir():
    """获取媒体库根目录"""
    config = load_config()
    library_path = config["paths"]["library"]

    # 如果是相对路径，相对于项目根目录
    if not os.path.isabs(library_path):
        project_root = Path(__file__).parent.parent
        return project_root / library_path

    return Path(library_path)


def get_photos_dir():
    """获取照片库目录"""
    return get_library_dir() / "photos"


def get_videos_dir():
    """获取视频输出目录"""
    return get_library_dir() / "videos"


def ensure_dir(path):
    """确保目录存在"""
    Path(path).mkdir(parents=True, exist_ok=True)


def get_config_value(key, default=None):
    """获取配置项"""
    config = load_config()
    keys = key.split(".")
    value = config
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return default
    return value if value is not None else default
