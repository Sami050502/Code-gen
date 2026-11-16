# Manifest Schema Reference

Complete reference for defining 3P operations in manifest.yaml. Validate with `scripts/validate-manifest.sh`.

## CRITICAL: Field Type Rules

**Supported:** `id`, `text`, `array`, `bool`, `int`

- **`id`** - MUST include `id_type` array with valid entity types
- **`text`** - For strings, JSON, dates, rich text
- **`array`** - Requires `base_type`: `text`, `enum`, or `composite`
- **`bool`** - Boolean values
- **`int`** - Numeric values

**NEVER use:** `enum` (use `array` + `base_type: enum`), `rich_text`, `object` (use `composite`), `date`, `datetime`
---
## Operation Structure

```yaml
operations:
  - name: operation_identifier      # Required: snake_case
    display_name: Display Name       # Required
    description: Description         # Required
    slug: operation_identifier       # Required: usually same as name
    function: operation_handler      # Required: usually operation_handler
    type: action                     # Required: always 'action'
    inputs:                          # Required
      fields: []                     # Array of input fields
      composites: []                # Optional: composite type definitions
    outputs:                         # Required
      fields: []                     # Array of output fields
```

---

## Field Schema

### Input/Output Field

```yaml
fields:
  - name: field_name                 # Required: snake_case
    field_type: text|id|array|bool|int  # Required
    description: Description         # Required
    is_required: false               # Optional: default false
    ui:                              # Optional
      display_name: Display Name     # User-facing name
    
    # Additional properties by type:
    id_type: [ticket, issue]         # Required for id fields
    base_type: text|enum|composite   # Required for array fields
    allowed_values: [...]             # Required for enum arrays
    composite_type: type_name        # Required for composite arrays
```

---

## Field Type Examples

### ID Field

```yaml
- name: work_id
  field_type: id
  id_type: [ticket, issue]  # Required
  description: Work item ID
  is_required: true
  ui:
    display_name: Work ID
```

**Valid id_type:** `ticket`, `issue`, `contact`, `devu`, `revu`, `group`, `opportunity`, `product`, `capability`, `feature`, `enhancement`, `account`, `rev_org`, `service_account`, `article`

### Text, Bool, Int Fields

```yaml
- name: message
  field_type: text
  description: Text message
  is_required: true
  ui:
    display_name: Message

- name: is_active
  field_type: bool
  description: Active status
  is_required: false
  default_value: true
  ui:
    display_name: Is Active

- name: count
  field_type: int
  description: Number of items
  is_required: false
  default_value: 0
  ui:
    display_name: Count
```

### Array Field

**Required:** `base_type` (text, enum, or composite)

#### Simple Array (`base_type: text`)

```yaml
- name: tags
  field_type: array
  base_type: text
  description: List of tags
  is_required: false
  default_value: []
  ui:
    display_name: Tags
```

#### Enum Array (`base_type: enum`)

**Required:** `allowed_values` array (provides validation)

```yaml
- name: priorities
  field_type: array
  base_type: enum
  allowed_values: [low, medium, high, critical]
  description: Priority levels
  is_required: true
  default_value: [medium]
  ui:
    display_name: Priorities
```

#### Composite Array (`base_type: composite`)

**Required:** Define composite type first, then reference it

```yaml
inputs:
  fields:
    - name: data_items
      field_type: array
      base_type: composite
      composite_type: data_item  # Must match composite name
      description: List of data items
      is_required: true
      ui:
        display_name: Data Items
  composites:
    - name: data_item
      description: Data item structure
      fields:
        - name: key
          field_type: text
          description: Item key
          is_required: true
          ui:
            display_name: Key
        - name: value
          field_type: text
          description: Item value
          is_required: true
          ui:
            display_name: Value
```

**Note:** No `object` type. Use `array` with `composite` base_type for structured data.

---

## Complete Example

```yaml
version: "2"
name: "Example Snap-in"
description: "Example with composite types"

service_account:
  display_name: Example Service

functions:
  - name: operation_handler
    description: Function to handle operations

operations:
  - name: process_data
    display_name: Process Data
    description: Processes input data and returns transformed result
    slug: process_data
    function: operation_handler
    type: action
    inputs:
      fields:
        - name: data_items
          field_type: array
          base_type: composite
          composite_type: data_item
          description: List of data items to process
          is_required: true
          ui:
            display_name: Data Items
        - name: transform_type
          field_type: text
          description: Type of transformation to apply
          is_required: true
          ui:
            display_name: Transform Type
      composites:
        - name: data_item
          description: Data item structure
          fields:
            - name: key
              field_type: text
              description: Item key
              is_required: true
              ui:
                display_name: Key
            - name: value
              field_type: text
              description: Item value
              is_required: true
              ui:
                display_name: Value
    outputs:
      fields:
        - name: result
          field_type: text
          description: Transformed data (JSON)
          is_required: true
          ui:
            display_name: Result
        - name: metadata
          field_type: text
          description: Processing metadata (JSON)
          is_required: true
          ui:
            display_name: Metadata
```

