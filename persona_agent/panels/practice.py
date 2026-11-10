"""The practice panel: the scripted demo and a practice group chat.

Both run in a child process (`python -m persona_agent.panels.practice`):
the demo swaps the process's home while it plays, and the trial builds an
Agent from the home's .env, neither of which the page's process may do.
"""
from __future__ import annotations

import argparse
import asyncio
import atexit
import itertools
import json
import logging
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

from fastapi import Request

# Error codes this panel raises as ValueError, which the page may show.
ERRORS: frozenset[str] = frozenset({
    "practice_needs_key", "practice_failed", "practice_busy", "practice_invalid",
    "practice_gone", "practice_demo_failed", "practice_timeout",
})

TEXT_LIMIT = 2000
NAME_LIMIT = 16
DEMO_TIMEOUT = 120
START_TIMEOUT = 90
TURN_TIMEOUT = 240
ENTRY_LIMIT = 200
FAILURES = ("auth", "request", "rate_limit", "unreachable", "server", "other")


def _env_stamp(home: Path) -> float:
    try:
        return (home / ".env").stat().st_mtime
    except OSError:
        return 0.0


def _child(home: Path, *args: str) -> tuple[list[str], dict]:
    """The child's command line and Popen options, set up as the service's are."""
    from dotenv import dotenv_values

    from .. import home as homes

    env = os.environ.copy()
    # Settings saved in the page win over a stale parent environment.
    env.update({k: v for k, v in dotenv_values(home / ".env").items() if v is not None})
    env.update(AGENT_HOME=str(home), PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    options = dict(cwd=str(homes.CHECKOUT if homes.is_checkout() else home), env=env)
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    return [sys.executable, "-m", "persona_agent.panels.practice", *args], options


def _log(home: Path):
    logs = home / "runtime" / "desktop"
    logs.mkdir(parents=True, exist_ok=True)
    return open(logs / "practice.log", "ab")


def _clean_name(value) -> str:
    name = " ".join(str(value or "").split())
    if not name or len(name) > NAME_LIMIT or not name.isprintable():
        raise ValueError("practice_invalid")
    return name


class Practice:
    """The page's side of the practice group: one child, its transcript."""

    def __init__(self, workspace) -> None:
        self.home: Path = workspace.home
        self.workspace = workspace
        self.proc: subprocess.Popen | None = None
        self.answers: queue.Queue = queue.Queue()
        self.lock = threading.Lock()
        self.stamp = 0.0
        self.name = ""
        self.entries: list[dict] = []
        self.ids = itertools.count(1)
        # Page entry id -> the child's turn number; a reply's id -> its quote id.
        self.turns: dict[str, int] = {}
        self.mids: dict[str, str] = {}
        self.uids: dict[str, str] = {}
        self.demos: dict[str, list] = {}
        atexit.register(self.stop)

    # -- the child ----------------------------------------------------------

    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def stop(self) -> None:
        proc, self.proc = self.proc, None
        self.turns.clear()
        self.mids.clear()
        if proc is None:
            return
        try:
            proc.stdin.close()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    def _read(self, proc: subprocess.Popen, answers: queue.Queue) -> None:
        for raw in proc.stdout:
            try:
                answers.put(json.loads(raw))
            except ValueError:
                continue
        answers.put(None)

    def _answer(self, timeout: float, late: str = "practice_timeout") -> dict:
        try:
            answer = self.answers.get(timeout=timeout)
        except queue.Empty:
            self.stop()
            raise ValueError(late) from None
        if answer is None:
            self.stop()
            raise ValueError("practice_failed")
        if answer.get("error") in ERRORS:
            raise ValueError(answer["error"])
        return answer

    def _ensure(self) -> None:
        if not self.workspace.config().get("LLM_API_KEY"):
            raise ValueError("practice_needs_key")
        stamp = _env_stamp(self.home)
        if self.running() and stamp == self.stamp:
            return
        # New settings: the character is built again from them.
        self.stop()
        self.answers = queue.Queue()
        argv, options = _child(self.home, "trial")
        with _log(self.home) as log:
            self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=log, **options)
        self.stamp = stamp
        threading.Thread(target=self._read, args=(self.proc, self.answers), daemon=True,
                         name="personagent-practice").start()
        # A start that hangs is a failed start, not a slow model.
        ready = self._answer(START_TIMEOUT, "practice_failed")
        self.name = str(ready.get("name") or "")

    def _call(self, request: dict) -> dict:
        self.proc.stdin.write((json.dumps(request) + "\n").encode("utf-8"))
        self.proc.stdin.flush()
        return self._answer(TURN_TIMEOUT)

    def _locked(self, work):
        if not self.lock.acquire(blocking=False):
            raise ValueError("practice_busy")
        try:
            return work()
        except ValueError as error:
            if str(error) in ERRORS:
                raise
            self.stop()
            raise ValueError("practice_failed") from None
        except (OSError, KeyError, TypeError, AttributeError):
            self.stop()
            raise ValueError("practice_failed") from None
        finally:
            self.lock.release()

    # -- what the routes do -------------------------------------------------

    def view(self) -> dict:
        return {"running": self.running(), "name": self.name, "entries": list(self.entries)}

    def _translate(self, lang: str) -> None:
        """Say the reasons of earlier lines again in `lang`, while the child still knows them."""
        stale = {self.turns[e["id"]]: e for e in self.entries
                 if e["kind"] == "said" and e.get("lang") != lang and e["id"] in self.turns}
        if not stale:
            return
        texts = self._call({"op": "texts", "lang": lang, "turns": sorted(stale)}).get("texts") or {}
        for number, entry in stale.items():
            text = texts.get(str(number))
            if isinstance(text, dict):
                entry.update(reason=str(text.get("reason") or ""),
                             learning=str(text.get("learning") or ""), lang=lang)

    def start(self, lang: str = "en") -> dict:
        def work() -> dict:
            self._ensure()
            self._translate(lang)
            return self.view()
        return self._locked(work)

    def say(self, payload: dict, lang: str) -> dict:
        text = str(payload.get("text") or "").strip()
        if not text or len(text) > TEXT_LIMIT:
            raise ValueError("practice_invalid")
        owner = payload.get("as") == "owner"
        name = "" if owner else _clean_name(payload.get("name"))
        quoted = str(payload.get("quote") or "")
        if quoted and quoted not in self.mids:
            raise ValueError("practice_gone")

        def work() -> dict:
            self._ensure()
            if quoted and quoted not in self.mids:
                raise ValueError("practice_gone")
            uid = "" if owner else self.uids.setdefault(name, str(3001 + len(self.uids)))
            answer = self._call({"op": "say", "lang": lang, "owner": owner, "name": name,
                                 "uid": uid, "text": text, "quote": self.mids.get(quoted, "")})
            failure = str(answer.get("failure") or "")
            said = {"id": f"e{next(self.ids)}", "kind": "said", "owner": owner,
                    "name": str(answer.get("speaker") or name), "text": text,
                    "quote": next((e["text"] for e in self.entries if e["id"] == quoted), ""),
                    "what": str(answer.get("what") or ""), "reason": str(answer.get("reason") or ""),
                    "learning": str(answer.get("learning") or ""),
                    "memory": str(answer.get("memory") or ""), "lang": lang,
                    "failure": failure if failure in FAILURES or not failure else "other"}
            fresh = [said]
            self.turns[said["id"]] = int(answer["turn"])
            if answer.get("reply"):
                reply = {"id": f"e{next(self.ids)}", "kind": "reply", "text": str(answer["reply"]),
                         "after": said["id"], "retry": bool(answer.get("retry")),
                         "quotable": bool(answer.get("mid"))}
                self.turns[reply["id"]] = int(answer["turn"])
                if answer.get("mid"):
                    self.mids[reply["id"]] = str(answer["mid"])
                fresh.append(reply)
            self.entries = (self.entries + fresh)[-ENTRY_LIMIT:]
            return {"entries": fresh, "name": self.name}
        return self._locked(work)

    def why(self, entry: str, lang: str) -> dict:
        def work() -> dict:
            if entry not in self.turns or not self.running():
                raise ValueError("practice_gone")
            return self._call({"op": "why", "lang": lang, "turn": self.turns[entry]})
        return self._locked(work)

    def learned(self, lang: str) -> dict:
        def work() -> dict:
            self._ensure()
            return self._call({"op": "learned", "lang": lang})
        return self._locked(work)

    def reset(self) -> dict:
        def work() -> dict:
            self._ensure()
            self._call({"op": "reset"})
            self.entries, self.uids = [], {}
            self.turns.clear()
            self.mids.clear()
            return self.view()
        return self._locked(work)

    def demo(self, lang: str) -> dict:
        if lang not in self.demos:
            argv, options = _child(self.home, "demo", "--lang", lang)
            try:
                with _log(self.home) as log:
                    done = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                          stderr=log, timeout=DEMO_TIMEOUT, **options)
            except (OSError, subprocess.TimeoutExpired):
                raise ValueError("practice_demo_failed") from None
            scenes: list[dict] = []
            for raw in done.stdout.decode("utf-8", "replace").splitlines():
                try:
                    item = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(item, dict):
                    continue
                if item.get("kind") == "scene":
                    scenes.append({"key": str(item.get("key", "")), "title": str(item.get("title", "")),
                                   "intro": str(item.get("intro", "")), "beats": []})
                elif scenes:
                    scenes[-1]["beats"].append(item)
            if done.returncode or len(scenes) != 3:
                raise ValueError("practice_demo_failed")
            self.demos[lang] = scenes
        return {"scenes": self.demos[lang]}


