"""Unit tests for SQL AST parsing utilities.

Tests the AST-based SQL parsing functions that replace regex parsing.
Verifies correct handling of edge cases like comments, string literals,
and nested structures.
"""

import pytest
from scripts.widget.lib.core.sql_ast import (
    parse_sql,
    extract_cte_names,
    extract_table_references,
    find_left_joins_on_ctes,
    extract_table_names_for_consistency_check
)


class TestParseSql:
    """Tests for parse_sql function."""

    def test_parse_simple_select(self):
        """Test parsing a simple SELECT statement."""
        sql = "SELECT * FROM users"
        ast = parse_sql(sql)
        assert ast is not None

    def test_parse_complex_query(self):
        """Test parsing a complex query with CTEs and joins."""
        sql = """
        WITH user_stats AS (
            SELECT user_id, COUNT(*) as count
            FROM events
            GROUP BY user_id
        )
        SELECT u.name, s.count
        FROM users u
        LEFT JOIN user_stats s ON u.id = s.user_id
        """
        ast = parse_sql(sql)
        assert ast is not None

    def test_parse_invalid_sql(self):
        """Test that invalid SQL returns None."""
        sql = "SELECT * FROM WHERE"
        ast = parse_sql(sql)
        assert ast is None

    def test_parse_empty_string(self):
        """Test that empty string returns None."""
        ast = parse_sql("")
        assert ast is None

    def test_parse_with_dialect(self):
        """Test parsing with explicit DuckDB dialect."""
        sql = "SELECT * FROM users"
        ast = parse_sql(sql, dialect='duckdb')
        assert ast is not None


class TestExtractCteNames:
    """Tests for extract_cte_names function."""

    def test_single_cte(self):
        """Test extracting a single CTE name."""
        sql = "WITH users_cte AS (SELECT 1) SELECT * FROM users_cte"
        ast = parse_sql(sql)
        cte_names = extract_cte_names(ast)
        assert cte_names == {'users_cte'}

    def test_multiple_ctes(self):
        """Test extracting multiple CTE names."""
        sql = """
        WITH cte1 AS (SELECT 1),
             cte2 AS (SELECT 2),
             cte3 AS (SELECT 3)
        SELECT * FROM cte1
        """
        ast = parse_sql(sql)
        cte_names = extract_cte_names(ast)
        assert cte_names == {'cte1', 'cte2', 'cte3'}

    def test_nested_ctes(self):
        """Test extracting nested CTE names."""
        sql = """
        WITH outer_cte AS (
            WITH inner_cte AS (SELECT 1)
            SELECT * FROM inner_cte
        )
        SELECT * FROM outer_cte
        """
        ast = parse_sql(sql)
        cte_names = extract_cte_names(ast)
        assert 'outer_cte' in cte_names
        assert 'inner_cte' in cte_names

    def test_no_ctes(self):
        """Test query without CTEs."""
        sql = "SELECT * FROM users"
        ast = parse_sql(sql)
        cte_names = extract_cte_names(ast)
        assert cte_names == set()

    def test_cte_in_comment_ignored(self):
        """Test that CTEs in comments are not extracted."""
        sql = """
        -- WITH fake_cte AS (SELECT 1)
        SELECT * FROM users
        """
        ast = parse_sql(sql)
        cte_names = extract_cte_names(ast)
        assert 'fake_cte' not in cte_names

    def test_cte_in_string_ignored(self):
        """Test that CTEs in string literals are not extracted."""
        sql = "SELECT 'WITH fake_cte AS (SELECT 1)' FROM users"
        ast = parse_sql(sql)
        cte_names = extract_cte_names(ast)
        assert 'fake_cte' not in cte_names


