---
name: explore
description: Discover available datasets for custom dataset creation. Lists fact_* tables (primary sources) and dim_* tables (for JOINs).
argument-hint: "[sources|oasis|bigquery|schema <table>|recommend <use_case>]"
allowed-tools:
  - Bash
  - Read
  - AskUserQuestion
---

# Explore Command

Discover available stock datasets and their schemas to help plan custom dataset creation.

**Key concept:**
- **fact_* tables**: Primary sources for custom datasets (time-partitioned, historical data)
- **dim_* tables**: For JOIN enrichment only (already directly usable in Oasis)

## Subcommands

### sources (default)

List known stock datasets with descriptions:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/dataset_discovery.py sources
```

Shows fact_* tables as primary aggregation sources and dim_* tables for JOIN enrichment.

### oasis

List datasets registered in Oasis (requires PAT in .env):

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/dataset_discovery.py oasis
```

Shows all datasets from Oasis API, categorized by type.

### bigquery

List all tables in BigQuery us_east1_devrev dataset:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/dataset_discovery.py bigquery
```

Requires `bq` CLI and gcloud authentication.

### schema <table_name>

Get detailed schema for a specific table:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/dataset_discovery.py schema <table_name>
```

Shows all columns, types, and identifies potential partition columns.

**Example:**
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/dataset_discovery.py schema fact_ticket
```

### recommend <use_case>

Get dataset recommendations for a specific use case:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/dataset_discovery.py recommend "ticket resolution times by account"
```

Returns:
- Recommended primary source (fact_* table)
- Suggested JOIN tables (dim_* for enrichment)
- Reasoning based on use case keywords

## Workflow

### Step 1: Parse Argument

Determine which subcommand to run:
- No argument or "sources" → Show known stock datasets
- "oasis" → Query Oasis API
- "bigquery" → Query BigQuery tables
- "schema <name>" → Show table schema
- "recommend <text>" → Get recommendations

### Step 2: Execute Discovery

Run the appropriate command. If API/BigQuery fails, fall back to hardcoded list.

### Step 3: Display Results

Format output with clear categorization:
- **Fact tables** with partition columns
- **Dim tables** with JOIN use cases
- **Custom datasets** (if any)

### Step 4: Provide Guidance

After showing results:

**For sources/oasis/bigquery:**
- Emphasize fact_* tables as primary aggregation sources
- Note that dim_* tables are already in Oasis (no custom dataset needed)
- Suggest running `schema` for detailed column info

**For schema:**
- Highlight partition column (required for efficient queries)
- Show common aggregation patterns
- Suggest query structure

**For recommend:**
- Explain why the recommendation was made
- Show suggested JOINs
- Provide next steps

## Interactive Follow-up

After displaying results, offer relevant next steps:

**After sources/oasis/bigquery:**
- "Would you like to see the schema for a specific table?"
- "What analytics question are you trying to answer?"

**After schema:**
- "Would you like me to help design a query using this table?"
- "Ready to create a custom dataset from this source?"

**After recommend:**
- "Would you like to explore the schema of the recommended table?"
- "Ready to proceed with creating this dataset?"

## Example Output

### sources

```
=== Fact Tables (Primary Sources for Custom Datasets) ===

  fact_ticket
    Ticket events over time - SLA, stage transitions, updates
    Partition: created_date

  fact_events
    General platform events - user actions, system events
    Partition: timestamp

=== Dimension Tables (For JOIN Enrichment Only) ===

Note: dim_* tables are directly usable in Oasis - no need to create custom datasets.

  dim_ticket
    Current ticket state - support tickets
    Use for: JOIN to get ticket details, current status

  dim_account
    Customer accounts
    Use for: JOIN to get account names and attributes
```

### recommend

```
=== Dataset Recommendations ===

Primary Source: fact_ticket
Reasoning: Based on keywords in your use case, fact_ticket is recommended. Ticket events over time - SLA, stage transitions, updates

Suggested JOINs:
  - dim_account: JOIN to get account names and attributes

--- Next Steps ---
1. Run: /dataset-builder:explore schema fact_ticket
2. Design your aggregation query
3. Run: /dataset-builder:create to generate the job
```