def _lang(payload: dict) -> str:
    from .. import langs

    return langs.normalize(payload.get("lang")) or "en"


def mount(app, workspace, body) -> None:
    practice = Practice(workspace)
    app.state.practice = practice
    app.state.closers.append(practice.stop)

    @app.post("/api/practice/start")
    async def practice_start(request: Request):
        payload = await body(request)
        return await asyncio.to_thread(practice.start, _lang(payload))

    @app.post("/api/practice/say")
    async def practice_say(request: Request):
        payload = await body(request)
        return await asyncio.to_thread(practice.say, payload, _lang(payload))

    @app.post("/api/practice/why")
    async def practice_why(request: Request):
        payload = await body(request)
        return await asyncio.to_thread(practice.why, str(payload.get("id") or ""), _lang(payload))

    @app.post("/api/practice/learned")
    async def practice_learned(request: Request):
        payload = await body(request)
        return await asyncio.to_thread(practice.learned, _lang(payload))

    @app.post("/api/practice/reset")
    async def practice_reset(request: Request):
        await body(request)
        return await asyncio.to_thread(practice.reset)

    @app.post("/api/practice/demo")
    async def practice_demo(request: Request):
        payload = await body(request)
        return await asyncio.to_thread(practice.demo, _lang(payload))


# ---------------------------------------------------------------------------
# The child process
# ---------------------------------------------------------------------------

