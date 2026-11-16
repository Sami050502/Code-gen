# Dashboard Hierarchy Rules

Rules and guidelines for organizing dashboards with tabs, sections, and widgets.

## Critical: CREATE vs GET Format

**For CREATE operations**, the API enforces "only tabs allowed at top level". This means:
- Tabs are **mandatory** at the root level
- Flat layouts and sections-only layouts are **invalid for CREATE**
- Widgets must be nested inside tabs

The hierarchies below describe conceptual organization. For CREATE payloads, always wrap content in at least one tab.

## Required Hierarchy for CREATE

```
Dashboard (Root)
└── Tab (Level 1, MANDATORY)
    ├── Section (Level 2, optional)
    │   └── Widget (Level 3)
    └── Widget (Level 3, direct child of Tab)
```

## Valid Hierarchies

### 1. Single Tab (Minimal CREATE)

**Structure**: Dashboard → Tab → Widgets

```json
{
  "layout": [
    {
      "reference_id": "tab-main",
      "layout": [
        {"reference_id": "widget_1", "position": {...}},
        {"reference_id": "widget_2", "position": {...}}
      ]
    }
  ],
  "tabs": [{"reference_id": "tab-main", "title": "Overview"}],
  "widgets": [...]
}
```

**When to use**:
- Simple dashboards with 1-5 widgets
- Single-purpose views
- Prototypes or MVPs

### 2. Tab with Sections

**Structure**: Dashboard → Tab → Sections → Widgets

```json
{
  "layout": [
    {
      "reference_id": "tab-main",
      "layout": [
        {
          "reference_id": "section_1",
          "layout": [
            {"reference_id": "widget_1", "position": {...}}
          ]
        }
      ]
    }
  ],
  "tabs": [{"reference_id": "tab-main", "title": "Overview"}],
  "sections": [{"reference_id": "section_1", "title": "Section 1"}],
  "widgets": [...]
}
```

**When to use**:
- Single page with logical groupings
- 5-15 widgets that fall into 2-4 categories
- Related metrics that benefit from visual separation

### 3. Multiple Tabs (No Sections)

**Structure**: Dashboard → Tabs → Widgets

```json
{
  "layout": [
    {
      "reference_id": "tab_overview",
      "layout": [
        {"reference_id": "widget_1", "position": {...}}
      ]
    },
    {
      "reference_id": "tab_details",
      "layout": [
        {"reference_id": "widget_2", "position": {...}}
      ]
    }
  ],
  "tabs": [
    {"reference_id": "tab_overview", "title": "Overview"},
    {"reference_id": "tab_details", "title": "Details"}
  ],
  "widgets": [...]
}
```

**When to use**:
- Multiple distinct views
- Different audiences (exec vs. analyst)
- Different time periods (daily vs. monthly)

### 4. Full Hierarchy (Tabs with Sections)

**Structure**: Dashboard → Tabs → Sections → Widgets

```json
{
  "layout": [
    {
      "reference_id": "tab_1",
      "position": {...},
      "layout": [
        {
          "reference_id": "section_1",
          "position": {...},
          "layout": [
            {"reference_id": "widget_1", "position": {...}}
          ]
        }
      ]
    }
  ],
  "tabs": [
    {"reference_id": "tab_1", "title": "Tab 1"}
  ],
  "sections": [
    {"reference_id": "section_1", "title": "Section 1"}
  ],
  "widgets": [...]
}
```

**When to use**:
- Complex dashboards with 20+ widgets
- Multiple perspectives, each with logical groupings
- Executive dashboards with detailed drilldowns

## Invalid Hierarchies

### ❌ Sections Above Tabs

```json
// WRONG - Sections cannot contain tabs
{
  "layout": [
    {
      "reference_id": "section_1",
      "layout": [
        {"reference_id": "tab_1", "layout": [...]}
      ]
    }
  ]
}
```

**Why invalid**: Tabs are top-level navigation, sections are content grouping.

### ❌ Nested Tabs

```json
// WRONG - Tabs cannot contain other tabs
{
  "layout": [
    {
      "reference_id": "tab_1",
      "layout": [
        {"reference_id": "tab_2", "layout": [...]}
      ]
    }
  ]
}
```

