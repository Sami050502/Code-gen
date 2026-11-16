# State Management Requirements (Data Extraction)

State pattern requirements for DevRev connector data extraction phase.

## ExtractorState

- State must be persisted via the adapter; use `adapter.state` for pagination and progress.
- Pagination (page, cursor, offset) must live in state, not in local variables, so that timeouts can resume correctly.

## Required State Fields (when applicable)

- Pagination: e.g. `page`, `cursor`, `nextPageToken`, or equivalent.
- Completion: e.g. `hasMore`, `lastSuccessfulSyncStarted`.
- Domain mapping: if using spawn(), state passed to child tasks must be consistent with `initialDomainMapping`.

## Timeout and Persistence

- Before any long-running loop or return, ensure state is in a form that can be restored on the next invocation.
- `onTimeout` callback must emit progress (e.g. `ExtractionDataProgress`) so the platform can save state and resume.
- Do not rely on in-memory-only variables for pagination across invocations.

## Anti-Patterns

- **C5 violation**: Using `let page = 1` or similar local variables for pagination instead of `adapter.state.page`.
- **H4 violation**: Returning or timing out without ensuring state was written.
- **H7 violation**: Not updating `lastSuccessfulSyncStarted` (or equivalent) after a successful sync run.

## References

- `data-extraction.md` – Full validation rules
- `common-anti-patterns.md` – Logging and emission anti-patterns
