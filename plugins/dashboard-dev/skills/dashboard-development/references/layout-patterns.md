# Dashboard Layout Patterns

Common layout patterns and best practices for arranging widgets in a 12-column grid.

## Standard Widget Sizes

### Full Width (12 columns)
```json
{"x": 0, "y": 0, "width": 12, "height": 4}
```
**Use for**: Large tables, detailed charts, section headers

### Half Width (6 columns)
```json
{"x": 0, "y": 0, "width": 6, "height": 3}
```
**Use for**: Side-by-side comparisons, paired metrics

### Third Width (4 columns)
```json
{"x": 0, "y": 0, "width": 4, "height": 2}
```
**Use for**: KPI cards, small charts, metric tiles

### Quarter Width (3 columns)
```json
{"x": 0, "y": 0, "width": 3, "height": 2}
```
**Use for**: Compact metrics, status indicators

## Common Layouts

### Pattern 1: Three KPIs in a Row

```json
{
  "layout": [
    {"reference_id": "kpi_1", "position": {"x": 0, "y": 0, "width": 4, "height": 2}},
    {"reference_id": "kpi_2", "position": {"x": 4, "y": 0, "width": 4, "height": 2}},
    {"reference_id": "kpi_3", "position": {"x": 8, "y": 0, "width": 4, "height": 2}}
  ]
}
```

Visual:
```
┌────────┬────────┬────────┐
│  KPI 1 │  KPI 2 │  KPI 3 │
│        │        │        │
└────────┴────────┴────────┘
```

### Pattern 2: Two Side-by-Side Charts

```json
{
  "layout": [
    {"reference_id": "chart_1", "position": {"x": 0, "y": 0, "width": 6, "height": 4}},
    {"reference_id": "chart_2", "position": {"x": 6, "y": 0, "width": 6, "height": 4}}
  ]
}
```

Visual:
```
┌─────────────┬─────────────┐
│   Chart 1   │   Chart 2   │
│             │             │
│             │             │
│             │             │
└─────────────┴─────────────┘
```

### Pattern 3: KPIs Above Chart

```json
{
  "layout": [
    {"reference_id": "kpi_1", "position": {"x": 0, "y": 0, "width": 4, "height": 2}},
    {"reference_id": "kpi_2", "position": {"x": 4, "y": 0, "width": 4, "height": 2}},
    {"reference_id": "kpi_3", "position": {"x": 8, "y": 0, "width": 4, "height": 2}},
    {"reference_id": "chart", "position": {"x": 0, "y": 2, "width": 12, "height": 5}}
  ]
}
```

Visual:
```
┌────────┬────────┬────────┐
│  KPI 1 │  KPI 2 │  KPI 3 │
├────────┴────────┴────────┤
│                          │
│       Full Chart         │
│                          │
│                          │
└──────────────────────────┘
```

### Pattern 4: Sidebar with Main Content

```json
{
  "layout": [
    {"reference_id": "sidebar_1", "position": {"x": 0, "y": 0, "width": 3, "height": 2}},
    {"reference_id": "sidebar_2", "position": {"x": 0, "y": 2, "width": 3, "height": 2}},
    {"reference_id": "main", "position": {"x": 3, "y": 0, "width": 9, "height": 6}}
  ]
}
```

Visual:
```
┌───┬──────────────────────┐
│ S │                      │
│ 1 │                      │
├───┤    Main Content      │
│ S │                      │
│ 2 │                      │
└───┴──────────────────────┘
```

### Pattern 5: Grid of Four

```json
{
  "layout": [
    {"reference_id": "w1", "position": {"x": 0, "y": 0, "width": 6, "height": 3}},
    {"reference_id": "w2", "position": {"x": 6, "y": 0, "width": 6, "height": 3}},
    {"reference_id": "w3", "position": {"x": 0, "y": 3, "width": 6, "height": 3}},
    {"reference_id": "w4", "position": {"x": 6, "y": 3, "width": 6, "height": 3}}
  ]
}
```

Visual:
```
┌─────────────┬─────────────┐
│   Widget 1  │   Widget 2  │
│             │             │
├─────────────┼─────────────┤
│   Widget 3  │   Widget 4  │
│             │             │
└─────────────┴─────────────┘
```

### Pattern 6: Mixed Heights

```json
{
  "layout": [
    {"reference_id": "tall", "position": {"x": 0, "y": 0, "width": 4, "height": 6}},
    {"reference_id": "short_1", "position": {"x": 4, "y": 0, "width": 4, "height": 3}},
    {"reference_id": "short_2", "position": {"x": 8, "y": 0, "width": 4, "height": 3}},
    {"reference_id": "short_3", "position": {"x": 4, "y": 3, "width": 4, "height": 3}},
    {"reference_id": "short_4", "position": {"x": 8, "y": 3, "width": 4, "height": 3}}
  ]
}
```

Visual:
```
┌──────┬──────┬──────┐
│      │  S1  │  S2  │
│ Tall ├──────┼──────┤
│      │  S3  │  S4  │
└──────┴──────┴──────┘
```

## Section Patterns

### Pattern 7: Section with Full-Width Header

```json
{
  "layout": [
    {
      "reference_id": "section_metrics",
      "position": {"x": 0, "y": 0, "width": 12, "height": 3},
      "layout": [
        {"reference_id": "w1", "position": {"x": 0, "y": 0, "width": 4, "height": 2}},
        {"reference_id": "w2", "position": {"x": 4, "y": 0, "width": 4, "height": 2}},
        {"reference_id": "w3", "position": {"x": 8, "y": 0, "width": 4, "height": 2}}
      ]
    }
  ],
  "sections": [
    {"reference_id": "section_metrics", "title": "Key Metrics"}
  ]
}
```

