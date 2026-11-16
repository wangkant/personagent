"""An OpenAI-compatible chat API, so any software that speaks to an
OpenAI-style endpoint can talk to the character: GET /v1/models and
POST /v1/chat/completions.

The character keeps its own persona and memory: of a request only the last
`user` message is read, as a new message in a one-to-one conversation on the
platform `api`. Off unless CHAT_API_ENABLED; without CHAT_API_KEY only
programs on this computer may call (the model of the connector endpoints).
"""
from __future__ import annotations

import asyncio
import base64
import binascii
import json
import secrets
import time
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from .access import API_PLATFORM
from .connector import TEXT_ONLY, opaque_value

#: The one model id served; any `model` in a request is accepted.
MODEL = "personagent"
CONVERSATION_HEADER = "x-personagent-conversation"
DEFAULT_CONVERSATION = "default"
MAX_CONVERSATION_CHARS = 64
# Characters, as the page's chat allows.
MAX_TEXT = 8000
MAX_IMAGES = 4
MAX_IMAGE_URL_CHARS = 2048
# Seconds between SSE comments while a turn runs: proxies drop a silent stream.
KEEPALIVE_S = 10.0
# The caller's name in the character's prompt, as the page's chat names its sender.
SENDER_NAME = "you"
KEY_PREFIX = "sk-pa-"
#: Counts are not measured per request; zeros keep clients that read them working.
USAGE = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
_CORS = {"Access-Control-Allow-Origin": "*",
         "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
         "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Personagent-Conversation",
         "Access-Control-Max-Age": "600"}

class ApiError(Exception):
    """A refusal in OpenAI's error shape."""

    def __init__(self, status: int, code: str, message: str, *,
                 kind: str = "invalid_request_error", retry_after: int | None = None) -> None:
        super().__init__(message)
        self.status, self.code, self.message, self.kind = status, code, message, kind
        self.retry_after = retry_after

    def body(self) -> dict:
        return {"error": {"message": self.message, "type": self.kind, "code": self.code, "param": None}}


def _server():
    from persona_agent import server
    return server


def new_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(32)


# ------------------------------------------------------------ the request ----

def _image_segment(part) -> dict:
    image = part.get("image_url")
    url = image.get("url") if isinstance(image, dict) else image
    if not isinstance(url, str) or not url.strip():
        raise ApiError(400, "invalid_image", "an image_url part needs image_url.url")
    url = url.strip()
    if url[:5].lower() == "data:":
        return {"type": "image", "b64": _data_url(url)}
    parts = urlsplit(url)
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc or len(url) > MAX_IMAGE_URL_CHARS:
        raise ApiError(400, "invalid_image",
                       "image_url must be a data: URL or an http(s) URL of at most "
                       f"{MAX_IMAGE_URL_CHARS} characters")
    # Fetched later by the agent's image reader, through its SSRF guard and size limit.
    return {"type": "image", "url": url}


def _data_url(url: str) -> str:
    """The base64 payload of an image data URL, under the vision size limit."""
    head, comma, data = url.partition(",")
    if not comma or not head.lower().startswith("data:image/") or not head.lower().endswith(";base64"):
        raise ApiError(400, "invalid_image", "an image data URL must be data:image/<type>;base64,<data>")
    data = "".join(data.split())
    from .ingestion import VISION_MAX_IMAGE_BYTES
    if len(data) > (VISION_MAX_IMAGE_BYTES + 2) // 3 * 4 + 4:
        raise ApiError(400, "image_too_large",
                       f"an image may be at most {VISION_MAX_IMAGE_BYTES} bytes (VISION_MAX_IMAGE_BYTES)")
    try:
        base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        raise ApiError(400, "invalid_image", "the image data URL is not valid base64") from None
    return data


def _last_user_message(messages) -> dict:
    if not isinstance(messages, list) or not messages:
        raise ApiError(400, "invalid_messages", "messages must be a non-empty list")
    for message in reversed(messages):
        if isinstance(message, dict) and message.get("role") == "user":
            return message
    raise ApiError(400, "no_user_message", "messages has no message with the role user")


