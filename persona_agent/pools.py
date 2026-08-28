"""Append-aware loading for the few-shot retrieval datasets.

examples/feedback JSONL are read on every LLM turn and appended to by
the agent itself, so the loader parses only the appended tail when it
can prove the consumed prefix is unchanged."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path


logger = logging.getLogger("agent")


# Bytes of the already-consumed prefix re-read to prove it is unchanged before
# trusting a seek-and-append. Cheap, and it turns "append-only" from an
# assumption about every present and future writer into a checked precondition.
_JSONL_SIG_BYTES = 64

def _parse_jsonl(blob: bytes) -> list[dict]:
    """Parse newline-delimited JSON objects, skipping blank and malformed lines.

    Skip-the-bad-line (rather than abandoning the whole file) matches what the
    feedback loader already did, and keeps one corrupted append from freezing
    the few-shot pool at its pre-corruption state."""
    out: list[dict] = []
    for ln in blob.decode("utf-8", "replace").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            rec = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out

def _read_jsonl_appended(
    path: Path, eof: int, offset: int, sig: bytes,
) -> tuple[list[dict], bool, int, int, bytes]:
    """Read `path` as JSONL, reusing whatever a previous read already consumed.

    Fast path (append-only): taken when the previous read consumed complete
    lines all the way to the then-EOF (``offset == eof > 0``), the file has
    since grown, and the last ``_JSONL_SIG_BYTES`` bytes of that consumed
    prefix are still byte-identical. Only the appended region is parsed.

    Every other shape falls back to parsing the whole file: first read, a
    shrink (the examples trim rewrites the file in place), an in-place rewrite,
    a prefix that no longer matches, or a dangling newline-less last line left
    over from the previous read.

    Returns ``(records, appended_only, new_eof, new_offset, new_sig)``.
    `new_offset` is the end of the last COMPLETE line, so a torn tail from an
    append still in flight stays unconsumed until its newline lands; on a full
    reload the fragment is still parsed (hand-edited files may legitimately
    lack a trailing newline) but is not claimed as consumed, which just means
    the next change re-reads the file whole instead of double-counting it.
    """
    with path.open("rb") as f:
        size = f.seek(0, 2)
        appended_only = bool(sig) and 0 < offset == eof < size
        if appended_only:
            f.seek(offset - len(sig))
            appended_only = f.read(len(sig)) == sig
        f.seek(offset if appended_only else 0)
        blob = f.read()
    cut = blob.rfind(b"\n")
    if appended_only:
        consumed = blob[:cut + 1] if cut >= 0 else b""
        records = _parse_jsonl(consumed)
        new_offset = offset + len(consumed)
        new_sig = (sig + consumed)[-_JSONL_SIG_BYTES:]
    else:
        records = _parse_jsonl(blob)
        new_offset = cut + 1 if cut >= 0 else 0
        new_sig = blob[:new_offset][-_JSONL_SIG_BYTES:]
    return records, appended_only, size, new_offset, new_sig

def _needs_leading_newline(path: Path) -> bool:
    """True when `path` has content that doesn't end in a newline.

    Every JSONL writer here appends ``json.dumps(...) + "\\n"``, which glues
    the new record onto an unterminated last line and destroys both. Files can
    legitimately arrive in that state from hand-editing — and the head of
    examples.jsonl is the hand-curated bootstrap pool, i.e. exactly the part
    people edit by hand and the part nothing is ever allowed to drop."""
    try:
        with path.open("rb") as f:
            if f.seek(0, 2) == 0:
                return False
            f.seek(-1, 2)
            return f.read(1) != b"\n"
    except OSError:
        return False

def _retrieval_fields(rec: dict) -> tuple[str, str, float]:
    """Precompute what the few-shot relevance scorer needs, once per record at
    load time instead of once per record on every LLM turn: the lowercased
    scenario / context blobs the focus tokens are matched against, and the
    entry's timestamp as an epoch float for the recency decay.

    ts_epoch is 0.0 when there is no parsable timestamp — same as the old
    inline parse, which simply skipped the recency bonus on failure. Naive
    timestamps keep being read as local time (``.timestamp()`` and the old
    ``datetime.now(None) - ts`` agree on that), aware ones as absolute."""
    epoch = 0.0
    ts = rec.get("ts")
    if ts:
        try:
            epoch = datetime.fromisoformat(
                str(ts).replace("Z", "+00:00")).timestamp()
        except (ValueError, TypeError, OSError, OverflowError):
            epoch = 0.0
    ctx = rec.get("context") or []
    if not isinstance(ctx, list):
        ctx = [ctx]
    return (
        str(rec.get("scenario") or "").lower(),
        " ".join(str(c) for c in ctx).lower(),
        epoch,
    )
