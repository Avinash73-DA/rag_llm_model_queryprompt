import sys
import asyncio
import logging as log
from typing import List
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

## Custom Modules ##
from llm_model.client import LLM_Client
from databricks.client import Databricks
from utils.validation import Validation
from mongo_client.mongo_db import Mongo_Db
from utils.csv_exporter import csv_downloader
from helper.query_validator import is_query_Safe
from mongo_client.logging_utils import APILogger
from helper.helper import build_schema_context,generate_sql_from_llm,execute_llm_query, OptimiseQuery_llm_model

## Pydantic Module ##
from models.types import Db_Define,Sql_Query,Llm_query,TableSearchResults,CsvReportRequests

## Crediential Module ##
from core.Config import settings

## Constants ## 
from constants.constants import (
    META_DATA_QUERY,
    SEARCH_TABLES_QUERY,
    SECURITY_FAILURE
)

## Logging Configuration ##
log.basicConfig(
    level=log.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        log.FileHandler("app.log"),
        log.StreamHandler() 
    ]
)

log = log.getLogger(__name__)

## Creating an Instance of an Object

d_key=settings.DATABRICKS_KEY
warehouse_key=settings.DATABRICKS_WAREHOUSE_KEY
db_domain=settings.DATABRICKS_DOMAIN
gemini_key=settings.GEMINI_2_0_API_KEY
mongo_url=settings.MONGO_URL
mongo_user=settings.MONGO_USER
mongo_password=settings.MONGO_PASSWORD

required_vars = [d_key, warehouse_key, db_domain, gemini_key, mongo_url]
if any(v is None for v in required_vars):
    log.error("Missing one or more required Environmental Variables")
    sys.exit(1)
    
## Creating Instance for Databricks Class ##
db = Databricks(
    d_key=d_key,
    warehouse_key=warehouse_key,
    db_domain=db_domain
)

## Creating Instance for Validation Class ##
val = Validation()

## Creating Instance for LLM Model Class ##
llm = LLM_Client(gemini_key=gemini_key)

## Creating Instance for Mongo DB Class ##
mongo = Mongo_Db(
    user=mongo_user,
    password=mongo_password,
    mongo_url=mongo_url,
)

## Creating Instance for FastAPI Class ##
app = FastAPI()

# CORS configuration so the HTML frontend (served from a different origin) can call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for local testing; narrow this down in production
    allow_credentials=True,
    allow_methods=["*"],  # includes GET, POST, OPTIONS, etc.
    allow_headers=["*"],
)

# Frontend path
frontend_path = Path(__file__).parent / "frontend"

