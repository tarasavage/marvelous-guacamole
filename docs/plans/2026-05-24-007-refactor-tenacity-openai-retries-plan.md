---
title: "refactor: Replace custom OpenAI retry logic with tenacity"
type: refactor
status: completed
date: 2026-05-24
origin: docs/plans/2026-05-24-003-feat-vision-summary-pipeline-plan.md
---

# refactor: Replace custom OpenAI retry logic with tenacity

## Summary

Replace the hand-rolled retry loop in `backend/app/services/openai.py` with the `tenacity` library while preserving the existing product contract: extraction gets 3 attempts with 2s/4s/8s waits, summary gets 2 attempts with 2s/4s waits, and only transient OpenAI failures are retried. Add focused unit tests so retry behavior is locked before and after the swap.

---

## Problem Frame

`openai.py` implements its own `_call_with_retries` helper with manual attempt counting, `_is_retryable` classification, and `time.sleep` backoff. This works but duplicates what `tenacity` provides and leaves retry behavior untested. The user wants to remove the custom logic and standardize on `tenacity` without changing upstream callers or Celery orchestration.

---

## Requirements

- R1. Remove `_call_with_retries` and its manual sleep loop from `backend/app/services/openai.py`.
- R2. Use `tenacity` for all OpenAI call retries in that module.
- R3. Preserve extraction retry policy: **3 total attempts**, waits **2s, 4s, 8s** between retries (see origin R7 / M3 retry policy).
- R4. Preserve summary retry policy: **2 total attempts**, waits **2s, 4s** between retries (see origin R8).
- R5. Preserve transient-error classification: retry `RateLimitError`, `APIConnectionError`, `APITimeoutError`, and HTTP **429 / 500 / 502 / 503 / 504**; fail fast on other errors including domain errors raised inside the inner call (`OpenAIServiceError`, `ContextLimitError`).
- R6. Preserve warning-level logging on retry attempts (equivalent to current `logger.warning` on failure).
- R7. Keep retry policy in the service layer — no Celery `autoretry` changes (see origin scope boundary).

---

## Scope Boundaries

- Celery task retry configuration or worker recovery changes
- Changes to `ProcessDocumentUseCase` error messages or page-range failure handling
- OpenAI prompt/content changes
- Implementing the M3 plan's truncation retry (`finish_reason=length`) — current code fails immediately; this refactor preserves that behavior unless explicitly added in a follow-up

### Deferred to Follow-Up Work

- Truncation retry on `finish_reason=length` per M3 plan decision (separate behavioral fix, not required for the tenacity swap)
- Documenting tenacity as the standard retry approach in `docs/solutions/` via `/ce-compound`

---

## Context & Research

### Relevant Code and Patterns

- `backend/app/services/openai.py` — sole retry site in backend; `_is_retryable`, `_call_with_retries`, `EXTRACTION_BACKOFF`, `SUMMARY_BACKOFF`
- `backend/app/use_cases/process_document.py` — calls `extract_batch` and `summarize`; no retry logic here
- `backend/requirements.txt` — runtime deps; `tenacity` not yet listed
- `backend/tests/conftest.py` — pytest fixtures pattern for backend tests

### Institutional Learnings

- `docs/solutions/architecture-patterns/fastapi-layered-backend-di-2026-05-24.md` — OpenAI wrapping (including retries) belongs in `services/openai.py`, not use-cases or Celery
- `docs/solutions/architecture-patterns/pdf-summary-ai-requirements-2026-05-24.md` §10 — locks attempt counts and backoff schedules
- `docs/plans/2026-05-24-003-feat-vision-summary-pipeline-plan.md` — retries stay inside the task/service, not Celery autoretry

### External References

