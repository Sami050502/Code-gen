# Ponos YAML Job Examples

**Important:** Custom dataset names should NOT use `dim_` or `fact_` prefixes. Those are reserved for stock datasets. Use descriptive names like `department_analytics`, `ticket_daily_summary`, etc.

**CRITICAL:** Always use three-part FROM clauses: `` `{{.source_project_name}}.{{.source_dataset_name}}.table_name` ``

## Summary Job (Standard Pattern)

The most common pattern. Uses a **dummy query** (`query: SELECT true`) with the real SQL in the publisher's `select_query`. Includes `query_args` for per-environment org identifiers.

```yaml
---
name: "ticket_daily_summary"
short_name: "TDS"
owners: ["analytics@devrev.ai"]
is_disabled: false
schedule_type: "periodic"
schedule_frequency_in_minutes: 60m
delay_time_in_minutes: 30m
tags: "summary"
environments:
  - "local"
  - "dev.dvrv-us-1"
  - "prod.dvrv-us-1"
env_configs:
  "local":
    config_values:
      source_project_name: "app-devrev-dev"
      source_dataset_name: "us_east1_devrev"
      destination_project_name: "app-devrev-dev"
      destination_dataset_name: "us_east1_summary_jobs_test"
      gcs_bucket_name: "devrev-ponos-test-bucket"

job_activities:
  - type: "query"
    queries:
      - query_id: "ticket_daily_summary"
        short_name: "TDS"
        description: "Daily ticket summary"
        query: SELECT true
        query_args:
          "local":
            devo_display_id: "DEV-787"
          "dev":
            devo_display_id: "DEV-787"
          "prod":
            devo_display_id: "DEV-XXXXX"

  - type: "publisher"
    publishers:
      - type: "camel"
        query_id: "ticket_daily_summary"
        camel_publisher_activity:
          dataset_config:
            name: "ticket_daily_summary"
            title: "Daily Ticket Summary"
            description: "Daily ticket counts and metrics"
            create_oasis_dataset: true
            timestamp_column_name: "record_date"
            owner_display_id: "{{.devo_display_id}}"
          exporter_type: "gcs_query"
          exporter_gcs_query:
            destination_file_format: "PARQUET"
            select_query: |
              SELECT
                dev_oid,
                DATE({{.agg_start_date}}) AS record_date,
                status,
                COUNT(DISTINCT id) AS ticket_count,
                COUNT(DISTINCT account_id) AS account_count
              FROM `{{.source_project_name}}.{{.source_dataset_name}}.fact_ticket`
              WHERE dev_oid = '{{.devo_display_id}}'
                AND TIMESTAMP_TRUNC(modified_date, DAY) >= TIMESTAMP_TRUNC({{.agg_start_date}}, DAY)
                AND TIMESTAMP_TRUNC(modified_date, DAY) < TIMESTAMP_TRUNC({{.agg_end_date}}, DAY)
              GROUP BY 1, 2, 3
```

**Key patterns:**
- `query: SELECT true` -- Dummy query, all real SQL goes in publisher's `select_query`
- **`query_args` is REQUIRED** -- Must have entries for ALL environments (local, dev, prod). Provides per-environment org identifiers. Without this, `owner_display_id` and dev_oid filters will fail in non-local environments
- `owner_display_id: "{{.devo_display_id}}"` -- References the query_args variable
- `select_query` contains the actual data transformation SQL
- No `table_creation_config` (only needed in rare cases)
- No `destination_table_name` (not needed with dummy query pattern)

## Multi-Table JOIN Job

Joins fact_* tables with dim_* tables for enrichment. Same dummy query pattern.

