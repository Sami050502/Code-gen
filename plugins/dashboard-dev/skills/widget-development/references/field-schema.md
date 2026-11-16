# Field Schema Reference

Detailed field structure requirements for dimensions and measures.

## Required devrev_schema Structure

Complete field schema with all required fields:

```json
{
  "reference_name": "field_name",
  "devrev_schema": {
    "name": "field_name",           // Required: equals reference_name
    "data_name": "field_name",      // Required: equals reference_name
    "db_name": "field_name",        // Required: equals reference_name
    "field_type": "text",           // Required: text, int, double, enum, id, timestamp, etc.
    "is_filterable": true,          // Required: true for dimensions, false for measures
    "id_type": ["entity_type"],     // Required only for field_type: "id"
    "oasis": {
      "name": "field_name"          // Optional: OASIS layer name
    },
    "ui": {
      "display_name": "Field Name"  // Optional: UI display name
    }
  },
  "meerkat_schema": {
    "type": "string",               // Required: string, number, time, etc.
    "sql_expression": "field_name", // Optional for dimensions, required for measures
    "function": {                   // Optional: for aggregate functions
      "type": "MeerkatWidgetColumnFunction_TypeEnumSum"
    }
  }
}
```

## Field Type Reference

### devrev_schema.field_type Values

| Field Type | Description | Example |
|------------|-------------|---------|
| `text` | Text strings | Names, descriptions, statuses |
| `int` | Integer numbers | Counts, IDs |
| `double` | Floating-point numbers | Averages, percentages |
| `enum` | Enumeration values | Priority (p0, p1), status (open, closed) |
| `id` | Entity IDs | Ticket IDs, user IDs |
| `timestamp` | Date/time values | Created date, updated date |
| `bool` | Boolean values | Is deleted, is active |
| `array` | Array values | Tags, assignees |

### meerkat_schema.type Values

| Type | Use Case |
|------|----------|
| `string` | Text fields, IDs, enums |
| `number` | Integers, doubles, counts, aggregates |
| `time` | Dates, timestamps |
| `boolean` | True/false flags |
| `string_array` | Arrays of text/ID values |
| `number_array` | Arrays of numeric values |

**Always use lowercase values** (e.g., `"type": "number"`).

## Type Mappings

### devrev_schema → meerkat_schema

| devrev field_type | meerkat type |
|-------------------|--------------|
| `text` | `string` |
| `enum` | `string` |
| `id` | `string` |
| `tokens` | `string` |
| `int` | `number` |
| `double` | `number` |
| `timestamp` | `time` |
| `date` | `time` |
| `bool` | `boolean` |
| `[]id`, `[]text`, `[]enum` | `string_array` |
| `[]int`, `[]double` | `number_array` |

**Rule**: Aggregate functions (COUNT, SUM, AVG) always output `number` type.

### Type Compatibility Rules (Validation)

The API enforces strict type compatibility. Mismatches cause HTTP 406 errors.

**INVALID Combinations** (will fail validation):

| devrev field_type | meerkat type | Why Invalid |
|-------------------|--------------|-------------|
| `text` | `time` | Text fields are strings, not timestamps |
| `text` | `number` | Text fields are strings, not numbers |
| `enum` | `number` | Enums are string values |
| `timestamp` | `string` | Timestamps must use `time` type |
| `int` | `string` | Integers must use `number` type |
| `double` | `string` | Doubles must use `number` type |

**Special Rules:**

1. **Aggregate functions ALWAYS output `number`:**
   ```json
   {
     "devrev_schema": {"field_type": "timestamp"},  // Input can be any type
     "meerkat_schema": {
       "type": "number",  // MUST be number with aggregate
       "function": {"type": "MeerkatWidgetColumnFunction_TypeEnumCount"}
     }
   }
   ```

2. **Use the devrev type as source of truth** - meerkat type must be compatible.

3. **When in doubt, check the source column type** in the dataset schema.

## Common Mistakes

### Mistake: display_name at Root Level

