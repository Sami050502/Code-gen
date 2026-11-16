---
name: dashboard-development
description: This skill should be used when the user asks to "create a dashboard", "build a DevRev dashboard", "generate dashboard JSON", "add dashboard tabs", "organize widgets in sections", "fix dashboard layout", "dashboard grid overflow error", "validate dashboard structure", "dashboard widget limit exceeded", "reference_id error", or needs guidance on 12-column grid layouts, tab/section/widget hierarchy, dashboard JSON structure, widget DON references, or position calculation for dashboard layouts.
---

# Dashboard Development

Generate DevRev dashboards with tabs, sections, widgets, and 12-column grid layouts.

## Critical: CREATE Format Requirements

Dashboard CREATE payloads have specific requirements that differ from downloaded dashboards:

| Field | CREATE Format | Note |
|-------|---------------|------|
| `version` | **OMIT** | API rejects this field |
| `description` | **Auto-stripped** | CLI removes during CREATE; use UPDATE to add later |
| Widget refs | `"widget": "don:..."` | Flat string format, NOT nested object |
| Root layout | **Tabs only** | API enforces tab hierarchy |
| `timezone` | `"Auto-detect"` | Recommended |

## Minimal CREATE Structure

```json
{
  "title": "Dashboard Title",
  "layout": [
    {
      "reference_id": "tab-main",
      "layout": [
        {"reference_id": "widget_1", "position": {"x": 0, "y": 0, "width": 4, "height": 2}}
      ]
    }
  ],
  "tabs": [{"reference_id": "tab-main", "title": "Overview"}],
  "widgets": [{"reference_id": "widget_1", "widget": "don:data:dvrv-us-1:devo/ORG:widget/ID"}],
  "timezone": "Auto-detect"
}
```

## Grid System

12-column grid with position object:

```json
{"x": 0, "y": 0, "width": 4, "height": 2}
```

**Constraints:**
- `x`: 0-11, `y`: 0+
- `width`: 1-12, `height`: 1+
- `x + width` must be <= 12 (no overflow)

**Common sizes:** 4x2 (KPI cards), 6x3 (charts), 12x4 (tables)

**Recommended chart heights:**

| Chart Type | Minimum Height | Recommended Height |
|------------|----------------|-------------------|
| KPI/Metric | 2 | 2 |
| Donut/Pie | 3 | **4-5** |
| Line Chart | 3 | **4-5** |
| Bar Chart | 3 | **4-5** |
| Table | 4 | 6+ |

## Widget Reference Format

**CRITICAL**: Widget references must use flat string format with ONLY the DON ID.

**CORRECT** (Flat string format):
```json
{
  "reference_id": "widget_1",
  "widget": "don:data:dvrv-us-1:devo/ORG:widget/W-123"
}
```

**WRONG** (Nested object - API rejects with "expected: 'STRING'"):
```json
{
  "reference_id": "widget_1",
  "widget": {"id": "don:..."}        // ❌ Nested object format
}
```

**WRONG** (Embedded full widget):
```json
{
  "reference_id": "widget_1",
  "widget": {
    "title": "My Widget",           // ❌ Do NOT embed full widget
    "data_sources": [...],          // ❌ Do NOT include widget definition
    "type": "widget",               // ❌ Only ID reference allowed
    "id": "don:..."                 // ❌ Wrong structure
  }
}
```

**WRONG** (Flat widget_id):
```json
{
  "reference_id": "widget_1",
  "widget_id": "don:..."             // ❌ API rejects this field
}
```

**How to Get Widget IDs**:
1. Widgets must be created FIRST via `dashboard-sync widget create widgets/<name>.json`
2. Extract the returned `id` from the API response
3. Use ONLY that ID in the dashboard widget reference
4. Do NOT copy the entire widget definition into dashboard.json

## Limits

- Maximum 300 widgets per dashboard
- Maximum 50 widgets per tab (counts nested sections recursively)

## Hierarchy

Required for CREATE:
```
Dashboard → Tabs (mandatory) → Sections (optional) → Widgets
```

API error if widgets placed directly at root: `"only tabs allowed at top level"`

## Dashboard Description

**CREATE behavior:** Root-level `description` is automatically stripped by CLI during CREATE operations. This is handled silently - no error is raised.

**To add description:**
1. Create dashboard without description
2. Use `dashboard-sync dashboard push` to UPDATE with description
3. Or add description to tab instead (supported in CREATE)

**Tab description example:**
```json
"tabs": [
  {
    "reference_id": "tab-overview",
    "title": "Overview",
    "description": "Key metrics and trends for article engagement"
  }
]
```

## Dashboard Filters (Date Range)

Add a `filters` array at dashboard root to enable global date filtering. Widgets with `is_filterable: true` dimensions automatically respect these filters.