def read_content(content) -> tuple[str, list[dict]]:
    """The text and image segments of one message's content."""
    if isinstance(content, str):
        texts, images = [content], []
    elif isinstance(content, list):
        texts, images = [], []
        for part in content:
            kind = part.get("type") if isinstance(part, dict) else None
            if kind == "text" and isinstance(part.get("text"), str):
                texts.append(part["text"])
            elif kind == "image_url":
                images.append(_image_segment(part))
            else:
                raise ApiError(400, "unsupported_content", "content parts may be text or image_url only")
    else:
        raise ApiError(400, "invalid_content", "content must be a string or a list of parts")
    text = "\n".join(t for t in texts if t.strip()).strip()
    if not text and not images:
        raise ApiError(400, "empty_message", "the last user message is empty")
    if len(text) > MAX_TEXT:
        raise ApiError(400, "message_too_long", f"a message may be at most {MAX_TEXT} characters")
    if len(images) > MAX_IMAGES:
        raise ApiError(400, "too_many_images", f"a message may carry at most {MAX_IMAGES} images")
    return text, images


def conversation_of(body: dict, header: str) -> str:
    """The body's `user`, else the X-Personagent-Conversation header, else the default."""
    for raw in (body.get("user"), header):
        if raw in (None, ""):
            continue
        value = opaque_value(raw, MAX_CONVERSATION_CHARS)
        if not value:
            raise ApiError(400, "invalid_user",
                           f"user (or {CONVERSATION_HEADER}) must be text of at most "
                           f"{MAX_CONVERSATION_CHARS} characters without control characters")
        return value
    return DEFAULT_CONVERSATION


def parse_request(raw: bytes, header: str = "") -> dict:
    """What a chat completion request asks: text, images, conversation, streaming."""
    try:
        body = json.loads(raw or b"")
    except (ValueError, UnicodeDecodeError):
        raise ApiError(400, "invalid_json", "the body is not JSON") from None
    if not isinstance(body, dict):
        raise ApiError(400, "invalid_json", "the body is not a JSON object")
    text, images = read_content(_last_user_message(body.get("messages")).get("content"))
    options = body.get("stream_options")
    return {"text": text, "images": images, "conversation": conversation_of(body, header),
            "stream": body.get("stream") is True,
            "usage": isinstance(options, dict) and options.get("include_usage") is True}


def build_event(request: dict) -> dict:
    """The connector event for one API message, shaped as the page's chat builds its own."""
    conversation = request["conversation"]
    segments = ([{"type": "text", "text": request["text"]}] if request["text"] else []) + request["images"]
    return {"kind": "event", "platform": API_PLATFORM, "conversation_type": "dm",
            "conversation_id": conversation, "sender_id": conversation,
            "sender_name": SENDER_NAME, "message_id": secrets.token_hex(12),
            "sent_at": int(time.time()), "text": request["text"], "segments": segments,
            # Admitted as the page's chat is; a text API shows no sticker.
            "prefiltered": True, "capabilities": [TEXT_ONLY]}


# ------------------------------------------------------------ the answer -----

def answer_messages(result: dict) -> list[str]:
    """The character's messages in a turn's result, or the error it amounts to."""
    items = [i for i in result.get("replies") or [] if isinstance(i, dict)]
    if any(i.get("reason") == "excuse" for i in items):
        raise ApiError(502, "model_failed", "the character's model service did not answer; "
                       "`personagent doctor` checks the model settings", kind="api_error")
    if not result.get("owned"):
        raise ApiError(403, "not_admitted", "the access settings do not admit this conversation: "
                       "ACCESS_DM_USERS lists api users and this one is not among them",
                       kind="permission_error")
    return [str(i["text"]) for i in items
            if i.get("type") == "text" and isinstance(i.get("text"), str) and i["text"].strip()]


def completion(cid: str, created: int, content: str) -> dict:
    return {"id": cid, "object": "chat.completion", "created": created, "model": MODEL,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                         "logprobs": None, "finish_reason": "stop"}],
            "usage": dict(USAGE)}


def chunk(cid: str, created: int, delta: dict, finish: str | None = None, *,
          usage: bool = False) -> dict:
    out = {"id": cid, "object": "chat.completion.chunk", "created": created, "model": MODEL,
           "choices": [{"index": 0, "delta": delta, "logprobs": None, "finish_reason": finish}]}
    if usage:
        out["usage"] = None
    return out


def _sse(data) -> str:
    return "data: " + json.dumps(data, ensure_ascii=False) + "\n\n"


