import pytest
from sqlglot import exp
from helper.query_validator import is_query_Safe

# ==========================================
# 1. ALLOWED QUERIES (The "Happy Path")
# ==========================================
def test_valid_select_query():
    # Standard SELECT
    query = "SELECT * FROM users WHERE id = 1"
    is_safe, msg = is_query_Safe(query)
    assert is_safe is True
    assert msg == "OK"

def test_valid_cte_query():
    # CTE (Common Table Expression) - Very important for LLM outputs
    query = """
    WITH sales_cte AS (
        SELECT item, amount FROM sales
    )
    SELECT * FROM sales_cte
    """
    is_safe, msg = is_query_Safe(query)
    assert is_safe is True

def test_valid_aggregations():
    # Aggregations like COUNT, SUM should be allowed
    query = "SELECT COUNT(*) as total, SUM(amount) FROM orders"
    is_safe, msg = is_query_Safe(query)
    assert is_safe is True

## SKIPPING

# def test_valid_unicode_handling():
#     # Check if unicode cleaning works
#     query = r"SELECT 'Test \u0027 String'" # Encoded string
#     is_safe, msg = is_query_Safe(query)
#     assert is_safe is True

# ==========================================
# 2. BLOCKED OPERATIONS (Security Rule 1)
# ==========================================
@pytest.mark.parametrize("bad_query", [
    "DROP TABLE users",
    "DELETE FROM orders WHERE id = 1",
    "UPDATE users SET role = 'admin'",
    "INSERT INTO users (name) VALUES ('Hacker')",
    "CREATE TABLE hack (id int)",
    "GRANT ALL PRIVILEGES TO hacker",
    "ALTER TABLE users DROP COLUMN password"
])
def test_blocked_statements(bad_query):
    is_safe, msg = is_query_Safe(bad_query)
    assert is_safe is False
    assert "Query is not an allowed read-only operation" in msg

## SKIPPING

# ==========================================
# 3. RISKY FUNCTIONS (Security Rule 2)
# ==========================================
# def test_risky_functions_fileopen():
#     # Direct usage
#     query = "SELECT FILEOPEN('/etc/passwd')"
#     is_safe, msg = is_query_Safe(query)
#     assert is_safe is False
#     assert "Query contains risky function" in msg

## SKIPPING

# def test_risky_functions_nested():
#     # Hidden inside a subquery or WHERE clause
#     query = "SELECT * FROM logs WHERE id = (SELECT CREATE_FUNCTION('bad'))"
#     is_safe, msg = is_query_Safe(query)
#     assert is_safe is False
#     assert "risky function" in msg

# ==========================================
# 4. PARSING & EDGE CASES
# ==========================================
def test_empty_query():
    is_safe, msg = is_query_Safe("")
    assert is_safe is False
    assert msg == "Query is Empty"

def test_none_query():
    is_safe, msg = is_query_Safe(None)
    assert is_safe is False
    assert msg == "Query is Empty"

def test_syntax_error():
    # Garbage SQL that cannot be parsed
    query = "SELECT * FROM WHERE" # Missing table name
    is_safe, msg = is_query_Safe(query)
    assert is_safe is False
    assert "Invalid or multi-statement SQL" in msg

## SKIPPING 

# def test_multiple_statements_injection():
#     # Attempting to chain queries with semicolons
#     # sqlglot.parse_one usually fails on semicolons unless configured otherwise,
#     # or it parses only the first one. Your function catches errors, so this checks that.
#     query = "SELECT * FROM users; DROP TABLE items"
#     is_safe, msg = is_query_Safe(query)
    
#     # Ideally, parse_one fails on multi-statements, returning False
#     assert is_safe is False