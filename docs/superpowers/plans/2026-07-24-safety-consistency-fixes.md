# Safety and State-Consistency Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent runtime chat data from entering tracked seed files, make state commits depend on validated delivery, and bound all image and webhook inputs.

**Architecture:** Keep the current `Agent` structure but add three narrow boundaries: seed/runtime path resolution, a shared `SendResult` delivery contract, and bounded input readers. Existing public webhook schemas and prompt behavior remain unchanged.

**Tech Stack:** Python 3.10+, FastAPI, httpx, pathlib, dataclasses, the repository's script-based regression suites.

## Global Constraints

- Do not split `persona_agent/agent.py` or replace JSON/JSONL persistence.
- Preserve Python 3.10 compatibility and existing webhook schemas.
- Preserve intentional `PASS` memory updates.
- Never write runtime-learned examples or feedback into tracked `data/` files.
- Never commit rejected or incompletely delivered output to memory or learning state.
- Maximum decoded/downloaded image size: 5,000,000 bytes.
- Default maximum webhook body size: 8,000,000 bytes.
- Follow TDD for every behavior change: test must fail for the expected reason before production edits.

---

### Task 1: Separate Seed and Runtime Learning Data

**Files:**
- Modify: `persona_agent/paths.py`
- Modify: `persona_agent/agent.py:109-118, 622-632, 3091-3130, 4468-4513`
- Modify: `persona_agent/evolution.py:172-178`
- Modify: `tools/auto_reviewer.py:65-68, 137-185`
- Modify: `tools/prompt_lab.py:22-34, 158-269`
- Modify: `tools/dspy_tune.py:30-65`
- Modify: `.gitignore`
- Test: `tests/test_evolution.py`
- Test: `tests/test_gateway.py`

**Interfaces:**
- Produces: `resolve_seed_lang_file(stem: str, ext: str, lang: str) -> Path`
- Produces: `resolve_runtime_lang_file(stem: str, ext: str, lang: str) -> Path`
- Produces: `read_jsonl(paths: Iterable[Path]) -> list[dict]`
- Changes: `load_feedback_keys(paths: Path | Iterable[Path]) -> set[tuple[str, str]]`
- `Agent.examples_seed_file` and `Agent.feedback_seed_file` are read-only.
- `Agent.examples_file` and `Agent.feedback_file` are runtime write targets.

- [ ] **Step 1: Write failing path and merge tests**

Add checks that isolate `AGENT_RUNTIME_DIR`, prove runtime writes do not change
seed bytes, and prove seed plus runtime rows are both loaded:

```python
def test_runtime_learning_paths(tmp: Path) -> None:
    old = os.environ.get("AGENT_RUNTIME_DIR")
    os.environ["AGENT_RUNTIME_DIR"] = str(tmp / "runtime")
    try:
        a = make_agent(tmp)
        check("runtime examples outside data",
              a.examples_file.parent == tmp / "runtime", str(a.examples_file))
        check("runtime feedback outside data",
              a.feedback_file.parent == tmp / "runtime", str(a.feedback_file))
    finally:
        if old is None:
            os.environ.pop("AGENT_RUNTIME_DIR", None)
        else:
            os.environ["AGENT_RUNTIME_DIR"] = old
```

In `tests/test_evolution.py`, create one seed pair and one runtime pair and
assert `load_feedback_keys([seed, runtime])` returns both.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
python tests/test_evolution.py
python tests/test_gateway.py
```

Expected: new runtime-path and multi-file de-dup checks fail because the agent
still points writes at `data/` and `load_feedback_keys` accepts one path.

- [ ] **Step 3: Add path helpers**

Add to `persona_agent/paths.py`:

```python
import json
import os
from collections.abc import Iterable

def resolve_seed_lang_file(stem: str, ext: str, lang: str) -> Path:
    lang_path = ROOT / "data" / f"{stem}.{lang}.{ext}"
    bare_path = ROOT / "data" / f"{stem}.{ext}"
    return bare_path if bare_path.exists() and not lang_path.exists() else lang_path

def runtime_dir() -> Path:
    configured = os.getenv("AGENT_RUNTIME_DIR", "").strip()
    path = Path(configured) if configured else ROOT / "runtime"
    return path if path.is_absolute() else ROOT / path

def resolve_runtime_lang_file(stem: str, ext: str, lang: str) -> Path:
    return runtime_dir() / f"{stem}.{lang}.{ext}"

def read_jsonl(paths: Iterable[Path]) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            continue
        for line in lines:
            try:
                row = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows
```

Keep `_resolve_lang_file` in `agent.py` as a compatibility wrapper around
`resolve_seed_lang_file`.

- [ ] **Step 4: Route agent reads and writes**

Initialize:

```python
self.examples_seed_file = resolve_seed_lang_file("examples", "jsonl", self.agent_lang)
self.examples_file = resolve_runtime_lang_file("examples", "jsonl", self.agent_lang)
self.feedback_seed_file = resolve_seed_lang_file("feedback", "jsonl", self.agent_lang)
self.feedback_file = resolve_runtime_lang_file("feedback", "jsonl", self.agent_lang)
```

Reload examples and pairs from both files, using a tuple of mtimes as the stale
cache key. `_append_example_with_trim` continues to write only
`self.examples_file` and must call `path.parent.mkdir(parents=True, exist_ok=True)`.

Change feedback de-dup calls to:

```python
evolution.load_feedback_keys([self.feedback_seed_file, self.feedback_file])
```

Change `evolution.load_feedback_keys` to normalize one `Path` into a one-item
list and merge every supplied file.

- [ ] **Step 5: Route tools to runtime writes and merged reads**

Use the shared path helpers in `auto_reviewer.py`, `prompt_lab.py`, and
`dspy_tune.py`. `auto_reviewer` and `prompt_lab` append only to runtime files;
all three tools read seed and runtime files together.

Add `runtime/` to `.gitignore`.

- [ ] **Step 6: Run the full regression set and verify GREEN**

Run:

```powershell
python tests/test_gateway.py
python tests/test_evolution.py
python tests/test_benchmark.py
python tests/test_reactions.py
```

Expected: every suite prints `all tests passed`.

- [ ] **Step 7: Commit**

```powershell
git add persona_agent/paths.py persona_agent/agent.py persona_agent/evolution.py tools/auto_reviewer.py tools/prompt_lab.py tools/dspy_tune.py tests/test_evolution.py tests/test_gateway.py .gitignore
git commit -m "fix: isolate runtime learning data"
```

---

### Task 2: Make Delivery Transactional

**Files:**
- Modify: `persona_agent/agent.py:1-27, 692-727, 989-1128, 1130-1216, 1345-1423, 3429-3550`
- Test: `tests/test_gateway.py`
- Test: `tests/test_reactions.py`

**Interfaces:**
- Produces: `SendResult(success: bool, partial: bool, message_ids: list[str], sticker_files: list[str])`
- Changes: `_send_qq(...) -> SendResult`
- Changes: `_send_private_qq(...) -> SendResult`
- Keeps: `_napcat_send_group(...) -> bool` and `_napcat_send_private(...) -> bool`

- [ ] **Step 1: Write failing delivery and memory tests**

Add regression checks for:

```python
async def test_private_send_failure_not_committed(tmp: Path) -> None:
    a = make_agent(tmp)
    a._chat_private = fake_chat_returning_hello
    a._napcat_send_private = async_false
    a._typing_delay = lambda _: 0
    handled = await a._handle_private("42", private_payload("hi"), is_owner=False)
    check("private failure returns false", handled is False, repr(handled))
    check("private failure leaves no assistant turn",
          not any(m["role"] == "assistant" for m in a.private_history.get("42", [])))
```

```python
async def test_rejected_candidate_does_not_persist_memory(tmp: Path) -> None:
    a = make_agent(tmp)
    a._think = fake_invalid_reply_with_core_and_mem
    handled = await a.handle(called_group_payload())
    check("invalid candidate returns false", handled is False)
    check("invalid candidate core discarded", "group" not in a.core_memory)
    check("invalid candidate auto memory discarded", "group" not in a.memories)
```

Add a private-message-id check where the fake NapCat response contains
`message_id=123` and assert the returned `SendResult.message_ids == ["123"]`.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```powershell
python tests/test_gateway.py
python tests/test_reactions.py
```

Expected: failures show private transport failure is reported as handled,
assistant history is committed, rejected memory is persisted, and the private
message ID is absent.

- [ ] **Step 3: Add `SendResult` and return it from both send funnels**

Add near the top of `agent.py`:

```python
from dataclasses import dataclass, field

@dataclass
class SendResult:
    success: bool = False
    partial: bool = False
    message_ids: list[str] = field(default_factory=list)
    sticker_files: list[str] = field(default_factory=list)