**Why invalid**: Only one level of tabs allowed. Use sections within tabs instead.

### ❌ Mixed Direct and Nested Widgets in Same Parent

```json
// WRONG - Mixing section and direct widgets at same level
{
  "layout": [
    {"reference_id": "widget_1", "position": {...}},
    {
      "reference_id": "section_1",
      "position": {...},
      "layout": [
        {"reference_id": "widget_2", "position": {...}}
      ]
    }
  ]
}
```

**Why invalid**: Ambiguous hierarchy. Either use sections for all widgets or none.

**Fix**: Wrap `widget_1` in its own section, or move `widget_2` out of section.

### ❌ Nested Sections

```json
// WRONG - Sections cannot contain sections
{
  "layout": [
    {
      "reference_id": "section_1",
      "layout": [
        {
          "reference_id": "section_2",
          "layout": [...]
        }
      ]
    }
  ]
}
```

**Why invalid**: Sections are one level only. Use multiple sections at same level instead.

## Widget Count Limits

### Global Limit: 300 Widgets

Total widgets across entire dashboard cannot exceed 300.

```python
total_widgets = len(dashboard["widgets"])
assert total_widgets <= 300, "Too many widgets"
```

### Tab Limit: 50 Widgets (Recursive)

Each tab can contain up to 50 widgets, counting recursively through sections.

```python
def count_widgets_in_tab(tab_layout):
    count = 0
    for item in tab_layout:
        if item["reference_id"] in widget_ids:
            count += 1
        elif item.get("layout"):
            count += count_widgets_in_tab(item["layout"])
    return count

assert count_widgets_in_tab(tab) <= 50, "Tab has too many widgets"
```

**Example**:
```
Tab "Overview"
├── Section "Metrics"
│   ├── Widget 1
│   ├── Widget 2
│   └── Widget 3
├── Section "Charts"
│   ├── Widget 4
│   └── Widget 5
└── Widget 6 (direct)

Total for Tab: 6 widgets
```

### No Limit on Sections

There's no specific limit on sections, but practical considerations:
- Keep to 2-5 sections per tab for usability
- Each section should have clear purpose
- Too many sections = should split into tabs

## Reference ID Scoping

Reference IDs must be unique **across the entire dashboard**:

```json
{
  "layout": [
    {
      "reference_id": "tab_1",
      "layout": [
        {"reference_id": "widget_1", ...}  // OK
      ]
    },
    {
      "reference_id": "tab_2",
      "layout": [
        {"reference_id": "widget_1", ...}  // ERROR: Duplicate!
      ]
    }
  ]
}
```

**Fix**: Use unique IDs like `widget_tab1_1` and `widget_tab2_1`.

## Component Arrays

Each component type needs its own array:

```json
{
  "tabs": [
    {"reference_id": "tab_1", "title": "Overview"}
  ],
  "sections": [
    {"reference_id": "section_1", "title": "Metrics"}
  ],
  "widgets": [
    {"reference_id": "widget_1", "widget": {"id": "don:..."}}
  ]
}
```

**Rules**:
- Every `reference_id` in layout must have matching entry in component array
- Component arrays can be empty if that level isn't used
- Widgets array is always required (even if empty)
- Widget references must use nested format: `"widget": {"id": "..."}` NOT `"widget_id"`

## Position Inheritance

Positions are relative to their parent container. Tabs do not require position fields.

```json
{
  "reference_id": "tab_1",
  "layout": [
    {
      "reference_id": "widget_1",
      // This position is relative to tab_1's coordinate system
      "position": {"x": 0, "y": 0, "width": 4, "height": 2}
    }
  ]
}
```

**Key point**: Child positions start fresh at (0,0) within parent bounds.

## Section Positioning

Sections span full width (12 columns) and stack vertically:

```json
{
  "layout": [
    {
      "reference_id": "section_1",
      "position": {"x": 0, "y": 0, "width": 12, "height": 3}
    },
    {
      "reference_id": "section_2",
      "position": {"x": 0, "y": 3, "width": 12, "height": 5}
    }
  ]
}
```

