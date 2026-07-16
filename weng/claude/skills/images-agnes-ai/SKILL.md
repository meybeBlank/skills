---
name: images-agnes-ai
description: This skill should be used when the user asks to "generate an image", "create a picture", "draw", "text to image", "image to image", "img2img", "edit image", "transform image style", "describe image", "recognize image", "image understanding", "generate video", "text to video", "image to video", "animate image", or any image/video generation and recognition task using Agnes AI API.
---

# Agnes AI Multimodal Generation

Generate images, recognize image content, and generate videos via Agnes AI API.

## API Configuration

- **Base**: `https://apihub.agnes-ai.com`
- **Auth**: `Authorization: Bearer <API_KEY>`
- **Content-Type**: `application/json`

API Key: environment variable `AGNES_API_KEY` or file `~/.agnes-ai-key`.

## Available Models

| Model | Capability | Endpoint |
|-------|-----------|----------|
| `agnes-image-2.0-flash` | Image generation (t2i, i2i) | `/v1/images/generations` |
| `agnes-image-2.1-flash` | Image generation (latest) | `/v1/images/generations` |
| `agnes-2.0-flash` | Image recognition / vision | `/v1/chat/completions` |
| `agnes-video-v2.0` | Video generation (t2v, i2v) | `/v1/videos` |

---

## 1. Text-to-Image

```bash
scripts/agnes-image.py --prompt "A futuristic city at sunset" --size 1024x1024
```

```json
{
  "model": "agnes-image-2.0-flash",
  "prompt": "A futuristic city at sunset",
  "n": 1, "size": "1024x1024", "seed": 42
}
```

## 2. Image-to-Image

```bash
scripts/agnes-image.py --prompt "turn into watercolor" --image "https://example.com/photo.png"
scripts/agnes-image.py --prompt "add a hat" --image "/path/to/local.png"
```

```json
{
  "model": "agnes-image-2.0-flash",
  "prompt": "turn into watercolor style",
  "n": 1, "size": "1024x1024",
  "extra_body": {
    "image": ["https://example.com/photo.png"],
    "response_format": "url"
  }
}
```

## 3. Image Recognition

Analyze/describe image content using the vision model (`agnes-2.0-flash`).

```bash
scripts/agnes-image.py recognize --image "https://example.com/photo.png" --prompt "Describe this image"
```

Endpoint: `POST /v1/chat/completions`

```json
{
  "model": "agnes-2.0-flash",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "Describe this image in detail."},
        {"type": "image_url", "image_url": {"url": "https://example.com/photo.png"}}
      ]
    }
  ],
  "max_tokens": 1024
}
```

Response: standard OpenAI-compatible chat completion with `choices[0].message.content`.

## 4. Video Generation (Async)

Video generation is **asynchronous**: submit a task, then poll for status.

### Text-to-Video

```bash
scripts/agnes-video.py --prompt "A cat walking on a beach at sunset" --width 1152 --height 768
```

```json
{
  "model": "agnes-video-v2.0",
  "prompt": "A cat walking on a beach at sunset",
  "height": 768, "width": 1152,
  "num_frames": 121, "frame_rate": 24
}
```

### Image-to-Video (animate single image)

```bash
scripts/agnes-video.py --prompt "The woman turns around" --image "https://example.com/photo.png"
```

```json
{
  "model": "agnes-video-v2.0",
  "prompt": "The woman turns around",
  "image": "https://example.com/photo.png",
  "num_frames": 121, "frame_rate": 24
}
```

### Multi-Image / Keyframe Video

```bash
scripts/agnes-video.py --prompt "Smooth transition" --images img1.png img2.png
scripts/agnes-video.py --prompt "Smooth transition" --images img1.png img2.png --mode keyframes
```

```json
{
  "model": "agnes-video-v2.0",
  "prompt": "Smooth transition between scenes",
  "extra_body": {
    "image": ["https://example.com/img1.png", "https://example.com/img2.png"],
    "mode": "keyframes"
  },
  "num_frames": 121, "frame_rate": 24
}
```

### Check Video Status

```bash
scripts/agnes-video.py status <task_id>
```

`GET /v1/videos/{task_id}` — returns `status`: `queued` → `processing` → `completed`.

---

## Parameters Quick Reference

### Image Generation

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `model` | Yes | agnes-image-2.0-flash | Model |
| `prompt` | Yes | - | Text description |
| `n` | No | 1 | Number of images |
| `size` | No | 1024x1024 | Dimensions (512x512, 1024x768, etc.) |
| `seed` | No | random | Reproducibility seed |
| `extra_body.image` | img2img | - | Input image URLs (array) |
| `extra_body.response_format` | No | url | "url" or "b64_json" (must be in extra_body) |

### Video Generation

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `model` | Yes | agnes-video-v2.0 | Model |
| `prompt` | Yes | - | Text description |
| `height` | No | 768 | Video height |
| `width` | No | 1152 | Video width |
| `num_frames` | No | 121 | Frame count (~5s at 24fps) |
| `frame_rate` | No | 24 | FPS |
| `image` | i2v | - | Single input image URL |
| `extra_body.image` | multi | - | Multiple image URLs (array) |
| `extra_body.mode` | No | - | "keyframes" for keyframe animation |

## Important Notes

- `response_format` at top level causes 400 for images; place inside `extra_body`
- Image generation: synchronous, timeout >= 60s
- Video generation: **asynchronous**, poll `GET /v1/videos/{task_id}` for completion
- Input images accept URLs or Data URI Base64 (local files auto-converted)

## Scripts

- **`scripts/agnes-image.py`** — Image generation (t2i, i2i) and recognition
- **`scripts/agnes-video.py`** — Video generation (t2v, i2v, multi-image, keyframes) and status polling

## API Documentation

- [Agnes 2.0 Flash (Vision)](https://agnes-ai.com/doc/agnes-20-flash)
- [Agnes Image 2.0 Flash](https://agnes-ai.com/doc/agnes-image-20-flash)
- [Agnes Image 2.1 Flash](https://agnes-ai.com/doc/agnes-image-21-flash)
- [Agnes Video V2.0](https://agnes-ai.com/doc/agnes-video-v20)
- [Agnes API Overview](https://agnes-ai.com/doc/overview)
