# Dashboard Structure Reference

Complete schema reference for DevRev dashboard CREATE operations.

## Critical: CREATE vs GET Format

Dashboard CREATE payloads differ from downloaded (GET) dashboards:
- **No `version` field** - API rejects this in CREATE
- **No root-level `description`** - Only tabs support descriptions
- **Nested widget references** - Use `"widget": {"id": "..."}` not `"widget_id"`
- **Mandatory tab hierarchy** - API enforces "only tabs allowed at top level"

## Root Schema (CREATE Format)

```json
{
  "title": "string (required)",
  "layout": [...],           // required, tab-first hierarchy
  "tabs": [...],             // required, at least one tab
  "widgets": [...],          // required, widget references
  "sections": [...],         // optional
  "timezone": "Auto-detect"  // recommended
}
```

## Layout Item Schema

Every item in the `layout` array:

```json
{
  "reference_id": "string (required, unique)",
  "position": {
    "x": "number (0-11)",
    "y": "number (0+)",
    "width": "number (1-12)",
    "height": "number (1+)"
  },
  "layout": [...] // nested layout for tabs/sections
}
```

**Note**: Tab layout items don't require position - only nested widget items do.

## Widget Reference Schema (CREATE Format)

```json
{
  "reference_id": "string (required, matches layout)",
  "widget": "string (required, DON format)"
}
```

**Wrong formats (API rejects):**
```json
// Nested object format
{"reference_id": "w1", "widget": {"id": "don:..."}}

// Flat widget_id field
{"reference_id": "w1", "widget_id": "don:..."}
```

**Correct format:**
```json
{"reference_id": "w1", "widget": "don:..."}
```

## Tab Schema

```json
{
  "reference_id": "string (required, matches layout)",
  "title": "string (required)",
  "description": "string (optional)"
}
```

## Section Schema

```json
{
  "reference_id": "string (required, matches layout)",
  "title": "string (required)",
  "description": "string (optional)"
}
```

## DON Format

Widget DON (DevRev Object Name):

```
don:data:{region}:devo/{org_id}:widget/{widget_id}
```

Components:
- **region**: `dvrv-us-1`, `dvrv-eu-1`, etc.
- **org_id**: Organization ID
- **widget_id**: Unique widget identifier

## Constraints

### Global Limits
- Maximum 300 widgets per dashboard
- Maximum 50 widgets per tab (recursive count)

### Grid Constraints
- x: 0-11 (12 columns, zero-indexed)
- y: 0+ (unlimited rows)
- width: 1-12 (must fit in grid)
- height: 1+ (minimum 1 row)
- x + width <= 12 (cannot overflow)

### Reference ID Rules
- Must be unique within dashboard
- Can contain: letters, numbers, underscore, hyphen

## Required Hierarchy for CREATE

```
Dashboard
└── Tabs (MANDATORY at root)
    └── Sections (optional)
        └── Widgets
```

API enforces: "only tabs allowed at top level"

## Complete CREATE Example

```json
{
  "title": "Sales Dashboard",
  "layout": [
    {
      "reference_id": "tab_overview",
      "layout": [
        {
          "reference_id": "widget_revenue",
          "position": {"x": 0, "y": 0, "width": 4, "height": 2}
        },
        {
          "reference_id": "widget_deals",
          "position": {"x": 4, "y": 0, "width": 4, "height": 2}
        },
        {
          "reference_id": "widget_chart",
          "position": {"x": 0, "y": 2, "width": 12, "height": 4}
        }
      ]
    }
  ],
  "tabs": [
    {"reference_id": "tab_overview", "title": "Overview"}
  ],
  "widgets": [
    {"reference_id": "widget_revenue", "widget": "don:data:dvrv-us-1:devo/DEV-123:widget/001"},
    {"reference_id": "widget_deals", "widget": "don:data:dvrv-us-1:devo/DEV-123:widget/002"},
    {"reference_id": "widget_chart", "widget": "don:data:dvrv-us-1:devo/DEV-123:widget/003"}
  ],
  "timezone": "Auto-detect"
}
```

## Validation Checklist

- [ ] No `version` field at root
- [ ] No `description` at root level
- [ ] `title` is present
- [ ] `layout` contains only tab references at root
- [ ] All widgets use flat string format: `"widget": "don:..."`
- [ ] All reference_ids are unique
- [ ] All grid positions satisfy x + width <= 12
- [ ] Total widget count <= 300
- [ ] Each tab has <= 50 widgets (recursive)
