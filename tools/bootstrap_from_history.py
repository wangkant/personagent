"""tools/bootstrap_from_history.py — one-shot bootstrap from NapCat group history.

Does two things:
  1) owner_profile.json: owner's sticker-send rate, text-length distribution, top stickers
  2) Downloads every sub_type=1 sticker seen in history to stickers/auto/<md5>.<ext>,
     capturing surrounding messages as seen_contexts (StickerLibrary tags them
     asynchronously once it has MIN_CONTEXTS_TO_TAG samples).

Usage:
    python tools/bootstrap_from_history.py             # both, default 2000 msgs per group
    python tools/bootstrap_from_history.py --no-stickers  # profile only
    python tools/bootstrap_from_history.py --limit 500    # pull fewer messages
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

import httpx

NAPCAT_API = os.getenv("NAPCAT_API", "http://127.0.0.1:3000").rstrip("/")
OWNER_QQ = os.getenv("OWNER_QQ", "")
BOT_QQ = os.getenv("BOT_QQ", "")
QQ_GROUPS = [g.strip() for g in os.getenv("QQ_GROUPS", "").split(",") if g.strip()]

STICKERS_DIR = ROOT / "stickers" / "auto"
STICKERS_JSON = ROOT / "stickers.json"
OWNER_PROFILE = ROOT / "owner_profile.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("bootstrap")

# ============ NapCat history ============
async def fetch_page(client: httpx.AsyncClient, group_id: str,
                     count: int, message_seq: int = 0) -> list[dict]:
    """One page of history. message_seq=0 means latest."""
    payload = {"group_id": int(group_id), "count": count}
    if message_seq:
        payload["message_seq"] = message_seq
    r = await client.post(f"{NAPCAT_API}/get_group_msg_history", json=payload)
    r.raise_for_status()
    data = r.json().get("data") or {}
    return data.get("messages") or []

async def pull_history(group_id: str, limit: int) -> list[dict]:
    """Paginate backward. NapCat returns oldest-first inside each page;
    message_seq of oldest msg in this page = anchor for next (older) page."""
    out: list[dict] = []
    seen_ids: set = set()
    cursor = 0
    page_size = 200
    async with httpx.AsyncClient(timeout=30) as client:
        while len(out) < limit:
            need = min(page_size, limit - len(out) + 10)
            msgs = await fetch_page(client, group_id, need, cursor)
            if not msgs:
                logger.info("  history exhausted")
                break
            fresh = [m for m in msgs if m.get("message_id") not in seen_ids]
            for m in fresh:
                seen_ids.add(m.get("message_id"))
            if not fresh:
                logger.info("  all duplicates — history reached")
                break
            out = fresh + out
            oldest_seq = int(msgs[0].get("message_seq", 0))
            new_cursor = oldest_seq - 1
            if new_cursor <= 0:
                logger.info("  reached origin (seq=%s)", oldest_seq)
                break
            cursor = new_cursor
            logger.info("  +%d unique (total=%d, anchor=%d)",
                        len(fresh), len(out), cursor)
    return out[-limit:]

# ============ Classify ============
def classify_message(msg: dict) -> dict:
    """Return {text_len, has_image, sticker_only, image_segs[]}.
    A 'sticker' here = image segment with sub_type 1 (animated/face) OR small file
    OR a NapCat animated-sticker summary tag."""
    segs = msg.get("message") or []
    text_len = 0
    image_segs: list[dict] = []
    for s in segs:
        if not isinstance(s, dict):
            continue
        t = s.get("type")
        d = s.get("data", {}) if isinstance(s.get("data"), dict) else {}
        if t == "text":
            text_len += len((d.get("text") or "").strip())
        elif t == "image":
            sub_type = d.get("sub_type", 0)
            try:
                sub_type = int(sub_type)
            except (TypeError, ValueError):
                sub_type = 0
            try:
                fsize = int(d.get("file_size") or 0)
            except (TypeError, ValueError):
                fsize = 0
            is_sticker = (
                sub_type == 1
                or "动画表情" in (d.get("summary") or "")
                or (0 < fsize < 200_000)
            )
            image_segs.append({
                "file": d.get("file", ""),
                "url": d.get("url", ""),
                "sub_type": sub_type,
                "file_size": fsize,
                "is_sticker": is_sticker,
            })
    has_image = len(image_segs) > 0
    return {
        "text_len": text_len,
        "has_image": has_image,
        "sticker_only": has_image and text_len == 0,
        "image_segs": image_segs,
        "ts": int(msg.get("time", 0)),
        "user_id": str(msg.get("user_id", "")),
        "msg_id": msg.get("message_id", 0),
    }

# ============ Owner profile ============
def compute_owner_profile(classified: list[dict]) -> dict:
    owner_msgs = [c for c in classified if c["user_id"] == OWNER_QQ]
    total = len(owner_msgs)
    if total == 0:
        return {"total_msgs": 0}

    with_image = sum(1 for c in owner_msgs if c["has_image"])
    sticker_only = sum(1 for c in owner_msgs if c["sticker_only"])
    text_only = [c["text_len"] for c in owner_msgs if not c["has_image"]]
    text_w_sticker = [c["text_len"] for c in owner_msgs if c["has_image"] and c["text_len"] > 0]

    sticker_md5s: Counter = Counter()
    for c in owner_msgs:
        for s in c["image_segs"]:
            m = re.match(r"^([a-fA-F0-9]{32})\.", s.get("file") or "")
            if m:
                sticker_md5s[m.group(1).lower()] += 1

    return {
        "ts": time.time(),
        "total_msgs": total,
        "msgs_with_image": with_image,
        "sticker_only_msgs": sticker_only,
        "ratio_image": with_image / total,
        "ratio_sticker_only": sticker_only / max(with_image, 1),
        "avg_text_len_no_sticker": (sum(text_only) / len(text_only)) if text_only else 0,
        "avg_text_len_with_sticker": (sum(text_w_sticker) / len(text_w_sticker)) if text_w_sticker else 0,
        "top_sticker_md5s": sticker_md5s.most_common(20),
    }

# ============ Sticker seeding ============
async def download_sticker(client: httpx.AsyncClient, url: str) -> bytes | None:
    if not url:
        return None
    try:
        r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"},
                             follow_redirects=True, timeout=15)
        if r.status_code != 200:
            return None
        return r.content
    except Exception as e:
        logger.debug("download failed (%s): %s", url[:80], e)
        return None

def guess_ext(b: bytes) -> str:
    if b[:8] == b"\x89PNG\r\n\x1a\n": return "png"
    if b[:3] == b"\xff\xd8\xff":      return "jpg"
    if b[:4] == b"GIF8":              return "gif"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP": return "webp"
    return "bin"

def format_ctx_line(msg: dict) -> str:
    name = (msg.get("sender") or {}).get("card") or (msg.get("sender") or {}).get("nickname") or "?"
    raw = (msg.get("raw_message") or "").strip()
    raw = re.sub(r"\[CQ:image[^\]]*\]", "[image]", raw)
    return f"{name}: {raw[:80]}"

async def seed_stickers(messages: list[dict], classified: list[dict]) -> dict:
    """Download all sticker-shaped images and register in stickers.json with
    surrounding context. Skips dupes (md5)."""
    STICKERS_DIR.mkdir(parents=True, exist_ok=True)
    if STICKERS_JSON.exists():
        try:
            entries = json.loads(STICKERS_JSON.read_text(encoding="utf-8"))
        except Exception:
            entries = {}
    else:
        entries = {}
    md5_index = {v.get("md5"): k for k, v in entries.items() if isinstance(v, dict) and v.get("md5")}

    new_count = 0
    ctx_count = 0
    seen_skip = 0

    async with httpx.AsyncClient() as client:
        for i, c in enumerate(classified):
            if not c["has_image"]:
                continue
            if c["user_id"] == BOT_QQ:
                continue
            ctx_before = [
                format_ctx_line(messages[j])
                for j in range(max(0, i - 6), i)
                if messages[j].get("user_id") != int(BOT_QQ or 0)
            ][-5:]

            for seg in c["image_segs"]:
                if not seg["is_sticker"]:
                    continue
                file_md5 = ""
                m = re.match(r"^([a-fA-F0-9]{32})\.", seg.get("file") or "")
                if m:
                    file_md5 = m.group(1).lower()

                if file_md5 and file_md5 in md5_index:
                    filename = md5_index[file_md5]
                    entry = entries[filename]
                    entry.setdefault("seen_contexts", []).append({
                        "ts": c["ts"],
                        "sender": c["user_id"],
                        "before": ctx_before,
                    })
                    entry["seen_contexts"] = entry["seen_contexts"][-5:]
                    entry["use_count"] = entry.get("use_count", 0) + 1
                    ctx_count += 1
                    seen_skip += 1
                    continue

                img_bytes = await download_sticker(client, seg["url"])
                if not img_bytes:
                    continue
                if len(img_bytes) < 200 or len(img_bytes) > 800_000:
                    continue
                md5 = hashlib.md5(img_bytes).hexdigest()
                if md5 in md5_index:
                    continue
                ext = guess_ext(img_bytes)
                filename = f"auto/{md5}.{ext}"
                filepath = ROOT / "stickers" / filename
                filepath.parent.mkdir(parents=True, exist_ok=True)
                try:
                    filepath.write_bytes(img_bytes)
                except Exception as e:
                    logger.warning("write failed: %s", e)
                    continue
                entry = {
                    "md5": md5,
                    "src_user": c["user_id"],
                    "src_group": str((messages[i].get("group_id") or "")),
                    "first_seen": c["ts"],
                    "use_count": 1,
                    "seen_contexts": [{
                        "ts": c["ts"],
                        "sender": c["user_id"],
                        "before": ctx_before,
                    }],
                    "meaning": "",
                    "tags": [],
                    "auto_tagged": False,
                }
                entries[filename] = entry
                md5_index[md5] = filename
                new_count += 1
                ctx_count += 1
                if new_count % 10 == 0:
                    logger.info("  seeded %d stickers...", new_count)

    STICKERS_JSON.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "new_stickers": new_count,
        "contexts_recorded": ctx_count,
        "existing_md5_hits": seen_skip,
        "total_stickers_now": len(entries),
    }

# ============ Main ============
async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=2000,
                   help="messages to pull per group (default 2000)")
    p.add_argument("--group", default="",
                   help="only process this group; defaults to QQ_GROUPS")
    p.add_argument("--no-stickers", action="store_true",
                   help="compute owner profile only, skip sticker download")
    p.add_argument("--no-profile", action="store_true",
                   help="download stickers only, skip profile")
    args = p.parse_args()

    if not OWNER_QQ:
        logger.error("OWNER_QQ not configured")
        return 1
    groups = [args.group] if args.group else QQ_GROUPS
    if not groups:
        logger.error("QQ_GROUPS not configured")
        return 1

    all_messages: list[dict] = []
    for gid in groups:
        logger.info("pulling history for group %s (limit %d)...", gid, args.limit)
        msgs = await pull_history(gid, args.limit)
        logger.info("  %d messages", len(msgs))
        all_messages.extend(msgs)

    classified = [classify_message(m) for m in all_messages]
    owner_count = sum(1 for c in classified if c["user_id"] == OWNER_QQ)
    logger.info("total %d messages, of which owner (%s) sent %d", len(classified), OWNER_QQ, owner_count)

    if not args.no_profile:
        profile = compute_owner_profile(classified)
        OWNER_PROFILE.write_text(
            json.dumps(profile, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("owner profile written to %s", OWNER_PROFILE.name)
        if profile.get("total_msgs", 0):
            logger.info("  image rate: %.1f%% (1 image per %d msgs)",
                        profile["ratio_image"] * 100,
                        round(profile["total_msgs"] / max(profile["msgs_with_image"], 1)))
            logger.info("  image-only ratio: %.1f%%", profile["ratio_sticker_only"] * 100)
            logger.info("  avg text length (no-image / with-image): %.0f / %.0f",
                        profile["avg_text_len_no_sticker"],
                        profile["avg_text_len_with_sticker"])

    if not args.no_stickers:
        logger.info("downloading stickers...")
        result = await seed_stickers(all_messages, classified)
        logger.info("seeding done: %d new, %d context samples, %d md5 hits, %d total",
                    result["new_stickers"], result["contexts_recorded"],
                    result["existing_md5_hits"], result["total_stickers_now"])

    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
