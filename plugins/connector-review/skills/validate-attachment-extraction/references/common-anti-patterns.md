# Common Anti-Patterns (Shared)

Shared quick-reference patterns for data and attachment extraction validation.

## Logging

- **No PII**: Do not log email, password, token, or other PII (use IDs only).
- **No full error objects**: Log `error.message`, `error.status`, not `error` or `JSON.stringify(error)`.
- **No adapter.event**: Do not log `adapter.event`; log specific properties (e.g. `event_type`) if needed.
- **Limit volume**: Prefer ≤5 console.log/warn per file; use console.error for errors.

## Emissions

- **Single emit per path**: At most one progress/result emit per invocation (plus onTimeout emit if used).
- **No parameters on Progress**: `ExtractorEventType.ExtractionDataProgress` and similar must be emitted with no payload when required by the SDK.

## Rate Limits and Timeouts

- **429 handling**: Detect 429, use Delay event with Retry-After (or reasonable default).
- **onTimeout**: Implement onTimeout in processTask so state can be saved and extraction can resume.
- **Loops**: Check `adapter.isTimeout` in while/for loops to avoid Lambda timeouts without saving state.

## References

- Data extraction: `data-extraction.md`, `state-management.md`, `anti-pattern-detection.md`
- Attachment extraction: `attachment-extraction.md`, `anti-pattern-detection.md`
