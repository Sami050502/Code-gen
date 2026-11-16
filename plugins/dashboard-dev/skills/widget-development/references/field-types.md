# Field Types Reference

## ID Types (Complete List)

Common types:
```
account, ai_agent, article, conversation, custom_stage, dev_user,
group, part, rev_org, rev_user, service_account, tag, work
```

Full list (rarely needed):
```
account, action, ai_agent, article, artifact, automation, bot, change_event,
chat, code_change, code_version, command, comment, conversation, credit,
custom_object.log_pattern, custom_stage, custom_state, dashboard, dataset,
dev_org, emoji, engagement, entity, event, event_source, external_import,
external_sync_unit, flow, form, function_definition, group, intent, invoice,
invoice_line_item, job, journey, keyring, keyring_template, link, marketplace,
marketplace_category, marketplace_item, marketplace_submission, meeting,
metric_definition, metric_tracker, microflow_definition,
notification_content_template, oasis_data, one_time_line_item, org,
org_schedule, org_schedule_fragment, part, payment_method, pricing,
push_device, quote, quote_line_item, quote_term, recurring_line_item,
rev_org, rev_user, reward, reward_transaction, role, role_v1, room, scenario,
schedule, schedule_fragment, schema, secret, service_account, service_plan,
sku, sla, sla_policy, sla_tracker, slot, snap_component, snap_in,
snap_in_function, snap_in_package, snap_in_preferences, snap_in_version,
snap_kit_action, snap_widget, survey, survey_response, svc_acc, sync_history,
sync_unit, tag, timeline_entry, uom, user, user_mention, user_participation,
user_session, version, vista, vista_group_item, widget, work
```

---

## Common Enum Values

| Field | Values |
|-------|--------|
| priority | `p0`, `p1`, `p2`, `p3` |
| state | `open`, `in_progress`, `closed` |
| ticket stage | `new`, `needs_response`, `waiting_on_user`, `hold`, `resolved`, `archived` |
| issue stage | `backlog`, `triage`, `prioritized`, `in_development`, `completed`, `duplicate`, `wont_fix` |
| source_channel | `email`, `chat`, `plug`, `slack`, `whatsapp` |
| sentiment | `delighted`, `happy`, `neutral`, `unhappy`, `frustrated` |

---

## Common Datasets

| Dataset | Purpose |
|---------|---------|
| `devrev.dim_ticket` | Support tickets |
| `devrev.dim_issue` | Engineering issues |
| `devrev.dim_conversation` | Conversations |
| `devrev.dim_account` | Customer accounts |
| `devrev.dim_devu` | DevRev users (internal) |
| `devrev.dim_revu` | Rev users (customers) |
| `devrev.dim_revo` | Rev orgs |
| `devrev.dim_article` | Knowledge base |
| `devrev.fact_engagement` | Engagement events |

---

## Type Mapping Rules (Runtime-Enforced)

These rules are enforced by the backend and will cause `InvalidArgument` errors if violated.

### DevRev to Meerkat Type Mappings

Valid type mappings (source: `mosaic/internal/utils/constants.go`):

| DevRev Type | Required Meerkat Type |
|-------------|----------------------|
| `int`, `double` | `number` |
| `bool` | `boolean` |
| `date`, `timestamp` | `time` |
| `id`, `tokens`, `text`, `enum` | `string` |
| `uenum` | `number` |
| `[]int`, `[]double` | `number_array` |
| `[]id`, `[]text`, `[]tokens`, `[]enum` | `string_array` |
| `[]uenum` | `number_array` |

**Unsupported types**: `composite`, `[]bool`, `[]date`, `[]timestamp`

### Aggregate Function Output Types

| Function | Output Type | Rule |
|----------|-------------|------|
| `COUNT`, `COUNT_DISTINCT` | `number` | Always returns number |
| `SUM`, `AVG`, `MEDIAN` | `number` | Always returns number |
| `MIN`, `MAX` | (preserves input) | Output matches input type |

**Example**:
```yaml
# COUNT always returns number, regardless of input type
- reference_name: count_tickets
  devrev_schema:
    type: text  # Input type doesn't matter
  meerkat_schema:
    type: number  # Must be number for COUNT
    function:
      type: count
```
