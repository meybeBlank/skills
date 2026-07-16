#!/usr/bin/env python3
"""Agnes AI Video Generation CLI - text-to-video, image-to-video, multi-image, keyframes."""

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.request
import ssl

API_BASE = "https://apihub.agnes-ai.com"
VIDEO_ENDPOINT = API_BASE + "/v1/videos"
DEFAULT_MODEL = "agnes-video-v2.0"


def get_api_key():
    key = os.environ.get("AGNES_API_KEY")
    if key:
        return key
    key_file = os.path.expanduser("~/.agnes-ai-key")
    if os.path.isfile(key_file):
        with open(key_file) as f:
            return f.read().strip()
    print("Error: Set AGNES_API_KEY env var or create ~/.agnes-ai-key", file=sys.stderr)
    sys.exit(1)


def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def image_to_data_uri(path):
    mime, _ = mimetypes.guess_type(path)
    if not mime:
        mime = "image/png"
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return "data:%s;base64,%s" % (mime, data)


def resolve_image(image):
    if os.path.isfile(image):
        return image_to_data_uri(image)
    return image


def api_post(endpoint, body, timeout=120):
    api_key = get_api_key()
    data = json.dumps(body).encode()
    headers = {
        "Authorization": "Bearer %s" % api_key,
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx()) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        print("API Error %d: %s" % (e.code, error_body), file=sys.stderr)
        sys.exit(1)


def api_get(endpoint, timeout=30):
    api_key = get_api_key()
    headers = {"Authorization": "Bearer %s" % api_key}
    req = urllib.request.Request(endpoint, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx()) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        print("API Error %d: %s" % (e.code, error_body), file=sys.stderr)
        sys.exit(1)


def cmd_generate(args):
    """Submit video generation task."""
    body = {
        "model": args.model,
        "prompt": args.prompt,
        "height": args.height,
        "width": args.width,
        "num_frames": args.num_frames,
        "frame_rate": args.frame_rate,
    }

    if args.image:
        # Single image-to-video
        body["image"] = resolve_image(args.image)
    elif args.images:
        # Multi-image or keyframes
        resolved = [resolve_image(img) for img in args.images]
        extra = {"image": resolved}
        if args.mode:
            extra["mode"] = args.mode
        body["extra_body"] = extra

    result = api_post(VIDEO_ENDPOINT, body)
    task_id = result.get("task_id") or result.get("id")
    status = result.get("status", "unknown")

    print("Task ID: %s" % task_id)
    print("Status: %s" % status)
    print("Size: %s" % result.get("size", ""))
    print("Duration: %ss" % result.get("seconds", ""))

    if args.wait:
        print("\nWaiting for completion...")
        poll_task(task_id, args.output)
    else:
        print("\nTo check status: agnes-video.py status %s" % task_id)


def cmd_status(args):
    """Check video task status."""
    poll_task(args.task_id, args.output, single_check=not args.wait)


def poll_task(task_id, output=None, single_check=False, max_wait=600, interval=10):
    """Poll task status until completion or timeout."""
    url = "%s/%s" % (VIDEO_ENDPOINT, task_id)
    elapsed = 0

    while True:
        result = api_get(url)
        status = result.get("status", "unknown")
        progress = result.get("progress", 0)

        if single_check:
            print(json.dumps(result, indent=2))
            if status == "completed":
                download_video(result, output)
            return

        print("\r[%ds] Status: %s, Progress: %s%%" % (elapsed, status, progress), end="")
        sys.stdout.flush()

        if status == "completed":
            print()
            download_video(result, output)
            return
        elif status in ("failed", "error"):
            print()
            print("Task failed: %s" % result.get("error", "unknown error"), file=sys.stderr)
            sys.exit(1)

        if elapsed >= max_wait:
            print()
            print("Timeout after %ds. Task ID: %s" % (max_wait, task_id), file=sys.stderr)
            sys.exit(1)

        time.sleep(interval)
        elapsed += interval


def download_video(result, output):
    """Extract and optionally download video URL from completed task."""
    # Try common response fields for video URL
    video_url = None
    for key in ("url", "video_url", "download_url", "remixed_from_video_id"):
        val = result.get(key)
        if val and isinstance(val, str) and (val.startswith("http://") or val.startswith("https://")):
            video_url = val
            break
    # Check nested data
    if not video_url and result.get("data"):
        data = result["data"]
        if isinstance(data, list) and data:
            video_url = data[0].get("url")
        elif isinstance(data, dict):
            video_url = data.get("url")

    if video_url:
        print("Video URL: %s" % video_url)
        if output:
            req = urllib.request.Request(video_url)
            with urllib.request.urlopen(req, timeout=120, context=ssl_ctx()) as resp:
                with open(output, "wb") as f:
                    f.write(resp.read())
            print("Saved: %s" % output)
    else:
        print("Task completed but no video URL found in response:")
        print(json.dumps(result, indent=2))


def make_generate_parser():
    parser = argparse.ArgumentParser(description="Agnes AI Video Generation")
    parser.add_argument("--prompt", "-p", required=True, help="Text prompt")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL, help="Model name")
    parser.add_argument("--width", "-W", type=int, default=1152, help="Video width")
    parser.add_argument("--height", "-H", type=int, default=768, help="Video height")
    parser.add_argument("--num-frames", type=int, default=121, help="Number of frames")
    parser.add_argument("--frame-rate", type=int, default=24, help="Frame rate (FPS)")
    parser.add_argument("--image", "-i", default=None, help="Single input image (URL or local)")
    parser.add_argument("--images", nargs="+", default=None, help="Multiple input images")
    parser.add_argument("--mode", default=None, help="Mode (e.g. 'keyframes')")
    parser.add_argument("--output", "-o", default=None, help="Save video to local path")
    parser.add_argument("--wait", "-w", action="store_true", help="Wait for completion")
    return parser


def main():
    known_commands = ("generate", "status")
    if len(sys.argv) > 1 and sys.argv[1] in known_commands:
        command = sys.argv[1]
        rest = sys.argv[2:]
    else:
        command = "generate"
        rest = sys.argv[1:]

    if command == "generate":
        args = make_generate_parser().parse_args(rest)
        cmd_generate(args)
    elif command == "status":
        parser = argparse.ArgumentParser(description="Check video task status")
        parser.add_argument("task_id", help="Task ID to check")
        parser.add_argument("--output", "-o", default=None, help="Save video if completed")
        parser.add_argument("--wait", "-w", action="store_true", help="Poll until completion")
        args = parser.parse_args(rest)
        cmd_status(args)


if __name__ == "__main__":
    main()
