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

        # Fence text the speaker did not author (web pages, vision captions,
        # sticker meanings, quoted messages) so it never reaches ctrl_text —
        # a page titled "<BOT> remember X" must not drive is_called or memory
        # commands, even when re-quoted. Cleaned of all four delimiters first:
        # a quote may be an older rendering that carries its own spans, and
        # none of it may close this one or forge the user-data frame.
        def _fence(s: str) -> str:
            return f"{_WEB_DESC_OPEN}{_clean_prompt_source(s)}{_WEB_DESC_CLOSE}"

        # Links are described once for the whole message, after the loop:
        # one concurrent fetch under one LINK_ENRICHMENT_BUDGET_SEC. Awaited
        # per text segment, an @mention-split paste fetched each segment's
        # links after the last one's, every segment with a fresh budget.
        # Each slot is (index in parts, how many of `msg_urls` it holds).
        msg_urls: list[str] = []
        link_slots: list[tuple[int, int]] = []
        for seg in payload.get("message", []):
            if not isinstance(seg, dict):
                continue
            t = seg.get("type")
            d = seg.get("data", {}) if isinstance(seg.get("data"), dict) else {}
            if t == "text":
                # The sender's own words may not manufacture either frame.
                txt = _clean_prompt_source(d.get("text", ""))
                parts.append(txt)
                # Inline URLs in plain text: pull metadata as separate buffer
                # segments so reasoning can actually "see" what the link is
                # about (Bilibili, YouTube, or any OG-tagged site). The cap
                # counts across every text segment of the message.
                urls = self._extract_urls(txt)[
                    :self.MAX_URLS_PER_MESSAGE - len(msg_urls)]
                if urls:
                    link_slots.append((len(parts), len(urls)))
                    parts.append("")  # this segment's descriptors, below
                    msg_urls.extend(urls)
            elif t == "at":
                qq = _clean_prompt_source(d.get("qq", ""))
                parts.append(f"@{self.persona_name}"
                             if qq == self._self_mention_id() else f"@{qq}")
            elif t == "image":
                url = d.get("url") or d.get("file", "")
                file_field = d.get("file", "")
                # A connector marks a sticker sent as an image; the focus
                # block and the prompt treat [sticker] and [image] alike.
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
                # Sticker stealing is a QQ-path feature: connector images must
                # not get cataloged into the QQ sticker library or burn
                # tagging calls, so skip the spawn while the connector sink is
                # set (the steal decision happens inside handle_event).
                if group_id and sender_uid != self.qq_bot_id \
                        and current_sink.get() is None:
                    self._spawn(self._steal_image_async(
                        url=url,
                        sender_uid=sender_uid,
                        group_id=group_id,
                    ))
            elif t == "face":
                # A forwarded platform emoji carries its name; fenced because
                # whoever named a custom emoji is not the sender.
                name = _clean_prompt_source(d.get("name")).strip()[:40]
                parts.append(_fence(f"[emoji: {name}]") if name else "[face]")
            elif t == "reply":
                # QQ quote-reply: data.id is the quoted message's id. Resolve it
                # to the original text so the model knows what's being replied to;
                # otherwise it sees a referent-less "[reply]111" and guesses who/
                # what → wrong-person / crossed-thread replies. Falls back to a
                # bare "[reply]" if it can't be fetched (never blocks / drops).
                qid = d.get("id")
                hint = self._quote_hint(d)
                quoted = (await self._resolve_quote(qid, group_id, hint=hint)
                          if qid or hint else "")
                parts.append(_fence(f"[reply {quoted}]") if quoted else "[reply]")
            elif t == "record":
                # Voice message — no ASR pipeline; show a clean placeholder
                # so the raw CQ-code (which would leak file paths) doesn't
                # fall through to raw_message at the bottom of this function.
                parts.append("[voice]")
            elif t == "video":
                parts.append("[video]")
            elif t == "file":
                parts.append("[file]")
            elif t == "forward":
                # Merged-forward contents aren't fetched here — mark "not visible"
                # so the model asks instead of fabricating what the forward said.
                parts.append("[forwarded-chat (content not visible)]")
            elif t == "mface":
                # Market emoji: the `summary` field often carries a name
                # (e.g. "[dice]") — prefer it; otherwise fall back to a placeholder.
                summary = _clean_prompt_source(d.get("summary")).strip()
                parts.append(summary if summary else "[face]")
            elif t == "json":
                raw_data = d.get("data", "")
                if raw_data:
                    # Fail soft like every other segment parser here: the card
                    # JSON is sender-controlled, and an exception would unwind
                    # to handle()'s catch-all and drop the WHOLE message
                    # (including its other text segments).
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
            return "".join(parts).strip()
        return _clean_prompt_source(payload.get("raw_message")).strip()

    def _index_msg(self, mid, rendered: str) -> None:
        """Record a message_id -> 'speaker: text' entry for quote-reply
        resolution (Layer A, zero cost). Bounded: drops the oldest on overflow."""
        if mid is None or not rendered:
            return
        key = str(mid)
        self._msg_index.pop(key, None)  # re-insert at the end to refresh recency
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

    async def _resolve_quote(self, mid, group_id: str, hint: str = "") -> str:
        """Resolve a quoted (引用回复) message_id to 'speaker: text' so the model
        understands the referent. Layer A: local _msg_index (zero cost, hits most
        recent messages). Then the connector's own copy (`hint`), which covers
        the bot's replies and anything older than the index. Layer B: NapCat
        get_msg (one call, only on a miss). Any failure returns '' — the caller
        degrades to a bare '[reply]', never blocking or dropping the message."""
        key = "" if mid is None or mid == "" else str(mid)
        if key:
            hit = self._msg_index.get(key)
            if hit:
                return hit
        if hint:
            if key:
                self._index_msg(key, hint)
            return hint
        # Connector path has no NapCat to query; skip the API call.
        if not key or current_sink.get() is not None:
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
        # Strip nested CQ codes (image/at/reply/...) to keep a clean one-liner; cap.
        raw = re.sub(r"\[CQ:[^\]]*\]", "", raw).strip()[:60]
        if not raw:
            return ""
        rendered = f"{name}: {raw}" if name else raw
        self._index_msg(key, rendered)  # cache so repeats in a burst skip the API
        return rendered

    def _append_buffer(self, group_id: str, name: str, text: str, user_id: str = "") -> None:
        buf = self.buffers[group_id]
        # Merge only when BOTH name AND user_id match the previous entry —
        # keying on name alone cross-merges different users sharing a nickname
        # and collides with the bot's own name.
        if (buf and buf[-1].get("name") == name
                and buf[-1].get("user_id", "") == user_id
                and len(buf[-1].get("text", "")) < 300):
            buf[-1]["text"] = buf[-1]["text"] + " " + text
        else:
            buf.append({"name": name, "text": text, "user_id": user_id})

    def _self_mention_id(self) -> str:
        """The id an @ of the bot carries: QQ_BOT_ID, or CONNECTOR_BOT_ID on an
        install without QQ, where the connector mints it for a self mention.
        Only the mention paths use it; NapCat's own-message filters and the
        missed-mention sweep stay on qq_bot_id."""
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
