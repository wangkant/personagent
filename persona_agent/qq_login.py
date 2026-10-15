"""Runs with AstrBot's interpreter; reuse its QQ binding implementation."""
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


async def bind(progress: Path, result: Path) -> None:
    import qrcode
    from astrbot.core.platform.sources.qqofficial.login_registration import (
        request_qqofficial_login_qr, poll_qqofficial_login_once,
    )

    registration = await request_qqofficial_login_qr({})
    image = io.BytesIO()
    qrcode.make(registration.qrcode).save(image, format="PNG")
    write_json(progress, {"status": "scan", "qrUrl": registration.qrcode,
                         "qrImage": "data:image/png;base64," + base64.b64encode(image.getvalue()).decode()})
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        value = await poll_qqofficial_login_once(
            platform_config={}, task_id=registration.task_id, bind_key=registration.bind_key)
        status = value.get("status")
        if status == "created":
            write_json(result, {"appid": value["appid"], "secret": value["secret"]})
            write_json(progress, {"status": "bound"})
            return
        if status in ("expired", "error"):
            raise RuntimeError("QR code expired or binding was declined; request a new code")
        await asyncio.sleep(max(1, registration.interval))
    raise RuntimeError("QR code expired; request a new code")


if __name__ == "__main__":
    progress, result = map(Path, sys.argv[1:3])
    try:
        asyncio.run(bind(progress, result))
    except Exception:
        # Upstream errors can contain credentials. Keep this boundary generic.
        write_json(progress, {"status": "error", "error": "QQ binding failed or expired. Please retry."})
        raise SystemExit(1)