❌ **WRONG**:
```json
{
  "reference_name": "priority",
  "display_name": "Priority",  // ❌ Wrong location
  "devrev_schema": {
    "field_type": "enum"
  }
}
```

✅ **CORRECT**:
```json
{
  "reference_name": "priority",
  "devrev_schema": {
    "field_type": "enum",
    "ui": {
      "display_name": "Priority"  // ✓ Inside devrev_schema.ui
    }
  }
}
```

### Mistake: Using "type" Instead of "field_type"

❌ **WRONG**:
```json
{
  "devrev_schema": {
    "type": "text"  // ❌ Wrong field name
  }
}
```

✅ **CORRECT**:
```json
{
  "devrev_schema": {
    "field_type": "text"  // ✓ Correct field name
  }
}
```

### Mistake: Using "column" Instead of "sql_expression"

❌ **WRONG**:
```json
{
  "meerkat_schema": {
    "column": "revenue"  // ❌ Wrong field name
  }
}
```

✅ **CORRECT**:
```json
{
  "meerkat_schema": {
    "sql_expression": "revenue"  // ✓ Correct field name
  }
}
```

### Mistake: Wrong Direction Value

❌ **WRONG**:
```json
{
  "order_by": [
    {"reference_name": "data.date", "direction": "desc"}  // ❌ Wrong value
  ]
}
```

✅ **CORRECT**:
```json
{
  "order_by": [
    {"reference_name": "data.date", "direction": "descending"}  // ✓ Use "descending" or "ascending"
  ]
}
```

## is_filterable Rules

**Dimensions**: Always `"is_filterable": true`
**Measures**: Always `"is_filterable": false`

```json
// Dimension
{
  "reference_name": "priority",
  "devrev_schema": {
    "field_type": "enum",
    "is_filterable": true  // ✓ Dimensions are filterable
  }
}

// Measure
{
  "reference_name": "ticket_count",
  "devrev_schema": {
    "field_type": "number",
    "is_filterable": false  // ✓ Measures are not filterable
  }
}
```

### Edge Case: Meerkat Auto-Filter Injection

**CRITICAL**: When `is_filterable: true`, Meerkat automatically injects filter conditions from dashboard-level filters. This can cause type mismatch errors on VARCHAR fields.

**Problem**: Dashboard has a date filter on `created_date`. Widget has a VARCHAR dimension named `record_date` with `is_filterable: true`. Meerkat injects a timestamp comparison against the VARCHAR field.

**Error signature**:
```
Cannot compare VARCHAR with TIMESTAMP
Type mismatch: expected TIMESTAMP, got VARCHAR
```

**Solution**: Set `is_filterable: false` on dimensions that should NOT inherit dashboard filters.

```json
// VARCHAR field that looks like a date but shouldn't receive date filters
{
  "reference_name": "record_date",
  "devrev_schema": {
    "field_type": "text",
    "is_filterable": false  // Prevents Meerkat auto-filter injection
  }
}
```

**When to use `is_filterable: false` on dimensions**:

| Scenario | Reason |
|----------|--------|
| VARCHAR fields with date-like names | Prevents timestamp comparison on string |
| Pre-aggregated dimensions from OASIS | Original column no longer exists |
| Custom SQL transformations (CASE, CONCAT) | Filter can't apply to computed value |
| Dimensions with intentional NULL handling | Filter may bypass COALESCE logic |

**Note**: This is an exception to the "dimensions always filterable" rule. Only use when you specifically need to prevent dashboard filter inheritance.

**See also**: `references/sql-patterns.md` → "Safe Type Conversion with TRY_CAST" for handling VARCHAR date fields in OASIS.

## ID Field Requirements

For `field_type: "id"`, must specify `id_type` array:

```json
{
  "reference_name": "ticket_id",
  "devrev_schema": {
    "field_type": "id",
    "id_type": ["work"],  // Required for ID fields
    "is_filterable": true
  }
}
```