async def stream(task: asyncio.Task, cid: str, created: int, include_usage: bool):
    """SSE for a turn already running: the role at once, comments while it runs,
    one delta per message, the finish, the usage if asked, then [DONE]."""
    yield _sse(chunk(cid, created, {"role": "assistant", "content": ""}, usage=include_usage))
    while not task.done():
        # wait() leaves the turn running when the caller hangs up.
        await asyncio.wait({task}, timeout=KEEPALIVE_S)
        if not task.done():
            yield ": keep-alive\n\n"
    try:
        messages = answer_messages(task.result())
    except ApiError as error:
        yield _sse(error.body())
        yield "data: [DONE]\n\n"
        return
    except Exception:
        yield _sse(ApiError(500, "internal_error", "the turn failed; see the service log",
                            kind="api_error").body())
        yield "data: [DONE]\n\n"
        return
    for number, text in enumerate(messages):
        yield _sse(chunk(cid, created, {"content": text if number == 0 else "\n" + text},
                         usage=include_usage))
    yield _sse(chunk(cid, created, {}, "stop", usage=include_usage))
    if include_usage:
        yield _sse({"id": cid, "object": "chat.completion.chunk", "created": created,
                    "model": MODEL, "choices": [], "usage": dict(USAGE)})
    yield "data: [DONE]\n\n"


# ------------------------------------------------------------ the doors ------

def _bearer(request: Request) -> str:
    scheme, _, value = request.headers.get("authorization", "").strip().partition(" ")
    return value.strip() if scheme.lower() == "bearer" else ""


def refusal(request: Request) -> ApiError | None:
    """Why this caller may not use the API, None when it may. Off answers 404."""
    srv = _server()
    if not srv.CHAT_API_ENABLED:
        return ApiError(404, "api_disabled",
                        "the OpenAI-compatible API is turned off; set CHAT_API_ENABLED=true "
                        "(or run `personagent connect api`) and restart personagent")
    expected = srv.CHAT_API_KEY
    if expected:
        supplied = _bearer(request)
        if not supplied:
            return ApiError(401, "missing_api_key", "send the key as the header Authorization: Bearer <key>")
        if not srv._ct_equal(supplied, expected):
            return ApiError(401, "invalid_api_key", "the key does not match CHAT_API_KEY")
        return None
    # No key: a local program only, judged as the connector endpoints judge one.
    reason = srv._non_local_header(request)
    peer = request.client.host if request.client is not None else ""
    if reason or not srv._is_loopback_host(peer):
        return ApiError(401, "key_required",
                        "CHAT_API_KEY is blank, so only programs on this computer may call: "
                        + (reason or "this caller is on another computer"))
    return None


def _respond(request: Request, response: Response) -> Response:
    # A browser app may read the answer only when a key, not the origin, is the credential.
    if _server().CHAT_API_KEY and "origin" in request.headers:
        response.headers.update(_CORS)
    return response


def _error(request: Request, error: ApiError) -> Response:
    headers = {"Retry-After": str(error.retry_after)} if error.retry_after is not None else None
    return _respond(request, JSONResponse(error.body(), status_code=error.status, headers=headers))


_BODY_ERRORS = {"body_too_large": 413, "body_timeout": 408, "client_disconnected": 400}


async def _read(request: Request) -> bytes:
    body = await _server()._read_webhook_body(request)
    if isinstance(body, JSONResponse):
        code = json.loads(body.body).get("code", "")
        raise ApiError(_BODY_ERRORS.get(code, 400), code,
                       "the body is larger than SERVER_MAX_BODY_BYTES" if code == "body_too_large"
                       else "the body was not received")
    return body


async def models(request: Request) -> Response:
    refused = refusal(request)
    if refused is not None:
        return _error(request, refused)
    return _respond(request, JSONResponse({"object": "list", "data": [
        {"id": MODEL, "object": "model", "created": 0, "owned_by": "personagent"}]}))