## Centralized Exception Handling 
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handles HTTPExceptions that are intentionally raised (e.g., 404, 400).
    We just log them and return the response.
    """
    log.error(f"HTTPException for {request.url.path}: {exc.detail}")
    return JSONResponse (
        status_code=exc.status_code,
        content={"detail":exc.detail}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handles any *unexpected* exception (e.g., ValueError, TypeError, DB errors).
    We log the full traceback and return a generic 500 error.
    This prevents leaking sensitive error details to the client.
    """
    log.error(f"Unexpected error for {request.url.path}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )

### API END POINTS ###
@app.get("/v1/query_engines")
def query_engine():
    return {
        "Database Engine": ["Databricks", "Athena", "Redshift"]
    }

@app.post("/v1/db_definement")
async def database_definement(data:Db_Define):
    user_dat = data.Database
    
    if user_dat.lower() not in ["databricks", "athena", "redshift"]:
        raise HTTPException(
                    status_code=400,
                    detail="Selection Error: Select Query Engine Accordingly --> [Databricks, Athena, Redshift]"
                )
    
    return f"{user_dat.lower()} Connection Establishing" 

@app.get("/v1/metadata")
async def metadata(request:Request):
    # Initialize Logger
    logger = APILogger(mongo,request)
    
    try:
        data = await asyncio.to_thread(db.execute_query,query_statement=META_DATA_QUERY)
        output = await asyncio.to_thread(db.fetch_results,data)
        final_output = await asyncio.to_thread(val.join_data,output)
        
        await logger.log(200,"SUCCESS",detail="Request for Metadata")
        
        return final_output
    
    except Exception as e:
        await logger.log(400,"ERROR",detail=str(e),error_type=type(e).__name__)
        raise e

@app.get("/v1/search_tables",response_model=List[TableSearchResults])
async def search_tables(table:str,request:Request):
    logger = APILogger(mongo,request)
    
    if not table:
        raise HTTPException(status_code=400,detail="Searche query 'table' is required")
    
    query_statement = SEARCH_TABLES_QUERY.format(
        # Surround with wildcards so partial matches (anywhere in the name/comment) are found
        search=f"%{table}%"
    )
    
    log.info(f"Executing metadata search query")
    
    try:
        data = await asyncio.to_thread(db.execute_query,query_statement=query_statement)
        output = await asyncio.to_thread(db.fetch_results,data)
        final_output = await asyncio.to_thread(val.join_data,output)
        
        await logger.log(200,"SUCCESS",parameter_used=f"/table={table}",results_count=len(final_output.get('result', [])))
        return final_output['result']
    
    except Exception as e:
        log.critical(f"An unhandled error occurred in /v1/metadata: {e}", exc_info=True)
        await logger.log(500,"ERROR",detail=str(e),error_type=type(e).__name__)
        raise e
    
        
@app.post('/v1/sql_query')
async def sql_query(query_attribute:Sql_Query):
  
    data = await asyncio.to_thread (db.execute_query,query_attribute.query_statement)
    output = await asyncio.to_thread (db.fetch_results,data)
    final_output = await asyncio.to_thread (val.join_data,output)
    
    return final_output

## LLM Model Route API
@app.post('/v1/llm')
async def llm_query_engine(inputs: Llm_query,request:Request):
    
    logger = APILogger(mongo, request)
    
    # Set Context (Applied to all future logs in this request)
    logger.set_context(
        selected_database=inputs.db_selection,
        user_prompt=inputs.user_input
    )
    sql_query = None
    table_info_context = None
    
    try:
        # Step 1: Build the schema context
        table_info_context = await build_schema_context(inputs.selected_tables, db=db,  val=val)
        
        # Step 2: Call the LLM to get the SQL
        UNOP_sql_query = await generate_sql_from_llm(inputs.db_selection, inputs.user_input, table_info_context, llm=llm,retry=False)

        # Validating the Query
        is_safe,reason = await asyncio.to_thread(is_query_Safe,sql_query=UNOP_sql_query) 

        
        if not is_safe:
            await logger.log(
                400, "Error", 
                error_type=SECURITY_FAILURE, 
                detail=f"Generated SQL failed security check: {reason}",
                llm_generated_sql=UNOP_sql_query
            )
            raise HTTPException(status_code=400, detail=reason)
           
        await logger.log(200, "Success - UNOPTIMISED QUERY", llm_generated_sql=UNOP_sql_query, results_count=0)
        
        ## -- STEP:3 QUERY OPTIMIZATION -- ##
        sql_query = await OptimiseQuery_llm_model(inputs.db_selection, inputs.user_input, table_info_context, llm=llm, db=db, val=val, sql_query=UNOP_sql_query)
        
        is_safe,reason = await asyncio.to_thread(is_query_Safe,sql_query=sql_query) 
        
        if not is_safe:
            await logger.log(
                400, "Error", 
                error_type=SECURITY_FAILURE, 
                detail=f"Generated SQL failed security check: {reason}",
                llm_generated_sql=sql_query
            )
            raise HTTPException(status_code=400, detail=reason)
        
        await logger.log(200, "Success - OPTIMISED QUERY", llm_generated_sql=sql_query, results_count=0)
        
        # -- Step 4: Execute the generated SQL -- ##
        final_output = await execute_llm_query(sql_query, db=db, val=val)
    
        ## --- RETRY LOGIC START --- ##
        if final_output.get('status') == 'ERROR':
            log.info(f"Initial Query Failed: {final_output.get('result')}. Attempting Retry.")
            
            # Log the failure attempt
            await logger.log(
                400, "Error - Retry Pushed",
                Error_Type=str(final_output.get('result')),
                llm_generated_sql=sql_query
            )
            
            # Generate Correction
            UNOP_sql_query_2 = await generate_sql_from_llm(inputs.db_selection, inputs.user_input, table_info_context,llm=llm,previous_sql=sql_query,error_message=final_output['result'],retry=True)
            
            is_safe,reason = await asyncio.to_thread(is_query_Safe,sql_query=UNOP_sql_query_2)
            
            if not is_safe:
                await logger.log(
                    400, "Error - Retry", 
                    error_type=SECURITY_FAILURE, 
                    detail=f"Generated SQL failed security check: {reason}",
                    llm_generated_sql=UNOP_sql_query_2
                )
                raise HTTPException(status_code=400, detail=f"Retry Query Unsafe: {reason}")
            
            ## -- Retry: QUERY OPTIMIZATION -- ##
            sql_query_2 = await OptimiseQuery_llm_model(inputs.db_selection, inputs.user_input, table_info_context, llm=llm, db=db, val=val, sql_query=UNOP_sql_query_2)
            
            is_safe,reason = await asyncio.to_thread(is_query_Safe,sql_query=sql_query_2) 
            
            if not is_safe:
                await logger.log(
                    400, "Error", 
                    error_type=SECURITY_FAILURE, 
                    detail=f"Generated SQL failed security check: {reason}",
                    llm_generated_sql=sql_query_2
                )
                raise HTTPException(status_code=400, detail=reason)
                
            # Execute 2nd Query
            final_output = await execute_llm_query(sql_query_2, db=db, val=val)
            
            # Tracking Update for Logs
            sql_query = sql_query_2
            
            if final_output.get('status') == "ERROR":
                await logger.log(
                    400, "Error Retry - Query Execution Failed", 
                    llm_generated_sql=sql_query
                )
                
                return JSONResponse(
                    status_code=400, 
                    content={
                        "status": "Error", 
                        "message": "Query failed after retry", 
                        "detail": final_output.get('result'),
                        "llm_generated_sql": sql_query
                    }
                )
                        
        ## --- RETRY LOGIC END --- ##
        
        if final_output is None:
            await logger.log(200, "Success", llm_generated_sql=sql_query, results_count=0)
            return JSONResponse(content={
                "status": "No Results", 
                "result": [],
                "llm_generated_sql": sql_query
            })
            
        results_list = final_output.get('result', []) if final_output else []
        row_count = len(results_list)
        
        await logger.log(200, "Success", llm_generated_sql=sql_query, results_count=row_count)
        
        # Include SQL in the response for frontend display
        response_data = final_output.copy() if final_output else {}
        response_data['llm_generated_sql'] = sql_query
        
        return response_data
    
    except Exception as e:
        # Catch any other unexpected errors
        log.critical(f"An unhandled error occurred in /v1/llm: {e}", exc_info=True)
        
        await logger.log(
            500, "Error", 
            error_type=type(e).__name__, 
            detail=str(e),
            llm_generated_sql=sql_query
        )
        raise e
@app.post("/v1/csv_report")
async def csv_report(request_data:CsvReportRequests, request:Request):
    """
    Generate and download a CSV report from the provided data.
    
    Args:
        request_data: Contains 'data' (list of dicts) and optional 'filename'
        request: FastAPI Request object for logging
    
    Returns:
        StreamingResponse with CSV file
    """
    logger = APILogger(mongo,request)

    try:
        # Validate that data is provided
        if not request_data.data:
            await logger.log(400, "ERROR", detail="No data provided for CSV export")
            raise HTTPException(status_code=400, detail="No data provided for CSV export")

        # Generate CSV using the csv_downloader function
        csv_output = await asyncio.to_thread(csv_downloader, request_data.data)
        
        # Set filename with default if not provided
        filename = request_data.filename or "report.csv"
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        # Get CSV content as string from StringIO object
        csv_content = csv_output.getvalue()
        
        # Log successful CSV generation
        await logger.log(
            200, 
            "SUCCESS", 
            detail=f"CSV report generated: {filename}",
            results_count=len(request_data.data)
        )

        # Return CSV as streaming response with proper headers for download
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except ValueError as e:
        # Handle empty data error from csv_downloader
        await logger.log(400, "ERROR", detail=str(e), error_type=type(e).__name__)
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        log.critical(f"An unhandled error occurred in /v1/csv_report: {e}", exc_info=True)
        await logger.log(500, "ERROR", detail=str(e), error_type=type(e).__name__)
        raise e

@app.get("/v1/healthz")
def healthz():
    return {
        "status":"OK"
    }

# Frontend serving routes (must be after all API routes)
# Serve index.html at root
@app.get("/")
async def read_root():
    """Serve the frontend HTML file"""
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    raise HTTPException(status_code=404, detail="Frontend files not found")

# Serve frontend static files (CSS, JS) - only known frontend files
@app.get("/{filename}")
async def serve_frontend(filename: str):
    """Serve frontend files (CSS, JS) - excludes API routes"""
    # Don't serve anything that looks like an API route
    if filename.startswith("v1") or filename.startswith("api"):
        raise HTTPException(status_code=404, detail="Not found")
    
    # Only serve known frontend file types
    if not (filename.endswith(".css") or filename.endswith(".js") or filename.endswith(".html")):
        raise HTTPException(status_code=404, detail="Not found")
    
    file_path = frontend_path / filename
    if file_path.exists() and file_path.is_file() and file_path.suffix in [".css", ".js", ".html"]:
        # Determine content type
        content_type = "text/html"
        if filename.endswith(".css"):
            content_type = "text/css"
        elif filename.endswith(".js"):
            content_type = "application/javascript"
        return FileResponse(str(file_path), media_type=content_type)
    raise HTTPException(status_code=404, detail="File not found")