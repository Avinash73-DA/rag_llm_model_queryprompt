##SQL Queries ##
META_DATA_QUERY = """SELECT * FROM cta_project.utils.db_metadata_snapshot"""

SEARCH_TABLES_QUERY = """
SELECT DISTINCT
    catalog_name AS catalog,
    schema_name AS schema,
    table_name AS table,
    table_comment AS comment
FROM cta_project.utils.db_metadata_snapshot
WHERE
    lower(table_name) LIKE lower('{search}')
    OR lower(table_comment) LIKE lower('{search}')
LIMIT 20
"""

SCHEMA_META_QUERY = """
SELECT
    catalog_name,
    schema_name,
    table_name,
    column_name,
    data_type,
    column_comment,
    table_comment
FROM cta_project.utils.db_metadata_snapshot
WHERE {where_clause}
ORDER BY catalog_name, schema_name, table_name, ordinal_position
"""

EXPLAIN_EXTENDED_QUERY = "EXPLAIN EXTENDED {sql_query}"

### Logging Success & Failure ##
SECURITY_FAILURE = "SecurityCheckFailed"

### LLM PROMPT ###

SQL_GENERATION_PROMPT = """
Generate me a {db_selection} SQL query to {user_input}.

Table schema and information:
{table_info}

INSTRUCTIONS:
- Infer the schema strictly based on the provided metadata.
- IMPORTANT: Only output the raw SQL query inside markdown code blocks.
- Do not include any explanation.
"""

SQL_RETRY_PROMPT = """
You are an expert SQL generator and debugger. The target SQL dialect is {db_selection}.
The user's request (goal) is: {user_input}.

Table schema and metadata:
{table_info}

You previously generated this SQL which failed when executed:
{previous_sql}

The database returned this error message:
{error_message}

Task:
1. Analyze the error message and the previously generated SQL.
2. Fix the root cause (syntax, wrong column, type mismatch, etc.).

IMPORTANT OUTPUT RULES:
- ONLY output the raw SQL query text inside markdown code blocks (```sql ... ```).
"""

SQL_OPTIMIZATION_PROMPT = """
You are an expert {db_selection} SQL Performance Tuner.

YOUR GOAL: Optimize the SQL query below based on the provided Spark/SQL Execution Plan.

CONTEXT:
User Goal: {user_input}
Table Schema: {table_info}

CURRENT SQL:
{sql_query}

EXECUTION PLAN:
{explain_plan_text}

INSTRUCTIONS:
1. Analyze the execution plan for bottlenecks.
2. If already optimal, return the query exactly as-is.
3. Otherwise, rewrite with improvements.

IMPORTANT:
- Output ONLY raw SQL
- No explanations
- No markdown
"""

### REGEX CODE BLOCK ###
SQL_CODE_BLOCK_REGEX = r"```sql\n?(.*?)```"