### Pattern 8: Multiple Sections Stacked

```json
{
  "layout": [
    {
      "reference_id": "section_top",
      "position": {"x": 0, "y": 0, "width": 12, "height": 3},
      "layout": [...]
    },
    {
      "reference_id": "section_middle",
      "position": {"x": 0, "y": 3, "width": 12, "height": 5},
      "layout": [...]
    },
    {
      "reference_id": "section_bottom",
      "position": {"x": 0, "y": 8, "width": 12, "height": 4},
      "layout": [...]
    }
  ]
}
```

## Tab Patterns

**Note:** Tab layout items do not require position fields. Only nested widgets/sections need positions.

### Pattern 9: Simple Tab with Widgets

```json
{
  "layout": [
    {
      "reference_id": "tab_overview",
      "layout": [
        {"reference_id": "w1", "position": {"x": 0, "y": 0, "width": 6, "height": 4}},
        {"reference_id": "w2", "position": {"x": 6, "y": 0, "width": 6, "height": 4}}
      ]
    }
  ],
  "tabs": [
    {"reference_id": "tab_overview", "title": "Overview"}
  ]
}
```

### Pattern 10: Tab with Sections

```json
{
  "layout": [
    {
      "reference_id": "tab_main",
      "layout": [
        {
          "reference_id": "section_kpis",
          "layout": [...]
        },
        {
          "reference_id": "section_charts",
          "layout": [...]
        }
      ]
    }
  ],
  "tabs": [
    {"reference_id": "tab_main", "title": "Main"}
  ],
  "sections": [
    {"reference_id": "section_kpis", "title": "KPIs"},
    {"reference_id": "section_charts", "title": "Charts"}
  ]
}
```

## Auto-Layout Algorithm

For generating positions automatically:

```python
def auto_layout(widgets, default_width=4, default_height=2):
    """
    Auto-position widgets in a grid.

    Args:
        widgets: List of widget reference_ids
        default_width: Default widget width (columns)
        default_height: Default widget height (rows)

    Returns:
        List of layout objects with positions
    """
    layout = []
    x = 0
    y = 0
    current_row_height = default_height

    for widget_id in widgets:
        # Check if widget fits in current row
        if x + default_width > 12:
            # Wrap to next row
            x = 0
            y += current_row_height
            current_row_height = default_height

        # Place widget
        layout.append({
            "reference_id": widget_id,
            "position": {
                "x": x,
                "y": y,
                "width": default_width,
                "height": default_height
            }
        })

        # Move right
        x += default_width

    return layout
```

### Example auto-layout output:

Input: `["widget_1", "widget_2", "widget_3", "widget_4", "widget_5"]`

Output:
```json
[
  {"reference_id": "widget_1", "position": {"x": 0, "y": 0, "width": 4, "height": 2}},
  {"reference_id": "widget_2", "position": {"x": 4, "y": 0, "width": 4, "height": 2}},
  {"reference_id": "widget_3", "position": {"x": 8, "y": 0, "width": 4, "height": 2}},
  {"reference_id": "widget_4", "position": {"x": 0, "y": 2, "width": 4, "height": 2}},
  {"reference_id": "widget_5", "position": {"x": 4, "y": 2, "width": 4, "height": 2}}
]
```

## Responsive Considerations

While DevRev dashboards don't automatically reflow, consider these principles:

1. **Mobile-first sizing**: Prefer full-width (12) or half-width (6) for mobile viewing
2. **Minimum widget width**: Don't go below width=3 for readability
3. **Logical grouping**: Keep related widgets adjacent
4. **Visual hierarchy**: Place important widgets at top-left
5. **Consistent spacing**: Use uniform heights within rows when possible

## Best Practices

### Do:
- ✅ Use consistent widget sizes within a section
- ✅ Align widgets to grid boundaries
- ✅ Leave visual breathing room (don't pack too tightly)
- ✅ Group related metrics together
- ✅ Use full width for tables and detailed charts
- ✅ Place KPIs at the top for quick scanning

### Don't:
- ❌ Mix too many different sizes (creates visual chaos)
- ❌ Overflow the grid (x + width > 12)
- ❌ Use fractional columns (stick to integer positions)
- ❌ Create orphan widgets (single widget on a row when it could fit above)
- ❌ Use overly small widgets (width < 3 is hard to read)

## Common Widget Sizes by Type

| Widget Type | Recommended Size | Rationale |
|-------------|------------------|-----------|
| Metric/KPI Card | 4x2 or 3x2 | Quick scan, 3-4 per row |
| Small Chart | 4x3 or 6x3 | Readable trends |
| Large Chart | 12x5 or 6x4 | Detailed visualization |
| Table | 12x6+ | Full width for columns |
| Donut Chart | 4x3 or 6x4 | Square aspect works best |
| Bar Chart | 6x4 or 12x4 | Width for labels |
| Line Chart | 6x4 or 12x4 | Width for time series |

## Section Height Calculation

When using sections, calculate height as:

```
section_height = max(widget_y + widget_height for all widgets in section)
```

Example:
```json
{
  "section": {
    "position": {"x": 0, "y": 0, "width": 12, "height": 5},
    "layout": [
      {"position": {"x": 0, "y": 0, "width": 6, "height": 4}},
      {"position": {"x": 6, "y": 0, "width": 6, "height": 2}}
    ]
  }
}
```

Section height = max(0+4, 0+2) = 4, but we set to 5 to include padding.

## Dynamic Layout Tips

When generating layouts programmatically:

1. **Sort widgets by priority**: Place important widgets first (top-left)
2. **Group by size**: Place same-sized widgets together
3. **Balance rows**: Try to fill rows evenly
4. **Section breaks**: Add sections to create visual hierarchy
5. **Test on different screens**: Verify readability at different scales