def _emit(stream, value: dict) -> None:
    stream.write(json.dumps(value) + "\n")
    stream.flush()


def _demo(lang: str, out) -> int:
    from .. import demo, paths

    class PageDemo(demo.Demo):
        """The demo's scenes as beats the page plays, not printed lines."""

        def _scene(self, key, **fmt):
            self.trial.conv = f"demo-{key}"
            self.trial.last, self.trial.last_mid = None, ""
            joiner = "" if lang.split("-")[0] in ("zh", "ja", "ko") else " "
            intro = self.t[f"{key}_intro"].format(name=self.name, **fmt)
            _emit(out, {"kind": "scene", "key": key,
                        "title": self.t[key].format(name=self.name).strip("= "),
                        "intro": joiner.join(part.strip() for part in intro.splitlines())})
            return self.scripts[key]

        def _line(self, who, text):
            _emit(out, {"kind": "say", "who": who, "text": text})

        def _bot(self, turn):
            _emit(out, {"kind": "bot", "who": self.name, "text": turn.reply})

        def _note(self, text):
            text = " ".join(text.split())
            # The terminal brackets its notes; the page sets them apart by style.
            if text[:1] in "(（" and text[-1:] in ")）":
                text = text[1:-1]
            _emit(out, {"kind": "note", "text": text})

    def info(line: str) -> None:
        text = line.strip()
        if text.startswith(("[x] ", "[ ] ")):
            _emit(out, {"kind": "check", "ok": text[1] == "x", "text": text[4:]})
        elif text:
            _emit(out, {"kind": "info", "text": text})

    logging.getLogger("agent").setLevel(logging.CRITICAL)
    base = paths.ROOT / "runtime" / "desktop"
    base.mkdir(parents=True, exist_ok=True)

    async def play() -> int:
        with demo.throwaway_home(str(base)) as root:
            agent, model = demo.build_agent(lang, root, offline=True)
            try:
                scenes = PageDemo(agent, model, lang, info)
                for scene in demo.SCENES:
                    await getattr(scenes, scene)()
                return 0
            except demo.ModelFailed:
                return 1
            finally:
                await agent.aclose()
    return asyncio.run(play())


