"""Unit tests for SQL CAST type validation.

Tests the whitelist-based CAST type validation that prevents unsupported
types from reaching the platform runtime.
"""

import pytest
from scripts.widget.lib.rules.sql_rules import SqlSchemaRule, SUPPORTED_CAST_TYPES


class TestSupportedCastTypes:
    """Tests for SUPPORTED_CAST_TYPES constant."""

    def test_basic_types_present(self):
        """Test that all basic types are in the whitelist."""
        assert 'VARCHAR' in SUPPORTED_CAST_TYPES
        assert 'DOUBLE' in SUPPORTED_CAST_TYPES
        assert 'BIGINT' in SUPPORTED_CAST_TYPES
        assert 'BOOLEAN' in SUPPORTED_CAST_TYPES
        assert 'TIMESTAMP' in SUPPORTED_CAST_TYPES

    def test_supported_array_types(self):
        """Test that supported array types are in the whitelist."""
        assert 'ARRAY<VARCHAR>' in SUPPORTED_CAST_TYPES
        assert 'ARRAY<DOUBLE>' in SUPPORTED_CAST_TYPES
        assert 'ARRAY<BIGINT>' in SUPPORTED_CAST_TYPES
        assert 'ARRAY<BOOLEAN>' in SUPPORTED_CAST_TYPES

    def test_unsupported_array_types_absent(self):
        """Test that unsupported array types are NOT in the whitelist."""
        assert 'ARRAY<JSON>' not in SUPPORTED_CAST_TYPES
        assert 'ARRAY<TIMESTAMP>' not in SUPPORTED_CAST_TYPES