```

In both send funnels, track `sendable`, `sent_any`, and `failed`. Return:

```python
return SendResult(
    success=sendable and not failed,
    partial=sent_any and failed,
    message_ids=list(self._sent_mids.get(target_key, [])),
    sticker_files=sent_stickers,
)
```

Use `target_key = group_id` for group messages and
`target_key = f"private:{user_id}"` for private messages. Fix
`_napcat_send_private` to append message IDs under that private key instead of
the undefined `group_id`.

- [ ] **Step 4: Delay all candidate state commits**

For group replies:

1. Extract core memory without committing it.
2. Apply output filter.
3. If filtering blocks or sanitization turns a non-empty visible candidate into
   empty text, return without either memory write.
4. For valid `PASS`, commit core and auto memory and return `False`.
5. Snapshot evaluation context, release the group lock, and send.
6. If `SendResult.success` is false, do not append the bot line, update
   `last_reply_at`, evaluate, or register a pending reaction; return
   `SendResult.partial`.
7. On success, reacquire the group lock and commit buffer, timestamps, core
   memory, and auto memory.

For private replies, keep the pending user turn only after full delivery,
append the assistant turn only after success, and apply the same memory order.

- [ ] **Step 5: Update secondary send call sites**

Update memory-command, fallback, elicitation, and proactive call sites to accept
`SendResult`. Only proactive paths commit generated state when
`result.success` is true. Fire-and-forget fallback and elicitation paths log a
failed result but do not create learning state.

Update test doubles to return `SendResult(success=True)` rather than bare lists
or `None`.

- [ ] **Step 6: Run the full regression set and verify GREEN**

Run:

```powershell
python tests/test_gateway.py
python tests/test_evolution.py
python tests/test_benchmark.py
python tests/test_reactions.py
```

Expected: every suite prints `all tests passed`, including the new delivery and
memory checks.

- [ ] **Step 7: Commit**

```powershell
git add persona_agent/agent.py tests/test_gateway.py tests/test_reactions.py
git commit -m "fix: commit agent state only after delivery"
```

---

### Task 3: Bound and Validate Image Input

**Files:**
- Modify: `persona_agent/agent.py:1594-1649, 2001-2026, 4090-4305`
- Modify: `.env.example`
- Test: `tests/test_gateway.py`

**Interfaces:**
- Produces: `_detect_image_mime(data: bytes) -> str`
- Produces: `_safe_get_bytes(url: str, *, timeout: float, headers: dict | None, max_bytes: int) -> bytes | None`
- Keeps: `_fetch_image_bytes(url: str) -> bytes | None`

- [ ] **Step 1: Write failing local/base64/HTTP/format tests**

Add checks that:

- A valid PNG outside any configured directory is rejected through `file://`.
- The same PNG inside `NAPCAT_IMAGE_DIR` is accepted.
- A symlink or resolved path outside the directory is rejected.
- Base64 whose encoded length exceeds the 5 MB decoded limit is rejected before
  decoding.
- A streamed HTTP response exceeding the limit returns `None`.
- Arbitrary text bytes with no supported image signature return `None`.

- [ ] **Step 2: Run the gateway suite and verify RED**

Run:

```powershell
python tests/test_gateway.py
```

Expected: unrestricted `file://`, oversized input, and unknown-format checks
fail under the current implementation.

- [ ] **Step 3: Add image constants and signature detection**

Add:

```python
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", "5000000"))

def _detect_image_mime(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"GIF8"):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"BM"):
        return "image/bmp"
    if data[4:12] in (b"ftypheic", b"ftypheix", b"ftyphevc",
                      b"ftypmif1", b"ftypmsf1"):
        return "image/heic"
    if data[4:12] in (b"ftypavif", b"ftypavis"):
        return "image/avif"
    return ""
```

- [ ] **Step 4: Implement bounded readers**

For `base64://`, reject encoded strings larger than
`((MAX_IMAGE_BYTES + 2) // 3) * 4 + 4`, decode, then check decoded size and
signature.

For `file://`, require `NAPCAT_IMAGE_DIR`, resolve both paths, check containment,
check `stat().st_size`, read at most `MAX_IMAGE_BYTES + 1`, and validate the
signature.

Implement `_safe_get_bytes` with manual redirect checks, `AsyncClient.stream`,
an early `Content-Length` check, and cumulative `aiter_bytes()` counting.
Validate the final bytes before returning them.

Remove the unknown-format fallback to JPEG in `_describe_image_glm`; use
`_detect_image_mime` and return an empty caption for unsupported formats.

