import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from helper.helper import (
    build_schema_context, 
    generate_sql_from_llm, 
    execute_llm_query
)

# ==========================================
# 1. SETUP: MOCKS
# ==========================================
@pytest.fixture
def mock_db():
    db = MagicMock()
    # Important: These are async methods, so we use AsyncMock equivalent logic
    db.execute_query = MagicMock()
    db.fetch_results = MagicMock()
    return db

@pytest.fixture
def mock_llm():
    """Mocks the LLM Client"""
    llm = MagicMock()
    # This is an async method in your class, so use AsyncMock
    llm.gemini_flash_2_5 = AsyncMock()
    return llm

@pytest.fixture
def mock_val():
    """Mocks the Validation Class"""
    val = MagicMock()
    val.join_data = MagicMock()
    return val

# ==========================================
# 2. TEST: build_schema_context
# ==========================================
@pytest.mark.asyncio
async def test_build_schema_context_success(mock_db, mock_val):
    # INPUT
    selected_tables = [{'catalog': 'main', 'schema': 'sales', 'table': 'orders'}]
    
    # MOCK BEHAVIOR
    # 1. DB returns raw data
    mock_db.fetch_results.return_value = "raw_data" 
    # 2. Validator formats it into a list of dicts
    mock_val.join_data.return_value = {
        'result': [{
            'catalog_name': 'main', 'schema_name': 'sales', 'table_name': 'orders',
            'table_comment': 'Sales table', 'column_name': 'id', 'data_type': 'int', 'column_comment': None
        }]
    }

    # EXECUTE
    result = await build_schema_context(selected_tables, mock_db, mock_val)

    # ASSERT
    assert "-- Table: main.sales.orders" in result
    assert "-- Description: Sales table" in result
    assert "id (int)" in result

@pytest.mark.asyncio
async def test_build_schema_context_no_tables(mock_db, mock_val):
    # Test if it correctly raises 400 when list is empty
    with pytest.raises(HTTPException) as exc:
        await build_schema_context([], mock_db, mock_val)
    assert exc.value.status_code == 400

# ==========================================
# 3. TEST: generate_sql_from_llm (Regex Logic)
# ==========================================
@pytest.mark.asyncio
async def test_generate_sql_markdown_parsing(mock_llm):
    # Scenario: LLM returns text with markdown code blocks
    mock_llm.gemini_flash_2_5.return_value = """
    Here is your query:
    ```sql
    SELECT * FROM orders
    ```
    Hope it helps!
    """
    
    sql = await generate_sql_from_llm("db", "show orders", "context", mock_llm)
    
    assert sql == "SELECT * FROM orders"

@pytest.mark.asyncio
async def test_generate_sql_raw_text(mock_llm):
    # Scenario: LLM returns just the raw SQL without markdown
    mock_llm.gemini_flash_2_5.return_value = "SELECT * FROM orders"
    
    sql = await generate_sql_from_llm("db", "show orders", "context", mock_llm)
    
    assert sql == "SELECT * FROM orders"

# ==========================================
# 4. TEST: execute_llm_query (Error Handling)
# ==========================================
@pytest.mark.asyncio
async def test_execute_llm_query_failure(mock_db, mock_val):
    # Scenario: Databricks fails to run the query
    mock_db.execute_query.side_effect = Exception("Databricks is down")
    
    response = await execute_llm_query("SELECT *", mock_db, mock_val)
    
    # Your code catches the error and returns a JSONResponse
    assert response.status_code == 400
    
    # We have to parse the body to check content because it's a JSONResponse object
    import json
    body = json.loads(response.body)
    assert body['status'] == "Error"
    assert "Databricks is down" in body['detail']