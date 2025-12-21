import re
import asyncio
import logging
import datetime
from fastapi import HTTPException
from fastapi.responses import JSONResponse

## CUSTOM MODULES
from llm_model.client import LLM_Client
from databricks.client import Databricks
from utils.validation import Validation

from constants.constants import (
    SCHEMA_META_QUERY,
    SQL_GENERATION_PROMPT,
    SQL_RETRY_PROMPT,
    SECURITY_FAILURE,
    SQL_CODE_BLOCK_REGEX,
    EXPLAIN_EXTENDED_QUERY,
    SQL_OPTIMIZATION_PROMPT
)

log = logging.getLogger(__name__)


async def build_schema_context(
    selected_tables: list, 
    db: Databricks,        
    val: Validation        
) -> str:
    """
    Builds the schema context string from the selected tables.
    Handles all database logic for fetching metadata.
    """
    if not selected_tables:
        raise HTTPException(status_code=400, detail="No tables selected for LLM query.")

    where_clause = []
    for table_names in selected_tables:
        try:
            catalog = table_names.get('catalog')
            schema = table_names.get('schema')
            table = table_names.get('table')
            
            if not all([catalog, schema, table]):
                log.warning(f"Skipping malformed table entry: {table_names}")
                continue
                
            where_clause.append(
                f"(catalog_name = '{catalog}' "
                f"AND schema_name = '{schema}' "
                f"AND table_name = '{table}')"
            )
        
        except Exception as e:
            log.warning(f"Error processing table name: {table_names}. Error: {e }")
            continue

    if not where_clause:
        raise HTTPException(status_code=400, detail="Invalid table names provided. Must be in 'catalog.schema.table' format.")

    schema_query = SCHEMA_META_QUERY.format(
        where_clause=" OR ".join(where_clause)
    )
    
    try:
        # Use the passed-in 'db' and 'val' objects
        schema_data_raw = await asyncio.to_thread(db.execute_query, schema_query)
        schema_output = await asyncio.to_thread(db.fetch_results, schema_data_raw)
        schema_rows = await asyncio.to_thread(val.join_data, schema_output) 
    except Exception as e:
        log.error(f"Failed to fetch schema from Databricks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch database schema. Error: {e}")
            
    table_info_context = ""
    current_table = ""  

    for row in schema_rows['result']:
        full_name = f"{row.get('catalog_name')}.{row.get('schema_name')}.{row.get('table_name')}"
        
        if full_name != current_table:
            table_info_context += f"\n-- Table: {full_name}\n"
            current_table = full_name
            table_comment = row.get('table_comment')
            table_info_context += f"-- Description: {table_comment or 'Null'}\n"

        col_comment = f"({row.get('column_comment')})" if row.get('column_comment') else ""
        table_info_context += f"--  {row.get('column_name')} ({row.get('data_type')}) {col_comment}\n"

    return table_info_context