**Filter structure:**
```json
{
  "filters": [
    {
      "reference_id": "date_filter",
      "expression": {
        "operands": [
          {
            "type": "condition",
            "condition": {
              "key": "created_date",
              "operator": "equals",
              "value_type": "relative_date_value",
              "relative_date_value": {
                "type": "prev_n_days",
                "value": 30
              }
            }
          }
        ],
        "operator": "and"
      }
    }
  ]
}
```

**Filter condition fields:**
- `key`: Field name to filter on (e.g., `created_date`, `record_date`)
- `operator`: `equals`, `not_equals`, `greater_than`, `less_than`, etc.
- `value_type`: `relative_date_value`, `json_value`, or `value`
- `relative_date_value.type`: `prev_n_days`, `this_week`, `this_month`, `last_month`, etc.

**Widget filter consumption:**
Widgets automatically consume dashboard filters when:
1. Dimension has `is_filterable: true` in `devrev_schema`
2. Dimension field name matches filter `key`

**Example filterable dimension:**
```json
{
  "reference_name": "record_date",
  "devrev_schema": {
    "field_type": "timestamp",
    "is_filterable": true,
    "name": "record_date"
  }
}
```

## Dashboard Assembly Workflow

When creating a dashboard from widget files:

1. **Widget files exist** in `dashboards/<name>/widgets/*.json`
2. **Read each widget file** to extract metadata
3. **Create widgets on platform** using `dashboard-sync widget create`
4. **Collect widget IDs** from API responses
5. **Build dashboard.json** with ID-only references
6. **Upload dashboard** using `dashboard-sync dashboard create`

**DO NOT**:
- ❌ Copy widget file contents into dashboard.json
- ❌ Embed widget definitions in dashboard widget array
- ❌ Use local file paths or reference_names as IDs
- ❌ Skip widget creation step

## Dashboard URL Requirements

**CRITICAL**: Dashboard URLs must use the full DON ID format for reliable access.

**CORRECT** (Full DON ID - always works):
```
https://app.devrev.ai/<org>/dashboard?dashboardId=don:data:dvrv-us-1:devo/<org-id>:dashboard/<id>
```

**WRONG** (Short ID - intermittent 400 errors):
```
https://app.devrev.ai/<org>/dashboard?dashboardId=<short-id>
```

**Why**: The short ID format causes intermittent HTTP 400 errors. The platform sometimes resolves short IDs but fails unpredictably.

**Where to find the full DON ID**:
- CLI response after `dashboard-sync dashboard create`
- `dashboards/<slug>/meta.json` → `id` field
- `dashboards/<slug>/manifest.json` → `dashboard_id` field

**Example**:
```
✓ Short ID: u02MpJQq4C
✓ Full DON: don:data:dvrv-us-1:devo/3fAHEC:dashboard/u02MpJQq4C

Use full DON in URLs: https://app.devrev.ai/my-org/dashboard?dashboardId=don:data:dvrv-us-1:devo/3fAHEC:dashboard/u02MpJQq4C
```

## Validation

```bash
dashboard-sync dashboard validate <file>
```

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Unexpected JSON type for field: 'widget', expected: 'STRING'` | Nested widget object | Use flat string: `{"widget": "don:..."}` |
| `Invalid field: description` (in widget) | Embedded widget has description field | Remove embedded widget, use ID reference only |
| `Invalid field: data_sources` (in widget) | Embedded widget has data_sources | Remove embedded widget, use ID reference only |
| `Invalid field: version` | Using `"version": "v0"` | Remove field |
| `Invalid field: description` | Root-level description in CREATE | CLI auto-strips; use UPDATE to add later |
| `Invalid field: widget_id` | Wrong field name | Use `"widget": "don:..."` (flat string) |
| `only tabs allowed at top level` | Widgets in root layout | Wrap in tab structure |
| `GRID_OVERFLOW` | x + width > 12 | Adjust position |
| Short dashboard ID intermittent 400 | Using short ID in URL | Use full DON ID from meta.json |

## Resources

### Reference Files

- **`references/dashboard-structure.md`** - Complete schema, DON format, constraints
- **`references/layout-patterns.md`** - Common grid patterns, auto-layout algorithm
- **`references/hierarchy-rules.md`** - Tab/section nesting rules, migration paths

### Examples

- **`examples/simple-dashboard.json`** - Single tab, 3 widgets
- **`examples/multi-tab-dashboard.json`** - Multiple tabs with sections
- **`examples/auto-layout.json`** - Auto-positioned widgets in grid

## Quick Reference

### Position Calculation

```
Row 1: y=0, widgets at x=0,4,8 (width=4 each)
Row 2: y=2, widgets at x=0,4,8
```

### Auto-Layout Pattern

For n widgets with width=4, height=2:
- 3 per row (columns 0, 4, 8)
- Wrap to next row (y += 2) when x > 8

### Reference ID Conventions

- Tabs: `tab-overview`, `tab-details`
- Sections: `section-metrics`, `section-trends`
- Widgets: `widget_revenue`, `widget_chart`
