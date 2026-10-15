"""Runs with AstrBot's interpreter; reuse its QR login for QQ and WeChat."""
from __future__ import annotations

import asyncio
import base64
import io
import json
import os
from pathlib import Path
import sys
import time


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(".tmp")
    fd = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False)
    os.replace(temporary, path)


def show(progress: Path, content: str) -> None:
    import qrcode

    image = io.BytesIO()
    qrcode.make(content).save(image, format="PNG")
    write_json(progress, {"status": "scan", "qrUrl": content,
                          "qrImage": "data:image/png;base64," + base64.b64encode(image.getvalue()).decode()})


async def qq_official(progress: Path) -> dict:
    from astrbot.core.platform.sources.qqofficial.login_registration import (
        request_qqofficial_login_qr, poll_qqofficial_login_once,
    )

    registration = await request_qqofficial_login_qr({})
    show(progress, registration.qrcode)
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        value = await poll_qqofficial_login_once(
            platform_config={}, task_id=registration.task_id, bind_key=registration.bind_key)
        status = value.get("status")
        if status == "created":
            return {"appid": value["appid"], "secret": value["secret"]}
        if status in ("expired", "error"):
            raise RuntimeError("QR code expired or binding was declined")
        await asyncio.sleep(max(1, registration.interval))
    raise RuntimeError("QR code expired")


async def weixin_oc(progress: Path) -> dict:
    from astrbot.core.platform.sources.weixin_oc.login_registration import (
        request_weixin_oc_login_qr, poll_weixin_oc_login_once,
    )

    registration = await request_weixin_oc_login_qr({})
    show(progress, registration.qrcode_img_content)
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        # A long poll: each call waits on the server for up to 35 seconds.
        value = await poll_weixin_oc_login_once(platform_config={}, qrcode=registration.qrcode)
        status = value.get("status")
        if status == "created":
            return {key: value[key] for key in ("weixin_oc_token", "weixin_oc_account_id",
                                                "weixin_oc_base_url") if value.get(key)}
        if status in ("expired", "denied", "error"):
            raise RuntimeError("QR code expired or login was declined")
        await asyncio.sleep(max(1, registration.interval))
    raise RuntimeError("QR code expired")


LOGINS = {"qq_official": qq_official, "weixin_oc": weixin_oc}


async def bind(kind: str, progress: Path, result: Path) -> None:
    credentials = await LOGINS[kind](progress)
    write_json(result, credentials)
    write_json(progress, {"status": "bound"})


if __name__ == "__main__":
    kind, progress, result = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    try:
        asyncio.run(bind(kind, progress, result))
    except Exception:
        # Upstream errors can contain credentials. Keep this boundary generic.
        write_json(progress, {"status": "error", "error": "Login failed or expired. Please retry."})
        raise SystemExit(1)
