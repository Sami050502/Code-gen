# Attachment Extraction Validation Rules

Primary validation rules for DevRev connector attachment extraction phase. File: `functions/extraction/workers/*attachment*-extraction.ts`.

## CRITICAL Checks (C1–C10) – Must All Pass

| ID | Rule | Detection |
|----|------|-----------|
| **C1** | Uses `processTask` pattern | `adapter.processTask(...)` for the attachment task |
| **C2** | Calls `adapter.streamAttachments()` | Core SDK streaming method used |
| **C3** | Stream function returns `{ httpStream }` or `{ error }` | Correct return shape for streaming |
| **C4** | Single message emission per invocation | At most 1–2 emits per execution path |
| **C5** | Uses `responseType: 'stream'` | Prevents memory overflow from buffering |
| **C6** | Implements `onTimeout` callback | onTimeout in processTask options |
| **C7** | Batch size 5–50 | Memory management; avoid too large batches |
| **C8** | Try/catch around stream operations | Stream errors caught and returned as { error } |
| **C9** | 429 rate limit handling with Delay | Detect 429, emit Delay or return delay |
| **C10** | No logging of full error objects | Avoid console.log(error) or JSON.stringify(error) |

## HIGH Priority (H1–H7)

- **H1**: Explicit timeout configuration (e.g. 30s).
- **H2**: Timeout error handling with retry (e.g. ECONNABORTED).
- **H3**: Authentication headers included in requests.
- **H4**: Accept-Encoding: identity header where required.
- **H5**: 4xx errors emit/return error immediately (no retry).
- **H6**: 5xx errors retry with warning.
- **H7**: Clear, non-verbose error logging.

## MEDIUM Priority

- Batch size not too small (<5) for efficiency.
- Consistent use of stream return type.

## References

- `common-anti-patterns.md` – Logging and emission anti-patterns
- `anti-pattern-detection.md` – Automated grep patterns
