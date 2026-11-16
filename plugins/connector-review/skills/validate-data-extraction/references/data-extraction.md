# Data Extraction Validation Rules

Primary validation rules for DevRev connector data extraction phase. File: `functions/extraction/workers/data-extraction.ts`.

## CRITICAL Checks (C1–C14) – Must All Pass

| ID | Rule | Detection |
|----|------|-----------|
| **C1** | Progress events have NO parameters | `emit(ExtractorEventType.ExtractionDataProgress)` with no second argument |
| **C2** | Uses `processTask<ExtractorState>` pattern | `adapter.processTask("extraction", async ({adapter, state}) => ...)` |
| **C3** | Checks `adapter.isTimeout` in loops | `while (hasMore && !adapter.isTimeout)` and similar in for-loops |
| **C4** | Single message emission per invocation | At most 1–2 emits (task + onTimeout) per execution path |
| **C5** | State tracks pagination/completion | Pagination in `adapter.state`, not local variables |
| **C6** | Implements `onTimeout` callback | `{ onTimeout: async ({adapter, state}) => { ... } }` in processTask |
| **C7** | Required fields present | Work items include required DevRev fields |
| **C8** | Work items include `item_url_field` | Metadata defines and items populate item_url_field |
| **C9** | No manual data batching | No chunk/slice/batch of items; use repo.upload(items) |
| **C10** | 4xx errors emit Error immediately | Do not retry 4xx; emit error and return |
| **C11** | 5xx errors retry with warning | Retry 5xx with Delay/warning, then rethrow or continue |
| **C12** | Initializes repos before use | All repos from adapter.repos initialized before upload |
| **C13** | Repo `itemType` matches metadata `record_type` | Consistent record_type across metadata and repo usage |
| **C14** | Provides `initialDomainMapping` to spawn() | spawn() called with initialDomainMapping when required |

## HIGH Priority (H1–H9)

- **H1**: Rate limiting with Delay event (429 / Retry-After).
- **H2**: Pagination with reasonable batch sizes.
- **H3**: TIME_SCOPED_SYNCS support when enabled.
- **H4**: State persisted before timeout/return.
- **H5**: Handles EXTRACTION_DATA_CONTINUE event.
- **H6**: Distinguishes initial vs incremental sync.
- **H7**: Updates `lastSuccessfulSyncStarted` after success.
- **H8**: External API errors logged clearly (no full error objects).
- **H9**: No PII in logs (no email, password, token in console.log).

## MEDIUM Priority (M1–M3)

- **M1**: Configurable batch sizes (no hardcoded large literals).
- **M2**: Extraction statistics where applicable.
- **M3**: Parallel extraction only where safe (timeout-aware).

## References

- `state-management.md` – State pattern requirements
- `common-anti-patterns.md` – Shared anti-patterns (logging, emissions)
- `anti-pattern-detection.md` – Automated grep patterns