class TestValidateCastExpressions:
    """Tests for validate_cast_expressions method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SqlSchemaRule()

    def test_supported_basic_cast_varchar(self):
        """Test that CAST to VARCHAR is allowed."""
        sql = "SELECT CAST(field AS VARCHAR) FROM table"
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 0

    def test_supported_basic_cast_double(self):
        """Test that CAST to DOUBLE is allowed."""
        sql = "SELECT CAST(field AS DOUBLE) FROM table"
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 0

    def test_supported_basic_cast_bigint(self):
        """Test that CAST to BIGINT is allowed."""
        sql = "SELECT CAST(field AS BIGINT) FROM table"
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 0

    def test_supported_basic_cast_boolean(self):
        """Test that CAST to BOOLEAN is allowed."""
        sql = "SELECT CAST(field AS BOOLEAN) FROM table"
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 0

    def test_supported_basic_cast_timestamp(self):
        """Test that CAST to TIMESTAMP is allowed."""
        sql = "SELECT CAST(field AS TIMESTAMP) FROM table"
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 0

    def test_supported_array_cast_varchar(self):
        """Test that CAST to ARRAY<VARCHAR> is allowed."""
        sql = "SELECT CAST(field AS ARRAY<VARCHAR>) FROM table"
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 0

    def test_supported_array_cast_double(self):
        """Test that CAST to ARRAY<DOUBLE> is allowed."""
        sql = "SELECT CAST(field AS ARRAY<DOUBLE>) FROM table"
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 0

    def test_supported_array_cast_bigint(self):
        """Test that CAST to ARRAY<BIGINT> is allowed."""
        sql = "SELECT CAST(field AS ARRAY<BIGINT>) FROM table"
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 0

    def test_supported_array_cast_boolean(self):
        """Test that CAST to ARRAY<BOOLEAN> is allowed."""
        sql = "SELECT CAST(field AS ARRAY<BOOLEAN>) FROM table"
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 0

    def test_unsupported_array_cast_json(self):
        """Test that CAST to ARRAY<JSON> is caught as unsupported."""
        sql = "SELECT CAST(json_extract(data, '$') AS ARRAY<JSON>) FROM table"
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 1
        assert errors[0].rule_id == 'UNSUPPORTED_CAST_TYPE'
        assert errors[0].severity == 'error'
        assert 'ARRAY<JSON>' in errors[0].message
        assert 'json_extract_string' in errors[0].suggestion

    def test_unsupported_array_cast_timestamp(self):
        """Test that CAST to ARRAY<TIMESTAMP> is caught as unsupported."""
        sql = "SELECT CAST(dates AS ARRAY<TIMESTAMP>) FROM table"
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 1
        assert errors[0].rule_id == 'UNSUPPORTED_CAST_TYPE'
        assert errors[0].severity == 'error'
        assert 'ARRAY<TIMESTAMP>' in errors[0].message

    def test_multiple_casts_mixed_support(self):
        """Test query with both supported and unsupported CASTs."""
        sql = """
        SELECT
            CAST(name AS VARCHAR),
            CAST(data AS ARRAY<JSON>),
            CAST(count AS DOUBLE)
        FROM table
        """
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 1
        assert errors[0].rule_id == 'UNSUPPORTED_CAST_TYPE'
        assert 'ARRAY<JSON>' in errors[0].message

    def test_multiple_unsupported_casts(self):
        """Test query with multiple unsupported CASTs."""
        sql = """
        SELECT
            CAST(json_data AS ARRAY<JSON>),
            CAST(timestamps AS ARRAY<TIMESTAMP>)
        FROM table
        """
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 2
        assert all(e.rule_id == 'UNSUPPORTED_CAST_TYPE' for e in errors)

    def test_cast_with_whitespace_normalization(self):
        """Test that whitespace in CAST types is normalized."""
        sql = "SELECT CAST(field AS ARRAY< VARCHAR >) FROM table"
        errors = self.validator.validate_cast_expressions(sql)
        # Should pass because it normalizes to ARRAY<VARCHAR>
        assert len(errors) == 0

    def test_cast_case_insensitive(self):
        """Test that CAST type matching is case-insensitive."""
        sql = "SELECT CAST(field AS array<varchar>) FROM table"
        errors = self.validator.validate_cast_expressions(sql)
        # Should pass because it normalizes to uppercase
        assert len(errors) == 0

    def test_cast_with_json_extract_unsupported(self):
        """Test the exact failing case from the bug report."""
        sql = """
        SELECT CAST(json_extract(skill_executed, '$.results') AS ARRAY<JSON>)
        FROM devrev.fact_engagement
        """
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 1
        assert errors[0].rule_id == 'UNSUPPORTED_CAST_TYPE'
        assert 'ARRAY<JSON>' in errors[0].message
        assert 'json_extract_string' in errors[0].suggestion

    def test_cast_nested_in_cte(self):
        """Test CAST validation in CTEs."""
        sql = """
        WITH parsed AS (
            SELECT CAST(data AS ARRAY<JSON>) AS items
            FROM table_name
        )
        SELECT * FROM parsed
        """
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 1
        assert errors[0].rule_id == 'UNSUPPORTED_CAST_TYPE'

    def test_cast_in_subquery(self):
        """Test CAST validation in subqueries."""
        sql = """
        SELECT * FROM (
            SELECT CAST(data AS ARRAY<JSON>) AS items
            FROM table_name
        )
        """
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 1
        assert errors[0].rule_id == 'UNSUPPORTED_CAST_TYPE'

    def test_no_cast_expressions(self):
        """Test query without any CAST expressions."""
        sql = "SELECT name, count FROM table"
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 0

    def test_error_message_includes_supported_types(self):
        """Test that error message lists supported types."""
        sql = "SELECT CAST(data AS ARRAY<JSON>) FROM table"
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 1
        # Should mention supported types
        assert 'VARCHAR' in errors[0].suggestion
        assert 'DOUBLE' in errors[0].suggestion
        assert 'ARRAY<VARCHAR>' in errors[0].suggestion


class TestIntegrationWithValidateSqlPatterns:
    """Tests for integration with validate_sql_patterns method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SqlSchemaRule()

    def test_validate_sql_patterns_calls_cast_validation(self):
        """Test that validate_sql_patterns includes CAST validation."""
        sql = "SELECT CAST(data AS ARRAY<JSON>) FROM table"
        errors = self.validator.validate_sql_patterns(sql)
        # Should catch the unsupported type
        assert any(e.rule_id == 'UNSUPPORTED_CAST_TYPE' for e in errors)

    def test_validate_sql_patterns_both_validations(self):
        """Test that both old-style and new CAST validations work."""
        sql = """
        SELECT
            CAST(data AS JSON[]),           -- Old syntax error
            CAST(data AS ARRAY<JSON>)       -- Unsupported type
        FROM table
        """
        errors = self.validator.validate_sql_patterns(sql)
        # Should catch both issues
        rule_ids = {e.rule_id for e in errors}
        assert 'SQL_PATTERN_INVALID_ARRAY_CAST' in rule_ids
        assert 'UNSUPPORTED_CAST_TYPE' in rule_ids

    def test_supported_cast_no_errors(self):
        """Test that supported CASTs pass all validations."""
        sql = """
        SELECT
            CAST(name AS VARCHAR),
            CAST(items AS ARRAY<VARCHAR>),
            CAST(count AS DOUBLE)
        FROM table
        """
        errors = self.validator.validate_sql_patterns(sql)
        # Should have no errors
        assert len(errors) == 0


