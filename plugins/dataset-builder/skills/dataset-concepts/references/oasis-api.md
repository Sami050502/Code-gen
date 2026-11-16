# Oasis API Reference

## Dataset APIs

### oasis.dataset.create

Create a new dataset.

**Required fields:**
- `name` - Dataset identifier (lowercase, underscores)
- `title` - Human-readable title (required!)
- `columns` - Array of column definitions

**Request:**
```json
POST /internal/oasis.dataset.create

{
  "name": "department_analytics",
  "title": "Department Analytics",
  "description": "Rev user distribution by department",
  "columns": [
    {
      "name": "department",
      "sql": { "type": "VARCHAR" }
    },
    {
      "name": "user_count",
      "sql": { "type": "BIGINT" }
    }
  ],
  "partition_columns": []
}
```

**For time-partitioned datasets:**

Note: Partition columns MUST include:
- `"sql": {"type": "TIMESTAMP"}` (not DATE)
- `"devrev_field_type": "timestamp"` (required!)

```json
{
  "name": "daily_ticket_counts",
  "title": "Daily Ticket Counts",
  "columns": [
    { "name": "total_tickets", "sql": { "type": "BIGINT" } },
    { "name": "created_date", "sql": { "type": "TIMESTAMP" } }
  ],
  "partition_columns": [
    {
      "name": "created_date",
      "sql": { "type": "TIMESTAMP" },
      "devrev_field_type": "timestamp",
      "timestamp_granularity": "month",
      "data_window_granularity": 3
    }
  ]
}
```

### oasis.dataset.get

Get dataset metadata.

**Request:**
```
GET /internal/oasis.dataset.get?name=fact_capability
```

**Response:**
```json
{
  "dataset": {
    "id": "don:data:dvrv-us-1:devo/787:dataset/25",
    "dataset_name": "fact_capability",
    "title": "Fact Capabilities",
    "description": "Table holding capability fact events",
    "columns": [
      { "name": "id", "type": "VARCHAR" },
      { "name": "name", "type": "VARCHAR" }
    ],
    "partition_columns": [
      {
        "name": "customer_oid",
        "type": "VARCHAR",
        "devrev_field_type": "rev_org"
      },
      {
        "name": "modified_date",
        "type": "TIMESTAMP",
        "devrev_field_type": "timestamp",
        "timestamp_granularity": "month"
      }
    ],
    "created_date": "2023-06-22T02:07:03.224Z",
    "modified_date": "2023-06-22T02:07:03.224Z"
  }
}
```

### oasis.dataset.list

List all datasets.

**Request:**
```
GET /internal/oasis.dataset.list
```

## Data APIs

### oasis.data.fetch

Fetch data entries for a dataset.

**Request:**
```json
POST /internal/oasis.data.fetch

{
  "dataset_name": "fact_capability",
  "date_range": {
    "after": "2023-05-01T00:00:00Z",
    "before": "2023-06-01T00:00:00Z"
  }
}
```

**Response:**
```json
{
  "data": [
    {
      "id": "don:data:dvrv-us-1:devo/787:oasis_data/19",
      "partition": {
        "partition_by": ["customer_oid", "modified_date"],
        "partition_values": ["all", "2023-06-01"]
      },
      "sources": [
        {
          "uri": "https://serengeti.dev.devrev-eng.ai?token=..."
        }
      ]
    }
  ],
  "dataset": { ... }
}
```

### oasis.data.put

Ingest, update, or delete source files.

**Request:**
```json
POST /internal/oasis.data.put

{
  "dataset_name": "my_dataset",
  "partition_values": {
    "dev_oid": "DEV-787",
    "created_date": "2025-01-01"
  },
  "sources": [
    {
      "uri": "s3://bucket/path/data.parquet",
      "start_time": "2025-01-01T00:00:00Z",
      "end_time": "2025-01-02T00:00:00Z"
    }
  ]
}
```

## Using the API Client

The plugin provides a Python script for making API calls:

```bash
# List datasets
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py oasis.dataset.list

# Get specific dataset
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py oasis.dataset.get --name fact_ticket

# Create dataset from JSON file
python ${CLAUDE_PLUGIN_ROOT}/scripts/devrev_api.py oasis.dataset.create --data-file schema.json
```
