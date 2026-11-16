"""
Central configuration for Dashboard Development Plugin.

All constants that configure behavior should be defined here.
This makes it easy to adjust settings without hunting through code.

Organized by category:
- Widget Structure
- Dataset Configuration
- Schema Analysis Parameters
- Type Mappings
- Validation Rules
- Workspace Defaults
"""

# ==============================================================================
# WIDGET STRUCTURE
# ==============================================================================

# Order of fields in cleaned widget JSON (dashboard_sync.py)
WIDGET_FIELD_ORDER = ('title', 'description', 'version', 'data_sources', 'sub_widgets', 'layout')
WIDGET_ALLOWED_FIELDS = set(WIDGET_FIELD_ORDER)

# ==============================================================================
# DATASET CONFIGURATION
# ==============================================================================

# Core OLAP tables (dim_*, fact_*) for dashboard development
# These are cached during workspace initialization for immediate use
# OLAP tables are available in all orgs via oasis.dataset.list with scope=SYSTEM
ALL_DATASETS = [
    # Core dimension tables (most commonly used in dashboards)
    'dim_ticket',                           # Support tickets (most common)
    'dim_account',                          # Customer accounts
    'dim_issue',                            # Engineering issues
    'dim_conversation',                     # Customer conversations
    'dim_revu',                             # Customer contacts (rev users)
    'dim_devu',                             # Internal users (dev users)
    'dim_group',                            # Teams and groups
    'dim_product',                          # Products/parts

    # Core fact tables (for metrics and aggregations)
    'fact_ticket',                          # Ticket facts and metrics
    'fact_conversation',                    # Conversation metrics

    # Additional useful dimensions (can add more as needed)
    # 'dim_article',                        # Knowledge base articles
    # 'dim_enhancement',                    # Product enhancements
    # 'dim_feature',                        # Product features
    # 'dim_opportunity',                    # Sales opportunities
    # 'dim_sla_tracker',                    # SLA tracking
    # 'dim_vista',                          # Sprint boards
    # 'fact_issue',                         # Issue facts
    # 'fact_enhancement',                   # Enhancement facts
]

# ==============================================================================
# SCHEMA ANALYSIS PARAMETERS
# ==============================================================================

# Number of rows to sample for schema discovery
DEFAULT_SAMPLE_ROWS = 100

# Enum detection thresholds
ENUM_MIN_DISTINCT = 3       # Minimum distinct values to classify as enum
ENUM_MAX_DISTINCT = 20      # Maximum distinct values to classify as enum
MAX_ENUM_VALUES = 500       # Safety limit for extracting enum values

# ID type detection
ID_SAMPLE_LIMIT = 50        # Number of ID values to sample for type detection

# ==============================================================================
# TYPE MAPPINGS
# ==============================================================================

# DevRev field_type to Meerkat type (schema_discovery.py)
MEERKAT_TYPE_MAP = {
    # Number types
    'int': 'number',
    'double': 'number',
    'uenum': 'number',

    # Time types
    'timestamp': 'time',
    'date': 'time',

    # Array types
    '[]id': 'string_array',

    # String types (default)
    'id': 'string',
    'enum': 'string',
    'text': 'string',
    'tokens': 'string',

    # Boolean type
    'bool': 'boolean',

    # Composite (not directly usable, map to string for safety)
    'composite': 'string',
}

# Meerkat type to DuckDB type (sql_rules.py)
DUCKDB_TYPE_MAP = {
    'string': 'VARCHAR',
    'number': 'DOUBLE',
    'time': 'TIMESTAMP',
    'boolean': 'BOOLEAN',
    'string_array': 'VARCHAR[]',
}

# ID field name patterns to ID types (schema_discovery.py)
# Order matters - more specific patterns first
ID_TYPE_MAP = [
    # User-related IDs
    ('owned_by', ['dev_user']),
    ('created_by', ['dev_user']),
    ('modified_by', ['dev_user']),
    ('assignee', ['dev_user']),
    ('reporter', ['dev_user']),
    ('member', ['dev_user']),
    ('dev_user', ['dev_user']),
    ('author', ['dev_user']),

    # Organization IDs
    ('account', ['account']),
    ('rev_org', ['rev_org']),
    ('rev_user', ['rev_user']),

    # Work item IDs
    ('ticket', ['work']),
    ('issue', ['work']),
    ('work', ['work']),

    # Component IDs
    ('part', ['part']),
    ('product', ['part']),
    ('capability', ['part']),
    ('feature', ['part']),
    ('enhancement', ['part']),

    # Communication IDs
    ('conversation', ['conversation']),
    ('article', ['article']),
    ('comment', ['comment']),

    # Metadata IDs
    ('tag', ['tag']),
    ('stage', ['custom_stage']),
    ('group', ['group']),
    ('sla', ['sla_policy']),
    ('custom_field', ['custom_type_fragment']),

    # Service account IDs
    ('service_account', ['service_account']),
    ('bot', ['service_account']),

    # Generic user fallback
    ('user', ['dev_user']),

    # Generic relationships (assume work items)
    ('parent_id', ['work']),
    ('parent', ['work']),
    ('child_id', ['work']),
    ('child', ['work']),
    ('related', ['work']),
    ('linked', ['work']),
    ('source_id', ['work']),
    ('target_id', ['work']),

    # Project management
    ('sprint', ['sprint']),
    ('milestone', ['milestone']),
    ('project', ['project']),

    # Automation & webhooks
    ('webhook', ['webhook']),
    ('workflow', ['workflow']),
    ('automation', ['automation']),
]

# ==============================================================================
# VALIDATION RULES
# ==============================================================================

# Cartesian chart types - charts that use x/y axes (viz_rules.py)
CARTESIAN_CHART_TYPES = ['line', 'bar', 'column']

# Circular chart types - charts that use segments/slices (viz_rules.py)
CIRCULAR_CHART_TYPES = ['pie', 'donut']

# All supported visualization types
ALL_VIZ_TYPES = ['line', 'bar', 'column', 'table', 'metric', 'pie', 'donut']


# Wrong property names to check for in chart configurations
WRONG_VIZ_PROPS = ['x_axis', 'y_axes', 'lines']

# Field validation (field_rules.py)
TIMESTAMP_FIELD_TYPES = ['timestamp', 'date', 'time']
AGGREGATION_KEYWORDS = ['count', 'sum', 'avg', 'median', 'min', 'max']

# SQL validation (sql_rules.py)
SQL_KEYWORDS = {'unnest', 'lateral', 'generate_series', 'json_table'}
UPPERCASE_AGG_PATTERNS = ['COUNT(', 'SUM(', 'AVG(', 'MEDIAN(', 'MIN(', 'MAX(', 'DISTINCT ']

# Unsupported SQL functions - functions from other dialects that don't exist in DuckDB
# Maps unsupported function name (lowercase) to DuckDB replacement
UNSUPPORTED_SQL_FUNCTIONS = {
    'json_extract_scalar': 'json_extract_string',  # BigQuery/Presto
    'json_value': 'json_extract_string',           # SQL Server/Oracle
    'get_json_object': 'json_extract_string',      # Spark/Hive
    'json_query': 'json_extract',                  # SQL Server (for objects/arrays)
}