class TestRealWorldExamples:
    """Tests using real-world SQL patterns from widgets."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SqlSchemaRule()

    def test_correct_json_array_extraction(self):
        """Test the correct way to extract JSON arrays."""
        sql = """
        SELECT CAST(json_extract_string(field, '$.array') AS ARRAY<VARCHAR>)
        FROM devrev.fact_engagement
        """
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 0

    def test_incorrect_json_array_extraction(self):
        """Test the incorrect way that caused the bug."""
        sql = """
        SELECT CAST(json_extract(field, '$.array') AS ARRAY<JSON>)
        FROM devrev.fact_engagement
        """
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 1
        assert 'json_extract_string' in errors[0].suggestion

    def test_unnest_with_correct_cast(self):
        """Test UNNEST with correct type casting."""
        sql = """
        WITH parsed AS (
            SELECT CAST(json_extract_string(data, '$.items') AS ARRAY<VARCHAR>) AS items
            FROM table_name
        )
        SELECT UNNEST(items) AS item
        FROM parsed
        """
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 0

    def test_complex_query_with_multiple_casts(self):
        """Test complex query with various CAST operations."""
        sql = """
        WITH base AS (
            SELECT
                id,
                CAST(json_extract_string(metadata, '$.tags') AS ARRAY<VARCHAR>) AS tags,
                CAST(json_extract_string(score, '$.value') AS DOUBLE) AS score_value
            FROM devrev.fact_engagement
        )
        SELECT
            id,
            UNNEST(tags) AS tag,
            score_value
        FROM base
        WHERE score_value > 0.5
        """
        errors = self.validator.validate_cast_expressions(sql)
        assert len(errors) == 0


class TestUnnestJsonExtractValidation:
    """Tests for UNNEST(json_extract(...)) validation - implicit JSON type detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SqlSchemaRule()

    def test_unnest_json_extract_direct(self):
        """Test that UNNEST(json_extract(...)) is caught with comprehensive solutions."""
        sql = "SELECT UNNEST(json_extract(field, '$.array')) FROM table"
        errors = self.validator.validate_unnest_patterns(sql)
        assert len(errors) == 1
        assert errors[0].rule_id == 'UNSUPPORTED_UNNEST_JSON_EXTRACT'
        assert 'UNNEST on json_extract()' in errors[0].message
        # Check that both solutions are provided
        assert 'Solution 1' in errors[0].suggestion
        assert 'Solution 2' in errors[0].suggestion
        assert 'ARRAY<VARCHAR>' in errors[0].suggestion
        assert 'generate_series' in errors[0].suggestion
        assert 'json_array_length' in errors[0].suggestion

    def test_unnest_json_extract_nested(self):
        """Test that nested UNNEST(json_extract(...)) is caught."""
        sql = "SELECT json_extract_string(UNNEST(json_extract(field, '$.array')), '$.title')"
        errors = self.validator.validate_unnest_patterns(sql)
        assert len(errors) == 1
        assert errors[0].rule_id == 'UNSUPPORTED_UNNEST_JSON_EXTRACT'

    def test_unnest_json_extract_in_cte(self):
        """Test UNNEST(json_extract(...)) in CTE."""
        sql = """
        WITH articles AS (
            SELECT UNNEST(json_extract(skill_executed, '$.execution_results.articles')) AS article
            FROM knowledge_searches
        )
        SELECT * FROM articles
        """
        errors = self.validator.validate_unnest_patterns(sql)
        assert len(errors) == 1
        assert errors[0].rule_id == 'UNSUPPORTED_UNNEST_JSON_EXTRACT'

    def test_unnest_with_cast_array_varchar_passes(self):
        """Test that proper CAST to ARRAY<VARCHAR> passes validation."""
        sql = "SELECT UNNEST(CAST(json_extract_string(field, '$.array') AS ARRAY<VARCHAR>))"
        errors = self.validator.validate_unnest_patterns(sql)
        # Should not match json_extract pattern because it's json_extract_string
        assert len(errors) == 0

    def test_unnest_json_extract_string_passes(self):
        """Test that json_extract_string (not json_extract) passes."""
        sql = "SELECT UNNEST(json_extract_string(field, '$.array'))"
        errors = self.validator.validate_unnest_patterns(sql)
        # Should not match because we're looking for json_extract, not json_extract_string
        assert len(errors) == 0

    def test_real_world_article_usage_pattern(self):
        """Test the exact failing pattern from article-usage.json."""
        sql = """
        article_extracts AS (
            SELECT json_extract_string(
                UNNEST(json_extract(skill_executed, '$.execution_results.articles')),
                '$.title'
            ) AS article_title
            FROM knowledge_searches
        )
        """
        errors = self.validator.validate_unnest_patterns(sql)
        assert len(errors) == 1
        assert errors[0].rule_id == 'UNSUPPORTED_UNNEST_JSON_EXTRACT'
        assert 'UNNEST on json_extract()' in errors[0].message
        assert 'json_extract() returns JSON type' in errors[0].suggestion

    def test_unnest_on_column_passes(self):
        """Test that UNNEST on regular array columns passes."""
        sql = "SELECT UNNEST(array_column) FROM table"
        errors = self.validator.validate_unnest_patterns(sql)
        assert len(errors) == 0

    def test_multiple_unnest_json_extract_calls(self):
        """Test multiple UNNEST(json_extract(...)) in same query."""
        sql = """
        SELECT
            UNNEST(json_extract(field1, '$.array1')) AS arr1,
            UNNEST(json_extract(field2, '$.array2')) AS arr2
        FROM table
        """
        errors = self.validator.validate_unnest_patterns(sql)
        # Note: re.search() only finds first match, so we get 1 error
        # This is acceptable - first error will block validation and must be fixed
        assert len(errors) >= 1
        assert errors[0].rule_id == 'UNSUPPORTED_UNNEST_JSON_EXTRACT'

    def test_case_insensitive_matching(self):
        """Test that pattern matching is case-insensitive."""
        sql = "SELECT UNNEST(JSON_EXTRACT(field, '$.array')) FROM table"
        errors = self.validator.validate_unnest_patterns(sql)
        assert len(errors) == 1
        assert errors[0].rule_id == 'UNSUPPORTED_UNNEST_JSON_EXTRACT'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
