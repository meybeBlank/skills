# Photo Manager

照片整理与纪念视频生成助手。

## 我能做什么

- **整理** - 扫描照片，按年月自动分类
- **理解** - 分析照片内容（场景、情绪、标签）
- **聚类** - 按内容智能分段（对话式交互）
- **生成音乐** - 根据 segment 内容生成歌词+背景音乐
- **生成视频** - LLM 排序 + FFmpeg 合成 + 背景音乐

## 工作流程

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  Step 1: 整理                                           │
│    scanner.py → 扫描 → library/photos/{year}/{month}/   │
│                                                          │
│  Step 2: 理解                                           │
│    image_understanding_batch.py → AI 分析               │
│                                                          │
│  Step 3: 聚类 (对话式)                                   │
│    segmenter.py --preview → 分析结果 → 用户确认 →        │
│    segment_01_名称/ (info.json)                         │
│                                                          │
│  Step 4: 生成音乐                                        │
│    music_generator.py → segment_*/lyrics.json + bgm.mp3 │
│                                                          │
│  Step 5: 生成视频                                        │
│    video_maker.py → videos/{year}/{month}/名称.mp4       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## 对话交互示例

```
用户：帮我聚类
Agent：📊 聚类预览（共 13 个分段，每段 1 张）

建议聚合方案：
A: 2 个分段（室内/户外）
B: 3 个分段（超市、户外、室内）
C: 4 个分段

用户：分为两个就够了
Agent：建议：
  居家日常 - 6张（超市购物车等）
  户外游玩 - 7张（游乐场、水族馆等）

用户：确认
Agent：✅ segments 已生成

用户：生成音乐
Agent：开始生成...
  segment_01: 歌词《推着小车去远方》+ 音乐 ✅
  segment_02: 歌词《童年乐园》+ 音乐 ✅

用户：生成视频
Agent：开始生成视频...
  segment_01: 孩子.mp4 ✅
  segment_02: 户外.mp4 ✅
```

## 目录结构

```
library/
├── photos/
│   └── {year}/
│       └── {month}/
│           ├── metadata.json       # 月份汇总 + AI 理解
│           ├── IMG_001.jpg        # 原始媒体文件
│           ├── segment_01_名称/   # 分段（直接在下）
│           │   ├── info.json      # 分段信息（无冗余拷贝）
│           │   ├── lyrics.json    # 歌词
│           │   └── bgm.mp3        # 背景音乐
│           └── segment_02_名称/
└── videos/
    └── {year}/
        └── {month}/
            ├── 名称.mp4           # 输出视频
            └── 名称.mp4
```

## 快速命令

| 操作 | 命令 |
|------|------|
| 整理照片 | `python scripts/scanner.py <目录>` |
| 理解照片 | `python scripts/image_understanding_batch.py <目录>` |
| 聚类预览 | `python scripts/segmenter.py <月份> --preview` |
| 生成聚类 | `python scripts/segmenter.py <月份> --generate --threshold 0.1` |
| 生成音乐 | `python scripts/music_generator.py <segment_dir>` |
| 生成视频 | `python scripts/video_maker.py <segment_dir>` |

## 配置

编辑 `config/settings.yaml`:

```yaml
paths:
  library: ./library
  temp: /tmp/photo-manager

video:
  fps: 24
  duration_per_photo: 3
  resolution: "1920x1080"
```