async def generate_sql_from_llm(
    db_selection: str, 
    user_input: str, 
    table_info: str,
    llm: LLM_Client,
    previous_sql=None,
    error_message=None,
    retry=False 
) -> str:
    """
    Calls the LLM to generate the SQL query and sanitizes the output.
    """
    # Choose the appropriate prompt template based on whether this is a retry call
    prompt_template = SQL_RETRY_PROMPT if retry else SQL_GENERATION_PROMPT
    prompt = prompt_template.format(
        db_selection=db_selection,
        user_input=user_input,
        table_info=table_info,
        previous_sql=previous_sql,
        error_message=error_message
    )

    # ---  REGEX EXTRACTION (Same as Optimizer) ---
    sql_query = None
    llm_query_output = None

    try:
        llm_query_output = await llm.gemini_flash_2_5(prompt=prompt)
        
        if llm_query_output and isinstance(llm_query_output, str):
            # Regex to extract content between ```sql and ``` tags
            sql_match = re.search(
                SQL_CODE_BLOCK_REGEX,
                llm_query_output or "",
                re.DOTALL | re.IGNORECASE
            )
            
            if sql_match:
                sql_query = sql_match.group(1).strip()
            else:
                # Fallback: Clean up raw string
                cleaned_output = llm_query_output.replace("```sql", "").replace("```", "").strip()
                # Basic check to see if it looks like SQL
                if "select" in cleaned_output.lower() or "with" in cleaned_output.lower():
                    sql_query = cleaned_output
        
        if not sql_query:
            log.warning(f"LLM returned invalid format: {llm_query_output}")
            raise HTTPException(status_code=500, detail="LLM failed to generate a valid SQL query.")

        return sql_query
        
    except Exception as e:
        log.error(f"LLM call failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"LLM generation failed. Error: {e}")

async def OptimiseQuery_llm_model(
    db_selection: str, 
    user_input: str, 
    table_info: str,
    llm: LLM_Client,
    db: Databricks,        
    val: Validation,   
    sql_query: str) -> str:
    """
    Executes an EXPLAIN plan, analyzes it via LLM, and returns an optimized query 
    (or the original if no optimization is needed).
    """
    start_time = datetime.datetime.now(datetime.timezone.utc)
    
    EXPLAIN_QUERY = EXPLAIN_EXTENDED_QUERY.format(sql_query=sql_query)
    
    ## -- Connects with Databricks for Query Plan -- ##
    try:
        data = await asyncio.to_thread (
            db.execute_query,
            query_statement=EXPLAIN_QUERY
        )
        output = await asyncio.to_thread (
            db.fetch_results,
            data
        )
        
        ## Holds the Query Plan
        explain_plan_text = await asyncio.to_thread (
            val.explain_query_parser,
            output
        )
        
    except (ValueError, Exception) as e:
        log.error(f"LLM-generated SQL query failed!")
        log.error(f"Failing Query: {sql_query}")
        log.error(f"Exception: {e}", exc_info=True)
        return JSONResponse (
            status_code=400,
            content={
                "status_code": 400,
                "status": "Error",
                "error_type": SECURITY_FAILURE,
                "detail": f"Error executing LLM-generated SQL. Query: '{sql_query}'. Error: {str(e)}",
                "llm_generated_sql": sql_query.strip().strip('"').encode().decode('unicode_escape'),
                "processed_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "duration_ms": (datetime.datetime.now(datetime.timezone.utc) - start_time).total_seconds() * 1000,
                "results": [],
            }
        )
        
    ## -- LLM Model for Inference and Optimization -- ##
    prompt = SQL_OPTIMIZATION_PROMPT.format(
        db_selection=db_selection,
        user_input=user_input,
        table_info=table_info,
        sql_query=sql_query,
        explain_plan_text=explain_plan_text
    )

    try:
        log.info("Query Optimization Triggered")
        # Call LLM for Query Optimization
        llm_query_output = await llm.gemini_flash_2_5(prompt=prompt)
        # log.info(f"Raw LLM Output: {llm_query_output}")
        
        # 2. Safety Check: Ensure output is actually a string
        if llm_query_output and isinstance(llm_query_output, str):
            
            # 3. Strategy A: Use Regex to find text specifically inside ```sql ... ```
            # This handles cases where the LLM talks before/after the code.
            sql_match = re.search(
                SQL_CODE_BLOCK_REGEX,
                llm_query_output or "",
                re.DOTALL | re.IGNORECASE
            )
            
            if sql_match:
                # Found a code block, extract just the content
                sql_query = sql_match.group(1).strip()
            else:
                # 4. Strategy B: Fallback (No markdown tags found)
                # Clean up the raw string just in case
                cleaned_output = llm_query_output.replace("```sql", "").replace("```", "").strip()
                
                # specific check to ensure we didn't just get a conversational apology
                if "select" in cleaned_output.lower() or "with" in cleaned_output.lower():
                    sql_query = cleaned_output
                else:
                    log.warning("LLM output does not look like SQL.")
        
    except Exception as e:
        log.error(f"LLM Internal Processing Failed: {e}")
        # We catch the error, but sql_query remains None
    
    # 5. Final Validation
    if not sql_query:
        log.warning(f"Failed to extract valid SQL. Raw output was: {llm_query_output}")
        # Return specific error so your Agentic Retry logic knows it wasn't a DB error, but a Generation error
        raise HTTPException(status_code=500, detail="LLM failed to generate a valid SQL format.")

    return sql_query

async def execute_llm_query(
    sql_query: str,
    db: Databricks,        
    val: Validation         
) -> list:
    """
    Executes the LLM-generated SQL query against Databricks.
    """
    start_time = datetime.datetime.now(datetime.timezone.utc)
    
    try:
        data = await asyncio.to_thread (
            db.execute_query,
            query_statement=sql_query
        )
        output = await asyncio.to_thread (
            db.fetch_results,
            data
        )
        final_output = await asyncio.to_thread (
            val.join_data,
            output
        )
        return final_output
        
    except (ValueError, Exception) as e:
        log.error(f"LLM-generated SQL query failed!")
        log.error(f"Failing Query: {sql_query}")
        log.error(f"Exception: {e}", exc_info=True)
        return JSONResponse (
            status_code=400,
            content={
                "status_code": 400,
                "status": "Error",
                "error_type": SECURITY_FAILURE,
                "detail": f"Error executing LLM-generated SQL. Query: '{sql_query}'. Error: {str(e)}",
                "llm_generated_sql": sql_query.strip().strip('"').encode().decode('unicode_escape'),
                "processed_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "duration_ms": (datetime.datetime.now(datetime.timezone.utc) - start_time).total_seconds() * 1000,
                "results": [],
            }
        )
        # raise HTTPException(
        #     status_code=400,
        #     detail=f"Error executing LLM-generated SQL. Query: '{sql_query}'. Error: {str(e)}"
        # )