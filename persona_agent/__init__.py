"""persona_agent — the application package.

``Agent`` is configured by one settings record and composed from one mixin per
concern:

- settings   everything the agent is configured with, built once and passed in
- agent      wiring: applies the settings and builds the runtime state
- turns      intake, admission, modes and debounce for one message
- decision   whether to speak, the gate, then the reply
- dm         the one-on-one turn
- llm        model calls: endpoints, retries, fallback, probes
- prompts    the persona contract (style guide, output protocol, intent rules)
- textproc   pure text: tokenising, sanitising, whitelist validator, splitting,
             the prompt's data frames
- ingestion  links, share cards, images, OCR, vision, with the SSRF guard
- transport  throttling, chunking, typing simulation, sends, conversation LRU
- learning   self-eval, reaction adjudication, the EVOLVE_AUTO_ENABLED loop

Learning is three layers, so recording something and being changed by it are
separate acts:

- evidence   append-only record of what happened; carries no authority
- candidates versioned proposals and the append-only lifecycle that owns them
- promotion  when evidence may grant a candidate authority

Supporting modules, pure logic with no agent state:

- reactions  reaction attribution and adjudicator prompts
- evolution  eval -> feedback conversion, dedup, pool trimming
- endpoints  which endpoint serves a model name
- connector  platform-neutral inbound event schema and reply sink
- channels   conversation / memory / learning keys derived from an event
- stickers   sticker library: steal -> tag -> persona-fit gates -> feedback
- lineage    which persona-document hashes count as one character
- health     startup / runtime environment checks
- config_env the one way to read a setting out of the environment

Entry points are the `personagent` command (cli.py): init, chat, demo, run,
connect, doctor, learned, eval.
Read-only seed datasets ship with the package (paths.seed_file); everything
the agent learns at runtime goes to <home>/runtime/ (paths.ROOT is the home).
"""

__version__ = "1.2.2"
