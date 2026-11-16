# PaaS Job Examples

**Important:** Custom dataset names should NOT use `dim_` or `fact_` prefixes. Those are reserved for stock datasets. Use descriptive names like `department_analytics`, `ticket_metrics`, etc.

## Simple Aggregation Job

### Dataset Creation
```json
{
  "name": "department_analytics",
  "title": "Department Analytics",
  "description": "User distribution by department",
  "columns": [
    {"name": "department", "sql": {"type": "VARCHAR"}},
    {"name": "user_count", "sql": {"type": "BIGINT"}}
  ],
  "partition_columns": []
}
```

### Job Creation
```json
{
  "name": "department_analytics_job",
  "description": "Aggregates users by department",
  "queries": [
    {
      "sql": "SELECT JSON_EXTRACT_SCALAR(custom_fields, '$.tnt__department') AS department, COUNT(*) AS user_count FROM `dim_revu` WHERE is_deleted = FALSE AND JSON_EXTRACT_SCALAR(custom_fields, '$.tnt__department') IS NOT NULL GROUP BY 1 ORDER BY 2 DESC",
      "input_tables": ["dim_revu"],
      "transient_output_table": "dept_output"
    }
  ],
  "publishers": [
    {
      "type": "oasis",
      "oasis": {
        "sql": "SELECT * FROM @dept_output",
        "dataset_name": "department_analytics"
      }
    }
  ]
}
```

## Time-Partitioned Job

### Dataset Creation

**Important:** Partition columns must use `TIMESTAMP` type with `devrev_field_type: "timestamp"`.

```json
{
  "name": "daily_ticket_metrics",
  "title": "Daily Ticket Metrics",
  "columns": [
    {"name": "record_date", "sql": {"type": "TIMESTAMP"}},
    {"name": "status", "sql": {"type": "VARCHAR"}},
    {"name": "ticket_count", "sql": {"type": "BIGINT"}}
  ],
  "partition_columns": [
    {
      "name": "record_date",
      "sql": {"type": "TIMESTAMP"},
      "devrev_field_type": "timestamp",
      "timestamp_granularity": "month",
      "data_window_granularity": 3
    }
  ]
}
```

### Job Creation with Parameter
```json
{
  "name": "daily_ticket_job",
  "description": "Daily ticket counts by status",
  "queries": [
    {
      "sql": "SELECT DATE(@scheduled_at) AS record_date, status, COUNT(DISTINCT id) AS ticket_count FROM `dim_ticket` WHERE DATE(created_date) = DATE(@scheduled_at) AND is_deleted = FALSE GROUP BY 1, 2",
      "input_tables": ["dim_ticket"],
      "transient_output_table": "ticket_output"
    }
  ],
  "publishers": [
    {
      "type": "oasis",
      "oasis": {
        "sql": "SELECT * FROM @ticket_output",
        "dataset_name": "daily_ticket_metrics"
      }
    }
  ]
}
```

### Execution with Parameter

The job ID comes from the `job.id` field in the create response:

```json
{
  "id": "don:data:dvrv-us-1:devo/787:oasis_job/123",
  "parameters": {
    "scheduled_at": "2025-01-15"
  }
}
```

## Multi-Table JOIN Job

### Job with JOIN
```json
{
  "name": "account_ticket_summary",
  "description": "Ticket counts per account with names",
  "queries": [
    {
      "sql": "SELECT t.account_id, a.name AS account_name, COUNT(DISTINCT t.id) AS ticket_count FROM `dim_ticket` t LEFT JOIN `dim_account` a ON t.account_id = a.id WHERE t.is_deleted = FALSE GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 100",
      "input_tables": ["dim_ticket", "dim_account"],
      "transient_output_table": "account_summary"
    }
  ],
  "publishers": [
    {
      "type": "oasis",
      "oasis": {
        "sql": "SELECT * FROM @account_summary",
        "dataset_name": "account_ticket_summary"
      }
    }
  ]
}
```
