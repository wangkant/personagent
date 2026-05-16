"""tools/import_stickers_folder.py — 批量把文件夹里的图片导入 sticker 库 + 立刻打 tag。

不依赖群上下文,直接 OCR 文字 + GLM-4V vision 推语义打 tag,适合 cold start。

Usage:
    python tools/import_stickers_folder.py <src_folder>
    python tools/import_stickers_folder.py "<your sticker folder>"
    python tools/import_stickers_folder.py --limit 50 <src_folder>     # 只导前 N 张
    python tools/import_stickers_folder.py --no-tag <src_folder>       # 只复制不 tag
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

import httpx

GLM_API_KEY = os.getenv("GLM_API_KEY", "")
GLM_BASE_URL = os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4").rstrip("/")
VISION_MODEL = os.getenv("VISION_MODEL", "glm-4v-flash")

STICKERS_DIR = ROOT / "stickers" / "auto"
STICKERS_JSON = ROOT / "stickers.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("import")


VISION_PROMPT = (
    "这张图是 QQ/微信群里用的**表情包**（不是真照片）。\n"
    "**任务：给它打 tag，严格按 JSON 一行输出。**\n"
    "\n"
    "硬规则：\n"
    "1. 看不清/打不开 → 输出 `{\"meaning\":\"看不到\",\"tags\":[]}`\n"
    "2. **重含义不重像素**——错『一只柴犬』 对『doge 笑/嘲讽』\n"
    "3. 图上有文字必读出来融进 meaning，例『字面「绝了」+ 配图夸张』\n"
    "4. 著名梗直接报名字：doge / 无语熊猫 / 摸鱼大鱼 / 流泪猫猫头 / 委屈鼠 / 你说得对 等\n"
    "\n"
    "JSON 字段：\n"
    "- meaning: 2-12 字描述这张表情包的语义/情绪/梗名\n"
    "- tags: 2-4 个简短标签便于按情绪检索，例如 嘲讽/笑/无语/抱抱/敷衍/震惊/委屈/疑惑\n"
    "\n"
    "示例输出：\n"
    '{"meaning":"doge 笑/嘲讽","tags":["嘲讽","doge","笑"]}\n'
    '{"meaning":"无语猫.jpg","tags":["无语","敷衍","吐槽"]}\n'
    '{"meaning":"求抱抱委屈","tags":["委屈","抱抱","求安慰"]}'
)


def guess_ext(b: bytes) -> str | None:
    if b[:8] == b"\x89PNG\r\n\x1a\n": return "png"
    if b[:3] == b"\xff\xd8\xff":      return "jpg"
    if b[:4] == b"GIF8":              return "gif"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP": return "webp"
    return None


def guess_mime(ext: str) -> str:
    return {"png":"image/png","jpg":"image/jpeg","gif":"image/gif","webp":"image/webp"}.get(ext, "image/jpeg")


async def tag_image(client: httpx.AsyncClient, img_bytes: bytes, ext: str) -> dict | None:
    if len(img_bytes) > 5_000_000:
        return None
    b64 = base64.b64encode(img_bytes).decode()
    mime = guess_mime(ext)
    data_url = f"data:{mime};base64,{b64}"
    try:
        r = await client.post(
            f"{GLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {GLM_API_KEY}"},
            json={
                "model": VISION_MODEL,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }],
                "max_tokens": 150,
                "temperature": 0.3,
            },
            timeout=30,
        )
        if r.status_code != 200:
            logger.debug("GLM HTTP %d: %s", r.status_code, r.text[:120])
            return None
        text = ((r.json().get("choices") or [{}])[0]
                .get("message", {}).get("content", "") or "").strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            logger.debug("non-json: %s", text[:100])
            return None
        meaning = (parsed.get("meaning") or "").strip()[:50]
        tags = [str(t).strip()[:20] for t in (parsed.get("tags") or []) if t][:6]
        if not meaning or meaning == "看不到" or not tags:
            return None
        return {"meaning": meaning, "tags": tags}
    except Exception as e:
        logger.debug("tag failed: %s: %s", type(e).__name__, e)
        return None


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("src", help="源图片文件夹")
    p.add_argument("--limit", type=int, default=0, help="只导前 N 张 (0=全部)")
    p.add_argument("--no-tag", action="store_true", help="只复制，不打 tag")
    args = p.parse_args()

    src = Path(args.src)
    if not src.is_dir():
        logger.error("不是文件夹: %s", src)
        return 1

    # Load existing library
    STICKERS_DIR.mkdir(parents=True, exist_ok=True)
    if STICKERS_JSON.exists():
        entries = json.loads(STICKERS_JSON.read_text(encoding="utf-8"))
    else:
        entries = {}
    md5_index = {v.get("md5"): k for k, v in entries.items() if isinstance(v, dict) and v.get("md5")}

    # Enumerate source files
    files = sorted([p for p in src.iterdir() if p.is_file()])
    if args.limit:
        files = files[:args.limit]
    logger.info("源文件夹 %s: %d 张", src.name, len(files))

    if not args.no_tag and not GLM_API_KEY:
        logger.error("GLM_API_KEY 未配置,无法 tag。用 --no-tag 跳过 tagging 或先配 .env")
        return 1

    new_count = 0
    tagged_count = 0
    skipped_dup = 0
    skipped_unsupported = 0

    async with httpx.AsyncClient() as client:
        for i, src_file in enumerate(files):
            try:
                img_bytes = src_file.read_bytes()
            except Exception as e:
                logger.debug("read failed: %s", e)
                continue
            if len(img_bytes) < 200 or len(img_bytes) > 5_000_000:
                skipped_unsupported += 1
                continue
            ext = guess_ext(img_bytes)
            if not ext:
                skipped_unsupported += 1
                continue
            md5 = hashlib.md5(img_bytes).hexdigest()
            if md5 in md5_index:
                skipped_dup += 1
                continue

            filename = f"auto/{md5}.{ext}"
            (ROOT / "stickers" / filename).write_bytes(img_bytes)

            entry = {
                "md5": md5,
                "src_user": "imported",
                "src_group": "",
                "first_seen": time.time(),
                "use_count": 0,
                "seen_contexts": [],
                "meaning": "",
                "tags": [],
                "auto_tagged": False,
                "imported_from": str(src_file),
            }
            entries[filename] = entry
            md5_index[md5] = filename
            new_count += 1

            if not args.no_tag:
                tagged = await tag_image(client, img_bytes, ext)
                if tagged:
                    entry["meaning"] = tagged["meaning"]
                    entry["tags"] = tagged["tags"]
                    entry["auto_tagged"] = True
                    entry["tagged_ts"] = time.time()
                    tagged_count += 1
                    logger.info("[%d/%d] %s: %s %s",
                                i + 1, len(files), md5[:8],
                                tagged["meaning"], tagged["tags"])
                else:
                    logger.info("[%d/%d] %s: 入库未 tag",
                                i + 1, len(files), md5[:8])

            # Save every 20 stickers to avoid losing progress
            if new_count % 20 == 0:
                STICKERS_JSON.write_text(
                    json.dumps(entries, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

    STICKERS_JSON.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("完成: 新增 %d, 已 tag %d, 重复跳过 %d, 不支持 %d, 库总量 %d",
                new_count, tagged_count, skipped_dup, skipped_unsupported, len(entries))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