**Best practices**:
- Always use `width: 12` for sections
- Stack sections vertically (increment y by previous section's height)
- Leave no gaps between sections

## Tab Positioning

Tabs also span full width and define viewport:

```json
{
  "layout": [
    {
      "reference_id": "tab_1",
      "position": {"x": 0, "y": 0, "width": 12, "height": 15}
    }
  ]
}
```

**Best practices**:
- Always use `x: 0, y: 0, width: 12` for tabs
- Height should accommodate all content
- Each tab is independent (positions don't affect other tabs)

## Choosing the Right Hierarchy

### Decision Tree

```
How many widgets?
├── 1-5 widgets → Flat (no hierarchy)
├── 6-15 widgets → Use sections
└── 16+ widgets
    ├── Single perspective → Use sections
    └── Multiple perspectives → Use tabs
        ├── Simple tabs → Tabs only
        └── Complex tabs → Tabs + sections
```

### By Use Case

| Use Case | Hierarchy | Example |
|----------|-----------|---------|
| Executive Summary | Flat | 3-4 KPI cards |
| Team Dashboard | Sections | Metrics, Charts, Tables |
| Multi-Team View | Tabs | Engineering, Sales, Support |
| Comprehensive Analytics | Tabs + Sections | Multiple tabs, each sectioned |

## Migration Paths

### Flat → Sections

When dashboard grows:

```json
// Before (flat)
{
  "layout": [
    {"reference_id": "widget_1", ...},
    {"reference_id": "widget_2", ...},
    {"reference_id": "widget_3", ...}
  ]
}

// After (sectioned)
{
  "layout": [
    {
      "reference_id": "section_1",
      "position": {"x": 0, "y": 0, "width": 12, "height": 3},
      "layout": [
        {"reference_id": "widget_1", ...},
        {"reference_id": "widget_2", ...}
      ]
    },
    {
      "reference_id": "section_2",
      "position": {"x": 0, "y": 3, "width": 12, "height": 2},
      "layout": [
        {"reference_id": "widget_3", ...}
      ]
    }
  ],
  "sections": [
    {"reference_id": "section_1", "title": "Overview"},
    {"reference_id": "section_2", "title": "Details"}
  ]
}
```

### Sections → Tabs

When perspectives diverge:

```json
// Before (sections)
{
  "layout": [
    {"reference_id": "section_daily", ...},
    {"reference_id": "section_monthly", ...}
  ]
}

// After (tabs)
{
  "layout": [
    {
      "reference_id": "tab_daily",
      "position": {...},
      "layout": [...]
    },
    {
      "reference_id": "tab_monthly",
      "position": {...},
      "layout": [...]
    }
  ],
  "tabs": [
    {"reference_id": "tab_daily", "title": "Daily View"},
    {"reference_id": "tab_monthly", "title": "Monthly View"}
  ]
}
```

## Validation Algorithm

```python
def validate_hierarchy(dashboard):
    # Check all reference_ids are unique
    all_refs = collect_all_reference_ids(dashboard)
    assert len(all_refs) == len(set(all_refs)), "Duplicate reference_ids"

    # Check component arrays match layout
    for ref in all_refs:
        assert ref_in_component_array(ref, dashboard), f"Missing {ref} in component array"

    # Check widget limits
    assert len(dashboard["widgets"]) <= 300, "Too many widgets"

    # Check tab limits (if tabs exist)
    if "tabs" in dashboard:
        for tab_ref in [t["reference_id"] for t in dashboard["tabs"]]:
            count = count_widgets_recursive(find_layout_item(tab_ref, dashboard))
            assert count <= 50, f"Tab {tab_ref} has too many widgets"

    # Check no nested tabs or invalid nesting
    validate_no_nested_tabs(dashboard["layout"])
    validate_no_sections_above_tabs(dashboard["layout"])
```

## Summary

**Key Principles**:
1. Maximum 3 levels: Dashboard → Tabs → Sections → Widgets
2. Tabs are top-level navigation (if used)
3. Sections group related content (if used)
4. Widgets are always leaf nodes
5. Reference IDs must be globally unique
6. Respect widget count limits (300 total, 50 per tab)