class TestExtractTableReferences:
    """Tests for extract_table_references function."""

    def test_simple_from_clause(self):
        """Test extracting table from simple FROM clause."""
        sql = "SELECT * FROM users"
        ast = parse_sql(sql)
        tables = extract_table_references(ast)
        assert ('', 'users') in tables

    def test_schema_qualified_table(self):
        """Test extracting schema-qualified table references."""
        sql = "SELECT * FROM devrev.users JOIN system.logs"
        ast = parse_sql(sql)
        tables = extract_table_references(ast)
        assert ('devrev', 'users') in tables
        assert ('system', 'logs') in tables

    def test_multiple_joins(self):
        """Test extracting tables from multiple JOINs."""
        sql = """
        SELECT *
        FROM users u
        JOIN tickets t ON u.id = t.user_id
        LEFT JOIN comments c ON t.id = c.ticket_id
        """
        ast = parse_sql(sql)
        tables = extract_table_references(ast)
        table_names = {name for schema, name in tables}
        assert 'users' in table_names
        assert 'tickets' in table_names
        assert 'comments' in table_names

    def test_subquery_tables(self):
        """Test extracting tables from subqueries."""
        sql = """
        SELECT * FROM (
            SELECT * FROM users
        ) AS subquery
        """
        ast = parse_sql(sql)
        tables = extract_table_references(ast)
        assert ('', 'users') in tables

    def test_table_in_comment_ignored(self):
        """Test that table references in comments are not extracted."""
        sql = """
        -- FROM fake_table
        SELECT * FROM users
        """
        ast = parse_sql(sql)
        tables = extract_table_references(ast)
        table_names = {name for schema, name in tables}
        assert 'users' in table_names
        assert 'fake_table' not in table_names

    def test_table_in_string_ignored(self):
        """Test that table references in string literals are not extracted."""
        sql = "SELECT 'FROM fake_table' FROM users"
        ast = parse_sql(sql)
        tables = extract_table_references(ast)
        table_names = {name for schema, name in tables}
        assert 'users' in table_names
        assert 'fake_table' not in table_names


class TestFindLeftJoinsOnCtes:
    """Tests for find_left_joins_on_ctes function."""

    def test_left_join_on_cte(self):
        """Test detecting LEFT JOIN on CTE."""
        sql = """
        WITH users_cte AS (SELECT * FROM users)
        SELECT * FROM base LEFT JOIN users_cte ON base.id = users_cte.id
        """
        ast = parse_sql(sql)
        cte_names = extract_cte_names(ast)
        violations = find_left_joins_on_ctes(ast, cte_names)
        assert 'users_cte' in violations

    def test_right_join_on_cte(self):
        """Test detecting RIGHT JOIN on CTE."""
        sql = """
        WITH users_cte AS (SELECT * FROM users)
        SELECT * FROM base RIGHT JOIN users_cte ON base.id = users_cte.id
        """
        ast = parse_sql(sql)
        cte_names = extract_cte_names(ast)
        violations = find_left_joins_on_ctes(ast, cte_names)
        assert 'users_cte' in violations

    def test_inner_join_on_cte_allowed(self):
        """Test that INNER JOIN on CTE is allowed."""
        sql = """
        WITH users_cte AS (SELECT * FROM users)
        SELECT * FROM base JOIN users_cte ON base.id = users_cte.id
        """
        ast = parse_sql(sql)
        cte_names = extract_cte_names(ast)
        violations = find_left_joins_on_ctes(ast, cte_names)
        assert len(violations) == 0

    def test_left_join_on_regular_table_allowed(self):
        """Test that LEFT JOIN on regular table (not CTE) is allowed."""
        sql = """
        WITH users_cte AS (SELECT * FROM users)
        SELECT * FROM users_cte LEFT JOIN tickets ON users_cte.id = tickets.user_id
        """
        ast = parse_sql(sql)
        cte_names = extract_cte_names(ast)
        violations = find_left_joins_on_ctes(ast, cte_names)
        assert len(violations) == 0

    def test_multiple_left_joins_on_ctes(self):
        """Test detecting multiple LEFT JOINs on CTEs."""
        sql = """
        WITH cte1 AS (SELECT * FROM t1),
             cte2 AS (SELECT * FROM t2)
        SELECT *
        FROM base
        LEFT JOIN cte1 ON base.id = cte1.id
        LEFT JOIN cte2 ON base.id = cte2.id
        """
        ast = parse_sql(sql)
        cte_names = extract_cte_names(ast)
        violations = find_left_joins_on_ctes(ast, cte_names)
        assert 'cte1' in violations
        assert 'cte2' in violations

    def test_no_joins(self):
        """Test query with CTEs but no JOINs."""
        sql = """
        WITH users_cte AS (SELECT * FROM users)
        SELECT * FROM users_cte
        """
        ast = parse_sql(sql)
        cte_names = extract_cte_names(ast)
        violations = find_left_joins_on_ctes(ast, cte_names)
        assert len(violations) == 0


