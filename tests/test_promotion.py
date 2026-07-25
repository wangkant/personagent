"""Tests for the evidence gate in front of the example pool.

The rule being protected: a single positive signal must never mint a permanent
example. These check the weights, the decay, the promotion threshold and the
retraction path — the parts that decide what the agent will imitate forever.

Run from the repo root:  python tests/test_promotion.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from persona_agent import promotion  # noqa: E402
from persona_agent.promotion import CandidatePool, retract_example  # noqa: E402

_failures: list[str] = []
DAY = 86400.0
NOW = 1_800_000_000.0


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        _failures.append(name)


def ex(reply: str) -> dict:
    return {"reply": reply, "scenario": "s", "mode": "called",
            "intent": "joke", "context": ["[u] hi"], "score": 5}


def pool(tmp: Path) -> CandidatePool:
    return CandidatePool(tmp / "cand.json")


def test_single_signal_never_promotes() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        for src in ("reaction_owner", "reaction_other", "self_eval"):
            p = pool(tmp / src)
            (tmp / src).mkdir(parents=True, exist_ok=True)
            promote, conf = p.record(ex("one laugh"), src, NOW)
            check(f"single {src} does not promote",
                  not promote and conf < promotion.PROMOTE_AT, f"conf={conf}")


def test_corroboration_promotes() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p = pool(tmp)
        r = ex("two owner laughs")
        check("owner 1/2: held", p.record(r, "reaction_owner", NOW)[0] is False)
        check("owner 2/2: promoted", p.record(r, "reaction_owner", NOW)[0] is True)

        p2 = CandidatePool(tmp / "b.json")
        r2 = ex("three strangers")
        p2.record(r2, "reaction_other", NOW)
        p2.record(r2, "reaction_other", NOW)
        check("stranger 3/3: promoted",
              p2.record(r2, "reaction_other", NOW)[0] is True)

        p3 = CandidatePool(tmp / "c.json")
        r3 = ex("self eval only")
        promoted = [p3.record(r3, "self_eval", NOW)[0] for _ in range(4)]
        check("self-eval needs four", promoted == [False, False, False, True],
              str(promoted))


def test_promotion_consumes_the_candidate() -> None:
    """A banked reply must not keep re-promoting every time it lands again."""
    with tempfile.TemporaryDirectory() as d:
        p = pool(Path(d))
        r = ex("consumed")
        p.record(r, "reaction_owner", NOW)
        check("promoted once", p.record(r, "reaction_owner", NOW)[0] is True)
        check("candidate cleared after promotion", p.confidence("consumed", NOW) == 0.0)
        check("next sighting starts over",
              p.record(r, "reaction_owner", NOW)[0] is False)


def test_confidence_decays() -> None:
    with tempfile.TemporaryDirectory() as d:
        p = pool(Path(d))
        p.record(ex("fading"), "reaction_owner", NOW)
        fresh = p.confidence("fading", NOW)
        half = p.confidence("fading", NOW + promotion.HALF_LIFE_DAYS * DAY)
        check("one half-life halves confidence", abs(half - fresh / 2) < 1e-6,
              f"{fresh} -> {half}")
        check("stale evidence cannot promote on its own",
              p.record(ex("fading"), "reaction_owner",
                       NOW + promotion.HALF_LIFE_DAYS * 2 * DAY)[0] is False)


def test_stale_candidates_pruned() -> None:
    with tempfile.TemporaryDirectory() as d:
        p = pool(Path(d))
        p.record(ex("ancient"), "self_eval", NOW)
        p.record(ex("recent"), "self_eval", NOW + 400 * DAY)
        check("decayed-below-floor candidate dropped",
              p.confidence("ancient", NOW + 400 * DAY) == 0.0)
        check("recent candidate kept", p.confidence("recent", NOW + 400 * DAY) > 0)


def test_withdraw() -> None:
    with tempfile.TemporaryDirectory() as d:
        p = pool(Path(d))
        p.record(ex("disputed"), "reaction_owner", NOW)
        check("withdraw reports a hit", p.withdraw("disputed") is True)
        check("evidence gone", p.confidence("disputed", NOW) == 0.0)
        check("withdrawing an unknown reply is a no-op", p.withdraw("never seen") is False)


def test_persistence() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p = pool(tmp)
        p.record(ex("survives restart"), "reaction_owner", NOW)
        again = pool(tmp)
        check("evidence survives a restart",
              abs(again.confidence("survives restart", NOW) - 0.60) < 1e-6)
        check("restart then corroborate promotes",
              again.record(ex("survives restart"), "reaction_owner", NOW)[0] is True)


def test_retract_example_from_pool() -> None:
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "examples.jsonl"
        rows = [ex("keep me"), ex("drop me"), ex("keep me too")]
        f.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        n = retract_example(f, "drop me")
        left = [json.loads(l)["reply"] for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        check("retract removes exactly the rejected reply", n == 1 and left == ["keep me", "keep me too"],
              f"n={n} left={left}")
        check("retracting an absent reply rewrites nothing",
              retract_example(f, "not here") == 0)

        # A malformed row must survive untouched rather than be silently eaten.
        f.write_text('{"reply": "drop me"}\nnot json\n', encoding="utf-8")
        retract_example(f, "drop me")
        check("malformed row preserved",
              f.read_text(encoding="utf-8").strip() == "not json")


def test_pool_is_bounded() -> None:
    with tempfile.TemporaryDirectory() as d:
        p = pool(Path(d))
        for i in range(promotion.MAX_CANDIDATES + 60):
            p.record(ex(f"r{i}"), "self_eval", NOW + i)
        check("candidate pool stays bounded",
              len(p._d) <= promotion.MAX_CANDIDATES, f"{len(p._d)} entries")


def main() -> int:
    test_single_signal_never_promotes()
    test_corroboration_promotes()
    test_promotion_consumes_the_candidate()
    test_confidence_decays()
    test_stale_candidates_pruned()
    test_withdraw()
    test_persistence()
    test_retract_example_from_pool()
    test_pool_is_bounded()
    print()
    if _failures:
        print(f"{len(_failures)} test(s) FAILED: {', '.join(_failures)}")
        return 1
    print("all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
