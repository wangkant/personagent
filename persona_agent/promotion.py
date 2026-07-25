"""Evidence gate between "a reply seemed to land" and "imitate this reply".

Banking an example on a single positive signal is the weakest link in the
learning loop. One `haha` is weak evidence: it may be politeness, it may be
aimed at someone else in the thread, and the LLM self-evaluator — which is the
other source — is documented to score generously. Yet an entry that reaches
examples.jsonl is retrieved as a model of how to talk, indefinitely.

So nothing is banked on first sighting. A reply enters a candidate pool
carrying a confidence weight chosen by how much its source is worth, and is
promoted only once corroboration accumulates past PROMOTE_AT:

    owner positive reaction   0.60   two independent owner laughs promote
    other positive reaction   0.34   three strangers agreeing promote
    self-eval scored 5        0.26   four lenient self-scores promote

Confidence decays with a half-life, so a reply that landed once in March and
never again fades instead of waiting forever at the threshold. And evidence
runs both ways: when a later reaction rejects or corrects the same reply, it
is withdrawn from the candidate pool *and* from the live example pool, because
the strongest evidence about a reply is a human disagreeing with it.

Pure logic — no clock reads, no LLM. Callers pass `now`.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

# What each signal is worth. Deliberately set so that no single event of any
# kind can promote on its own: the cheapest path to the pool is two owner
# reactions, and the self-eval channel needs four.
# Each is set slightly above its exact share of PROMOTE_AT so the intended
# count still clears the bar after the decay applied between sightings —
# 4 x 0.25 lands exactly on 1.0 and then loses a hair to decay, which would
# make "four self-evals promote" quietly false.
WEIGHTS = {
    "reaction_owner": 0.60,   # 2 promote
    "reaction_other": 0.34,   # 3 promote
    "self_eval": 0.26,        # 4 promote
}
PROMOTE_AT = 1.0
HALF_LIFE_DAYS = 21.0
# Below this a candidate is not worth carrying; it is dropped on the next touch.
FLOOR = 0.08
MAX_CANDIDATES = 400


def _decayed(weight: float, age_days: float) -> float:
    if age_days <= 0:
        return weight
    return weight * (0.5 ** (age_days / HALF_LIFE_DAYS))


class CandidatePool:
    """Replies with some evidence behind them, but not yet enough to imitate."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._d: dict[str, dict] = {}
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self._d = {k: v for k, v in loaded.items() if isinstance(v, dict)}
        except (OSError, json.JSONDecodeError):
            self._d = {}

    # -- persistence -------------------------------------------------------
    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(self._d, fh, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
        except OSError:
            pass

    # -- queries -----------------------------------------------------------
    def confidence(self, reply: str, now: float) -> float:
        rec = self._d.get((reply or "").strip())
        if not rec:
            return 0.0
        age = max(0.0, (now - float(rec.get("ts", now))) / 86400.0)
        return _decayed(float(rec.get("weight", 0.0)), age)

    def sightings(self, reply: str) -> int:
        rec = self._d.get((reply or "").strip())
        return int(rec.get("n", 0)) if rec else 0

    # -- mutations ---------------------------------------------------------
    def record(self, example: dict, source: str, now: float) -> tuple[bool, float]:
        """Add evidence for `example`. Returns (should_promote, confidence).

        On promotion the candidate is consumed, so a reply is banked once and
        does not keep re-promoting every time someone laughs at it again.
        """
        reply = str(example.get("reply") or "").strip()
        if not reply:
            return False, 0.0
        add = WEIGHTS.get(source, WEIGHTS["self_eval"])
        prior = self.confidence(reply, now)
        rec = self._d.get(reply, {})
        total = prior + add
        self._d[reply] = {
            "weight": total,
            "ts": now,
            "n": int(rec.get("n", 0)) + 1,
            "sources": sorted(set(rec.get("sources", []) + [source])),
            "example": example,
        }
        if total >= PROMOTE_AT:
            self._d.pop(reply, None)
            self._save()
            return True, total
        self._prune(now)
        self._save()
        return False, total

    def withdraw(self, reply: str) -> bool:
        """Drop a candidate outright — a human disagreed with this reply."""
        if self._d.pop((reply or "").strip(), None) is not None:
            self._save()
            return True
        return False

    def _prune(self, now: float) -> None:
        for k in [k for k in self._d if self.confidence(k, now) < FLOOR]:
            self._d.pop(k, None)
        if len(self._d) > MAX_CANDIDATES:
            ordered = sorted(self._d.items(), key=lambda kv: float(kv[1].get("ts", 0)))
            for k, _ in ordered[: len(self._d) - MAX_CANDIDATES]:
                self._d.pop(k, None)


def retract_example(path: Path, reply: str) -> int:
    """Remove every banked example whose reply is `reply`. Returns how many.

    The counterpart to promotion: a reply the user later rejected must stop
    being retrieved as a model answer. Rewrites atomically and leaves every
    other row byte-identical.
    """
    reply = (reply or "").strip()
    if not reply or not Path(path).exists():
        return 0
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0
    kept, dropped = [], 0
    for ln in lines:
        if not ln.strip():
            continue
        try:
            rec = json.loads(ln)
        except json.JSONDecodeError:
            kept.append(ln)
            continue
        if isinstance(rec, dict) and str(rec.get("reply") or "").strip() == reply:
            dropped += 1
            continue
        kept.append(ln)
    if not dropped:
        return 0
    try:
        fd, tmp = tempfile.mkstemp(dir=str(Path(path).parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(kept) + ("\n" if kept else ""))
        os.replace(tmp, path)
    except OSError:
        return 0
    return dropped
