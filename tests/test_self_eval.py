"""A self-score is a whole number from 1 to 5, or no row at all."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from persona_agent import evolution

from helpers import check, isolated_agent


class _Answer:
    def __init__(self, content: str) -> None:
        self._content = content

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {"choices": [{"message": {"content": self._content}}]}


def _agent(tmp: Path, answer: dict):
    agent = isolated_agent(tmp)
    agent.eval_model = "m"
    agent.examples_seed_file = tmp / "examples.seed.jsonl"
    agent.examples_file = tmp / "examples.jsonl"

    async def post(url, auth, payload, timeout=30):
        return _Answer(json.dumps(answer))

    agent._post_chat = post
    return agent


def _rows(agent) -> list[dict]:
    path = agent.eval_file
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip()]


async def _evaluate(agent) -> None:
    await agent._evaluate_reply("g", "called", "question", "a reply", None, "chat",
                                ["Alice: question"])


async def test_a_score_that_is_not_one_to_five_writes_no_row(tmp: Path, caplog) -> None:
    caplog.set_level(logging.WARNING, logger="agent")
    for i, answer in enumerate(({"rating": 5}, {"score": 9}, {"score": 0},
                                {"score": "great"}, {"score": True},
                                {"score": 4.5})):
        caplog.clear()
        agent = _agent(tmp / str(i), answer)
        await _evaluate(agent)
        check(f"{answer}: no row", _rows(agent) == [], repr(_rows(agent)))
        said = [r.getMessage() for r in caplog.records if "score" in r.getMessage()]
        check(f"{answer}: one warning", len(said) == 1, repr(said))


async def test_a_score_written_as_text_is_read(tmp: Path) -> None:
    for i, (answer, score) in enumerate(((({"score": "4/5"}), 4),
                                         ({"score": " 3 "}, 3),
                                         ({"score": 2}, 2),
                                         ({"score": 5.0}, 5))):
        agent = _agent(tmp / str(i), answer)
        await _evaluate(agent)
        rows = _rows(agent)
        check(f"{answer}: stored as {score}",
              len(rows) == 1 and rows[0]["score"] == score, repr(rows))


def test_load_evals_skips_a_row_whose_score_is_not_one_to_five(tmp: Path) -> None:
    path = tmp / "evals.jsonl"
    rows = [{"ts": "a", "score": 0}, {"ts": "b", "score": 9}, {"ts": "c", "score": "x"},
            {"ts": "d", "score": None}, {"ts": "e"}, {"ts": "f", "score": 2},
            {"ts": "g", "score": 4}, {"ts": "h", "score": True}, ["not", "a", "row"]]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    check("only real low scores are diagnosed",
          [r["ts"] for r in evolution.load_evals(path, 2)] == ["f"])
    check("and the threshold still reads the real ones",
          [r["ts"] for r in evolution.load_evals(path, 4)] == ["f", "g"])
