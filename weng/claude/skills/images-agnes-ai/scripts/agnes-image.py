#!/usr/bin/env python3
"""Agnes AI Image CLI - text-to-image, image-to-image, and image recognition."""

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.request
import ssl

API_BASE = "https://apihub.agnes-ai.com"
IMAGE_ENDPOINT = API_BASE + "/v1/images/generations"
CHAT_ENDPOINT = API_BASE + "/v1/chat/completions"
DEFAULT_IMAGE_MODEL = "agnes-image-2.0-flash"
DEFAULT_VISION_MODEL = "agnes-2.0-flash"


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
    """Resolve local file path to data URI, or return URL as-is."""
    if os.path.isfile(image):
        return image_to_data_uri(image)
    return image


def api_request(endpoint, body, timeout=120):
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


def download_file(url, path):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=60, context=ssl_ctx()) as resp:
        with open(path, "wb") as f:
            f.write(resp.read())


def cmd_generate(args):
    """Text-to-image or image-to-image generation."""
    body = {
        "model": args.model,
        "prompt": args.prompt,
        "n": args.n,
        "size": args.size,
    }
    if args.seed is not None:
        body["seed"] = args.seed

    if args.image:
        body["extra_body"] = {
            "image": [resolve_image(args.image)],
            "response_format": "url",
        }

    result = api_request(IMAGE_ENDPOINT, body)
    urls = [item["url"] for item in result.get("data", []) if item.get("url")]

    if not urls:
        print("No images returned.", file=sys.stderr)
        print(json.dumps(result, indent=2))
        sys.exit(1)

    for i, url in enumerate(urls):
        print(url)
        if args.output:
            out_path = args.output if args.n == 1 else "%s_%d%s" % (
                os.path.splitext(args.output)[0], i, os.path.splitext(args.output)[1] or ".png"
            )
            download_file(url, out_path)
            print("Saved: %s" % out_path)


def cmd_recognize(args):
    """Image recognition / understanding."""
    image_url = resolve_image(args.image)
    prompt = args.prompt or "Describe this image in detail."

    body = {
        "model": args.model or DEFAULT_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
        "max_tokens": args.max_tokens,
    }

    result = api_request(CHAT_ENDPOINT, body)
    choices = result.get("choices", [])
    if choices:
        content = choices[0].get("message", {}).get("content", "")
        print(content)
    else:
        print("No response.", file=sys.stderr)
        print(json.dumps(result, indent=2))
        sys.exit(1)


def main():
    # Check if first arg is a known subcommand
    known_commands = ("generate", "recognize")
    if len(sys.argv) > 1 and sys.argv[1] in known_commands:
        command = sys.argv[1]
        rest = sys.argv[2:]
    else:
        command = "generate"
        rest = sys.argv[1:]

    if command == "generate":
        parser = argparse.ArgumentParser(description="Agnes AI Image Generation")
        parser.add_argument("--prompt", "-p", required=True, help="Text prompt")
        parser.add_argument("--model", "-m", default=DEFAULT_IMAGE_MODEL, help="Model name")
        parser.add_argument("--size", "-s", default="1024x1024", help="Image size")
        parser.add_argument("--n", type=int, default=1, help="Number of images")
        parser.add_argument("--seed", type=int, default=None, help="Seed")
        parser.add_argument("--image", "-i", default=None, help="Input image (URL or local path, for i2i)")
        parser.add_argument("--output", "-o", default=None, help="Save to local path")
        args = parser.parse_args(rest)
        cmd_generate(args)
    elif command == "recognize":
        parser = argparse.ArgumentParser(description="Agnes AI Image Recognition")
        parser.add_argument("--image", "-i", required=True, help="Image URL or local path")
        parser.add_argument("--prompt", "-p", default=None, help="Question about the image")
        parser.add_argument("--model", "-m", default=DEFAULT_VISION_MODEL, help="Vision model")
        parser.add_argument("--max-tokens", type=int, default=1024, help="Max response tokens")
        args = parser.parse_args(rest)
        cmd_recognize(args)


if __name__ == "__main__":
    main()
