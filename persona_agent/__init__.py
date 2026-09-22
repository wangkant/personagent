"""persona_agent — the application package.

``Agent`` is configured by one record and composed from one mixin per concern,
so the orchestration in agent.py stays readable and each layer is testable on
its own:

- settings   everything the agent is configured with, built once and passed in
- agent      orchestration: intake, modes, debounce, _think, prompt assembly
- prompts    the persona contract (style guide, output protocol, intent rules)
- textproc   pure text: tokenising, sanitising, whitelist validator, splitting
- pools      append-aware JSONL loading for the retrieval datasets
- ingestion  links, share cards, images, OCR, vision — with the SSRF guard
- transport  throttling, chunking, typing simulation, sends, conversation LRU
- learning   self-eval, reaction adjudication, the EVOLVE_AUTO loop

The learning path is three layers on purpose, so that recording something and
being changed by it are separate acts:

- evidence   append-only record of what happened; carries no authority
- candidates versioned proposals + the append-only lifecycle that owns them
- promotion  when evidence may grant a candidate authority (+ the legacy gate)

Supporting modules, all pure logic with no agent state:

- reactions  reaction attribution + adjudicator prompts
- evolution  eval -> feedback conversion, dedup, pool trimming
- gateway    platform-neutral inbound event schema + reply sink
- channels   the one place conversation / memory / learning keys are derived from an event
- stickers   sticker library: steal -> tag -> persona-fit gates -> feedback
- lineage    which persona-document hashes count as one character, so an edit doesn't orphan what was learned
- health     startup / runtime environment checks
- config_env the one way to read a setting out of the environment

Entry points live at the repo root (main.py, try_chat.py, quickstart.py).
Read-only seed datasets live in data/; everything the agent learns at runtime
goes to runtime/ (gitignored) — see paths.ROOT.
"""

__version__ = "0.3.0"