---

## Keyrings (external credentials)

For operations that call external APIs, declare required secrets in the operation’s `keyrings` block. Do not put API keys or tokens in `inputs`. At runtime, access them via `context.secrets.<keyring_name>` (e.g. `context.secrets.external_api_key`). Configure the actual secret values in the snap-in’s keyring in DevRev.

**Sample: operation using a keyring**

```yaml
operations:
  - name: call_external_api
    display_name: Call External API
    description: Invoke an external service. Check the documentation for usage and limitations.
    slug: call_external_api
    function: operation_handler
    type: action
    keyrings:
      - name: external_api_key
        description: API key for the external service
        types:
          - api_key
        display_name: External API Key
    inputs:
      fields:
        - name: endpoint
          field_type: text
          description: API endpoint or resource path
          is_required: true
          ui:
            display_name: Endpoint
        - name: payload
          field_type: text
          description: Request payload (e.g. JSON)
          is_required: false
          ui:
            display_name: Payload
    outputs:
      fields:
        - name: result
          field_type: text
          description: Response from the external service
          is_required: true
          ui:
            display_name: Result
```

In the operation handler, use `context.secrets.external_api_key`; never read the API key from input fields.

---

## Quick Reference

| Field Type | Required Properties | Notes |
|------------|---------------------|-------|
| `id` | `id_type: [...]` | Array of allowed entity types |
| `text` | None | Use for strings, JSON, dates |
| `array` | `base_type: text\|enum\|composite` | For lists |
| `array` (enum) | `base_type: enum`, `allowed_values: [...]` | Validated enum list |
| `array` (composite) | `base_type: composite`, `composite_type: name` | Requires composite definition |
| `bool` | None | Boolean values |
| `int` | None | Numeric values |

**All fields require:** `name`, `field_type`, `description`, `is_required`, `ui.display_name`

---

## Field Type Rules

### Enum Values

**Rule:** Never use `field_type: enum`. Use `field_type: array` with `base_type: enum` instead.

```yaml
- name: priorities
  field_type: array
  base_type: enum
  allowed_values: [low, medium, high]
  default_value: [medium]
```

### Rich Text and Objects

**Rule:** Never use `field_type: rich_text` or `field_type: object`. Use `field_type: text` for rich text and JSON strings.

```yaml
- name: description
  field_type: text
  description: Rich text description
```

For structured objects, use `field_type: array` with `base_type: composite`.

### Dates

**Rule:** Never use `field_type: date` or `field_type: datetime`. Use `field_type: text` with ISO 8601 format.

```yaml
- name: due_date
  field_type: text
  description: Due date in ISO 8601 format (YYYY-MM-DD)
```

### ID Fields

**Rule:** All `field_type: id` fields MUST include `id_type` array with at least one entity type.

```yaml
- name: work_id
  field_type: id
  id_type: [ticket, issue]  # Required
```

---
## TypeScript Type Mapping

```typescript
interface OperationInput {
  // field_type: text
  title: string;
  metadata: string;  // JSON as string
  due_date: string;  // ISO date string

  // field_type: id
  work_id: string;

  // field_type: array with base_type: text
  tags: string[];

  // field_type: array with base_type: enum
  priorities: string[];

  // field_type: array with base_type: composite
  custom_fields: Array<{ key: string; value: string }>;

  // field_type: bool
  is_active: boolean;

  // field_type: int
  count: number;
}

// Access in handler
const input_data = input.data as OperationInput;
```

---
## Validation Rules

1. **All fields MUST have:** `name`, `field_type`, `description`, `is_required`, `ui.display_name`

2. **ID fields MUST have:** `id_type` array with at least one entity type

3. **Array fields MUST have:**
   - `base_type` (text, enum, or composite)
   - `allowed_values` (if `base_type: enum`)
   - `composite_type` (if `base_type: composite`)

4. **Enum arrays MUST have:** `allowed_values` with at least 2 values; `default_value` must be from `allowed_values`

5. **Composite arrays MUST have:** Corresponding `composite_types` definition matching `composite_type` name

---

## Common Mistakes

**Missing `id_type`:**
```yaml
# Wrong
- name: entity_id
  field_type: id

# Correct
- name: entity_id
  field_type: id
  id_type: [ticket, issue]
```

**Using unsupported types:**
```yaml
# Wrong
- name: status
  field_type: enum

# Correct
- name: status
  field_type: array
  base_type: enum
  allowed_values: [open, closed]
```

**Validation:** Run `./scripts/validate-manifest.sh` to catch these errors automatically.
