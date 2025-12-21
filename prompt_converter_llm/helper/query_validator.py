from sqlglot import parse_one, exp

def is_query_Safe(sql_query: str) -> (bool, str):
    """
    Parses a SQL query and checks it against a set of security rules.
    """
    
    # 1. Sanitize input
    if not sql_query:
        return (False, "Query is Empty")
        
    clean_query = sql_query.strip().strip('"')
    
    # decode unicode escape if necessary, but be careful with standard strings
    try:
        clean_query = clean_query.encode().decode('unicode_escape')
    except Exception:
        pass # If decoding fails, continue with original string

    # 2. Parse Query
    try:
        # parsed_expression = parse_one(clean_query, read="databricks") 
        # Recommended: specify 'read' dialect if known (e.g., 'databricks', 'spark')
        parsed_expression = parse_one(clean_query)
    except Exception as e:
        return (False, f"Invalid or multi-statement SQL: {str(e)}")

    # Rule 1: Only allow specific statement types
    # Added exp.With because your LLM generates CTEs (WITH clauses)
    allowed_types = (exp.Select, exp.Union, exp.Intersect, exp.Except, exp.With)

    if not isinstance(parsed_expression, allowed_types):
        return (False, f"Query is not an allowed read-only operation. Type: {type(parsed_expression)}")

    # Rule 2: Deny specific risky functions 
    for node in parsed_expression.find_all(exp.Func):
        
        # --- FIX START ---
        # 1. Use sql_name() to get the function name (e.g. "SUM", "COUNT")
        # 2. node.this is often None for 0-argument functions, causing your crash.
        func_name = node.sql_name()
        
        # Fallback for anonymous functions where name might be in 'this'
        if not func_name and isinstance(node, exp.Anonymous):
             func_name = node.this if isinstance(node.this, str) else ""
             
        if not func_name:
            continue
            
        func_name = func_name.upper()
        # --- FIX END ---

        if func_name in ('FILEOPEN', 'CREATE_FUNCTION', 'FS', 'HDFS_TOOLS'): 
             return (False, f"Query contains risky function: {func_name}")

    return (True, "OK")