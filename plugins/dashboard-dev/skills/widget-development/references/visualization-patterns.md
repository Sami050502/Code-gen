# Visualization Patterns

Detailed patterns and constraints for DevRev widget visualizations.

## Chart x/y Arrays Must Be Objects

All chart types require `x` and `y` to be arrays of objects, not simple strings.

✅ **CORRECT**:
```json
"line": {
  "x": [{"reference_name": "data.date", "label": "Date"}],
  "y": [{
    "reference_name": "data.count",
    "label": "Count",
    "color": {"type": "static", "static": "chart-category-1-base"}
  }]
}
```

❌ **WRONG** - causes `Cannot read properties of undefined (reading 'split')`:
```json
"x": ["data.date"]  // String instead of object
```

**Rule**: Always use object format with `reference_name` and `label` fields.

## Color Values

Use DevRev's chart color palette:
- `chart-category-1-base` through `chart-category-10-base`

**Color object structure**:
```json
{
  "color": {
    "type": "static",
    "static": "chart-category-1-base"
  }
}
```

## Line Charts

Standard line chart structure:

```json
{
  "type": "line",
  "line": {
    "x": [{"reference_name": "data.date", "label": "Date"}],
    "y": [
      {
        "reference_name": "data.count",
        "label": "Count",
        "color": {"type": "static", "static": "chart-category-1-base"}
      }
    ]
  }
}
```

**Key points**:
- `x` is array (allows multiple x-axes theoretically, typically one)
- `y` is array (supports multiple series)
- Each y-series can have its own color

## Bar vs Column Charts

**CRITICAL**: DevRev follows the Highcharts convention for bar orientation:
- **`bar`** = **Horizontal** bars (categories on Y-axis, values on X-axis)
- **`column`** = **Vertical** bars (categories on X-axis, values on Y-axis)

❌ **WRONG** - `horizontal_bar` does not exist:
```json
"type": "horizontal_bar"  // Invalid! This type does not exist
```

### Horizontal Bar Chart (type: bar)

```json
{
  "type": "bar",
  "bar": {
    "x": [{"reference_name": "data.value", "label": "Value"}],
    "y": [
      {
        "reference_name": "data.category",
        "label": "Category",
        "color": {"type": "static", "static": "chart-category-1-base"}
      }
    ]
  }
}
```

### Vertical Bar Chart (type: column)

```json
{
  "type": "column",
  "column": {
    "x": [{"reference_name": "data.category", "label": "Category"}],
    "y": [
      {
        "reference_name": "data.value",
        "label": "Value",
        "color": {"type": "static", "static": "chart-category-1-base"}
      }
    ]
  }
}
```

**Rule**: Use `bar` for horizontal, `column` for vertical. There is no `horizontal_bar` type.

## Metric Visualization

For displaying a single KPI value (metric card):

```json
{
  "type": "metric",
  "metric": {
    "y": [
      {
        "reference_name": "data.kpi_value",
        "label": "KPI Name"
      }
    ]
  }
}
```

**Key Differences from Other Charts**:
- `metric.y` is an **array**, not an object (unlike pie/donut)
- Array must have at least one element
- No `x` axis needed (metric cards show one value)
- Used for KPI cards: ticket count, deflection rate, response time, etc.

**Common Mistake**:
```json
// ❌ WRONG - y is object, not array
"metric": {
  "y": {"reference_name": "data.count", "label": "Count"}
}

// ✅ CORRECT - y is array
"metric": {
  "y": [{"reference_name": "data.count", "label": "Count"}]
}
```

**Error you'll see if using wrong structure**:
```
Runtime error: e?.forEach is not a function
```

This happens because preview code expects `metric.y` to be an array and calls `.forEach()` on it.

## Donut/Pie Visualization

**CRITICAL**: Donut and pie visualizations have an **asymmetric structure** - `x` is an array, `y` is an object.

✅ **CORRECT** - Complete donut structure:
```json
{
  "type": "donut",
  "donut": {
    "x": [
      {
        "reference_name": "data.category",
        "label": "Category"
      }
    ],
    "y": {
      "reference_name": "data.count",
      "label": "Count"
    }
  }
}
```

**Key differences from other charts**:
- `x`: **Array** of dimension objects (slice categories)
- `y`: **Single object** (not array) for the measure (slice size)
- Donut shows proportions - `y` measure determines slice sizes

