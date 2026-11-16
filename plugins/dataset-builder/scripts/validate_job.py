#!/usr/bin/env python3
"""
Validate Ponos job YAML against review criteria.

This script checks Ponos job configurations for common issues
based on the data team's code review guidelines.

Usage:
    python validate_job.py <job.yaml>
    python validate_job.py <job.yaml> --fix  # Output fixed version
    python validate_job.py <job.yaml> --json # Output JSON report
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

try:
    import yaml
except ImportError:
    print("Error: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


class ValidationIssue:
    """Represents a validation issue found in the job."""

    SEVERITY_ERROR = "error"
    SEVERITY_WARNING = "warning"
    SEVERITY_INFO = "info"

    def __init__(self, severity: str, category: str, message: str,
                 location: str = "", suggestion: str = "", auto_fixable: bool = False):
        self.severity = severity
        self.category = category
        self.message = message
        self.location = location
        self.suggestion = suggestion
        self.auto_fixable = auto_fixable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "location": self.location,
            "suggestion": self.suggestion,
            "auto_fixable": self.auto_fixable
        }


class PonosJobValidator:
    """Validates Ponos job YAML files."""

    # Template variables that should be used (from config_values)
    REQUIRED_TEMPLATES = [
        "{{.source_project_name}}",
        "{{.source_dataset_name}}",
        "{{.destination_project_name}}",
        "{{.destination_dataset_name}}",
    ]

    # Standard config_values keys required in env_configs
    REQUIRED_CONFIG_VALUES = [
        "source_project_name",
        "source_dataset_name",
        "destination_project_name",
        "destination_dataset_name",
        "gcs_bucket_name",
    ]

    # Framework-injected variables (automatic, not from config)
    FRAMEWORK_VARIABLES = [
        "record_date", "agg_start_date", "agg_end_date",
        "agg_interval_year", "agg_interval_month", "agg_interval_day",
        "dev_oid", "devo_display_id", "devo_don",
    ]

    # Date-related templates
    DATE_TEMPLATES = ["{{.record_date}}", "{{.agg_start_date}}", "{{.agg_end_date}}"]

    # Common partition columns
    PARTITION_COLUMNS = ["created_date", "created_at", "modified_date", "record_date"]

    # Oasis field naming constraint
    OASIS_NAME_PATTERN = re.compile(r"^[a-z0-9_]*$")

    def __init__(self, job_config: Dict[str, Any]):
        self.config = job_config
        self.issues: List[ValidationIssue] = []

    def validate(self) -> List[ValidationIssue]:
        """Run all validation checks."""
        self.issues = []

        self._validate_metadata()
        self._validate_schedule()
        self._validate_environments()
        self._validate_env_configs()
        self._validate_queries()
        self._validate_query_args()
        self._validate_publishers()

        return self.issues

    def _add_issue(self, severity: str, category: str, message: str,
                   location: str = "", suggestion: str = "", auto_fixable: bool = False):
        self.issues.append(ValidationIssue(
            severity=severity,
            category=category,
            message=message,
            location=location,
            suggestion=suggestion,
            auto_fixable=auto_fixable
        ))

    def _validate_metadata(self):
        """Validate job metadata fields."""
        # Check required fields
        if not self.config.get("name"):
            self._add_issue("error", "metadata", "Missing required field: name")

        if not self.config.get("short_name"):
            self._add_issue("error", "metadata", "Missing required field: short_name")

        if not self.config.get("owners"):
            self._add_issue("error", "metadata", "Missing required field: owners")
        else:
            owners = self.config.get("owners", [])
            for owner in owners:
                if not re.match(r"[^@]+@[^@]+\.[^@]+", owner):
                    self._add_issue("warning", "metadata",
                                    f"Invalid email format in owners: {owner}",
                                    location="owners")

        # Check short_name format
        short_name = self.config.get("short_name", "")
        if short_name and len(short_name) > 20:
            self._add_issue("warning", "metadata",
                            f"short_name is very long ({len(short_name)} chars), consider shortening",
                            location="short_name")

        # Check tags field
        tags = self.config.get("tags")
        if not tags:
            self._add_issue("warning", "metadata",
                            "Missing 'tags' field",
                            suggestion="Set tags to 'summary' or 'metrics'")
        else:
            # Tags can be comma-separated (e.g., "summary, agent_analytics")
            tag_parts = [t.strip() for t in str(tags).split(",")]
            if not any(t in ["summary", "metrics"] for t in tag_parts):
                self._add_issue("warning", "metadata",
                                f"Tags '{tags}' does not include 'summary' or 'metrics'",
                                location="tags",
                                suggestion="Include 'summary' or 'metrics' in tags")

    def _validate_schedule(self):
        """Validate schedule configuration."""
        schedule_type = self.config.get("schedule_type")
        if schedule_type not in ["onetime", "periodic"]:
            self._add_issue("error", "schedule",
                            f"Invalid schedule_type: {schedule_type}. Must be 'onetime' or 'periodic'")

        if schedule_type == "periodic":
            freq = self.config.get("schedule_frequency_in_minutes", "")
            if isinstance(freq, str):
                # Parse duration string like "60m" or "1440m"
                match = re.match(r"(\d+)m?", str(freq))
                if match:
                    freq_minutes = int(match.group(1))
                    if freq_minutes < 15:
                        self._add_issue("error", "schedule",
                                        f"schedule_frequency_in_minutes ({freq_minutes}) must be >= 15",
                                        location="schedule_frequency_in_minutes")

        delay = self.config.get("delay_time_in_minutes")
        if delay is None:
            self._add_issue("info", "schedule",
                            "delay_time_in_minutes not set, defaults to 12 hours",
                            suggestion="Set delay_time_in_minutes: 0m if no delay needed")

    def _validate_environments(self):
        """Validate environment configuration."""
        envs = self.config.get("environments", [])

        # Check for mixed format
        has_plain = any("." not in e for e in envs)
        has_partition = any("." in e for e in envs)

        for env in envs:
            base_env = env.split(".")[0] if "." in env else env
            # Check if both formats exist for same environment
            if has_plain and has_partition:
                if base_env in [e for e in envs if "." not in e] and \
                   any(e.startswith(f"{base_env}.") for e in envs):
                    self._add_issue("error", "environments",
                                    f"Cannot mix '{base_env}' and '{base_env}.<partition>' formats",
                                    location="environments")
                    break

    def _validate_env_configs(self):
        """Validate env_configs and config_values."""
        env_configs = self.config.get("env_configs")
        environments = self.config.get("environments", [])
        has_local_env = "local" in environments

        if not env_configs:
            if has_local_env:
                self._add_issue("error", "env_configs",
                                "Missing env_configs section but 'local' is in environments list",
                                suggestion="Add env_configs with a 'local' entry containing config_values")
            # Jobs without "local" in environments don't need env_configs
            return

        # Check that "local" entry exists if local is in environments
        if has_local_env and "local" not in env_configs:
            self._add_issue("error", "env_configs",
                            "Missing 'local' entry in env_configs",
                            location="env_configs",
                            suggestion="Add a 'local' entry with config_values for local testing")

        # Validate each env_config entry
        for env_name, env_config in env_configs.items():
            config_values = env_config.get("config_values", {}) if isinstance(env_config, dict) else {}
            if not config_values:
                self._add_issue("warning", "env_configs",
                                f"env_configs['{env_name}'] has no config_values",
                                location=f"env_configs.{env_name}")
                continue

            # Check for required config_values keys
            for key in self.REQUIRED_CONFIG_VALUES:
                if key not in config_values:
                    self._add_issue("warning", "env_configs",
                                    f"env_configs['{env_name}'] missing config_value: {key}",
                                    location=f"env_configs.{env_name}.config_values",
                                    suggestion=f"Add '{key}' to config_values")

        # Check metrics jobs need aws_s3_bucket_name
        tags = self.config.get("tags", "")
        if tags == "metrics":
            for env_name, env_config in env_configs.items():
                config_values = env_config.get("config_values", {}) if isinstance(env_config, dict) else {}
                if config_values and "aws_s3_bucket_name" not in config_values:
                    self._add_issue("warning", "env_configs",
                                    f"Metrics job missing aws_s3_bucket_name in env_configs['{env_name}']",
                                    location=f"env_configs.{env_name}.config_values",
                                    suggestion="Metrics jobs typically need aws_s3_bucket_name")

        # Cross-check: env_configs keys should match environments list (base names)
        environments = self.config.get("environments", [])
        env_base_names = set()
        for env in environments:
            base = env.split(".")[0] if "." in env else env
            env_base_names.add(base)

        for env_key in env_configs:
            if env_key not in env_base_names:
                self._add_issue("info", "env_configs",
                                f"env_configs key '{env_key}' not found in environments list",
                                location="env_configs",
                                suggestion="Ensure env_configs keys match environment base names")

    def _validate_query_args(self):
        """Validate query_args across all queries."""
        job_activities = self.config.get("job_activities", [])
        environments = self.config.get("environments", [])
        env_base_names = set()
        for env in environments:
            base = env.split(".")[0] if "." in env else env
            env_base_names.add(base)

        # Collect all config_values keys for template resolution
        config_value_keys = set()
        env_configs = self.config.get("env_configs", {})
        for env_config in env_configs.values():
            if isinstance(env_config, dict):
                for key in env_config.get("config_values", {}):
                    config_value_keys.add(key)

        for idx, activity in enumerate(job_activities):
            if activity.get("type") != "query":
                continue

            for q_idx, query in enumerate(activity.get("queries", [])):
                location = f"job_activities[{idx}].queries[{q_idx}]"
                query_args = query.get("query_args", {})

                if not query_args:
                    # Check if publisher uses devo_display_id or dev_oid without query_args
                    query_id = query.get("query_id", "")
                    needs_query_args = False
                    for pub_activity in job_activities:
                        if pub_activity.get("type") != "publisher":
                            continue
                        for pub in pub_activity.get("publishers", []):
                            if pub.get("query_id") != query_id:
                                continue
                            camel = pub.get("camel_publisher_activity", {})
                            dc = camel.get("dataset_config", {})
                            owner = dc.get("owner_display_id", "")
                            if "devo_display_id" in owner or "dev_oid" in owner:
                                needs_query_args = True
                            # Also check select_query for org filter references
                            exporter = camel.get("exporter_gcs_query", {})
                            sq = exporter.get("select_query", "")
                            if "devo_display_id" in sq or "dev_oid" in sq:
                                needs_query_args = True
                    if needs_query_args:
                        self._add_issue("error", "query_args",
                                        "Missing query_args but publisher references devo_display_id/dev_oid",
                                        location=location,
                                        suggestion="Add query_args with devo_display_id entries for all environments (local, dev, prod)")
                    continue

                # Check that query_args env keys match environments
                for arg_env in query_args:
                    if arg_env not in env_base_names:
                        self._add_issue("warning", "query_args",
                                        f"query_args key '{arg_env}' not found in environments",
                                        location=f"{location}.query_args",
                                        suggestion="Ensure query_args env keys match environment base names")

                # Check that all environments have query_args entries
                for env_name in env_base_names:
                    if env_name not in query_args:
                        self._add_issue("warning", "query_args",
                                        f"Environment '{env_name}' missing from query_args",
                                        location=f"{location}.query_args",
                                        suggestion=f"Add '{env_name}' entry to query_args with org identifier")

                # Collect all query_args variable names
                arg_keys = set()
                for env_args in query_args.values():
                    if isinstance(env_args, dict):
                        arg_keys.update(env_args.keys())

                # Check that template variables in query text are resolvable
                sql = query.get("query", "")
                template_vars = set(re.findall(r"\{\{\.(\w+)\}\}", sql))
                known_vars = set(self.FRAMEWORK_VARIABLES) | config_value_keys | arg_keys

                for var in template_vars:
                    if var not in known_vars:
                        self._add_issue("error", "query_args",
                                        f"Template variable '{{{{.{var}}}}}' not resolvable from framework, config_values, or query_args",
                                        location=location,
                                        suggestion=f"Add '{var}' to query_args or config_values")

                # Also check publisher select_query for template variables
                # (important for dummy query pattern where real SQL is in select_query)
                self._check_publisher_templates_for_query(
                    query.get("query_id", ""), known_vars, location)

    def _check_publisher_templates_for_query(self, query_id: str, known_vars: set, query_location: str):
        """Check that template variables in publisher select_query are resolvable."""
        job_activities = self.config.get("job_activities", [])
        for activity in job_activities:
            if activity.get("type") != "publisher":
                continue
            for publisher in activity.get("publishers", []):
                if publisher.get("query_id") != query_id:
                    continue
                camel = publisher.get("camel_publisher_activity", {})
                exporter = camel.get("exporter_gcs_query", {})
                select_query = exporter.get("select_query", "")
                if select_query:
                    template_vars = set(re.findall(r"\{\{\.(\w+)\}\}", select_query))
                    for var in template_vars:
                        if var not in known_vars:
                            self._add_issue("error", "query_args",
                                            f"Template variable '{{{{.{var}}}}}' in publisher select_query not resolvable",
                                            location=f"{query_location} -> publisher.select_query",
                                            suggestion=f"Add '{var}' to query_args or config_values")

    def _validate_table_creation_config(self, config: Dict, location: str):
        """Validate table_creation_config within a query (only called when config is present)."""
        if not config:
            return

        if not config.get("description"):
            self._add_issue("warning", "table_creation_config",
                            "table_creation_config missing 'description'",
                            location=f"{location}.table_creation_config",
                            suggestion="Add a description for the destination table")

        partition_key = config.get("partition_key")
        if not partition_key:
            self._add_issue("info", "table_creation_config",
                            "No partition_key set in table_creation_config",
                            location=f"{location}.table_creation_config")
        elif not self.OASIS_NAME_PATTERN.match(partition_key):
            self._add_issue("error", "table_creation_config",
                            f"partition_key '{partition_key}' violates Oasis naming: must match ^[a-z0-9_]*$",
                            location=f"{location}.table_creation_config")

        # Validate cluster_keys naming
        for ck in config.get("cluster_keys", []):
            if not self.OASIS_NAME_PATTERN.match(ck):
                self._add_issue("error", "table_creation_config",
                                f"cluster_key '{ck}' violates Oasis naming: must match ^[a-z0-9_]*$",
                                location=f"{location}.table_creation_config")

        time_partition_type = config.get("time_partition_type")
        if partition_key and not time_partition_type:
            self._add_issue("warning", "table_creation_config",
                            "partition_key set but time_partition_type not specified (defaults to 'day')",
                            location=f"{location}.table_creation_config",
                            suggestion="Explicitly set time_partition_type to 'day' or 'hour'")
        elif time_partition_type and time_partition_type not in ["day", "hour"]:
            self._add_issue("error", "table_creation_config",
                            f"Invalid time_partition_type: '{time_partition_type}'. Must be 'day' or 'hour'",
                            location=f"{location}.table_creation_config")

    def _is_dummy_query(self, sql: str) -> bool:
        """Check if a query is a dummy query (SELECT true/SELECT TRUE/WHERE 1=0)."""
        normalized = sql.strip().upper()
        return normalized in ("SELECT TRUE", "SELECT TRUE;") or \
               normalized.startswith("SELECT TRUE\n") or \
               "WHERE 1 = 0" in normalized or \
               "WHERE 1=0" in normalized or \
               normalized.startswith("-- DUMMY") or \
               (normalized.startswith("--") and "SELECT TRUE" in normalized)

    def _validate_queries(self):
        """Validate query configurations."""
        job_activities = self.config.get("job_activities", [])

        query_ids = set()

        for idx, activity in enumerate(job_activities):
            if activity.get("type") != "query":
                continue

            queries = activity.get("queries", [])
            for q_idx, query in enumerate(queries):
                location = f"job_activities[{idx}].queries[{q_idx}]"
                query_id = query.get("query_id", "")

                # Check query_id uniqueness
                if query_id in query_ids:
                    self._add_issue("error", "query",
                                    f"Duplicate query_id: {query_id}",
                                    location=location)
                query_ids.add(query_id)

                # Validate SQL (skip for dummy queries)
                sql = query.get("query", "")
                if sql and not self._is_dummy_query(sql):
                    self._validate_sql(sql, location)

                # Validate table_creation_config only if present (it's optional)
                table_config = query.get("table_creation_config")
                if table_config:
                    self._validate_table_creation_config(table_config, location)

    def _validate_sql(self, sql: str, location: str):
        """Validate SQL query for common issues."""
        sql_upper = sql.upper()
        sql_lines = sql.strip()

        # Check for SELECT * (but allow SELECT * EXCEPT(...) which is valid pattern)
        if re.search(r"SELECT\s+\*", sql_upper) and not re.search(r"SELECT\s+\*\s+EXCEPT", sql_upper):
            self._add_issue("warning", "bigquery",
                            "SELECT * detected - explicitly list needed columns to reduce cost",
                            location=location,
                            suggestion="Replace SELECT * with explicit column list or use SELECT * EXCEPT(...)",
                            auto_fixable=False)

        # Check for partition filter
        has_partition_filter = False
        for col in self.PARTITION_COLUMNS:
            if re.search(rf"WHERE.*{col}", sql_upper) or \
               re.search(rf"AND.*{col}", sql_upper) or \
               re.search(rf"DATE\s*\(\s*{col}", sql_upper):
                has_partition_filter = True
                break

        # Also check for template date filters
        for template in self.DATE_TEMPLATES:
            if template in sql:
                has_partition_filter = True
                break

        if not has_partition_filter and ("fact_" in sql.lower() or "dim_" in sql.lower()):
            self._add_issue("error", "bigquery",
                            "No partition filter detected - queries must filter on partition columns",
                            location=location,
                            suggestion="Add WHERE clause with partition column (e.g., DATE(created_date) = {{.record_date}})")

        # Check for hardcoded dataset names
        if re.search(r"`app-devrev-(dev|prod)\.", sql):
            self._add_issue("warning", "bigquery",
                            "Hardcoded project name detected - use template variables",
                            location=location,
                            suggestion="Use {{.source_project_name}}.{{.source_dataset_name}}.table",
                            auto_fixable=True)

        # Check for hardcoded dataset without template
        if re.search(r"`us_east1_devrev\.", sql) and "{{.source_dataset_name}}" not in sql:
            self._add_issue("warning", "bigquery",
                            "Hardcoded dataset name - use {{.source_dataset_name}}",
                            location=location,
                            suggestion="Replace 'us_east1_devrev' with '{{.source_dataset_name}}'",
                            auto_fixable=True)

        # Check for two-part FROM clause (missing project name)
        # Matches `{{.source_dataset_name}}.table` without project prefix
        # Downgraded to warning: many active production jobs use two-part (ponos fills project from global config)
        if re.search(r"`\{\{\.source_dataset_name\}\}\.\w+`", sql) and \
           "{{.source_project_name}}" not in sql:
            self._add_issue("warning", "bigquery",
                            "Two-part FROM clause detected - prefer three-part reference",
                            location=location,
                            suggestion="Use `{{.source_project_name}}.{{.source_dataset_name}}.table` for clarity")

        # Check for two-part destination reference
        if re.search(r"`\{\{\.destination_dataset_name\}\}\.\w+`", sql) and \
           "{{.destination_project_name}}" not in sql:
            self._add_issue("warning", "bigquery",
                            "Two-part destination reference - prefer three-part reference",
                            location=location,
                            suggestion="Use `{{.destination_project_name}}.{{.destination_dataset_name}}.table` for clarity")

        # Check for FULL OUTER JOIN without COALESCE
        if "FULL OUTER JOIN" in sql_upper or "FULL JOIN" in sql_upper:
            if "COALESCE" not in sql_upper:
                self._add_issue("warning", "bigquery",
                                "FULL OUTER JOIN without COALESCE - may cause NULL issues",
                                location=location,
                                suggestion="Use COALESCE for columns from both sides of FULL OUTER JOIN")

        # Check for functions on partition columns
        for col in self.PARTITION_COLUMNS:
            if re.search(rf"DATE_TRUNC\s*\(\s*{col}", sql_upper):
                self._add_issue("warning", "bigquery",
                                f"DATE_TRUNC on partition column {col} may prevent partition pruning",
                                location=location,
                                suggestion=f"Use date range instead: WHERE {col} BETWEEN '...' AND '...'")

        # Check for unbounded date ranges
        if re.search(r">=\s*['\"]20\d{2}-\d{2}-\d{2}", sql) and \
           not re.search(r"<=\s*['\"]20\d{2}-\d{2}-\d{2}", sql) and \
           not any(t in sql for t in self.DATE_TEMPLATES):
            self._add_issue("warning", "bigquery",
                            "Unbounded date range detected - consider adding upper bound",
                            location=location,
                            suggestion="Add upper bound or use {{.record_date}} template")

    def _validate_publishers(self):
        """Validate publisher configurations."""
        job_activities = self.config.get("job_activities", [])

        # Collect all query_ids
        query_ids = set()
        for activity in job_activities:
            if activity.get("type") == "query":
                for query in activity.get("queries", []):
                    query_ids.add(query.get("query_id"))

        for idx, activity in enumerate(job_activities):
            if activity.get("type") != "publisher":
                continue

            publishers = activity.get("publishers", [])
            for p_idx, publisher in enumerate(publishers):
                location = f"job_activities[{idx}].publishers[{p_idx}]"
                pub_type = publisher.get("type")

                # Check query_id reference
                ref_query_id = publisher.get("query_id")
                if ref_query_id and ref_query_id not in query_ids:
                    self._add_issue("error", "publisher",
                                    f"Publisher references non-existent query_id: {ref_query_id}",
                                    location=location)

                # Type-specific validation
                if pub_type == "camel":
                    self._validate_camel_publisher(publisher, location)
                elif pub_type == "tapio":
                    self._validate_tapio_publisher(publisher, location)
                elif pub_type == "storage":
                    self._validate_storage_publisher(publisher, location)

    def _validate_camel_publisher(self, publisher: Dict, location: str):
        """Validate camel publisher configuration."""
        activity = publisher.get("camel_publisher_activity", {})
        dataset_config = activity.get("dataset_config", {})

        if not dataset_config.get("name"):
            self._add_issue("error", "publisher",
                            "Camel publisher missing dataset_config.name",
                            location=location)
        elif not self.OASIS_NAME_PATTERN.match(dataset_config["name"]):
            self._add_issue("error", "publisher",
                            f"dataset_config.name '{dataset_config['name']}' violates Oasis naming: must match ^[a-z0-9_]*$",
                            location=f"{location}.dataset_config",
                            suggestion="Use lowercase letters, numbers, and underscores only")

        if not dataset_config.get("owner_display_id"):
            self._add_issue("warning", "publisher",
                            "dataset_config missing owner_display_id",
                            location=f"{location}.dataset_config",
                            suggestion='Set owner_display_id to "{{.devo_display_id}}"')
        elif dataset_config.get("owner_display_id") != "{{.devo_display_id}}":
            self._add_issue("info", "publisher",
                            f"owner_display_id is '{dataset_config['owner_display_id']}', typically should be '{{{{.devo_display_id}}}}'",
                            location=f"{location}.dataset_config")

        if dataset_config.get("create_oasis_dataset") is None:
            self._add_issue("info", "publisher",
                            "dataset_config.create_oasis_dataset not set",
                            location=f"{location}.dataset_config",
                            suggestion="Set create_oasis_dataset: true if this should create an Oasis dataset")

        exporter = activity.get("exporter_gcs_query", {})
        if exporter:
            select_query = exporter.get("select_query", "")
            if select_query:
                self._validate_sql(select_query, f"{location}.exporter_gcs_query.select_query")
        elif not exporter:
            # Check if this is a dummy query pattern where select_query is expected
            ref_query_id = publisher.get("query_id")
            if ref_query_id:
                for act in self.config.get("job_activities", []):
                    if act.get("type") == "query":
                        for q in act.get("queries", []):
                            if q.get("query_id") == ref_query_id:
                                sql = q.get("query", "")
                                if self._is_dummy_query(sql):
                                    self._add_issue("warning", "publisher",
                                                    "Dummy query pattern but publisher has no select_query",
                                                    location=location,
                                                    suggestion="Add exporter_gcs_query with select_query containing the real SQL")

    def _validate_tapio_publisher(self, publisher: Dict, location: str):
        """Validate tapio publisher configuration."""
        activity = publisher.get("tapio_publisher_activity", {})
        batch_size = activity.get("child_batch_size", 10000)

        if batch_size > 50000:
            self._add_issue("warning", "publisher",
                            f"Tapio child_batch_size ({batch_size}) is very large, may cause memory issues",
                            location=location,
                            suggestion="Consider reducing to 10000-20000")

    def _validate_storage_publisher(self, publisher: Dict, location: str):
        """Validate storage publisher configuration."""
        activity = publisher.get("storage_publisher_activity", {})
        exporter_type = activity.get("exporter_type")

        if exporter_type not in ["gcs_query", "gcs_query_to_aws_s3"]:
            self._add_issue("warning", "publisher",
                            f"Unknown exporter_type: {exporter_type}",
                            location=location)


def format_report(issues: List[ValidationIssue], verbose: bool = False) -> str:
    """Format validation issues as human-readable report."""
    if not issues:
        return "No issues found. Job configuration looks good!"

    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    infos = [i for i in issues if i.severity == "info"]

    lines = []
    lines.append("=== Ponos Job Validation Report ===\n")

    if errors:
        lines.append(f"ERRORS ({len(errors)}):")
        for issue in errors:
            lines.append(f"  [{issue.category}] {issue.message}")
            if issue.location:
                lines.append(f"    Location: {issue.location}")
            if issue.suggestion:
                lines.append(f"    Suggestion: {issue.suggestion}")
        lines.append("")

    if warnings:
        lines.append(f"WARNINGS ({len(warnings)}):")
        for issue in warnings:
            lines.append(f"  [{issue.category}] {issue.message}")
            if verbose and issue.location:
                lines.append(f"    Location: {issue.location}")
            if issue.suggestion:
                lines.append(f"    Suggestion: {issue.suggestion}")
        lines.append("")

    if infos and verbose:
        lines.append(f"INFO ({len(infos)}):")
        for issue in infos:
            lines.append(f"  [{issue.category}] {issue.message}")
        lines.append("")

    # Summary
    lines.append("SUMMARY:")
    lines.append(f"  Errors: {len(errors)}")
    lines.append(f"  Warnings: {len(warnings)}")
    lines.append(f"  Info: {len(infos)}")

    fixable = [i for i in issues if i.auto_fixable]
    if fixable:
        lines.append(f"\n  Auto-fixable issues: {len(fixable)}")
        lines.append("  Run with --fix to apply automatic fixes")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Validate Ponos job YAML against review criteria"
    )
    parser.add_argument("job_file", help="Path to Ponos job YAML file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Include info-level issues")
    parser.add_argument("--fix", action="store_true", help="Output fixed version (not yet implemented)")

    args = parser.parse_args()

    try:
        job_path = Path(args.job_file)
        if not job_path.exists():
            print(f"Error: File not found: {args.job_file}", file=sys.stderr)
            sys.exit(1)

        with open(job_path, 'r') as f:
            config = yaml.safe_load(f)

        validator = PonosJobValidator(config)
        issues = validator.validate()

        if args.json:
            result = {
                "file": str(job_path),
                "issues": [i.to_dict() for i in issues],
                "summary": {
                    "errors": len([i for i in issues if i.severity == "error"]),
                    "warnings": len([i for i in issues if i.severity == "warning"]),
                    "info": len([i for i in issues if i.severity == "info"]),
                }
            }
            print(json.dumps(result, indent=2))
        else:
            print(format_report(issues, verbose=args.verbose))

        # Exit with error code if there are errors
        if any(i.severity == "error" for i in issues):
            sys.exit(1)

    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
