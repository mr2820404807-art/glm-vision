#!/usr/bin/env python3
"""GLM Vision CLI — describe / OCR / ask about an image.

Backed by Zhipu GLM vision models (OpenAI-compatible API).

Usage:
  vision.py describe <image> [prompt]
  vision.py ocr <image> [language]
  vision.py ask <image> <question>

<image> can be: local file path | http(s) URL | data: URL | base64 string

Env:
  ZHIPU_API_KEY  (required)
  ZHIPU_BASE_URL (optional, default https://open.bigmodel.cn/api/paas/v4)
  GLM_VISION_MODEL (optional, default glm-4.1v-thinking-flash)
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_MODEL = "glm-4.1v-thinking-flash"
MAX_IMAGE_BYTES = 15 * 1024 * 1024
RETRY_MAX = 5
RETRY_BASE_DELAY = 5.0


def cfg(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name) or default


def detect_mime(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".ico": "image/x-icon",
    }.get(ext, "image/jpeg")


def is_http_url(s: str) -> bool:
    try:
        return urlparse(s).scheme in ("http", "https")
    except ValueError:
        return False


def looks_like_base64(s: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9+/=]+", s)) and len(s) % 4 == 0


def auto_compress(raw: bytes, mime: str, max_bytes: int = 5 * 1024 * 1024, max_side: int = 1600) -> tuple[bytes, str]:
    """Compress oversized images so the vision API accepts them."""
    if len(raw) <= max_bytes:
        return raw, mime
    try:
        from io import BytesIO
        from PIL import Image
    except ImportError:
        return raw, mime
    try:
        img = Image.open(BytesIO(raw))
        img.load()
        if max(img.size) > max_side:
            img.thumbnail((max_side, max_side))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        out = BytesIO()
        img.save(out, format="JPEG", quality=85)
        compressed = out.getvalue()
        if len(compressed) >= len(raw):
            return raw, mime
        print(f"[compress] {len(raw)} -> {len(compressed)} bytes (mime {mime} -> image/jpeg)", file=sys.stderr)
        return compressed, "image/jpeg"
    except Exception as exc:  # noqa: BLE001
        print(f"[compress] skipped: {exc}", file=sys.stderr)
        return raw, mime


def build_vision_message(prompt: str, image_input: str, detail: bool = True) -> dict:
    content: list[dict] = []

    if is_http_url(image_input):
        content.append({
            "type": "image_url",
            "image_url": {"url": image_input, "detail": "high" if detail else "low"},
        })
    elif image_input.startswith("data:"):
        content.append({"type": "image_url", "image_url": {"url": image_input}})
    else:
        if image_input.startswith("base64:"):
            raw = base64.b64decode(image_input[len("base64:"):], validate=True)
            mime = "image/jpeg"
        elif len(image_input) > 4096 and looks_like_base64(image_input):
            raw = base64.b64decode(image_input, validate=True)
            mime = "image/jpeg"
        else:
            path = Path(image_input).expanduser()
            if not path.is_file():
                raise ValueError(f"image file not found: {path}")
            raw = path.read_bytes()
            mime = detect_mime(str(path))

        if len(raw) > MAX_IMAGE_BYTES:
            raise ValueError(
                f"image too large ({len(raw)} bytes > {MAX_IMAGE_BYTES}); "
                "resize/compress it or use an http(s) URL instead"
            )
        raw, mime = auto_compress(raw, mime)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{base64.b64encode(raw).decode()}", "detail": "high" if detail else "low"},
        })

    content.append({"type": "text", "text": prompt})
    return {"role": "user", "content": content}


def clean_answer(text: str) -> str:
    """Strip <think> reasoning blocks; keep only the final answer."""
    m = re.search(r"<answer>(.*?)</answer>", text, re.S)
    if m:
        return m.group(1).strip()
    return text


def call_glm(messages: list[dict], max_tokens: int = 2048) -> str:
    key = cfg("ZHIPU_API_KEY")
    if not key:
        raise RuntimeError(
            "ZHIPU_API_KEY is not set. Get one at https://open.bigmodel.cn"
        )
    payload = {
        "model": cfg("GLM_VISION_MODEL", DEFAULT_MODEL),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "stream": False,
    }
    try:
        resp = httpx.post(
            f"{cfg('ZHIPU_BASE_URL', DEFAULT_BASE_URL)}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
            timeout=120.0,
        )
    except httpx.HTTPError as exc:
        raise RuntimeError(f"GLM API request failed: {exc}") from exc

    if resp.status_code == 429 and RETRY_MAX > 0:
        delay = RETRY_BASE_DELAY
        for attempt in range(1, RETRY_MAX + 1):
            print(f"[retry {attempt}/{RETRY_MAX}] rate limited (429), waiting {delay:.0f}s...", file=sys.stderr)
            time.sleep(delay)
            try:
                resp = httpx.post(
                    f"{cfg('ZHIPU_BASE_URL', DEFAULT_BASE_URL)}/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=120.0,
                )
            except httpx.HTTPError as exc:
                raise RuntimeError(f"GLM API request failed: {exc}") from exc
            if resp.status_code != 429:
                break
            delay *= 2

    if resp.status_code >= 400:
        raise RuntimeError(f"GLM API error {resp.status_code}: {resp.text[:500]}")

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
        return clean_answer(content)
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            f"Unexpected GLM response: {json.dumps(data, ensure_ascii=False)[:500]}"
        ) from exc


def main() -> int:
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if len(sys.argv) < 3:
        print(__doc__)
        return 2

    action = sys.argv[1]
    image = sys.argv[2]

    try:
        if action == "describe":
            prompt = sys.argv[3] if len(sys.argv) > 3 else "Describe this image in detail."
            msg = build_vision_message(prompt, image, True)
            print(call_glm([msg], max_tokens=1024))
        elif action == "ocr":
            lang = sys.argv[3] if len(sys.argv) > 3 else "auto"
            prompt = (
                "Extract ALL visible text from this image exactly as written. "
                "Preserve line breaks and layout order. "
                + (f"The text is in {lang}. " if lang != "auto" else "")
                + "If there is no text, reply with an empty string."
            )
            msg = build_vision_message(prompt, image, True)
            print(call_glm([msg], max_tokens=1024))
        elif action == "ask":
            if len(sys.argv) < 4:
                print("ask requires a question: vision.py ask <image> <question>", file=sys.stderr)
                return 2
            msg = build_vision_message(sys.argv[3], image, True)
            print(call_glm([msg], max_tokens=1024))
        else:
            print(f"unknown action: {action}", file=sys.stderr)
            return 2
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