async def chat_completions(request: Request) -> Response:
    srv = _server()
    refused = refusal(request)
    if refused is not None:
        return _error(request, refused)
    # The same budget as connector turns: each holds a slot for a whole turn.
    if not srv._connector_admission.try_acquire():
        return _error(request, ApiError(
            429, "capacity_exceeded", "the character is answering as many conversations as it may; "
            "retry shortly", kind="rate_limit_error", retry_after=3))
    handed_off = False
    try:
        asked = parse_request(await _read(request), request.headers.get(CONVERSATION_HEADER, ""))
        agent = srv.agent
        if agent is None or not agent.enabled:
            srv._warn_agent_off_once()
            raise ApiError(503, "character_off", f"the character is off: {srv._agent_off_reason()}; "
                           f"{srv._agent_off_fix()}", kind="api_error")
        event = build_event(asked)
        cid, created = "chatcmpl-" + secrets.token_hex(12), int(time.time())
        if asked["stream"]:
            # The turn holds the slot from here, until it ends, whatever the stream does.
            task = srv._spawn(agent.handle_event(event))
            task.add_done_callback(lambda _done: srv._connector_admission.release())
            handed_off = True
            return _respond(request, StreamingResponse(
                stream(task, cid, created, asked["usage"]), media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}))
        messages = answer_messages(await agent.handle_event(event))
        return _respond(request, JSONResponse(completion(cid, created, "\n".join(messages))))
    except ApiError as error:
        return _error(request, error)
    finally:
        if not handed_off:
            srv._connector_admission.release()


async def preflight(request: Request) -> Response:
    """A browser's CORS preflight; answered only while a key guards the API."""
    srv = _server()
    if not (srv.CHAT_API_ENABLED and srv.CHAT_API_KEY):
        return Response(status_code=404)
    return Response(status_code=204, headers=_CORS)


def install(app) -> None:
    app.get("/v1/models")(models)
    app.post("/v1/chat/completions")(chat_completions)
    app.options("/v1/models")(preflight)
    app.options("/v1/chat/completions")(preflight)


# ------------------------------------------------------------ the settings ---

def _truthy(value) -> bool:
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def settings(home: Path) -> dict:
    """CHAT_API_ENABLED, CHAT_API_KEY and the address, as the home's .env has them."""
    from dotenv import dotenv_values
    values = dotenv_values(home / ".env") if (home / ".env").is_file() else {}
    port = str(values.get("SERVER_PORT") or "").strip() or "8080"
    return {"enabled": _truthy(values.get("CHAT_API_ENABLED")),
            "key": str(values.get("CHAT_API_KEY") or "").strip(),
            "address": f"http://127.0.0.1:{port}/v1"}


def switch(home: Path, on: bool, *, replace_key: bool = False) -> dict:
    """Turn the API on or off in .env; turning it on without a key creates one."""
    from . import setup_wizard as sw
    env = sw.copy_env_template(home)
    values = {"CHAT_API_ENABLED": "true" if on else "false"}
    if replace_key or (on and not settings(home)["key"]):
        values["CHAT_API_KEY"] = new_key()
    sw.write_env(env, values)
    return settings(home)


def running(home: Path) -> bool:
    """Whether a character service holds this home's instance lock."""
    from .storage import LockUnavailable, RuntimeInstanceLock
    lock = RuntimeInstanceLock(home)
    try:
        lock.acquire()
    except LockUnavailable:
        return True
    except OSError:
        return False
    lock.release()
    return False


def connect(home: Path, *, remove: bool, replace_key: bool) -> int:
    """`personagent connect api`: switch the API on (or off) and print what another app needs."""
    from . import setup_wizard as sw
    home = home.resolve()
    if remove and replace_key:
        raise SystemExit(sw.t("api_remove_and_key"))
    found = switch(home, not remove, replace_key=replace_key)
    if remove:
        print(sw.t("api_removed"))
    else:
        print(sw.t("api_on"))
        print()
        from . import langs
        rows = [(sw.t(label), value) for label, value in (
            ("api_address", found["address"]), ("api_key", found["key"]), ("api_model", MODEL))]
        wide = max(langs.width(label) for label, _ in rows)
        for label, value in rows:
            print(f"  {label}{' ' * (wide - langs.width(label))}  {value}")
        print()
        if replace_key:
            print(sw.t("api_key_replaced"))
        print(sw.t("api_while_running"))
    if running(home):
        print(sw.t("api_restart"))
    if not remove and not sw.env_get(home / ".env", "LLM_API_KEY"):
        print(sw.t("coding_no_key"))
    return 0
