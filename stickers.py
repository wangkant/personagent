"""Sticker library: md5-deduped store with auto-tagging."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import re
import time
from pathlib import Path
from typing import Awaitable, Callable, Optional

logger = logging.getLogger("agent.stickers")

MAX_STICKERS = 500
MAX_CONTEXTS_PER_STICKER = 5
MIN_CONTEXTS_TO_TAG = 2
RECENT_USE_COOLDOWN_SEC = 90

class StickerLibrary:
    def __init__(
        self,
        stickers_dir: str | Path,
        stickers_file: str | Path,
        unknown_log: str | Path,
        anthropic_caller: Optional[Callable[..., Awaitable[str]]] = None,
        tagger_model: str = "deepseek-chat",
    ):
        self.dir = Path(stickers_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "auto").mkdir(parents=True, exist_ok=True)
        self.file = Path(stickers_file)
        self.unknown_log = Path(unknown_log)
        self._anthropic_caller = anthropic_caller
        self.tagger_model = tagger_model

        self.entries: dict[str, dict] = self._load()
        self._md5_index: dict[str, str] = {
            v["md5"]: k for k, v in self.entries.items() if v.get("md5")
        }
        self._tagging_inflight: set[str] = set()
        self._last_used: dict[str, float] = {}

    def _load(self) -> dict:
        if not self.file.exists():
            return {}
        try:
            return json.loads(self.file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("stickers.json load failed: %s", e)
            return {}

    def _save(self) -> None:
        try:
            self.file.write_text(
                json.dumps(self.entries, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("stickers.json save failed: %s", e)

    def _log_unknown(self, md5: str, src_user: str, src_group: str, url: str) -> None:
        try:
            self.unknown_log.parent.mkdir(parents=True, exist_ok=True)
            with open(self.unknown_log, "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps({
                    "ts": time.time(),
                    "md5": md5,
                    "src_user": src_user,
                    "src_group": src_group,
                    "url": url,
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def lookup_by_md5(self, md5: str) -> Optional[dict]:
        if not md5:
            return None
        filename = self._md5_index.get(md5.lower())
        if not filename:
            return None
        return self.entries.get(filename)

    def lookup_by_file_field(self, file_field: str) -> Optional[dict]:
        """NapCat segment 'file' is often '<md5>.ext'; extract md5 and look up."""
        if not file_field:
            return None
        m = re.match(r"^([a-fA-F0-9]{32})\.", file_field)
        if m:
            return self.lookup_by_md5(m.group(1))
        return None

    def md5_from_file_field(self, file_field: str) -> str:
        m = re.match(r"^([a-fA-F0-9]{32})\.", file_field or "")
        return m.group(1).lower() if m else ""

    async def steal(
        self,
        image_bytes: bytes,
        url: str,
        src_user: str,
        src_group: str,
        context_before: list[str],
    ) -> Optional[str]:
        """Save new sticker (or update existing). Returns md5 on success.
        Returns None if image looks like a real photo (size > 800KB) — heuristic
        to avoid stealing user-uploaded photos."""
        if not image_bytes or len(image_bytes) < 200:
            return None
        if len(image_bytes) > 800_000:
            return None

        md5 = hashlib.md5(image_bytes).hexdigest()
        existing_filename = self._md5_index.get(md5)

        if existing_filename:
            self._append_context(existing_filename, src_user, context_before)
            entry = self.entries.get(existing_filename, {})
            entry["use_count"] = entry.get("use_count", 0) + 1
            self._save()
            return md5

        if len(self.entries) >= MAX_STICKERS:
            self._evict_least_used()

        ext = self._guess_ext(image_bytes)
        filename = f"auto/{md5}.{ext}"
        filepath = self.dir / filename
        try:
            filepath.write_bytes(image_bytes)
        except Exception as e:
            logger.warning("[stickers] write failed: %s", e)
            return None

        entry = {
            "md5": md5,
            "src_user": src_user,
            "src_group": src_group,
            "first_seen": time.time(),
            "use_count": 1,
            "seen_contexts": [],
            "meaning": "",
            "tags": [],
            "auto_tagged": False,
        }
        self.entries[filename] = entry
        self._md5_index[md5] = filename
        self._append_context(filename, src_user, context_before, save=False)
        self._save()
        logger.info("[stickers] stole new (%s, %d bytes, group=%s)",
                    md5[:8], len(image_bytes), src_group)
        self._log_unknown(md5, src_user, src_group, url)
        return md5

    def _append_context(
        self,
        filename: str,
        src_user: str,
        context_before: list[str],
        save: bool = True,
    ) -> None:
        entry = self.entries.get(filename)
        if not entry:
            return
        ctxs = entry.setdefault("seen_contexts", [])
        ctxs.append({
            "ts": time.time(),
            "sender": src_user,
            "before": context_before[-5:],
        })
        if len(ctxs) > MAX_CONTEXTS_PER_STICKER:
            entry["seen_contexts"] = ctxs[-MAX_CONTEXTS_PER_STICKER:]
        if save:
            self._save()

    @staticmethod
    def _guess_ext(b: bytes) -> str:
        if b[:8] == b"\x89PNG\r\n\x1a\n":
            return "png"
        if b[:3] == b"\xff\xd8\xff":
            return "jpg"
        if b[:4] == b"GIF8":
            return "gif"
        if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
            return "webp"
        return "bin"

    def _evict_least_used(self) -> None:
        """Drop the bottom 10% by use_count (untagged ones first)."""
        ranked = sorted(
            self.entries.items(),
            key=lambda kv: (
                kv[1].get("auto_tagged", False),
                kv[1].get("use_count", 0),
                kv[1].get("first_seen", 0),
            ),
        )
        cut = max(1, len(ranked) // 10)
        for filename, _ in ranked[:cut]:
            entry = self.entries.pop(filename, None)
            if entry:
                self._md5_index.pop(entry.get("md5", ""), None)
                try:
                    (self.dir / filename).unlink(missing_ok=True)
                except Exception:
                    pass
        logger.info("[stickers] evicted %d entries", cut)

    async def maybe_tag(self, md5: str) -> None:
        """If sticker has enough contexts and isn't tagged, kick off LLM tagging.
        Fire-and-forget; safe to call from anywhere."""
        if not self._anthropic_caller:
            return
        filename = self._md5_index.get(md5)
        if not filename:
            return
        entry = self.entries.get(filename)
        if not entry or entry.get("auto_tagged"):
            return
        if len(entry.get("seen_contexts", [])) < MIN_CONTEXTS_TO_TAG:
            return
        if filename in self._tagging_inflight:
            return
        self._tagging_inflight.add(filename)
        asyncio.create_task(self._tag_one(filename))

    async def _tag_one(self, filename: str) -> None:
        try:
            entry = self.entries.get(filename)
            if not entry:
                return
            ctxs = entry.get("seen_contexts", [])
            ctx_block = "\n\n".join(
                f"样本{i+1}（sender={c['sender']}）:\n" + "\n".join(c.get("before", []))
                for i, c in enumerate(ctxs)
            )
            prompt = (
                "你帮我给一张 QQ 群表情包打 tag。下面是这张表情包在群里被人发的 N 个上下文样本——\n"
                "你看不到图，但能从「发图前后大家在聊什么」推断出这张表情包大概是啥含义。\n\n"
                f"{ctx_block}\n\n"
                "[严格按 JSON 一行输出，不要 markdown 包裹]\n"
                '{"meaning":"<2-8 字描述这张表情包的语义/情绪，比如 \'doge 笑/嘲讽\' \'摸鱼大鱼/划水\'>",'
                '"tags":["<2-4 个标签，便于检索时 fuzzy match，例如：嘲讽、笑、无语、摸鱼>"]}'
            )
            raw = await self._anthropic_caller(
                system="你是表情包语义分析器，只输出 JSON。",
                messages=[{"role": "user", "content": prompt}],
                model=self.tagger_model,
                max_tokens=200,
                enable_search=False,
                max_search_uses=0,
            )
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw or "", flags=re.MULTILINE).strip()
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("[stickers] tag JSON parse failed for %s: %s",
                               filename, raw[:120])
                return
            entry["meaning"] = (parsed.get("meaning") or "").strip()[:50]
            entry["tags"] = [
                str(t).strip()[:20] for t in (parsed.get("tags") or []) if t
            ][:6]
            entry["auto_tagged"] = True
            entry["tagged_ts"] = time.time()
            self._save()
            logger.info("[stickers] tagged %s: meaning=%r tags=%s",
                        filename, entry["meaning"], entry["tags"])
        except Exception as e:
            logger.warning("[stickers] tagging failed for %s: %s: %s",
                           filename, type(e).__name__, e)
        finally:
            self._tagging_inflight.discard(filename)

    def available_tags_summary(self, limit: int = 20) -> str:
        """Prompt-friendly listing of available tagged stickers, ranked by use_count.
        Returns "" if no tagged stickers yet (so prompt skips the [STICKER:] guide)."""
        tagged = [
            (k, v) for k, v in self.entries.items()
            if v.get("auto_tagged") and v.get("tags")
        ]
        if not tagged:
            return ""
        tagged.sort(key=lambda kv: kv[1].get("use_count", 0), reverse=True)
        top = tagged[:limit]
        seen_tags: dict[str, str] = {}
        for _, v in top:
            for t in v.get("tags", []):
                if t and t not in seen_tags:
                    seen_tags[t] = v.get("meaning") or t
        lines = [f"  {tag}（{meaning}）" for tag, meaning in seen_tags.items()]
        return "\n".join(lines)

    _SYNONYMS = {
        "无奈": {"无奈", "翻白眼", "没办法", "醉了", "无语", "叹气", "服了"},
        "翻白眼": {"翻白眼", "无奈", "无语", "没办法"},
        "懒得理": {"懒得", "无语", "翻白眼", "无奈", "敷衍"},
        "懒得": {"懒得", "无语", "翻白眼", "无奈"},
        "敷衍": {"敷衍", "无语", "懒得"},
        "doge": {"doge", "嘲讽", "笑", "挑衅"},
        "嘲讽": {"嘲讽", "doge", "挑衅", "笑"},
        "挑衅": {"挑衅", "嘲讽", "doge"},
        "笑": {"笑", "doge", "绷不住", "嘲讽"},
        "绷不住": {"绷不住", "笑"},
        "抱抱": {"抱抱", "求安慰", "委屈"},
        "委屈": {"委屈", "抱抱", "心疼"},
        "心疼": {"心疼", "委屈", "抱抱"},
        "震惊": {"震惊", "卧槽", "牛", "绝"},
        "牛": {"牛", "震惊", "绝", "膜拜"},
        "绝": {"绝", "牛", "震惊"},
        "玩梗": {"玩梗", "doge", "嘲讽", "笑"},
        "共鸣": {"共鸣", "确实", "无奈", "我也"},
    }

    @classmethod
    def _expand_tag(cls, tag_lc: str) -> set[str]:
        out = {tag_lc}
        if tag_lc in cls._SYNONYMS:
            out |= cls._SYNONYMS[tag_lc]
        if len(tag_lc) >= 2:
            out.add(tag_lc[:2])
        return out

    def pick_by_tag(self, tag: str, exclude_md5s: set | None = None) -> Optional[Path]:
        """Fuzzy match a tag to best sticker. Matches across library tags, meaning,
        and a synonym table so common emotion-name tags hit even when library
        entries use related-but-different wording."""
        if not tag:
            return None
        tag_lc = tag.lower().strip()
        probes = self._expand_tag(tag_lc)
        exclude = exclude_md5s or set()
        now = time.time()
        best_filename = None
        best_score = 0.0
        for filename, v in self.entries.items():
            if not v.get("auto_tagged"):
                continue
            if v.get("md5", "") in exclude:
                continue
            last = self._last_used.get(filename, 0)
            if now - last < RECENT_USE_COOLDOWN_SEC:
                continue
            score = 0.0
            entry_tags_lc = [((t or "").lower()) for t in v.get("tags", []) if t]
            meaning_lc = (v.get("meaning") or "").lower()
            if tag_lc in entry_tags_lc:
                score += 3.0
            for probe in probes:
                if not probe:
                    continue
                for et in entry_tags_lc:
                    if probe == et:
                        score += 2.0
                    elif probe in et or et in probe:
                        score += 1.2
                if probe in meaning_lc:
                    score += 1.0
            score += min(v.get("use_count", 0), 20) * 0.02
            score += random.uniform(0, 0.1)
            if score > best_score:
                best_score = score
                best_filename = filename
        if not best_filename or best_score < 1.0:
            return None
        self._last_used[best_filename] = now
        entry = self.entries.get(best_filename)
        if entry:
            entry["use_count"] = entry.get("use_count", 0) + 1
        return self.dir / best_filename

    async def bootstrap_tag_all(self) -> int:
        """Scan library for untagged entries with enough contexts and kick off
        tagging for each. Called on agent startup to process seed data from
        bootstrap_from_history. Returns count scheduled."""
        if not self._anthropic_caller:
            return 0
        pending = [
            v["md5"] for v in self.entries.values()
            if not v.get("auto_tagged")
            and v.get("md5")
            and len(v.get("seen_contexts", [])) >= MIN_CONTEXTS_TO_TAG
        ]
        if not pending:
            return 0
        logger.info("[stickers] bootstrap: tagging %d pending entries", len(pending))
        for md5 in pending:
            await self.maybe_tag(md5)
            await asyncio.sleep(0.4)
        return len(pending)

    def stats(self) -> dict:
        total = len(self.entries)
        tagged = sum(1 for v in self.entries.values() if v.get("auto_tagged"))
        pending = sum(
            1 for v in self.entries.values()
            if not v.get("auto_tagged")
            and len(v.get("seen_contexts", [])) >= MIN_CONTEXTS_TO_TAG
        )
        return {"total": total, "tagged": tagged, "pending_tagging": pending}