```yaml
---
name: "account_ticket_metrics"
short_name: "ATM"
owners: ["analytics@devrev.ai"]
is_disabled: false
schedule_type: "periodic"
schedule_frequency_in_minutes: 60m
delay_time_in_minutes: 30m
tags: "summary"
end_at: 2030-12-31
environments:
  - "local"
  - "dev.dvrv-us-1"
  - "prod.dvrv-us-1"
env_configs:
  "local":
    config_values:
      source_project_name: "app-devrev-dev"
      source_dataset_name: "us_east1_devrev"
      destination_project_name: "app-devrev-dev"
      destination_dataset_name: "us_east1_summary_jobs_test"
      gcs_bucket_name: "devrev-ponos-test-bucket"

job_activities:
  - type: "query"
    queries:
      - query_id: "account_ticket_metrics"
        short_name: "ATM"
        description: "Account-level ticket metrics"
        query: SELECT true
        query_args:
          "local":
            devo_display_id: "DEV-787"
          "dev":
            devo_display_id: "DEV-787"
          "prod":
            devo_display_id: "DEV-XXXXX"

  - type: "publisher"
    publishers:
      - type: "camel"
        query_id: "account_ticket_metrics"
        camel_publisher_activity:
          dataset_config:
            name: "account_ticket_metrics"
            title: "Account Ticket Metrics"
            description: "Ticket counts per account"
            create_oasis_dataset: true
            timestamp_column_name: "record_date"
            owner_display_id: "{{.devo_display_id}}"
          exporter_type: "gcs_query"
          exporter_gcs_query:
            destination_file_format: "PARQUET"
            select_query: |
              SELECT
                t.dev_oid,
                DATE({{.agg_start_date}}) AS record_date,
                t.account_id,
                a.name AS account_name,
                COUNT(DISTINCT t.id) AS ticket_count,
                COUNTIF(t.status = 'open') AS open_tickets,
                COUNTIF(t.status = 'closed') AS closed_tickets
              FROM `{{.source_project_name}}.{{.source_dataset_name}}.fact_ticket` t
              LEFT JOIN `{{.source_project_name}}.{{.source_dataset_name}}.dim_account` a
                ON t.account_id = a.id AND t.dev_oid = a.dev_oid
              WHERE t.dev_oid = '{{.devo_display_id}}'
                AND TIMESTAMP_TRUNC(t.modified_date, DAY) >= TIMESTAMP_TRUNC({{.agg_start_date}}, DAY)
                AND TIMESTAMP_TRUNC(t.modified_date, DAY) < TIMESTAMP_TRUNC({{.agg_end_date}}, DAY)
              GROUP BY 1, 2, 3, 4
```

## Multi-Step DELETE + INSERT Job

When re-computing a full time window, DELETE first, then INSERT fresh data. This pattern uses real SQL in the `query:` field (not dummy queries) because it needs to write to a destination BQ table.

```yaml
---
name: "weekly_api_calls_summary"
short_name: "WACS"
owners: ["analytics@devrev.ai"]
is_disabled: false
schedule_type: "periodic"
schedule_frequency_in_minutes: 1440m
delay_time_in_minutes: 30m
tags: "summary"
end_at: 2030-12-31
environments:
  - "local"
  - "dev.dvrv-us-1"
  - "prod.dvrv-us-1"
env_configs:
  "local":
    config_values:
      source_project_name: "app-devrev-dev"
      source_dataset_name: "us_east1_devrev"
      destination_project_name: "app-devrev-dev"
      destination_dataset_name: "us_east1_summary_jobs_test"
      gcs_bucket_name: "devrev-ponos-test-bucket"

job_activities:
  # Step 1: Delete previous data for this date range
  - type: "query"
    queries:
      - query_id: "api_calls_delete"
        short_name: "D_WACS"
        query: |
          DELETE FROM `{{.destination_project_name}}.{{.destination_dataset_name}}.weekly_api_calls_summary`
          WHERE DATE(record_date) = DATE({{.agg_start_date}})

  # Step 2: Insert fresh aggregated data
  - type: "query"
    queries:
      - query_id: "api_calls_insert"
        short_name: "WACS"
        destination_table_name: "weekly_api_calls_summary"
        table_creation_config:
          description: "Weekly API call counts by endpoint"
          partition_key: "record_date"
          time_partition_type: "day"
          cluster_keys:
            - "dev_oid"
        query: |
          SELECT
            dev_oid,
            DATE({{.agg_start_date}}) AS record_date,
            endpoint,
            COUNT(*) AS call_count
          FROM `{{.source_project_name}}.{{.source_dataset_name}}.fact_events`
          WHERE TIMESTAMP_TRUNC(created_date, DAY) >= TIMESTAMP_TRUNC({{.agg_start_date}}, DAY)
            AND TIMESTAMP_TRUNC(created_date, DAY) < TIMESTAMP_TRUNC({{.agg_end_date}}, DAY)
          GROUP BY 1, 2, 3

  # Step 3: Publish to Oasis
  - type: "publisher"
    publishers:
      - type: "camel"
        query_id: "api_calls_insert"
        camel_publisher_activity:
          dataset_config:
            name: "weekly_api_calls_summary"
            title: "Weekly API Calls Summary"
            description: "Weekly API call counts by endpoint"
            create_oasis_dataset: true
            timestamp_column_name: "record_date"
            owner_display_id: "{{.devo_display_id}}"
          exporter_type: "gcs_query"
          exporter_gcs_query:
            destination_file_format: "PARQUET"
            select_query: |
              SELECT
                dev_oid,
                record_date,
                endpoint,
                call_count
              FROM `{{.destination_project_name}}.{{.destination_dataset_name}}.weekly_api_calls_summary`
              WHERE DATE(record_date) = DATE({{.agg_start_date}})
```

