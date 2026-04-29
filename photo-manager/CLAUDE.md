# Photo Manager - Agent 开发指南

本文档为 Agent 提供在此 Skill 中工作的指导。

## 项目结构

```
photo-manager/
├── skill.md                    # Skill 入口
├── CLAUDE.md                   # Agent 开发指南（本文档）
├── VALIDATION_CHECKLIST.md     # 验证清单
├── config/
│   └── settings.yaml           # 用户配置
├── scripts/
│   ├── config.py               # 配置加载
│   ├── utils.py                 # 工具函数
│   ├── scanner.py               # 扫描整理
│   ├── image_understanding_batch.py  # 图片理解 (MiniMax VLM)
│   ├── segmenter.py             # 智能聚类（对话式）
│   ├── music_generator.py        # 音乐生成（歌词+音乐两步）
│   └── video_maker.py           # 视频合成 (FFmpeg + LLM排序)
└── library/
    ├── photos/                  # 整理后的照片库
    │   └── {year}/
    │       └── {month}/
    │           ├── metadata.json
    │           ├── IMG_001.jpg
    │           └── segment_01_名称/
    │               ├── info.json
    │               ├── lyrics.json
    │               └── bgm.mp3
    └── videos/                  # 生成的视频输出
        └── {year}/
            └── {month}/
                └── 名称.mp4
```

## 核心设计决策

1. **无数据库** — 使用文件系统 + JSON 元数据，便于迁移
2. **无冗余拷贝** — segment 只存 info.json，图片从原目录读取
3. **对话式聚类** — Agent 展示预览，用户确认后再生成
4. **LLM 排序** — 视频中图片顺序由 LLM 根据内容决定
5. **两步音乐** — 先歌词生成，再音乐生成

## metadata.json 格式

```json
{
  "year": "2024",
  "month": "01",
  "media_count": 50,
  "photo_count": 45,
  "video_count": 5,
  "ai_understood": true,
  "ai_understood_at": "2024-01-15T10:00:00",
  "created_at": "2024-01-15T10:00:00",
  "media": [
    {
      "filename": "IMG_001.jpg",
      "original_name": "IMG_001.jpg",
      "source_path": "/path/to/IMG_001.jpg",
      "stored_path": "library/photos/2024/01/IMG_001.jpg",
      "hash": "abc123...",
      "date_taken": "2024-01-10T15:30:00",
      "date_source": "exif",
      "type": "image",
      "extension": ".jpg",
      "ai_understanding": {
        "scene": "场景描述",
        "emotion": "情绪",
        "tags": ["标签1", "标签2"],
        "suitable_music": "适合的背景音乐风格"
      }
    }
  ]
}
```

## segment info.json 格式

```json
{
  "id": 1,
  "name": "居家日常",
  "media_count": 6,
  "representative_scene": "...",
  "emotion": "温馨",
  "tags": ["孩子", "超市"],
  "media": [
    {
      "filename": "wx_camera_xxx.jpg",
      "ai_understanding": {
        "scene": "...",
        "emotion": "...",
        "tags": [...]
      }
    }
  ]
}
```

## 聚类方法

| 方法 | 说明 | 阈值建议 |
|------|------|----------|
| `scene` | 按场景描述相似度聚类 | 0.6 |
| `emotion` | 按情绪关键词分组 | 0.5 |
| `tags` | 按标签重叠度聚类 | 0.3 |
| `time_content` | 时间邻近 + 内容相似 | 0.5 |

阈值越小越容易合并。通过 `--threshold` 参数调整。

## 日期解析优先级

| 优先级 | 来源 | 适用 |
|--------|------|------|
| 1 | EXIF DateTimeOriginal | 图片 |
| 2 | FFprobe creation_time | 视频 |
| 3 | 文件名解析 | 所有文件 |
| 4 | unknown/13 目录 | 无法解析的文件 |

### 支持的文件名格式

| 格式 | 示例 |
|------|------|
| IMG_YYYYMMDD_HHmmss.jpg | IMG_20230213_191650.jpg |
| wx_camera_时间戳.jpg | wx_camera_1698475744144.jpg (毫秒时间戳) |
| JPEG_YYYYMMDD_HHmmss.jpg | JPEG_20210607_153606.jpg |
| Screenshot_YYYY-MM-DD-HH-mm-ss.jpg | Screenshot_2024-07-13-20-11-56-651_com.tencent.mm.jpg |
| YYYYMMDD_HHmmss.jpg | 20150109_161130.jpg |

## 对话式聚类流程

聚类通过 Agent 对话引导用户完成：

1. Agent 运行 `--preview` 展示聚类预览
2. Agent 提出多种聚合方案供用户选择
3. 用户可调整阈值或手动指定合并
4. 用户确认后 Agent 运行 `--generate`
5. 生成 segment 目录和 info.json

### 聚类对话示例

```
Agent：📊 聚类预览（共 13 个分段）

建议聚合方案：
A: 2 个分段（室内/户外）
B: 3 个分段

用户：分为两个就够了
Agent：建议：
  居家日常 - 6张（超市购物车等）
  户外游玩 - 7张（游乐场、水族馆等）
  确认生成？

用户：确认
Agent：✅ segments 已生成
```

## 重要约定

1. **所有文件内容更改必须经过用户确认，禁止直接更改**
2. 元数据文件使用 `ensure_ascii=False` 保持中文可读性
3. segment 只包含 info.json，不拷贝原图
4. 图片路径通过 month_dir / filename 读取
5. 视频输出到 videos/{year}/{month}/

## 常用命令

```bash
# 扫描照片入库
python scripts/scanner.py /path/to/photos

# 使用 MiniMax VLM API 分析照片
python scripts/image_understanding_batch.py library/photos

# 聚类预览
python scripts/segmenter.py library/photos/2024/07 --preview

# 生成聚类（阈值越小越容易合并）
python scripts/segmenter.py library/photos/2024/07 --generate --threshold 0.1

# 为 segment 生成音乐（歌词+音乐两步）
python scripts/music_generator.py library/photos/2024/07/segment_01_名称

# 为 segment 生成视频（LLM排序 + FFmpeg + 背景音乐）
python scripts/video_maker.py library/photos/2024/07/segment_01_名称
```
