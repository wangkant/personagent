"""The script suites' reporting path, and the one rule it obeys:
**it must not be able to throw results away.**

Two ways it can, both measured in this repo rather than imagined, and both
with the same symptom — a run that stops early and shows a traceback where
assertions should have been, so an experiment reads as proving less than it
did:

1. `print` raising on a character the console codec cannot encode —
   `use_utf8_stdout()`.
2. One test function raising and taking every test after it down with it —
   `run_suite()`.

---

**1. Encoding.** These suites report by printing, and on Windows a
subprocess's stdout defaults to the locale codec — cp936 on this machine.
`tests/pytest_regression.py` runs every suite as a subprocess, so that is the
normal path, not an edge case. Any failure detail containing a character the
codec cannot encode makes `print` raise `UnicodeEncodeError` **inside the
reporting path**, which aborts the run at that point and replaces every
remaining assertion with a traceback.

That is not hypothetical and it is not cosmetic. Measured 2026-08-07: with a
deliberately broken persona-sync fixture, a store suite stopped after 16
PASS lines where the fixed version reports 74 — **58
assertions silently not run**, and the one experiment that mattered reported
a traceback instead of the two named failures it should have. The trigger was
an emoji: three shipped personas carry U+1F373 / U+1F4D6 / U+1F319, none of
which GBK can encode.

**Scope, measured rather than assumed.** An asset scan found exactly four
GBK-unencodable characters in the repo's test-reachable content — those three
card emoji and one in a README. Every `persona.txt` and `examples.en.jsonl`
is clean today. So most suites cannot hit this *right now*; they are safe by
accident of their fixtures, not by construction. Two things make that a bad
place to leave it:

* **The character-policy suite is emoji-centric by definition.** Its measurement table is
  `'ok ❤️ sure'`, `'yay \U0001f1ef\U0001f1f5'`,
  `'hug \U0001f468‍\U0001f469 ok'`. Its first real failure will print
  one of those.
* `tests/test_evolution.py` was already safe only *by accident*: it imports
  `tools.auto_reviewer`, which reconfigures the streams as an import side
  effect. Safety by transitive import is not safety.

**Why this idiom and not a bespoke one.** `tools/auto_reviewer.py` and
`tools/candidates_admin.py` already carry
exactly this four-line block. An earlier fix briefly introduced a second answer — a
`check()` that wrote UTF-8 bytes to `sys.stdout.buffer` — which worked but
meant two idioms for one problem, and only fixed the three suites that
adopted it. This is the existing idiom, factored once because twenty callers
need it, and it fixes `print` everywhere in the process rather than one
function.

---

**2. One test's crash silencing the rest.** A suite's `main()` calls its
tests one after another. An exception anywhere — including in a test's SETUP,
which is not the property under test at all — ends the process there and
every later check goes unrun and unreported.

Measured 2026-08-07 on this file's own discrimination experiment (a
persona importer's `IntegrityError` catch removed): the store suite
reported **73 checks where the baseline reports 116**, because a later test
called the importer as setup and the exception escaped. Independently
measured at HEAD with one injected `raise`, before this was addressed:

```
test_gateway         430 checks -> 44 pass, 0 fail, named failure=False, 386 LOST
test_store           212 checks -> 27 pass, 0 fail, named failure=False, 185 LOST
test_server_chat     124 checks -> 19 pass, 0 fail, named failure=False, 105 LOST
```

`run_suite` turns an escaping exception into ONE named failure and carries
on. It is applied at the harness rather than at each call site, because
wrapping calls individually has to be remembered every time a test is added
— which is the kind of thing that failed here in the first place.

**ADOPTION IS 23 OF THE 28 SUITES, NOT ALL OF THEM.** Stated exactly,
because this is a claim about the safety net and a reader who believes it
covers everything will trust a suite that is not covered:

| Not adopted | Why |
| --- | --- |
| `test_astrbot_plugin.py` | Reports with bare `assert`. |
| `test_injection.py` | Reports with bare `assert`. |
| `test_launchers.py` | Reports with bare `assert`. |
| `test_context.py` | Its `check(cond, msg)` RAISES on failure. |
| `test_store_degradation.py` | Already has its own equivalent guard. |

The first four share one principled boundary rather than four excuses:
`run_suite` needs a NON-RAISING reporter to record a failure through, and in
an assert-based suite a failure IS an exception and stopping is the intended
contract. Giving them one would mean changing what a failure means in those
files, which is a different task from this one. They are also the four
smallest reporters in the tree — between them they emit zero `[PASS]`/`[FAIL]`
lines, so there is nothing for a crash to silence.

`test_store_degradation.py` is a genuine exception of the other kind: its
`main_async` already wraps each test in `try/except` and records
`"<name> completed without raising"` through its own `check` — the same
behaviour this module provides. It builds a temp directory per test inside
the loop, so routing it through `run_suite_async` would replace working
code with thunk soup for no change in behaviour. Left as it is,
deliberately.

**If you add a suite**, use `run_suite`. If you cannot — because your
reporter raises — say so where the next reader will look, which is this
table.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Callable, Iterable, Tuple, Union


def use_utf8_stdout() -> None:
    """Make `print` unable to raise on this process's stdout/stderr.

    Idempotent, and never itself raises: a stream that cannot be
    reconfigured (already detached, replaced by a non-TextIO object, closed)
    is left alone, because a reporting-path hardener that throws would be the
    very bug it exists to prevent."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass


Test = Union[Callable[[], object], Tuple[str, Callable[[], object]]]


def _named(test: Test) -> tuple[str, Callable[[], object]]:
    """`(name, thunk)` for either spelling.

    A bare function carries its own name. A test that needs an argument, or
    that has to be wrapped (`asyncio.run(...)`, a temp directory built by the
    caller), is passed as an explicit `("test_name", lambda: ...)` pair — the
    lambda's `__name__` is `<lambda>`, and a failure report that says
    `<lambda> ran to completion` names nothing at all."""
    if isinstance(test, tuple):
        return str(test[0]), test[1]
    return getattr(test, "__name__", repr(test)), test


def _record(name: str, exc: BaseException, check: Callable[..., None]) -> None:
    frames = traceback.extract_tb(exc.__traceback__)
    where = (f"{Path(frames[-1].filename).name}:{frames[-1].lineno}"
             if frames else "<no frame>")
    traceback.print_exc()
    check(f"{name} ran to completion", False,
          f"{type(exc).__name__}: {exc} (at {where})")


def run_suite(tests: Iterable[Test], check: Callable[..., None]) -> None:
    """Run each test, recording an escaping exception as one named failure
    through the suite's own `check` instead of ending the run.

    `check` is passed in rather than imported so this stays agnostic about
    each suite's reporter and failure list — the suites are deliberately
    framework-free and each owns its own.

    The detail carries the exception type, its message and the last frame,
    which is what you need to find it; the full traceback still goes to
    stderr, so nothing is hidden. It is only stopped from being the LAST
    thing the run produces.

    `BaseException` is deliberately NOT caught: a `KeyboardInterrupt` or a
    `SystemExit` means somebody wants the run to stop, and a harness that
    swallowed those would be a worse bug than the one this fixes."""
    for test in tests:
        name, thunk = _named(test)
        try:
            thunk()
        except Exception as exc:  # noqa: BLE001 - reported, not swallowed
            _record(name, exc, check)


async def run_suite_async(tests: Iterable[Test],
                          check: Callable[..., None]) -> None:
    """`run_suite` for a suite whose `main_async()` awaits its tests.

    A separate function rather than a flag, because awaiting a coroutine and
    calling a function are different operations and a runner that guessed
    would silently succeed on a never-awaited coroutine — which is exactly
    the "the test ran and proved nothing" failure this module exists to
    prevent. A thunk here returns an awaitable; anything falsy-awaitable is
    simply not awaited, so a plain callable still works."""
    import inspect

    for test in tests:
        name, thunk = _named(test)
        try:
            result = thunk()
            if inspect.isawaitable(result):
                await result
        except Exception as exc:  # noqa: BLE001 - reported, not swallowed
            _record(name, exc, check)
