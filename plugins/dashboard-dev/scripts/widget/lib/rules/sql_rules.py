"""SQL validation rules."""

import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..core.rule import ValidationRule
from ..core.models import ValidationError

# Add scripts directory to path for config import
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from config import DUCKDB_TYPE_MAP

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# Supported CAST target types in Meerkat query engine
# These are the only types that can be used in CAST expressions
SUPPORTED_CAST_TYPES = {
    # Basic types
    'VARCHAR',
    'DOUBLE',
    'BIGINT',
    'BOOLEAN',
    'TIMESTAMP',
    # Array types
    'ARRAY<VARCHAR>',
    'ARRAY<DOUBLE>',
    'ARRAY<BIGINT>',
    'ARRAY<BOOLEAN>',
    # Note: ARRAY<JSON> and ARRAY<TIMESTAMP> are NOT supported
}

# Meerkat-supported aggregate functions
# These can be used in measure sql_expression fields
# Source: /Users/devrev/code/explorer/dashboard/mosaic/internal/utils/constants.go
MEERKAT_AGGREGATE_FUNCTIONS = {
    'COUNT', 'SUM', 'AVG', 'MIN', 'MAX',
    'MEDIAN',  # Supported for P50 percentile
    'COUNT_DISTINCT',  # Meerkat-specific: COUNT_DISTINCT(col), not COUNT(DISTINCT col)
}

# Meerkat-supported window functions
MEERKAT_WINDOW_FUNCTIONS = {
    'ROW_NUMBER', 'RANK', 'DENSE_RANK',
    'LAG', 'LEAD', 'FIRST_VALUE', 'LAST_VALUE',
    'OVER',  # Window function clause
}

# Common SQL functions supported in OASIS (DuckDB)
# More comprehensive than Meerkat
OASIS_FUNCTIONS = {
    # Aggregates (DuckDB supports more than Meerkat)
    'COUNT', 'SUM', 'AVG', 'MIN', 'MAX',
    'PERCENTILE_CONT', 'PERCENTILE_DISC',  # Supported in OASIS, NOT in Meerkat
    'STDDEV', 'VARIANCE', 'CORR',
    # String functions
    'UPPER', 'LOWER', 'SUBSTRING', 'SUBSTR', 'CONCAT', 'CONCAT_WS',
    'LENGTH', 'TRIM', 'LTRIM', 'RTRIM', 'REPLACE',
    'SPLIT_PART', 'REGEXP_MATCHES', 'REGEXP_REPLACE',
    # Date functions
    'DATE_TRUNC', 'DATE_DIFF', 'EXTRACT', 'DATE_PART',
    'CURRENT_DATE', 'CURRENT_TIMESTAMP', 'NOW',
    'EPOCH', 'TO_TIMESTAMP',
    # JSON functions
    'JSON_EXTRACT', 'JSON_EXTRACT_STRING', 'JSON_EXTRACT_PATH',
    # Type casting
    'CAST', 'TRY_CAST',
    # Math
    'ROUND', 'FLOOR', 'CEIL', 'ABS', 'POWER', 'SQRT',
    'MOD', 'LN', 'LOG', 'EXP',
    # Conditional
    'COALESCE', 'NULLIF', 'CASE', 'IF',
    # Window functions
    'ROW_NUMBER', 'RANK', 'DENSE_RANK',
    'LAG', 'LEAD', 'FIRST_VALUE', 'LAST_VALUE',
    'OVER', 'PARTITION', 'ORDER',
    # Array functions
    'UNNEST', 'ARRAY_LENGTH', 'ARRAY_AGG',
    # Other
    'DISTINCT', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET',
}