- [Tenacity documentation](https://tenacity.readthedocs.io/) — `retry`, `stop_after_attempt`, `wait_chain`, `wait_fixed`, `retry_if_exception`, `before_sleep_log`

---

## Key Technical Decisions

- **Library over custom loop:** Use `tenacity` decorators (or a small shared retry wrapper built from tenacity primitives) instead of `_call_with_retries`. Rationale: less bespoke code, idiomatic Python, easier to test with tenacity's retry state.
- **Fixed backoff via `wait_chain`:** Use `wait_chain(wait_fixed(2), wait_fixed(4), wait_fixed(8))` for extraction and `wait_chain(wait_fixed(2), wait_fixed(4))` for summary — not `wait_exponential`, which would not match the product contract.
- **Keep `_is_retryable`:** Reuse the existing predicate via `retry=retry_if_exception(_is_retryable)` so behavior stays identical during the swap.
- **Logging via `before_sleep_log`:** Use tenacity's `before_sleep_log(logger, logging.WARNING)` to preserve warning logs before sleeps.
- **No caller changes:** `extract_batch` and `summarize` public signatures and exception types stay the same; only internal retry mechanics change.

---

## Open Questions

### Resolved During Planning

- **Where does retry live?** Service layer only — unchanged.
- **Attempt count semantics:** `max_attempts=3` extraction and `max_attempts=2` summary mean total attempts (initial + retries), matching current `_call_with_retries` loop.
- **Truncation retry?** Out of scope — preserve current fail-fast on `finish_reason=length`.

### Deferred to Implementation

- Whether to use two separate `@retry`-decorated inner functions vs one parameterized tenacity wrapper — either is fine if attempt counts, waits, and predicate match R3–R5

---

## Implementation Units

- U1. **Add tenacity dependency**

**Goal:** Make `tenacity` available to the backend runtime.

**Requirements:** R2

**Dependencies:** None

**Files:**
- Modify: `backend/requirements.txt`

**Approach:**
- Add `tenacity` with a pinned minimum version (e.g. `tenacity>=8.2.0`) alongside existing runtime deps

**Patterns to follow:**
- `backend/requirements.txt` existing style (unpinned or minimally pinned packages)

**Test scenarios:**
- Test expectation: none — dependency-only change

**Verification:**
- `tenacity` importable in the backend environment after install

---

- U2. **Replace custom retry loop with tenacity in openai.py**

**Goal:** Remove `_call_with_retries` and wire `extract_batch` / `summarize` through tenacity while preserving R3–R6.

**Requirements:** R1, R2, R3, R4, R5, R6, R7

**Dependencies:** U1

**Files:**
- Modify: `backend/app/services/openai.py`

**Approach:**
- Delete `_call_with_retries` and remove unused imports (`time`, `Callable`, `TypeVar` if no longer needed)
- Keep `_is_retryable` as the retry predicate
- Apply tenacity to the inner OpenAI call in `extract_batch` with `stop=stop_after_attempt(3)` and extraction wait chain
- Apply tenacity to the inner OpenAI call in `summarize` with `stop=stop_after_attempt(2)` and summary wait chain
- Use `before_sleep_log` for warning-level retry logging
- Ensure domain errors raised inside the inner call (`OpenAIServiceError` for empty/truncated responses, `ContextLimitError` from `check_context_limit`) are **not** retried

**Patterns to follow:**
- Existing backoff constants `EXTRACTION_BACKOFF` and `SUMMARY_BACKOFF` — can drive `wait_chain` construction to avoid magic numbers drifting from R3/R4

**Test scenarios:**
- Test expectation: none at unit level — behavior covered in U3; manual smoke: existing document processing path still calls the same public functions

**Verification:**
- No `_call_with_retries` or manual `time.sleep` retry loop remains in `openai.py`
- `extract_batch` and `summarize` signatures unchanged
- Retry counts and waits match R3/R4 when exercised by U3 tests

---

- U3. **Add unit tests for OpenAI retry behavior**

**Goal:** Lock retry semantics with mocked OpenAI client calls so the tenacity migration cannot silently change behavior.

**Requirements:** R3, R4, R5, R6

**Dependencies:** U2

**Files:**
- Create: `backend/tests/test_openai_retries.py`

**Approach:**
- Mock `OpenAI` client or `client.chat.completions.create` (monkeypatch at module level, consistent with `conftest.py` patterns)
- Use `side_effect` sequences for transient-then-success and exhaust-all-attempts cases
- Patch tenacity sleep (e.g. `monkeypatch.setattr` on `tenacity.nap.sleep` or equivalent) so tests run fast without real delays

**Execution note:** Implement after U2 so tests validate tenacity wiring directly.

**Patterns to follow:**
- `.agents/skills/python-testing-patterns/SKILL.md` — mock side effects, assert call counts, separate permanent vs transient errors
- `backend/tests/conftest.py` — pytest + monkeypatch conventions

**Test scenarios:**
- Happy path — Integration: transient `RateLimitError` on first call, success on second — `extract_batch` returns text; client called twice
- Happy path — Integration: transient failure on first summary call, success on second — `summarize` returns text; client called twice
- Error path — `RateLimitError` on all 3 extraction attempts — `extract_batch` raises after 3 client calls
- Error path — transient failure on both summary attempts — `summarize` raises after 2 client calls
- Error path — non-retryable `OpenAIServiceError` (e.g. empty response) — client called once, no retry
- Error path — non-retryable HTTP 401-style error (mock exception without retryable status/type) — client called once
- Edge case — verify wait schedule uses 2/4/8 for extraction (assert sleep calls or tenacity wait invocations if observable via mock)

**Verification:**
- All new tests pass
- Tests fail if retry counts or non-retryable behavior regress

---

## System-Wide Impact

- **Interaction graph:** Only `backend/app/services/openai.py` changes; `ProcessDocumentUseCase` and Celery task entry points unchanged
- **Error propagation:** Same exception types bubble to use-case failure handling; page-range messages unchanged
- **State lifecycle risks:** None — retries remain synchronous inside the worker process
- **API surface parity:** No HTTP or schema changes
- **Integration coverage:** Use-case tests do not cover OpenAI; U3 unit tests are the primary safety net
- **Unchanged invariants:** Celery does not autoretry batch/summary; document status transitions and `failed_at_page` semantics unchanged

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Tenacity retry predicate differs subtly from `_is_retryable` | Port predicate verbatim; U3 tests for retryable vs non-retryable |
| Sleep in tests slows CI | Mock tenacity sleep in U3 |
| Attempt-count off-by-one vs current loop | U3 asserts exact client call counts for exhaust and success paths |

---

## Sources & References

- **Origin document:** [docs/plans/2026-05-24-003-feat-vision-summary-pipeline-plan.md](docs/plans/2026-05-24-003-feat-vision-summary-pipeline-plan.md)
- Related code: `backend/app/services/openai.py`, `backend/app/use_cases/process_document.py`
- Learnings: `docs/solutions/architecture-patterns/fastapi-layered-backend-di-2026-05-24.md`
- External docs: https://tenacity.readthedocs.io/