class _Trial:
    """The child's side: a chat.Trial answering one JSON request per line."""

    def __init__(self) -> None:
        from .. import chat

        self.chat = chat
        lang = chat.normalize_lang(os.getenv("AGENT_LANG", "en"))
        agent, state = chat.build_agent(lang, chat.TRIAL_TRIGGER)
        self.trial = chat.Trial(agent, state_dir=state,
                                factory=lambda: chat.build_agent(lang, chat.TRIAL_TRIGGER)[0])
        self.turns: dict[int, object] = {}
        self.count = itertools.count(1)

    @property
    def agent(self):
        return self.trial.agent

    def _what(self, turn) -> str:
        from ..access import ADMIN_MODE
        from ..decision import GATED_MODES

        if turn.failure is not None:
            return "failed"
        if turn.memory:
            return "memory"
        if not turn.reply:
            return "quiet"
        if turn.mode in GATED_MODES:
            return "joined"
        return "admin" if turn.mode == ADMIN_MODE else "named"

    def _trace(self, lang: str, turn) -> str:
        from .. import langs

        if turn.reaction is None:
            return ""
        doctor = langs.say("the health check", "运行检查", lang)
        text = self.chat.trace(lang, turn.reaction, doctor)
        head = self.chat.text_for(lang)["learning"].split("{text}")[0]
        return text[len(head):] if text.startswith(head) else text

    def _held(self, lang: str, cand: dict) -> str:
        from .. import langs

        check = self.chat.checklist(self.agent, cand)
        if check.waiting_for() == "why_person":
            # The terminal names a command here; the page has no terminal.
            return langs.say("only the admin can approve this kind of change",
                             "此类改动只能由管理员批准", lang)
        return self.chat.held_reason(lang, check)

    def _cand(self, lang: str, cand: dict) -> dict:
        from .. import candidates

        t = self.chat.text_for(lang)
        state = cand.get("state", "")
        return {"kind": t["kind_pair" if cand.get("type") == candidates.TYPE_PAIR else "kind_example"],
                "reply": self.chat.clip(cand.get("reply"), 80),
                "better": self.chat.clip(cand.get("better"), 80),
                "state": self.chat.state_label(lang, state),
                "inUse": state == candidates.STATE_PROMOTED,
                "why": self._held(lang, cand) if state == candidates.STATE_PROPOSED else ""}

    def _reason(self, lang: str, turn, what: str) -> str:
        if what not in ("quiet", "joined"):
            return ""
        return self.chat.reason(lang, turn, self.agent.persona_name)

    def texts(self, req: dict) -> dict:
        lang = req.get("lang") or "en"
        out = {}
        for number in req.get("turns") or []:
            turn = self.turns.get(int(number))
            if turn is not None:
                out[str(number)] = {"reason": self._reason(lang, turn, self._what(turn)),
                                    "learning": self._trace(lang, turn)}
        return {"texts": out}

    async def say(self, req: dict) -> dict:
        lang = req.get("lang") or "en"
        text = str(req.get("text") or "")
        if req.get("owner"):
            name, uid = self.agent.admin_name or "admin", self.chat._admin_id()
        else:
            name, uid = str(req.get("name") or "?"), str(req.get("uid") or "3001")
        quote = str(req.get("quote") or "")
        try:
            turn = await self.trial._group_turn(name, uid, text, quote)
        except Exception as error:
            turn = self.chat.Turn(speaker=name, uid=uid, text=text,
                                  failure=self.chat.describe_failure(error))
        if quote and turn.reaction is not None and quote == self.trial.last_mid:
            self.trial.last_mid = ""
        number = next(self.count)
        self.turns[number] = turn
        what = self._what(turn)
        spoke = what in ("named", "admin", "joined")
        return {"turn": number, "speaker": turn.speaker, "what": what,
                "reply": turn.reply if what != "failed" else "",
                "mid": self.trial.last_mid if spoke else "",
                "reason": self._reason(lang, turn, what),
                "learning": self._trace(lang, turn), "retry": bool(turn.retry_of),
                "memory": ("saved" if turn.memory_saved else "refused") if turn.memory else "",
                "failure": turn.failure.kind if turn.failure is not None else ""}

    def why(self, req: dict) -> dict:
        lang = req.get("lang") or "en"
        turn = self.turns.get(int(req.get("turn") or 0))
        if turn is None:
            return {"error": "practice_gone"}
        what = self._what(turn)
        out = {"what": what, "speaker": turn.speaker, "text": self.chat.clip(turn.text, 80),
               "reply": self.chat.clip(turn.reply, 80) if what != "failed" else "",
               "reason": self._reason(lang, turn, what),
               "retryOf": self.chat.clip(turn.retry_of, 80),
               "learning": self._trace(lang, turn), "offered": [], "ledger": [], "candidates": []}
        if what in ("named", "admin", "joined"):
            out["offered"] = [{"reply": self.chat.clip(r.get("reply"), 80),
                               "better": self.chat.clip(r.get("better"), 80)} for r in turn.offered]
            events, cands = self.trial.about(turn)
            out["ledger"] = [{"who": e.get("speaker_name") or "?",
                              "verdict": self.chat.judged(lang, e)} for e in events]
            out["candidates"] = [self._cand(lang, c) for c in cands]
        return out

    def learned(self, req: dict) -> dict:
        lang = req.get("lang") or "en"
        conv = self.trial.conv
        try:
            summary = self.agent._learned_summary(conv, lang)
        except Exception:
            summary = self.agent._learned_summary(conv)
        cands = [c for c in self.agent.candidate_ledger.all()
                 if (c.get("scope") or {}).get("conv_id") == conv]
        cands.sort(key=lambda c: str(c.get("created_at") or ""), reverse=True)
        return {"summary": summary, "items": [self._cand(lang, c) for c in cands[:20]]}

    async def handle(self, req: dict) -> dict:
        op = req.get("op")
        if op == "say":
            return await self.say(req)
        if op == "why":
            return self.why(req)
        if op == "learned":
            return self.learned(req)
        if op == "texts":
            return self.texts(req)
        if op == "reset":
            await self.trial.reset()
            self.turns.clear()
            return {"ok": True}
        return {"error": "practice_invalid"}


