"""Reading a message: its text, quotes, buffer lines and @-mentions."""
from __future__ import annotations

import itertools
import logging
import re

from .connector import (CONNECTOR_BOT_ID, current_sink)
from .textproc import (
    _WEB_DESC_CLOSE,
    _WEB_DESC_OPEN,
    _clean_prompt_source,
)

logger = logging.getLogger("agent")


class MessageParsing:
    async def _extract_text(self, payload: dict) -> str:
        parts: list[str] = []
        group_id = str(payload.get("group_id", ""))
        sender_uid = str(payload.get("user_id", ""))

        # Text the speaker did not write is fenced out of ctrl_text, after
        # cleaning any delimiters it carries so it cannot close the span.
        def _fence(s: str) -> str:
            return f"{_WEB_DESC_OPEN}{_clean_prompt_source(s)}{_WEB_DESC_CLOSE}"

        # Links are fetched once, concurrently, under one budget after the loop;
        # each slot is (index in parts, how many of `msg_urls` it holds).
        msg_urls: list[str] = []
        link_slots: list[tuple[int, int]] = []
        # Mentions, so following text gets a space connectors may omit.
        at_slots: set[int] = set()
        for seg in payload.get("message", []):
            if not isinstance(seg, dict):
                continue
            t = seg.get("type")
            d = seg.get("data", {}) if isinstance(seg.get("data"), dict) else {}
            if t == "text":
                # The sender's own words may not manufacture either frame.
                txt = _clean_prompt_source(d.get("text", ""))
                parts.append(txt)
                # The cap counts across the whole message.
                urls = self._extract_urls(txt)[
                    :self.MAX_URLS_PER_MESSAGE - len(msg_urls)]
                if urls:
                    link_slots.append((len(parts), len(urls)))
                    parts.append("")  # this segment's descriptors, below
                    msg_urls.extend(urls)
            elif t == "at":
                qq = _clean_prompt_source(d.get("qq", ""))
                at_slots.add(len(parts))
                parts.append(f"@{self.persona_name}"
                             if qq == self._self_mention_id() else f"@{qq}")
            elif t == "image":
                url = d.get("url") or d.get("file", "")
                file_field = d.get("file", "")
                kind = "sticker" if d.get("sticker") is True else "image"
                if not url:
                    parts.append(f"[{kind}]")
                    continue
                entry = self.stickers.lookup_by_file_field(file_field)
                if entry and entry.get("auto_tagged") and entry.get("meaning"):
                    parts.append(_fence(f"[sticker: {entry['meaning']}]"))
                    self._spawn(self._record_sticker_context(
                        entry["md5"], group_id, sender_uid,
                    ))
                    continue
                desc = await self._describe_image(url)
                parts.append(_fence(f"[{kind}: {desc}]") if desc else f"[{kind}]")
                # Sticker stealing is QQ-only.
                if group_id and sender_uid != self.qq_bot_id \
                        and current_sink.get() is None:
                    self._spawn(self._steal_image_async(
                        url=url,
                        sender_uid=sender_uid,
                        group_id=group_id,
                    ))
            elif t == "face":
                # Fenced: whoever named a custom emoji is not the sender.
                name = _clean_prompt_source(d.get("name")).strip()[:40]
                parts.append(_fence(f"[emoji: {name}]") if name else "[face]")
            elif t == "reply":
                # Resolved to the quoted text, or a bare "[reply]".
                qid = d.get("id")
                hint = self._quote_hint(d)
                quoted = (await self._resolve_quote(qid, hint=hint)
                          if qid or hint else "")
                parts.append(_fence(f"[reply {quoted}]") if quoted else "[reply]")
            elif t == "record":
                # No speech recognition; never the raw CQ code (file paths).
                parts.append("[voice]")
            elif t == "video":
                parts.append("[video]")
            elif t == "file":
                parts.append("[file]")
            elif t == "forward":
                # Not fetched; said so, so the model asks instead of inventing it.
                parts.append("[forwarded-chat (content not visible)]")
            elif t == "mface":
                summary = _clean_prompt_source(d.get("summary")).strip()
                parts.append(summary if summary else "[face]")
            elif t == "json":
                raw_data = d.get("data", "")
                if raw_data:
                    # Sender-controlled JSON must not drop the whole message.
                    try:
                        desc = await self._describe_share(raw_data)
                    except Exception as e:
                        logger.warning("[Agent] _describe_share failed: %s: %s",
                                       type(e).__name__, e)
                        desc = ""
                    parts.append(_fence(desc or "[share-card]"))
                else:
                    parts.append("[share-card]")
        if msg_urls:
            descs = iter(await self._describe_urls(msg_urls))
            for slot, n in link_slots:
                parts[slot] = "".join(
                    " " + _fence(d) for d in itertools.islice(descs, n) if d)
        if parts:
            joined = ""
            for i, part in enumerate(parts):
                if (i - 1 in at_slots and part and not part[0].isspace()
                        and joined and not joined[-1].isspace()):
                    joined += " "
                joined += part
            return joined.strip()
        return _clean_prompt_source(payload.get("raw_message")).strip()

    def _index_msg(self, mid, rendered: str) -> None:
        """Record message_id -> 'speaker: text' for quote resolution (bounded LRU)."""
        if mid is None or not rendered:
            return
        key = str(mid)
        self._msg_index.pop(key, None)
        self._msg_index[key] = rendered
        if len(self._msg_index) > self._msg_index_cap:
            del self._msg_index[next(iter(self._msg_index))]

    def _quote_hint(self, data: dict) -> str:
        """The connector's copy of a quoted message as 'speaker: text', in
        the shape _index_msg stores, or ''."""
        text = " ".join(
            _clean_prompt_source(data.get("quote_text")).split())[:60]
        if not text:
            return ""
        if data.get("quote_self") is True:
            name = self.persona_name
        else:
            name = _clean_prompt_source(data.get("quote_name")).strip()[:8]
        return f"{name}: {text}" if name else text

    async def _resolve_quote(self, mid, hint: str = "") -> str:
        """A quoted message as 'speaker: text': the local index, then the
        connector's copy (`hint`), then one NapCat get_msg; '' on any failure."""
        key = "" if mid is None or mid == "" else str(mid)
        if key:
            hit = self._msg_index.get(key)
            if hit:
                return hit
        if hint:
            if key:
                self._index_msg(key, hint)
            return hint
        if not key or current_sink.get() is not None or not self.qq_onebot_url:
            return ""
        try:
            async with self._local_http(timeout=4) as client:
                r = await client.post(
                    f"{self.qq_onebot_url}/get_msg",
                    json={"message_id": int(mid)},
                )
            data = r.json().get("data") or {}
        except Exception as e:
            logger.debug("[Agent] get_msg(%s) failed: %s: %s",
                         mid, type(e).__name__, e)
            return ""
        sender = data.get("sender") or {}
        name = (sender.get("card") or sender.get("nickname") or "")[:8]
        raw = (data.get("raw_message") or "").strip()
        raw = re.sub(r"\[CQ:[^\]]*\]", "", raw).strip()[:60]
        if not raw:
            return ""
        rendered = f"{name}: {raw}" if name else raw
        self._index_msg(key, rendered)
        return rendered

    def _append_buffer(self, group_id: str, name: str, text: str, user_id: str = "") -> None:
        buf = self.buffers[group_id]
        # Merge on name and user_id: nicknames collide.
        if (buf and buf[-1].get("name") == name
                and buf[-1].get("user_id", "") == user_id
                and len(buf[-1].get("text", "")) < 300):
            buf[-1]["text"] = buf[-1]["text"] + " " + text
        else:
            buf.append({"name": name, "text": text, "user_id": user_id})

    def _self_mention_id(self) -> str:
        """The id an @ of the bot carries: QQ_BOT_ID, else CONNECTOR_BOT_ID
        (mention paths only; NapCat's filters stay on qq_bot_id)."""
        return self.qq_bot_id or CONNECTOR_BOT_ID

    def _is_at_me(self, payload: dict) -> bool:
        me = self._self_mention_id()
        for seg in payload.get("message", []):
            if (
                isinstance(seg, dict)
                and seg.get("type") == "at"
                and str(seg.get("data", {}).get("qq")) == me
            ):
                return True
        return False