**Common id_type values**:
- `["work"]` - Work items (tickets, issues, tasks)
- `["dev_user"]` - DevRev users
- `["account"]` - Customer accounts
- `["conversation"]` - Conversations
- `["part"]` - Parts/features/capabilities

## Aggregate Function Enums

When using aggregate functions, specify via `function.type`:

```json
{
  "reference_name": "total_revenue",
  "meerkat_schema": {
    "type": "number",
    "function": {
      "type": "MeerkatWidgetColumnFunction_TypeEnumSum"
    },
    "sql_expression": "revenue"
  }
}
```

**Available function types**:
- `MeerkatWidgetColumnFunction_TypeEnumCount` - COUNT
- `MeerkatWidgetColumnFunction_TypeEnumSum` - SUM
- `MeerkatWidgetColumnFunction_TypeEnumAvg` - AVG
- `MeerkatWidgetColumnFunction_TypeEnumMin` - MIN
- `MeerkatWidgetColumnFunction_TypeEnumMax` - MAX
- `MeerkatWidgetColumnFunction_TypeEnumMedian` - MEDIAN
- `MeerkatWidgetColumnFunction_TypeEnumP50` - 50th percentile
- `MeerkatWidgetColumnFunction_TypeEnumP90` - 90th percentile
- `MeerkatWidgetColumnFunction_TypeEnumP95` - 95th percentile
- `MeerkatWidgetColumnFunction_TypeEnumP99` - 99th percentile

## Unsupported Types

These types are not supported and will cause validation errors:
- `composite` - Complex nested objects
- `[]bool` - Boolean arrays
- `[]date` - Date arrays
- `[]timestamp` - Timestamp arrays

Use alternative representations if needed (e.g., JSON columns, separate tables).

## Complete Examples

### Dimension: Text Enum

```json
{
  "reference_name": "priority",
  "devrev_schema": {
    "name": "priority",
    "data_name": "priority",
    "field_type": "enum",
    "is_filterable": true,
    "ui": {
      "display_name": "Priority"
    }
  },
  "meerkat_schema": {
    "type": "string",
    "sql_expression": "priority"
  }
}
```

### Dimension: Timestamp

```json
{
  "reference_name": "created_date",
  "devrev_schema": {
    "name": "created_date",
    "data_name": "created_date",
    "field_type": "timestamp",
    "is_filterable": true,
    "ui": {
      "display_name": "Created Date"
    }
  },
  "meerkat_schema": {
    "type": "time",
    "sql_expression": "created_date"
  }
}
```

### Measure: Count

```json
{
  "reference_name": "ticket_count",
  "devrev_schema": {
    "name": "ticket_count",
    "data_name": "ticket_count",
    "field_type": "number",
    "is_filterable": false,
    "ui": {
      "display_name": "Ticket Count"
    }
  },
  "meerkat_schema": {
    "type": "number",
    "function": {
      "type": "MeerkatWidgetColumnFunction_TypeEnumCount"
    },
    "sql_expression": "id"
  }
}
```

### Measure: Sum

```json
{
  "reference_name": "total_revenue",
  "devrev_schema": {
    "name": "total_revenue",
    "data_name": "total_revenue",
    "field_type": "double",
    "is_filterable": false,
    "ui": {
      "display_name": "Total Revenue"
    }
  },
  "meerkat_schema": {
    "type": "number",
    "function": {
      "type": "MeerkatWidgetColumnFunction_TypeEnumSum"
    },
    "sql_expression": "revenue"
  }
}
```

### Measure: P90 Percentile

```json
{
  "reference_name": "p90_response_time",
  "devrev_schema": {
    "name": "p90_response_time",
    "data_name": "p90_response_time",
    "field_type": "double",
    "is_filterable": false,
    "ui": {
      "display_name": "P90 Response Time"
    }
  },
  "meerkat_schema": {
    "type": "number",
    "function": {
      "type": "MeerkatWidgetColumnFunction_TypeEnumP90"
    },
    "sql_expression": "response_time_ms"
  }
}
```
