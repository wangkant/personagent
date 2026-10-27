"""Run every stored direct platform until stopped: python -m persona_agent.direct --home DIR"""
from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

from dotenv import dotenv_values

from . import platform_for
from .base import Bridge, Status, load_credentials, sdk


async def serve(home: Path) -> int:
    env = {k: str(v or "") for k, v in dotenv_values(home / ".env").items()}
    stored = load_credentials(home)
    if not stored:
        print("No direct platforms are connected.", flush=True)
        return 0
    client_type = sdk().Connector
    agent_url = f"http://127.0.0.1:{env.get('SERVER_PORT') or 8080}"
    status = Status(home)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except (NotImplementedError, RuntimeError):
            pass            # Windows: the parent terminates the process instead
    bridges = []
    for kind, values in stored.items():
        platform = platform_for(kind, values, home)
        agent = client_type(agent_url, env.get("CONNECTOR_TOKEN", ""),
                            connector_id=f"direct-{kind}", timeout_s=420)
        bridges.append(Bridge(platform, agent, status))
    print(f"direct: running {', '.join(b.platform.kind for b in bridges)}", flush=True)
    await asyncio.gather(*(bridge.run(stop) for bridge in bridges))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m persona_agent.direct",
                                     description="Connect the stored platforms directly")
    parser.add_argument("--home", required=True)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # httpx logs every request URL at INFO, and Telegram's carry the token.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return asyncio.run(serve(Path(args.home).resolve()))


if __name__ == "__main__":
    sys.exit(main())