class SqlSchemaRule(ValidationRule):
    """Validate SQL syntax and column references against cached dataset schemas.

    When schemas are cached, this rule catches:
    - SQL syntax errors (malformed queries, missing keywords)
    - Missing columns (e.g., 'closed_date' instead of 'actual_close_date')
    - Table references with wrong column names
    - Missing dataset access permissions (HTTP 406 errors)

    When schemas are NOT cached:
    - Skips validation gracefully (no false warnings)
    - API validation remains final authority

    This is the ONLY local SQL validation - API handles business logic.
    """

    def __init__(self, workspace_path: Optional[Path] = None, pat: Optional[str] = None, endpoint: Optional[str] = None):
        self.workspace_path = Path(workspace_path) if workspace_path else None
        self.pat = pat
        self.endpoint = endpoint
        self._conn = None
        self._tables_registered = set()
        self._schema_index = None
        self._permission_errors_cache = {}  # Cache to avoid retrying failed fetches
    
    @property
    def rule_id(self) -> str:
        return "SQL_SCHEMA"

    @property
    def description(self) -> str:
        return "SQL column references must match cached dataset schemas"

    @staticmethod
    def _ensure_prefix(dataset_name: str) -> str:
        """Ensure dataset has devrev. prefix."""
        if not dataset_name.startswith('devrev.'):
            return f'devrev.{dataset_name}'
        return dataset_name
    
    def _load_schema_index(self) -> Optional[dict]:
        """Load schema index if available from datasets/ directory."""
        if self._schema_index is not None:
            return self._schema_index

        if not self.workspace_path or not YAML_AVAILABLE:
            return None

        index_file = self.workspace_path / "datasets" / "index.yaml"
        if not index_file.exists():
            return None

        try:
            with open(index_file) as f:
                self._schema_index = yaml.safe_load(f)
                return self._schema_index
        except Exception:
            return None
    
    def _dataset_exists_in_org(self, dataset_name: str) -> bool:
        """Check if dataset exists in organization via schema index."""
        index = self._load_schema_index()
        if not index:
            return True  # Assume exists if no index

        full_name = self._ensure_prefix(dataset_name)
        datasets = index.get('datasets', [])
        return any(ds.get('name') == full_name for ds in datasets)
    
    def _load_schema(self, dataset_name: str) -> Optional[dict]:
        """Load schema from datasets/ directory.

        Supports both new naming (devrev.dataset.yaml) and legacy naming (*-analyzed.yaml).
        """
        if not self.workspace_path or not YAML_AVAILABLE:
            return None

        full_name = self._ensure_prefix(dataset_name)
        schema_dir = self.workspace_path / "datasets"

        if not schema_dir.exists():
            return None

        # Try new naming first (clean, no -analyzed postfix)
        schema_file = schema_dir / f"{full_name}.yaml"
        if schema_file.exists():
            try:
                with open(schema_file) as f:
                    return yaml.safe_load(f)
            except Exception:
                pass

        # Fall back to legacy naming (with -analyzed postfix)
        legacy_file = schema_dir / f"{full_name}-analyzed.yaml"
        if legacy_file.exists():
            try:
                with open(legacy_file) as f:
                    return yaml.safe_load(f)
            except Exception:
                pass

        # Also try old format without prefix for legacy workspaces
        old_name = dataset_name.replace('devrev.', '')
        old_schema_file = schema_dir / f"{old_name}-analyzed.yaml"
        if old_schema_file.exists():
            try:
                with open(old_schema_file) as f:
                    return yaml.safe_load(f)
            except Exception:
                pass

        return None
    
    def _fetch_schema_on_demand(self, dataset_name: str) -> Optional[dict]:
        """
        On-demand schema fetch is disabled.

        Use CLI to download schemas instead: dashboard-sync dataset fetch <dataset>
        This avoids the complexity of on-demand fetching and ensures schemas
        are consistently generated by the CLI.
        """
        # On-demand fetch disabled - use CLI instead
        return None

    def _check_dataset_permission(self, dataset_name: str) -> tuple:
        """
        Check if dataset access is denied (permission error).

        Returns:
            (has_permission: bool, error_message: Optional[str])
        """
        # Check cache first
        if dataset_name in self._permission_errors_cache:
            return self._permission_errors_cache[dataset_name]

        # Check if schema exists in cached schemas directory
        full_name = self._ensure_prefix(dataset_name)
        if self._load_schema(dataset_name) is not None:
            result = (True, None)
            self._permission_errors_cache[dataset_name] = result
            return result

        # Check if dataset exists in org (schema index)
        if not self._dataset_exists_in_org(dataset_name):
            # Dataset doesn't exist in organization - likely permission issue
            error_msg = f"Dataset '{full_name}' not accessible. This typically indicates missing dataset permissions."
            result = (False, error_msg)
            self._permission_errors_cache[dataset_name] = result
            return result

        # Schema not cached but dataset exists - could fetch if needed
        result = (True, None)
        self._permission_errors_cache[dataset_name] = result
        return result
    
    def _map_type(self, meerkat_type: str) -> str:
        """Map meerkat types to DuckDB types."""
        return DUCKDB_TYPE_MAP.get(str(meerkat_type).lower(), 'VARCHAR')
    
    def _register_table(self, conn, dataset_full_name: str) -> bool:
        """Register dataset as DuckDB table from cached schema.

        Args:
            conn: DuckDB connection
            dataset_full_name: Full dataset name (e.g., 'devrev.fact_ticket' or 'fact_ticket')
        """
        # Extract just table name for DuckDB (devrev schema created separately)
        table_name = dataset_full_name.split('.')[-1]

        if table_name in self._tables_registered:
            return True

        # Load schema using full name (with devrev. prefix)
        schema = self._load_schema(dataset_full_name)
        if not schema:
            return False

        # Extract column names from analyzed schema
        columns = []
        analysis = schema.get('dataset_analysis', {})

        # Schema files use 'columns' array (not separate dimensions/measures)
        for col in analysis.get('columns', []):
            col_name = col.get('reference_name', '')
            col_type = self._map_type(col.get('meerkat_schema', {}).get('type', 'string'))
            if col_name:
                columns.append(f'"{col_name}" {col_type}')

        if not columns:
            return False

        # Create table with schema (DuckDB uses devrev.{table_name})
        try:
            conn.execute("CREATE SCHEMA IF NOT EXISTS devrev")
            conn.execute(f"CREATE TABLE devrev.{table_name} ({', '.join(columns)})")
            self._tables_registered.add(table_name)
            return True
        except Exception:
            return False
    
    def _get_connection(self):
        """Get or create DuckDB connection."""
        if self._conn is None and DUCKDB_AVAILABLE:
            self._conn = duckdb.connect(":memory:")
        return self._conn
    
    def validate(self, widget: Dict[str, Any]) -> List[ValidationError]:
        errors = []
        
        # Skip if dependencies not available or no workspace
        if not DUCKDB_AVAILABLE or not YAML_AVAILABLE:
            return errors
        
        if not self.workspace_path:
            return errors

        # Check if datasets directory exists
        schema_dir = self.workspace_path / "datasets"
        if not schema_dir.exists():
            return errors  # Skip silently if no cached schemas
        
        conn = self._get_connection()
        if not conn:
            return errors

        for ds_idx, ds in enumerate(widget.get('data_sources', [])):
            oasis = ds.get('oasis', {})
            sql = oasis.get('sql_query')
            datasets = oasis.get('datasets', [])

            if not sql:
                continue

            # First, check SQL patterns (syntax validation) before schema validation
            pattern_errors = self.validate_sql_patterns(sql)
            for pattern_error in pattern_errors:
                # Update field_path to include data source index
                pattern_error.field_path = f"data_sources[{ds_idx}].{pattern_error.field_path}"
                errors.append(pattern_error)

            # Validate Meerkat measure functions
            for measure_idx, measure in enumerate(ds.get('measures', [])):
                measure_errors = self.validate_meerkat_functions(measure, ds_idx, measure_idx)
                errors.extend(measure_errors)

            # Check for permission issues before attempting to register tables
            permission_denied_datasets = []
            for dataset in datasets:
                has_permission, error_msg = self._check_dataset_permission(dataset)
                if not has_permission:
                    permission_denied_datasets.append((dataset, error_msg))

            # If any dataset has permission issues, this is a critical error
            if permission_denied_datasets:
                dataset_names = [d[0] for d in permission_denied_datasets]
                errors.append(ValidationError(
                    rule_id="DATASET_PERMISSION_DENIED",
                    severity="error",
                    field_path=f"data_sources[{ds_idx}].oasis.datasets",
                    message=f"Access denied: {', '.join(dataset_names)}",
                    suggestion="Request dataset permissions from workspace admin"
                ))
                continue  # Skip further validation for this data source

            # Register all referenced tables
            tables_available = True
            missing_schemas = []
            for dataset in datasets:
                # Use full name with devrev. prefix for schema lookup
                full_name = self._ensure_prefix(dataset)
                if not self._register_table(conn, full_name):
                    tables_available = False
                    missing_schemas.append(full_name)

            if not tables_available:
                # Some schemas not available - skip but warn
                if missing_schemas:
                    errors.append(ValidationError(
                        rule_id=self.rule_id,
                        severity="warning",
                        field_path=f"data_sources[{ds_idx}].oasis.sql_query",
                        message=f"Schema unavailable: {', '.join(missing_schemas)}",
                        suggestion="Column validation skipped. Use CLI to fetch schemas: dashboard-sync dataset fetch <dataset>"
                    ))
                continue
            
            try:
                conn.execute(f"EXPLAIN {sql}")
            except duckdb.ParserException as e:
                # Syntax errors (malformed SQL)
                error_msg = str(e)
                suggestion = "Fix SQL syntax error"

                if "syntax error at or near" in error_msg.lower():
                    if "group" in error_msg.lower():
                        suggestion = "Check JOIN clauses before GROUP BY"
                    elif "from" in error_msg.lower():
                        suggestion = "Check SELECT clause syntax before FROM"

                errors.append(ValidationError(
                    rule_id=self.rule_id,
                    severity="error",
                    field_path=f"data_sources[{ds_idx}].oasis.sql_query",
                    message=f"SQL syntax error: {error_msg}",
                    suggestion=suggestion
                ))
            except duckdb.BinderException as e:
                error_msg = str(e)

                # Check for type mismatch errors (VARCHAR vs INTEGER comparison)
                type_mismatch = re.search(
                    r'Cannot compare values of type (\w+) and type (\w+)',
                    error_msg,
                    re.IGNORECASE
                )
                if type_mismatch:
                    type1, type2 = type_mismatch.group(1), type_mismatch.group(2)
                    suggestion = self._build_type_mismatch_suggestion(type1, type2, sql)
                    errors.append(ValidationError(
                        rule_id=self.rule_id,
                        severity="error",
                        field_path=f"data_sources[{ds_idx}].oasis.sql_query",
                        message=f"SQL type mismatch: Cannot compare {type1} with {type2}",
                        suggestion=suggestion
                    ))
                    continue

                # Extract problematic column name from error
                bad_column = None
                # Pattern: "Referenced column "closed_date" not found" or "Column 'closed_date' not found"
                match = re.search(r'Referenced column ["\']([^"\']+)["\']', error_msg)
                if match:
                    bad_column = match.group(1)
                else:
                    match = re.search(r'["\']([^"\']+)["\'] not found in FROM clause', error_msg)
                    if match:
                        bad_column = match.group(1)

                # Try to determine which table to search for alternatives
                table_name = None
                if datasets:
                    # Use first dataset as primary table for suggestions
                    table_name = datasets[0].split('.')[-1]

                # Load schema to get available columns
                available_columns = []
                if table_name:
                    schema = self._load_schema(table_name)
                    if schema:
                        analysis = schema.get('dataset_analysis', {})
                        # Schema files use 'columns' array
                        for col in analysis.get('columns', []):
                            col_name = col.get('reference_name', '')
                            if col_name:
                                available_columns.append(col_name)

                # Build enhanced error message
                if "not found in FROM clause" in error_msg or "not found" in error_msg.lower():
                    if bad_column and table_name:
                        suggestion = f"Column '{bad_column}' not found in {table_name}."
                    else:
                        suggestion = "Column not found in dataset."

                    # Find similar columns using fuzzy matching
                    if bad_column and available_columns:
                        from difflib import get_close_matches
                        # Try multiple cutoff thresholds to find close matches
                        similar = get_close_matches(bad_column, available_columns, n=3, cutoff=0.4)
                        if similar:
                            suggestion += f" Did you mean: {', '.join(similar)}?"

                    # Show available columns (first 15)
                    if available_columns:
                        cols_preview = ', '.join(sorted(available_columns)[:15])
                        if len(available_columns) > 15:
                            cols_preview += f' (+{len(available_columns)-15} more)'
                        suggestion += f"\nAvailable columns: {cols_preview}"
                        if table_name:
                            suggestion += f"\nView schema: cat datasets/{table_name}.yaml"
                    else:
                        suggestion += " Verify column exists in dataset schema."
                elif "does not exist" in error_msg.lower():
                    suggestion = "Column or table not found - verify dataset name and column spelling"
                else:
                    suggestion = "Check SQL references against dataset schema"

                # Use bad_column in message if found, otherwise use original error
                if bad_column and table_name:
                    clean_message = f"Column '{bad_column}' not found in {table_name}"
                else:
                    clean_message = f"Column reference error: {error_msg}"

                errors.append(ValidationError(
                    rule_id=self.rule_id,
                    severity="error",
                    field_path=f"data_sources[{ds_idx}].oasis.sql_query",
                    message=clean_message,
                    suggestion=suggestion
                ))
            except duckdb.Error as e:
                # Other errors - report as warnings
                errors.append(ValidationError(
                    rule_id=self.rule_id,
                    severity="warning",
                    field_path=f"data_sources[{ds_idx}].oasis.sql_query",
                    message=f"Schema validation error: {str(e)}",
                    suggestion="Review SQL against cached dataset schemas"
                ))

        return errors

    def _build_type_mismatch_suggestion(self, type1: str, type2: str, sql: str) -> str:
        """Build helpful suggestion for SQL type mismatch errors.

        Args:
            type1: First type in comparison
            type2: Second type in comparison
            sql: The SQL query for context

        Returns:
            Detailed suggestion string
        """
        type1_upper = type1.upper()
        type2_upper = type2.upper()

        # Determine which type needs casting
        if 'VARCHAR' in type1_upper or 'STRING' in type1_upper:
            # VARCHAR compared to numeric
            if 'INT' in type2_upper or 'DOUBLE' in type2_upper or 'NUMBER' in type2_upper:
                return (
                    f"Column is VARCHAR but compared to {type2}.\n\n"
                    "Solutions:\n"
                    "1. Cast the column to numeric:\n"
                    "   WHERE CAST(column_name AS BIGINT) > 0\n"
                    "   WHERE CAST(column_name AS DOUBLE) > 0.0\n\n"
                    "2. Handle NULL/empty values with COALESCE:\n"
                    "   WHERE COALESCE(CAST(NULLIF(column_name, '') AS BIGINT), 0) > 0\n\n"
                    "Note: Use BIGINT for integers, DOUBLE for decimals.\n"
                    "VARCHAR columns often contain NULL or empty strings that need handling."
                )
        elif 'INT' in type1_upper or 'DOUBLE' in type1_upper or 'NUMBER' in type1_upper:
            # Numeric compared to VARCHAR
            if 'VARCHAR' in type2_upper or 'STRING' in type2_upper:
                return (
                    f"Numeric value compared to VARCHAR column.\n\n"
                    "Solutions:\n"
                    "1. Cast the column to numeric:\n"
                    "   WHERE CAST(column_name AS BIGINT) > 0\n\n"
                    "2. Cast the literal to string (if string comparison intended):\n"
                    "   WHERE column_name = '123'\n\n"
                    "Most likely you need to cast the VARCHAR column to a numeric type."
                )

        # Generic suggestion for other type mismatches
        return (
            f"Cannot compare {type1} with {type2}.\n\n"
            "Add explicit CAST to match types:\n"
            f"  CAST(column AS {type2_upper})  -- if converting column\n"
            f"  CAST(value AS {type1_upper})   -- if converting literal\n\n"
            "Supported CAST types: VARCHAR, BIGINT, DOUBLE, BOOLEAN, TIMESTAMP"
        )

    def validate_cast_expressions(self, sql_query: str) -> List[ValidationError]:
        """Validate CAST target types are supported by platform.

        Catches:
        - Unsupported types like ARRAY<JSON>, ARRAY<TIMESTAMP>
        - Nested array types
        - Complex generic types not in whitelist

        Args:
            sql_query: SQL query string to validate

        Returns:
            List of ValidationError objects for unsupported CAST types
        """
        errors = []

        # Pattern to match CAST expressions: CAST(... AS TYPE)
        # We need to handle nested parentheses, so we use a different approach
        # Look for CAST followed by AS, then capture the type
        cast_pattern = r'CAST\s*\(((?:[^()]|\([^()]*\))*)\s+AS\s+([A-Z<>,\s]+)\)'

        for match in re.finditer(cast_pattern, sql_query, re.IGNORECASE):
            cast_type = match.group(2).strip().upper()
            # Normalize whitespace in generic types (e.g., "ARRAY< VARCHAR >" -> "ARRAY<VARCHAR>")
            cast_type = re.sub(r'\s+', '', cast_type)

            if cast_type not in SUPPORTED_CAST_TYPES:
                # Build helpful error message with supported alternatives
                supported_types = ', '.join(sorted(SUPPORTED_CAST_TYPES))

                # Provide specific suggestions based on the unsupported type
                suggestion = f"Supported CAST types: {supported_types}"

                if 'ARRAY<JSON>' in cast_type:
                    suggestion += "\n\nFor JSON arrays, extract to string first:"
                    suggestion += "\n  CAST(json_extract_string(field, '$') AS ARRAY<VARCHAR>)"
                elif 'JSON' in cast_type:
                    suggestion += "\n\nFor JSON data, use VARCHAR:"
                    suggestion += "\n  CAST(json_extract_string(field, '$') AS VARCHAR)"
                elif 'ARRAY<TIMESTAMP>' in cast_type:
                    suggestion += "\n\nTIMESTAMP arrays are not supported. Consider using VARCHAR:"
                    suggestion += "\n  CAST(array_column AS ARRAY<VARCHAR>)"

                suggestion += "\n\nSee the **widget-development** skill reference `references/sql-patterns.md` → 'CAST Type Constraints' for details"

                errors.append(ValidationError(
                    rule_id='UNSUPPORTED_CAST_TYPE',
                    severity='error',
                    field_path='oasis.sql_query',
                    message=f"Unsupported CAST type: {cast_type}",
                    suggestion=suggestion
                ))

        return errors

    def validate_meerkat_functions(self, measure: Dict[str, Any], ds_index: int, measure_index: int) -> List[ValidationError]:
        """Validate that functions in Meerkat measure expressions are supported.

        Meerkat has a limited function set compared to OASIS/DuckDB.
        Common mistake: Using PERCENTILE_CONT in Meerkat (not supported).

        Args:
            measure: Measure dictionary with meerkat_schema
            ds_index: Data source index for error reporting
            measure_index: Measure index for error reporting

        Returns:
            List of ValidationError objects for unsupported functions
        """
        errors = []

        meerkat_expr = measure.get('meerkat_schema', {}).get('sql_expression', '')
        if not meerkat_expr:
            return errors

        # Extract function calls from expression
        # Pattern: word followed by opening parenthesis
        function_pattern = r'\b([A-Z_][A-Z0-9_]*)\s*\('
        functions_used = set(re.findall(function_pattern, meerkat_expr, re.IGNORECASE))

        # Check against whitelist
        allowed_functions = MEERKAT_AGGREGATE_FUNCTIONS | MEERKAT_WINDOW_FUNCTIONS
        measure_name = measure.get('reference_name', f'measures[{measure_index}]')

        for func in functions_used:
            func_upper = func.upper()
            if func_upper not in allowed_functions:
                # Build helpful error message
                suggestion = f"Supported Meerkat functions: {', '.join(sorted(allowed_functions))}"

                # Specific guidance for common mistakes
                if func_upper == 'PERCENTILE_CONT' or func_upper == 'PERCENTILE_DISC':
                    suggestion = (
                        "Meerkat supports percentiles, but NOT via PERCENTILE_CONT() function.\n"
                        "Use function types instead:\n"
                        "\n"
                        "CORRECT - Use function.type field:\n"
                        "{\n"
                        "  \"meerkat_schema\": {\n"
                        "    \"type\": \"number\",\n"
                        "    \"function\": {\n"
                        "      \"type\": \"MeerkatWidgetColumnFunction_TypeEnumP90\"  // For P90\n"
                        "    },\n"
                        "    \"sql_expression\": \"column_name\"  // Column to compute percentile on\n"
                        "  }\n"
                        "}\n"
                        "\n"
                        "Supported percentiles: P50/MEDIAN, P90, P95, P99\n"
                        "For other percentiles (P75, P25), pre-compute in OASIS SQL query."
                    )
                elif func_upper in {'STDDEV', 'VARIANCE'}:
                    suggestion = (
                        f"{func_upper} is not supported in Meerkat.\n"
                        "Pre-compute this aggregate in OASIS SQL query instead."
                    )

                errors.append(ValidationError(
                    rule_id='UNSUPPORTED_MEERKAT_FUNCTION',
                    severity='error',
                    field_path=f'data_sources[{ds_index}].measures[{measure_index}].meerkat_schema.sql_expression',
                    message=f"Function '{func}' not supported in Meerkat measure expressions",
                    suggestion=suggestion
                ))

        return errors

    def validate_unnest_patterns(self, sql_query: str) -> List[ValidationError]:
        """Validate UNNEST usage patterns.

        Catches:
        - UNNEST on JSON types (not supported, must use array types)
        - recursive := true parameter (DuckDB-specific, not supported in Meerkat)
        - Common UNNEST mistakes
        - Direct UNNEST on json_extract() without CAST (implicit JSON type)

        Args:
            sql_query: SQL query string to validate

        Returns:
            List of ValidationError objects for invalid UNNEST usage
        """
        errors = []

        # Check for UNNEST with recursive parameter (DuckDB-specific, not in Meerkat)
        if re.search(r'UNNEST\s*\([^)]*recursive\s*:=', sql_query, re.IGNORECASE):
            errors.append(ValidationError(
                rule_id='UNSUPPORTED_UNNEST_PARAMETER',
                severity='error',
                field_path='oasis.sql_query',
                message="UNNEST parameter 'recursive := true' is not supported",
                suggestion=(
                    "Remove 'recursive := true' parameter from UNNEST call.\n"
                    "UNNEST in Meerkat does not support DuckDB-specific parameters."
                )
            ))

        # Check for UNNEST on ARRAY<JSON> casts
        # Pattern: UNNEST(CAST(... AS ARRAY<JSON>))
        # Need to handle nested parentheses in CAST expression
        pattern_json_array = r'UNNEST\s*\(\s*CAST\s*\(((?:[^()]|\([^()]*\))*)\s+AS\s+ARRAY\s*<\s*JSON\s*>'
        if re.search(pattern_json_array, sql_query, re.IGNORECASE):
            errors.append(ValidationError(
                rule_id='UNSUPPORTED_UNNEST_JSON',
                severity='error',
                field_path='oasis.sql_query',
                message="UNNEST cannot operate on ARRAY<JSON> type",
                suggestion=(
                    "UNNEST() can only be applied to lists, structs and NULL, not JSON.\n"
                    "\n"
                    "Solution - Use ARRAY<VARCHAR> instead:\n"
                    "1. Extract JSON to string: json_extract_string(...)\n"
                    "2. Cast to string array: CAST(... AS ARRAY<VARCHAR>)\n"
                    "3. UNNEST the string array: UNNEST(array_col)\n"
                    "4. Extract fields from each element: json_extract_string(element, '$.field')\n"
                    "\n"
                    "Example:\n"
                    "  CAST(json_extract_string(data, '$.articles') AS ARRAY<VARCHAR>)"
                )
            ))

        # NEW: Check for UNNEST(json_extract(...)) - Implicit JSON type
        # Pattern: UNNEST(json_extract(...)) - matches json_extract but not json_extract_string
        pattern_json_extract_unnest = r'UNNEST\s*\(\s*json_extract\s*\('
        if re.search(pattern_json_extract_unnest, sql_query, re.IGNORECASE):
            errors.append(ValidationError(
                rule_id='UNSUPPORTED_UNNEST_JSON_EXTRACT',
                severity='error',
                field_path='oasis.sql_query',
                message='UNNEST on json_extract() result is not supported',
                suggestion=(
                    'json_extract() returns JSON type which cannot be used with UNNEST.\n'
                    '\n'
                    'Solution 1 - Cast to ARRAY<VARCHAR> (simple arrays):\n'
                    '  CAST(json_extract_string(field, \'$.path\') AS ARRAY<VARCHAR>)\n'
                    '\n'
                    'Solution 2 - Indexed array access (for nested objects):\n'
                    '  WITH data AS (\n'
                    '    SELECT json_extract_string(field, \'$.array\') AS arr\n'
                    '  )\n'
                    '  SELECT json_extract_string(arr, \'$[\' || idx || \'].property\')\n'
                    '  FROM data, UNNEST(generate_series(0, json_array_length(arr) - 1)) AS idx\n'
                    '\n'
                    'This pattern:\n'
                    '  ✓ Uses json_extract_string() which returns VARCHAR (not JSON)\n'
                    '  ✓ UNNEST only the integer series (not JSON)\n'
                    '  ✓ Accesses array elements by index: $[0], $[1], etc.'
                )
            ))

        # Check for direct CAST to JSON before UNNEST
        # Pattern: CAST(... AS JSON) ... UNNEST
        if re.search(r'CAST\s*\([^)]+AS\s+JSON\s*\)', sql_query, re.IGNORECASE) and \
           'UNNEST' in sql_query.upper():
            errors.append(ValidationError(
                rule_id='UNNEST_JSON_WARNING',
                severity='warning',
                field_path='oasis.sql_query',
                message="Query contains both CAST(... AS JSON) and UNNEST",
                suggestion=(
                    "Verify that UNNEST is not operating on the JSON-casted value.\n"
                    "UNNEST requires array types (VARCHAR[], DOUBLE[], etc.), not JSON."
                )
            ))

        return errors

    def validate_sql_patterns(self, sql_query: str) -> List[ValidationError]:
        """Validate SQL patterns for DuckDB compatibility.

        Catches:
        - Invalid array type casting: AS TYPE[]
        - UNNEST usage issues
        - Function-specific syntax errors
        - Unsupported CAST types

        This validation is pattern-based (regex) to catch common syntax errors
        before they reach the runtime parser.
        """
        errors = []

        # First, check for unsupported CAST types (most specific)
        errors.extend(self.validate_cast_expressions(sql_query))

        # Check UNNEST patterns
        errors.extend(self.validate_unnest_patterns(sql_query))

        patterns = {
            'invalid_array_cast': {
                'pattern': r'\bAS\s+\w+\[\s*\]',
                'message': 'Invalid array type syntax "AS TYPE[]". Use "AS ARRAY<TYPE>" instead',
                'examples': [
                    'WRONG: CAST(...AS JSON[])',
                    'CORRECT: CAST(...AS ARRAY<VARCHAR>)'
                ],
                'severity': 'error'
            },
            'unnest_cast_json': {
                'pattern': r'UNNEST\s*\(\s*CAST\s*\(\s*json_extract',
                'message': 'Verify UNNEST with json_extract type casting is correct. Use ARRAY<> syntax for array types',
                'severity': 'warning'
            }
        }

        for pattern_id, pattern_info in patterns.items():
            pattern = pattern_info['pattern']
            message = pattern_info['message']
            severity = pattern_info.get('severity', 'error')

            if re.search(pattern, sql_query, re.IGNORECASE):
                suggestion = message
                if 'examples' in pattern_info:
                    suggestion += '\n' + '\n'.join(pattern_info['examples'])
                suggestion += '\nSee the **widget-development** skill reference `references/sql-constraints.md` → "Array Type Casting" for details'

                errors.append(ValidationError(
                    rule_id='SQL_PATTERN_' + pattern_id.upper(),
                    severity=severity,
                    field_path='oasis.sql_query',
                    message=message,
                    suggestion=suggestion
                ))

        return errors
