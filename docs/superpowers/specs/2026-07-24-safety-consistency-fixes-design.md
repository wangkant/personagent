# Safety and State-Consistency Fixes

## Goal

Fix four production risks without changing persona behavior or performing a
large-scale `Agent` refactor:

1. Runtime learning must never modify the tracked synthetic seed datasets.
2. Rejected or undelivered model output must not enter memory, history,
   evaluation, or reaction-learning state.
3. Group and private transports must report delivery outcomes explicitly.
4. Image and webhook inputs must be bounded and local-file access must be
   fail-closed.

## Scope

This change is limited to the four risks above and their regression tests.
It does not split `persona_agent/agent.py`, replace JSON/JSONL persistence with
SQLite, redesign prompts, or add a new test framework.

## Runtime Learning Storage

The tracked files under `data/` remain read-only synthetic seed datasets:

- `data/examples.<lang>.jsonl`
- `data/feedback.<lang>.jsonl`

Automatic learning writes to ignored files under `runtime/`:

- `runtime/examples.<lang>.jsonl`
- `runtime/feedback.<lang>.jsonl`

At load time, the agent merges seed rows first and runtime rows second. Existing
custom un-suffixed seed files remain supported by the current language fallback
rules. Runtime paths may be overridden through explicit environment variables
for deployments that store state elsewhere.

The auto-reviewer and every in-process learning path use the runtime feedback
file as their write target. Read and de-dup operations cover both seed and
runtime files so a learned pair cannot duplicate a shipped pair.

No automatic migration edits an existing tracked seed file. A deployment that
previously accumulated real rows there continues to read them, but all new
writes go to `runtime/`.

## Candidate, Validation, Delivery, Commit

Model output is treated as a candidate until it passes the complete pipeline:

1. Parse the structured model output.
2. Extract, but do not persist, `CORE_UPDATE` and `mem`.
3. Apply the configured output filter.
4. Sanitize and validate the visible reply.
5. Classify the result as an intentional `PASS`, a valid visible reply, or a
   rejected candidate.
6. For a visible reply, attempt delivery.
7. Commit memory and learning state only after a valid outcome.

If filtering or validation rejects a candidate, neither core memory nor auto
memory is written. A valid explicit `PASS` may still persist its extracted
memory because no transport delivery is expected. A visible reply persists
memory, history, evaluation state, and reaction-learning state only after full
delivery succeeds.

Partial delivery is not treated as full success. It is logged with enough
context to diagnose the transport failure, but the complete candidate is not
added to history or any learning channel.

## Delivery Result

Group and private send functions return a shared `SendResult` value with:

- `success`: every intended sendable segment was delivered.
- `partial`: at least one segment was delivered before a later failure.
- `message_ids`: outbound platform message IDs captured from successful sends.
- `sticker_files`: sticker files actually delivered.

An empty but valid candidate is not passed to the transport. Sticker markers
that have no library match do not by themselves make delivery fail; success is
based on the sendable segments that remain. A candidate with no sendable
segments is treated as not delivered.

Private sends record message IDs under their private conversation key rather
than referencing a group variable. Transport exceptions and non-200 responses
produce a failed `SendResult` rather than being silently converted into a
successful handler return.

## Input Boundaries

### Local files

`file://` image input is denied unless `NAPCAT_IMAGE_DIR` is configured. When it
is configured, the resolved file must be contained by that directory. Symlink
and `..` escapes are rejected by comparing resolved paths.

### Image size and format

The maximum decoded or downloaded image size is 5,000,000 bytes.

- Base64 length is checked before decoding and decoded bytes are checked again.
- HTTP responses are streamed and aborted once the limit is exceeded.
- `Content-Length` values over the limit are rejected before streaming.
- Only recognized PNG, JPEG, GIF, WebP, BMP, HEIC/HEIF, or AVIF signatures
  proceed to image processing. Unknown data is rejected rather than labeled as
  JPEG.

The existing SSRF checks continue to run for the initial URL and every redirect
hop.

### Webhook bodies

Both webhook endpoints stream request bodies through one helper with a default
limit of 8,000,000 bytes. This accommodates a 5 MB image encoded into base64
inside gateway JSON while bounding memory use. `Content-Length` is checked
early, but streamed byte counting remains authoritative when that header is
missing or false.

Oversized requests return HTTP 413 and are not dispatched to the agent.
Malformed JSON continues to fail soft according to the existing endpoint
contract.

## Error Handling

- Security rejection is fail-closed and emits a bounded warning without logging
  raw image bytes or secrets.
- Delivery failure returns `False` from the handler unless a partial delivery
  occurred; partial delivery is still excluded from learning and persistent
  conversation state.
- Runtime directories are created lazily before the first write.
- Seed-file read failures do not erase a successfully loaded runtime dataset,
  and runtime-file read failures do not erase seed rows.
- Background evaluation and reaction-learning tasks are spawned only for fully
  delivered replies.

## Compatibility

- Existing environment variables and public webhook schemas remain valid.
- The tracked seed datasets retain their current formats.
- Existing JSON/JSONL runtime data remains readable.
- Intentional `PASS` replies retain their current ability to save valid memory.
- QQ and gateway message rendering remains unchanged.
- Python 3.10 remains supported.

## Testing

The existing script-based suites remain the source of truth. New regression
checks cover:

1. Filtered and validator-rejected replies do not persist either memory channel.
2. A private transport failure does not append an assistant turn or report full
   handling success.
3. A group transport failure does not create evaluation or reaction-learning
   state.
4. Private outbound message IDs are captured under the private conversation.
5. Runtime examples and feedback are written outside tracked seed files, while
   loaders merge both sources and de-duplicate across them.
6. `file://` is denied by default and allowed only inside
   `NAPCAT_IMAGE_DIR`.
7. Oversized base64, local, and HTTP image inputs are rejected.
8. Unknown image formats are not sent to the vision provider.
9. Oversized webhook bodies return HTTP 413, including bodies without a truthful
   `Content-Length`.

The full existing gateway, evolution, benchmark, and reaction suites must pass
after every task, followed by `python -m compileall -q .`.
