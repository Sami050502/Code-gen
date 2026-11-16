# Widget Quick Reference

## Widget Format (CREATE vs DOWNLOAD)

**CREATE format** - Used for creating/updating widgets (what the API expects):
```json
{
  "version": "v0",
  "name": "my-widget",
  "title": "Widget Title",
  "data_sources": [...],
  "sub_widgets": [...],
  "layout": [...]
}
```

**DOWNLOAD format** - What you get from the API (wrapped with platform fields):
```json
{
  "widget": {
    "id": "don:data:...:widget/abc123",
    "version": "v0",
    "name": "my-widget",
    "title": "Widget Title",
    "created_by": {...},
    "modified_date": "2024-01-27T...",
    "data_sources": [...],
    ...
  }
}
```

**How to identify format:**
| Format | Markers |
|--------|---------|
| DOWNLOAD | Has outer `"widget"` wrapper, contains `id`, `created_by`, `modified_date` |
| CREATE | `title`, `data_sources`, `sub_widgets` at root level, no platform fields |

**Converting DOWNLOAD → CREATE:**
1. Extract contents of the `"widget"` key to root level
2. Remove platform fields: `id`, `display_id`, `created_by`, `created_date`, `modified_by`, `modified_date`, `object_version`, `stock`

---

## Version Field

| Version | Use When |
|---------|----------|
| `"v0"` | OASIS widgets (custom SQL) - **use this** |
| `"v1"` | data_view widgets only |

Missing version defaults to v1, causing: `Bad request: v1 widgets must use data_view data sources only`

---

## Minimal Structure

```json
{
  "version": "v0",
  "name": "unique-widget-name",
  "title": "Widget Title",
  "description": "What this shows",
  "data_sources": [{
    "reference_name": "data",
    "type": "oasis",
    "oasis": {
      "datasets": ["devrev.dim_ticket"],
      "sql_query": "SELECT id, priority FROM devrev.dim_ticket"
    },
    "dimensions": [...],
    "measures": [...]
  }],
  "sub_widgets": [{
    "reference_id": "chart1",
    "query": {
      "dimensions": ["data.priority"],
      "measures": ["data.count"]
    },
    "visualization": {...}
  }],
  "layout": [{"reference_id": "chart1", "position": {"x": 0, "y": 0, "width": 6, "height": 3}}]
}
```

**Required**: `version`, `name`, `title`, `description`, `data_sources`, `sub_widgets`, `layout`

---

## Chart x/y Format

**Must be objects, not strings**:

```json
"x": [{"reference_name": "data.date", "label": "Date"}],
"y": [{"reference_name": "data.count", "label": "Count"}]
```

**Wrong** (causes split error): `"x": ["data.date"]`

---

## Metric Visualization

Used for single KPI cards (e.g., "P90 Response Time: 2.5s").

**Structure**:
```json
{
  "visualization": {
    "type": "metric",
    "metric": {
      "y": [
        {
          "reference_name": "data.my_metric",
          "label": "My Metric"
        }
      ]
    }
  }
}
```

**Requirements**:
- `metric.y` MUST be an **array** (even for single metric)
- Array must have at least one element
- Each element must have `reference_name` and `label`

**WRONG** (causes forEach error at runtime):
```json
"metric": {
  "y": {"reference_name": "data.my_metric", "label": "..."}  // Object, not array!
}
```

**CORRECT**:
```json
"metric": {
  "y": [{"reference_name": "data.my_metric", "label": "My Metric"}]  // Array!
}
```

---

## Widget Required Fields

| Field | Required | Notes |
|-------|----------|-------|
| `name` | **YES** | Human-readable identifier (validated by API) |
| `version` | **YES** | Must be `"v0"` |
| `data_sources` | **YES** | At least one data source |
| `sub_widgets` | **YES** | At least one sub-widget |
| `layout` | **YES** | Without this, widget renders blank |
| `title` | Recommended | Display title in UI |
| `description` | Optional | Widget description |

**Note**: The `name` field is validated by the API during the final validation stage, not by semantic validation.

---

## Visualizations Quick Reference

| Type | x | y | Required Fields |
|------|---|---|-----------------|
| line | array | array | type, x, y |
| bar | array | array | type, x, y |
| column | array | array | type, x, y |
| donut | array | object | type, x, y |
| pie | array | object | type, x, y |
| scatter | array | array | type, x, y |
| heatmap | array | array | type, x, y |
| **metric** | — | **array** | **type, y** |
| table | — | — | type, columns |

---

## Color Configuration

```json
"color": {
  "type": "static",
  "static": "chart-category-1-base"
}
```

Colors: `chart-category-1-base` through `chart-category-10-base`

**Wrong**: `"color": "blue"`

---

## Layout Grid

12-column grid: `width` 1-12, `height` 1+, `x` 0-11, `y` 0+

---

## Meerkat Schema Types

Valid values for `meerkat_schema.type`:

| Type | Use For |
|------|---------|
| `string` | Text fields, IDs, enums |
| `number` | Integers, doubles, counts |
| `boolean` | True/false flags |
| `time` | Dates, timestamps |
| `string_array` | Arrays of text/ID values |
| `number_array` | Arrays of numeric values |

**Always use lowercase values** - the API expects simple names like `"number"`, not protobuf enum names.

---

## reference_id Pattern

Must match: `^[a-zA-Z][a-zA-Z0-9_]*$`

- ✅ `chart1`, `my_chart`, `ticketCount`
- ❌ `1-chart` (starts with number)
- ❌ `my-chart` (hyphens not allowed)
- ❌ `chart.1` (dots not allowed)

---

## Invalid Fields (Do Not Use)

These fields do NOT exist in the API and will cause errors:

| Invalid Field | Error | Correct Approach |
|---------------|-------|------------------|
| `unit` | `Invalid field: unit` | Use `devrev_schema.ui.format` for formatting |
| `sorts` | `Invalid field: sorts` | Use `query.order_by` array for sorting |
| `angle` | `Invalid field: angle` | Use `donut.y` or `pie.y` for slice values |
| `orientation` | `Invalid field: orientation` | Use `bar` type for horizontal, `column` for vertical |
| `format` | `Invalid field: format` | Use `devrev_schema.ui.format` inside field schema |
| `time_comparison` | `Invalid field: time_comparison` | Not supported; compute in SQL or use separate widgets |
| `horizontal_bar` | `Invalid enum value` | Use `type: "bar"` (bar = horizontal, column = vertical) |

---

## Authoritative References

- **Visualization types**: `validation-schema.yaml` → `enums.visualization_types`
- **Sort directions**: `validation-schema.yaml` → `enums.sort_directions`
- **Type mappings**: `validation-schema.yaml` → `type_mappings.devrev_to_meerkat`
- **Field templates**: `templates.yaml`
