"""SQL AST parsing utilities using sqlglot.

This module provides Abstract Syntax Tree (AST) based SQL parsing functions
to replace regex-based parsing. AST parsing is more robust and handles edge
cases like comments, string literals, and nested structures correctly.

Benefits over regex:
- No false positives from SQL in comments or string literals
- Handles nested structures (subqueries, CTEs) correctly
- Self-documenting code (AST node types are explicit)
- No regex backtracking performance issues

Usage:
    from .sql_ast import parse_sql, extract_cte_names

    ast = parse_sql("WITH cte AS (SELECT 1) SELECT * FROM cte")
    if ast:
        cte_names = extract_cte_names(ast)
"""

from typing import Optional, Set, Tuple, List
import sqlglot
from sqlglot import exp


def parse_sql(sql: str, dialect: str = 'duckdb') -> Optional[exp.Expression]:
    """Parse SQL string into AST with error handling.

    Args:
        sql: SQL query string to parse
        dialect: SQL dialect (default: 'duckdb')

    Returns:
        Parsed sqlglot Expression AST, or None if parsing fails

    Example:
        >>> ast = parse_sql("SELECT * FROM users")
        >>> if ast:
        ...     print(f"Parsed successfully: {type(ast)}")
    """
    try:
        # sqlglot.parse returns a list of statements
        statements = sqlglot.parse(sql, dialect=dialect)
        if not statements:
            return None
        # Return first statement (most widgets have single statement)
        return statements[0]
    except Exception:
        # Parse errors are expected for invalid SQL
        # Caller decides whether to skip or report error
        return None


def extract_cte_names(ast: exp.Expression) -> Set[str]:
    """Extract CTE (Common Table Expression) names from parsed AST.

    CTEs are subqueries defined in WITH clauses:
        WITH cte1 AS (...), cte2 AS (...) SELECT ...

    Args:
        ast: Parsed SQL AST from parse_sql()

    Returns:
        Set of CTE alias names (case-sensitive as they appear in SQL)

    Example:
        >>> sql = "WITH users_cte AS (SELECT 1) SELECT * FROM users_cte"
        >>> ast = parse_sql(sql)
        >>> extract_cte_names(ast)
        {'users_cte'}

    Edge cases handled:
        - Multiple CTEs: WITH cte1 AS (...), cte2 AS (...)
        - Nested CTEs: WITH outer AS (WITH inner AS (...) SELECT ...)
        - CTEs in comments: -- WITH fake_cte AS (ignored)
        - CTEs in strings: 'WITH fake_cte AS' (ignored)
    """
    cte_names = set()

    # find_all() recursively searches entire AST for CTE nodes
    for cte in ast.find_all(exp.CTE):
        # CTE.alias returns the CTE name (e.g., "users_cte")
        if cte.alias:
            cte_names.add(cte.alias)

    return cte_names


def extract_table_references(ast: exp.Expression) -> Set[Tuple[str, str]]:
    """Extract table references from SQL AST (excludes CTEs).

    Returns (schema, table_name) tuples for all table references in
    FROM and JOIN clauses. CTEs are excluded (they're not real tables).

    Args:
        ast: Parsed SQL AST from parse_sql()

    Returns:
        Set of (schema, table_name) tuples. Schema is empty string if not specified.

    Example:
        >>> sql = "SELECT * FROM devrev.users JOIN system.logs"
        >>> ast = parse_sql(sql)
        >>> extract_table_references(ast)
        {('devrev', 'users'), ('system', 'logs')}

        >>> sql = "SELECT * FROM users"  # No schema
        >>> ast = parse_sql(sql)
        >>> extract_table_references(ast)
        {('', 'users')}

    Note:
        To filter out CTEs, use:
            cte_names = extract_cte_names(ast)
            real_tables = {t for t in extract_table_references(ast)
                          if t[1] not in cte_names}
    """
    tables = set()

    # find_all() recursively searches for Table nodes (FROM, JOIN, etc.)
    for table in ast.find_all(exp.Table):
        # table.db = schema name (None if not specified)
        # table.name = table name
        schema = table.db or ''
        name = table.name
        if name:  # Ensure name is not None
            tables.add((schema, name))

    return tables


def find_left_joins_on_ctes(
    ast: exp.Expression,
    cte_names: Set[str]
) -> List[str]:
    """Find CTEs used in LEFT JOIN operations.

    Platform limitation: LEFT JOIN (and other non-INNER joins) on CTEs
    or subqueries are not supported. This function detects such violations.

    Args:
        ast: Parsed SQL AST from parse_sql()
        cte_names: Set of CTE names from extract_cte_names()

    Returns:
        List of CTE names used in LEFT JOIN (may contain duplicates if
        same CTE is joined multiple times)

    Example:
        >>> sql = '''
        ... WITH users_cte AS (SELECT * FROM users)
        ... SELECT * FROM base LEFT JOIN users_cte ON base.id = users_cte.id
        ... '''
        >>> ast = parse_sql(sql)
        >>> ctes = extract_cte_names(ast)
        >>> find_left_joins_on_ctes(ast, ctes)
        ['users_cte']

    Detects:
        - LEFT JOIN cte_name
        - LEFT OUTER JOIN cte_name
        - RIGHT JOIN cte_name (also unsupported)
        - FULL OUTER JOIN cte_name (also unsupported)

    Does NOT detect:
        - INNER JOIN cte_name (allowed)
        - JOIN cte_name (defaults to INNER, allowed)
    """
    violations = []

    # find_all() searches for all Join nodes in AST
    for join in ast.find_all(exp.Join):
        # join.side contains join type: "LEFT", "RIGHT", "FULL", etc.
        # None or empty means INNER JOIN (allowed)
        if join.side and join.side.upper() in ('LEFT', 'RIGHT', 'FULL'):
            # Check if the joined table is a CTE
            for table in join.find_all(exp.Table):
                if table.name in cte_names:
                    violations.append(table.name)

    return violations


def extract_table_names_for_consistency_check(ast: exp.Expression) -> Set[str]:
    """Extract table names from SQL for dataset consistency checking.

    This is a convenience function that combines extract_table_references()
    and extract_cte_names() to return only real table names (not CTEs),
    without schema qualifiers.

    Args:
        ast: Parsed SQL AST from parse_sql()

    Returns:
        Set of table names (without schema prefix) that should be declared
        in the datasets array

    Example:
        >>> sql = '''
        ... WITH cte AS (SELECT * FROM devrev.users)
        ... SELECT * FROM cte JOIN devrev.tickets
        ... '''
        >>> ast = parse_sql(sql)
        >>> extract_table_names_for_consistency_check(ast)
        {'users', 'tickets'}  # 'cte' is excluded
    """
    cte_names = extract_cte_names(ast)
    table_refs = extract_table_references(ast)

    # Extract table names (without schema), excluding CTEs
    table_names = {
        name for schema, name in table_refs
        if name not in cte_names
    }

    return table_names