class TestExtractTableNamesForConsistencyCheck:
    """Tests for extract_table_names_for_consistency_check function."""

    def test_simple_query(self):
        """Test extracting table names from simple query."""
        sql = "SELECT * FROM users"
        ast = parse_sql(sql)
        tables = extract_table_names_for_consistency_check(ast)
        assert 'users' in tables

    def test_query_with_cte(self):
        """Test that CTEs are excluded from table names."""
        sql = """
        WITH cte AS (SELECT * FROM devrev.users)
        SELECT * FROM cte JOIN devrev.tickets
        """
        ast = parse_sql(sql)
        tables = extract_table_names_for_consistency_check(ast)
        assert 'users' in tables
        assert 'tickets' in tables
        assert 'cte' not in tables

    def test_schema_qualified_tables(self):
        """Test that schema qualifiers are removed."""
        sql = "SELECT * FROM devrev.users JOIN system.logs"
        ast = parse_sql(sql)
        tables = extract_table_names_for_consistency_check(ast)
        assert 'users' in tables
        assert 'logs' in tables

    def test_nested_ctes(self):
        """Test that nested CTEs are excluded."""
        sql = """
        WITH outer_cte AS (
            WITH inner_cte AS (SELECT * FROM base_table)
            SELECT * FROM inner_cte
        )
        SELECT * FROM outer_cte JOIN real_table
        """
        ast = parse_sql(sql)
        tables = extract_table_names_for_consistency_check(ast)
        assert 'base_table' in tables
        assert 'real_table' in tables
        assert 'outer_cte' not in tables
        assert 'inner_cte' not in tables


class TestEdgeCases:
    """Tests for edge cases and complex scenarios."""

    def test_complex_query_with_all_features(self):
        """Test a complex query with CTEs, joins, subqueries, etc."""
        sql = """
        WITH user_stats AS (
            SELECT user_id, COUNT(*) as count
            FROM devrev.events
            WHERE created_date > '2024-01-01'
            GROUP BY user_id
        ),
        active_users AS (
            SELECT * FROM user_stats WHERE count > 10
        )
        SELECT
            u.name,
            s.count,
            t.title
        FROM devrev.users u
        LEFT JOIN active_users s ON u.id = s.user_id
        INNER JOIN devrev.tickets t ON u.id = t.owner_id
        WHERE u.active = true
        """
        ast = parse_sql(sql)

        # Test CTE extraction
        cte_names = extract_cte_names(ast)
        assert cte_names == {'user_stats', 'active_users'}

        # Test table extraction
        tables = extract_table_names_for_consistency_check(ast)
        assert 'users' in tables
        assert 'tickets' in tables
        assert 'events' in tables
        assert 'user_stats' not in tables
        assert 'active_users' not in tables

        # Test LEFT JOIN detection
        violations = find_left_joins_on_ctes(ast, cte_names)
        assert 'active_users' in violations

    def test_case_sensitivity(self):
        """Test that CTE names preserve case."""
        sql = """
        WITH UserStats AS (SELECT 1)
        SELECT * FROM UserStats
        """
        ast = parse_sql(sql)
        cte_names = extract_cte_names(ast)
        assert 'UserStats' in cte_names

    def test_sql_with_comments_and_strings(self):
        """Test that comments and strings don't interfere with parsing."""
        sql = """
        -- This is a comment with WITH fake_cte AS
        WITH real_cte AS (
            SELECT 'WITH another_fake_cte AS' as fake_sql
            FROM devrev.users
            /* Multi-line comment
               WITH yet_another_fake AS
            */
        )
        SELECT * FROM real_cte
        """
        ast = parse_sql(sql)
        cte_names = extract_cte_names(ast)
        assert cte_names == {'real_cte'}

        tables = extract_table_names_for_consistency_check(ast)
        assert 'users' in tables
        assert 'fake_cte' not in tables
        assert 'another_fake_cte' not in tables

    def test_empty_cte_set(self):
        """Test functions with empty CTE set."""
        sql = "SELECT * FROM users LEFT JOIN tickets"
        ast = parse_sql(sql)
        cte_names = extract_cte_names(ast)
        violations = find_left_joins_on_ctes(ast, cte_names)
        assert len(violations) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
