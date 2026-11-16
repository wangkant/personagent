"""Run every stored direct platform until stopped: python -m persona_agent.direct --home DIR"""
from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

from dotenv import dotenv_values

from persona_agent import langs
from . import platform_for
from .base import Bridge, Status, load_credentials, sdk


def admits(home: Path):
    """Whether the reply settings let the character answer an addressed group
    message, read again whenever <home>/.env changes."""
    from persona_agent import access
    from persona_agent.config_env import env_bool

    path = home / ".env"
    kept: dict = {}

    def settings() -> dict:
        try:
            stamp = path.stat().st_mtime_ns
        except OSError:
            stamp = None
        if kept.get("stamp") != stamp or "values" not in kept:
            kept.update(stamp=stamp, values={k: str(v or "") for k, v in dotenv_values(path).items()})
        return kept["values"]

    def answered(event: dict) -> bool:
        values = settings()
        if not env_bool("AGENT_ENABLED", True, env=values):
            return False
        identity = access.identity_from_env(values)
        group = access.canonical_id(f"{event.get('platform')}:{event.get('conversation_id')}",
                                    identity.native_platforms)
        if group in identity.paused_groups:
            return False
        # A group still waiting for approval hears at most one fixed line, never a written reply.
        if access.awaits_group_approval(group, str(event.get("platform") or ""), identity.groups,
                                        access.approval_platforms(values.get(access.APPROVAL_SETTING)),
                                        via_connector=True):
            return False
        return not access.group_refusal(group, identity.groups, via_connector=True)
    return answered


async def serve(home: Path) -> int:
    env = {k: str(v or "") for k, v in dotenv_values(home / ".env").items()}
    stored = load_credentials(home)
    if not stored:
        print(langs.term("No direct platforms are connected."), flush=True)
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
        try:
            platform = platform_for(kind, values, home)
        except Exception as error:  # one platform that cannot load must not stop the rest
            logging.getLogger(__name__).warning("direct: %s is skipped: %r", kind, error)
            status.set(kind, "error", type(error).__name__)
            continue
        agent = client_type(agent_url, env.get("CONNECTOR_TOKEN", ""),
                            connector_id=f"direct-{kind}", timeout_s=420)
        bridges.append(Bridge(platform, agent, status, admits=admits(home)))
    print(langs.term(f"direct: running {', '.join(b.platform.kind for b in bridges)}"), flush=True)
    await asyncio.gather(*(bridge.run(stop) for bridge in bridges))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m persona_agent.direct",
                                     description=langs.term("Connect the stored platforms directly"))
    parser.add_argument("--home", required=True)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # httpx logs every request URL at INFO, and Telegram's carry the token.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return asyncio.run(serve(Path(args.home).resolve()))


if __name__ == "__main__":
    sys.exit(main())