**Note:** The DELETE + INSERT pattern is the one case where `destination_table_name` and `table_creation_config` are needed, because data must be written to a BQ intermediate table before publishing.

## Metrics Job (Tapio Publisher)

Metrics jobs publish to Tapio instead of Oasis. They use `tags: "metrics"` and `use_gcs_destination: true`.

```yaml
---
name: "er_to_mr_product_devrev_num_of_tickets"
short_name: "PRODUCT_DEVREV_ER_2_MR_NUM_OF_TICKETS"
owners: ["analytics@devrev.ai"]
is_disabled: false
schedule_type: "periodic"
schedule_frequency_in_minutes: 1440m
delay_time_in_minutes: 0m
tags: "metrics"
environments:
  - "local"
  - "dev.dvrv-us-1"
  - "prod.dvrv-us-1"
env_configs:
  "local":
    config_values:
      source_project_name: "app-devrev-dev"
      source_dataset_name: "us_east1_devrev"
      destination_project_name: "app-devrev-dev"
      destination_dataset_name: "us_east1_summary_jobs_test"
      gcs_bucket_name: "devrev-ponos-test-bucket"
      aws_s3_bucket_name: "serengeti-dev"

job_activities:
  - type: "query"
    queries:
      - query_id: "num_of_tickets"
        short_name: "NUM_OF_TICKETS"
        use_gcs_destination: true
        query: |
          WITH ticket_counts AS (
            SELECT
              dev_oid,
              COUNT(DISTINCT id) AS ticket_count
            FROM `{{.source_project_name}}.{{.source_dataset_name}}.fact_ticket`
            WHERE DATE(created_date) = DATE({{.agg_end_date}}) - 1
              AND is_deleted = FALSE
            GROUP BY 1
          )
          SELECT
            "{{.devo_don}}" AS dev_oid,
            b.id AS org_ref,
            "" AS user_ref,
            "devrev_product_num_of_tickets" AS metric_name,
            {{.agg_end_date}} AS metric_timestamp,
            CAST(a.ticket_count AS float64) AS metric_value,
            ARRAY<STRUCT<name string, value string>>[] AS metric_dimensions
          FROM ticket_counts AS a
          INNER JOIN (
            SELECT external_oid, id
            FROM `{{.source_project_name}}.{{.source_dataset_name}}.dim_revo`
            WHERE dev_oid = "{{.devo_display_id}}" AND is_deleted = FALSE
          ) AS b
          ON b.external_oid = a.dev_oid

  - type: "publisher"
    publishers:
      - type: "tapio"
        query_id: "num_of_tickets"
        tapio_publisher_activity:
          child_batch_size: 50000
```