- [ ] **Step 5: Document input settings**

Add `MAX_IMAGE_BYTES=5000000` and fail-closed `NAPCAT_IMAGE_DIR` comments to
`.env.example`.

- [ ] **Step 6: Run all tests and verify GREEN**

Run:

```powershell
python tests/test_gateway.py
python tests/test_evolution.py
python tests/test_benchmark.py
python tests/test_reactions.py
```

Expected: every suite prints `all tests passed`.

- [ ] **Step 7: Commit**

```powershell
git add persona_agent/agent.py tests/test_gateway.py .env.example
git commit -m "fix: bound and validate image inputs"
```

---

### Task 4: Enforce Webhook Body Limits

**Files:**
- Modify: `main.py:1-20, 235-296`
- Modify: `.env.example`
- Modify: `.github/workflows/ci.yml`
- Create: `tests/test_http.py`
- Modify: `README.md`
- Modify: `README.zh-CN.md`

**Interfaces:**
- Produces: `RequestBodyTooLarge`
- Produces: `_read_body_limited(request: Request, limit: int) -> bytes`
- Adds: `MAX_WEBHOOK_BODY_BYTES`, default `8_000_000`

- [ ] **Step 1: Write the failing request-reader tests**

Create `tests/test_http.py` with a fake request exposing `headers` and an async
`stream()` generator. Cover:

```python
async def test_accepts_body_at_limit() -> None:
    body = await _read_body_limited(FakeRequest([b"ab", b"cd"]), 4)
    check("body at limit accepted", body == b"abcd", repr(body))

async def test_rejects_stream_over_limit_without_header() -> None:
    try:
        await _read_body_limited(FakeRequest([b"abc", b"de"]), 4)
    except RequestBodyTooLarge:
        check("stream over limit rejected", True)
    else:
        check("stream over limit rejected", False)

async def test_rejects_large_content_length_before_stream() -> None:
    request = FakeRequest([b"x"], headers={"content-length": "9"})
    try:
        await _read_body_limited(request, 8)
    except RequestBodyTooLarge:
        check("content-length over limit rejected", request.stream_reads == 0)
    else:
        check("content-length over limit rejected", False)
```

- [ ] **Step 2: Run the new suite and verify RED**

Run:

```powershell
python tests/test_http.py
```

Expected: import fails because `_read_body_limited` and
`RequestBodyTooLarge` do not exist.

- [ ] **Step 3: Implement the bounded request reader**

Add to `main.py`:

```python
MAX_WEBHOOK_BODY_BYTES = int(os.getenv("MAX_WEBHOOK_BODY_BYTES", "8000000"))

class RequestBodyTooLarge(Exception):
    pass

async def _read_body_limited(request: Request, limit: int) -> bytes:
    raw_length = request.headers.get("content-length", "")
    try:
        if raw_length and int(raw_length) > limit:
            raise RequestBodyTooLarge
    except ValueError:
        pass
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > limit:
            raise RequestBodyTooLarge
    return bytes(body)
```

Use the helper in both endpoints. Return:

```python
JSONResponse(status_code=413, content={"error": "request body too large"})
```

before signature verification or JSON dispatch when the limit is exceeded.

- [ ] **Step 4: Wire tests and update documentation**

Add `python tests/test_http.py` to CI. Document `AGENT_RUNTIME_DIR`,
`MAX_IMAGE_BYTES`, and `MAX_WEBHOOK_BODY_BYTES` in `.env.example` and both
README privacy/config sections. State that `data/examples.*` and
`data/feedback.*` are read-only synthetic seeds and runtime learning lands
under ignored `runtime/`.

- [ ] **Step 5: Run fresh final verification**

Run:

```powershell
python tests/test_gateway.py
python tests/test_evolution.py
python tests/test_benchmark.py
python tests/test_reactions.py
python tests/test_http.py
python -m compileall -q .
git diff --check
git status --short
```

Expected: all five suites print `all tests passed`, compilation exits zero,
`git diff --check` emits no output, and status lists only the intended Task 4
files before commit.

- [ ] **Step 6: Commit**

```powershell
git add main.py .env.example .github/workflows/ci.yml tests/test_http.py README.md README.zh-CN.md
git commit -m "fix: enforce webhook body limits"
```

- [ ] **Step 7: Inspect the completed branch**

Run:

```powershell
git log --oneline --decorate -5
git status --short --branch
```

Expected: the design commit plus four focused implementation commits and a
clean working tree on `codex/safety-consistency-fixes`.