def _trial(out) -> int:
    from .. import home

    home.load_env()
    if not os.getenv("LLM_API_KEY", "").strip():
        _emit(out, {"error": "practice_needs_key"})
        return 1
    logging.getLogger("agent").setLevel(logging.CRITICAL)

    async def serve() -> int:
        try:
            session = _Trial()
        except Exception:
            logging.exception("practice: the character could not be built")
            _emit(out, {"error": "practice_failed"})
            return 1
        _emit(out, {"ready": True, "name": session.agent.persona_name})
        try:
            while True:
                # The page closing its end of the pipe ends this process.
                line = await asyncio.to_thread(sys.stdin.readline)
                if not line:
                    return 0
                try:
                    answer = await session.handle(json.loads(line))
                except Exception:
                    logging.exception("practice: a request failed")
                    answer = {"error": "practice_failed"}
                _emit(out, answer)
        finally:
            await session.agent.aclose()
    return asyncio.run(serve())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="persona_agent.panels.practice")
    parser.add_argument("what", choices=("demo", "trial"))
    parser.add_argument("--lang", default="en")
    args = parser.parse_args(argv)
    # Only answers go to stdout; anything else printed goes to the log.
    out, sys.stdout = sys.stdout, sys.stderr
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    if args.what == "demo":
        from .. import langs

        return _demo(langs.normalize(args.lang) or "en", out)
    return _trial(out)


if __name__ == "__main__":
    raise SystemExit(main())