❌ **WRONG** - Common mistakes:

```json
// ❌ ERROR: x as object instead of array
"donut": {
  "x": {"reference_name": "data.category", "label": "Category"},
  "y": {"reference_name": "data.count", "label": "Count"}
}

// ❌ ERROR: y as array instead of object
"donut": {
  "x": [{"reference_name": "data.category", "label": "Category"}],
  "y": [{"reference_name": "data.count", "label": "Count"}]  // Array not allowed
}

// ❌ ERROR: Using "angle" field (from generic charting libraries)
"donut": {
  "angle": {"reference_name": "data.count"}  // Invalid field name
}
```

**Error messages you'll see**:
```
Bad Request: Invalid field: angle
Structure validation: donut.x must be array, donut.y must be object
```

**Complete example** - Tickets by Priority:
```json
{
  "version": "v0",
  "name": "tickets-by-priority",
  "title": "Tickets by Priority",
  "description": "Distribution of tickets by priority level",
  "data_sources": [{
    "reference_name": "data",
    "type": "oasis",
    "oasis": {
      "datasets": ["devrev.dim_ticket"],
      "sql_query": "SELECT priority FROM devrev.dim_ticket WHERE status = 'open'"
    },
    "dimensions": [{
      "reference_name": "priority",
      "devrev_schema": {
        "field_type": "enum",
        "type": "text",
        "ui": {"display_name": "Priority"}
      },
      "meerkat_schema": {
        "type": "string",
        "sql_expression": "priority"
      }
    }],
    "measures": [{
      "reference_name": "ticket_count",
      "devrev_schema": {
        "field_type": "number",
        "ui": {"display_name": "Ticket Count"}
      },
      "meerkat_schema": {
        "type": "number",
        "function": {
          "type": "count"
        },
        "sql_expression": "priority"
      }
    }]
  }],
  "sub_widgets": [{
    "reference_id": "donut_1",
    "query": {
      "dimensions": ["data.priority"],
      "measures": ["data.ticket_count"]
    },
    "visualization": {
      "type": "donut",
      "donut": {
        "x": [
          {
            "reference_name": "data.priority",
            "label": "Priority"
          }
        ],
        "y": {
          "reference_name": "data.ticket_count",
          "label": "Count"
        }
      }
    }
  }],
  "layout": [{
    "position": {"height": 4, "width": 6, "x": 0, "y": 0},
    "reference_id": "donut_1"
  }]
}
```

**Rule**: Remember the donut asymmetry:
- `x` = **array** of categories (what to slice by)
- `y` = **object** with measure (slice sizes)

## Table Visualization

Table structure for displaying data rows:

```json
{
  "type": "table",
  "table": {
    "columns": [
      {"reference_name": "data.dimension1", "label": "Column 1"},
      {"reference_name": "data.measure1", "label": "Metric 1"}
    ]
  }
}
```

**Key points**:
- `columns` is an array of column definitions
- Can include both dimensions and measures
- No x/y structure - uses columns directly

## Scatter Charts

Scatter plot structure:

```json
{
  "type": "scatter",
  "scatter": {
    "x": [{"reference_name": "data.x_value", "label": "X Axis"}],
    "y": [
      {
        "reference_name": "data.y_value",
        "label": "Y Axis",
        "color": {"type": "static", "static": "chart-category-1-base"}
      }
    ]
  }
}
```

**Key points**:
- Each point plotted at (x, y) coordinates
- Useful for correlation analysis

## Visualization Type Summary

| Type | x Structure | y Structure | Use Case |
|------|-------------|-------------|----------|
| `line` | Array of objects | Array of objects | Time series, trends |
| `bar` | Array of objects | Array of objects | **Horizontal** bar comparison |
| `column` | Array of objects | Array of objects | **Vertical** bar comparison |
| `scatter` | Array of objects | Array of objects | Correlation analysis |
| `heatmap` | Array of objects | Array of objects | Density visualization |
| `table` | N/A | N/A | Detailed data rows |
| `metric` | N/A | Array of objects | Single KPI value |
| `donut` | **Array of objects** | **Single object** | Proportions, parts of whole |
| `pie` | **Array of objects** | **Single object** | Proportions, parts of whole |

**Critical notes**:
- Only donut/pie have `y` as single object instead of array
- `bar` = horizontal bars, `column` = vertical bars (Highcharts convention)
- There is **no** `horizontal_bar` type
