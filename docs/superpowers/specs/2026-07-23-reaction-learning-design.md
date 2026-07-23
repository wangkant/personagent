# Learning from real user reactions — design

## Goal

Replace the weakest link in the self-evolution loop — lenient LLM self-scoring
— with the strongest available signal: **how real users react to the bot's
replies**. When a user pushes back ("no, I meant X", "you got it wrong") the
bot learns a correction; when a user laughs or plays along, the reply is
banked as a proven success. This is the mechanism the earlier benchmark showed
was missing: same-vendor LLM evals score ~90% of replies 4-5, so the negative
half of the loop rarely fires. Humans, by contrast, tell you directly.

Reading a *reaction relative to a reply* (is this a correction? genuine?) is a
far easier and more reliable LLM task than scoring human-likeness — that is
why this design works where score-based eval stalled.

## Signals (user decisions locked in)

- **Explicit + high-confidence implicit.** Corrections/rejections stated
  outright; plus repeats/rephrasings of the same ask (didn't land) and
  immediate laughter/riffing (landed).
- **Attribution: only messages aimed at the bot.** Group: @bot or quoting a
  bot message. Private chat: the interlocutor's next message within a window.
  No same-person-loose-window inference in groups.
- **Owner has highest priority, but nothing writes blindly**: an in-process
  **agent adjudicator** reviews every candidate reaction with full context and
  persona before anything is learned. Owner corrections are near-default
  accepted; strangers must convince the adjudicator (poison resistance).
- **Both directions learned**: corrections/rejections → BAD/OK preference
  pairs in `feedback.<lang>.jsonl`; genuine positive reactions → the reply is
  appended to `examples.<lang>.jsonl`. Real reactions become the *primary*
  learning signal; LLM self-eval remains as the fallback channel.

## Architecture

```
bot sends reply ──► PendingReplies table (per-conv, capped, TTL)
                         │  entry: {mids, reply, ctx, mode, intent, target}
incoming message ──► attribution match?
   group: quote of a pending mid | @bot     ──► pop entry (one-shot)
   private: interlocutor's next msg in TTL  ──►
                         │
                         ▼  (_spawn, off the reply path)
              Agent adjudicator (single LLM call, judge/react model)
   classify {correction|rejection|positive|neutral}
   + genuine? (joke/troll/user-wrong filtered out; owner-weighted)
   + for corrections/rejections: draft the OK rewrite in persona voice
                         │
        ┌────────────────┼──────────────────┐
        ▼                ▼                  ▼
   accepted neg     accepted pos        rejected/neutral
   → feedback pair  → examples append   → audit only
   (dedup, hot-     (existing trim +
    reload)          dedup pipeline)
        └────────► all outcomes audited in candidates.jsonl (src=user_reaction)
```

## Components

| Unit | Responsibility |
|---|---|
| `persona_agent/reactions.py` | Pure logic, no I/O: `PendingReplies` (record / match / lazy-expire / one-shot pop), adjudicator prompt builders (en/zh), `parse_adjudication`, `to_feedback_pair`, `to_example` |
| `agent.py` glue | Capture outbound group `message_id`s (parse NapCat send response); record a pending entry after each sent reply (reusing the eval ctx snapshot); attribution check early in `_handle_inner`; `_process_reaction` spawned off the hot path |
| Config | `REACT_LEARN` (default true), `REACT_TTL_SEC` (900), `REACT_MAX_PENDING` (4/conv), `REACT_MODEL` (default judge model) |
| Reuse | `evolution.append_jsonl` + feedback dedup keys; `_append_example_with_trim` + `_auto_examples_seen`; `candidates.jsonl` audit trail |

## Key behaviors

- **One reaction per reply**: a successful match pops the pending entry.
- **Reaction messages still get replied to normally** — learning is a
  side-channel, never blocks or alters the reply pipeline (spawned task).
- **Adjudicator output** (single-line JSON): `{"reaction", "accept",
  "reason", "better", "scenario"}`. The feedback pair is built code-side from
  the pending entry (context/mode/reply) + the drafted `better`; malformed
  output = no write (fail-closed, same as the output protocol).
- **Owner weighting lives in the prompt**: reactor identity (owner / regular
  member) is stated; owner corrections default-accept unless clearly banter;
  stranger corrections accepted only when self-evidently right.
- **Positive path guards**: only non-PASS, non-empty replies; deduped against
  the example pool; capped by the existing trim pipeline.
- **Fallback ordering**: user-reaction learning is primary; the existing
  self-eval → EVOLVE_AUTO channel keeps running for replies that never get a
  directed reaction.
- Restart drops the in-memory pending table (bounded loss, acceptable v1).

## Testing

`tests/test_reactions.py`, stdlib `check()` harness, no network (stubbed
`_call_anthropic`): pending record/match/expire/one-shot; quote vs @ vs
private-window attribution; adjudicator parse fail-closed; accepted
correction → feedback pair written + hot-reload sees it; positive → example
appended once (dedup); stranger troll with adjudicator reject → audit only;
repo state isolation (temp dirs).

## Rollout

1. Implement in `personagent` (template, en/zh prompts, tests, CI).
2. Port to the private twin `xiaoyi-qq-bot` (deployed QQ path benefits most:
   real group, real owner).
3. README: reaction learning becomes the headline of the Self-evolution
   section (real-signal primary, LLM-eval fallback).
