import datetime
import asyncio
import logging as log
from fastapi import Request
from typing import Any, Dict, Optional

from mongo_client.mongo_db import Mongo_Db

def get_Safe_headers(request:Request) -> dict:
    """Creates a serializable dict of headers, filtering sensitive ones."""
    
    headers_to_log = {}
    for k,v in request.headers.items():
        if k.lower() not in ['authorization', 'cookie', 'x-api-key']:
            headers_to_log[k] = v
    return headers_to_log

async def log_api_call(
    mongo:Mongo_Db,
    request:Request,
    status_code:int,
    status:str,
    **kwargs):
    """
    Centralized function to build and push API logs to MongoDB.
    """
    
    
    log_payload = {
        "status_code": status_code,
        "status": status,
        
        ## Request Info
        "request_info": {
            "method": request.method,
            "url": request.url.path,
            "client_ip": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "headers": get_Safe_headers(request)
        }
    }
    
    # Update payload with extra fields (user_prompt, sql, errors, etc.)
    log_payload.update(kwargs)
    
    try:
        await asyncio.to_thread(
            mongo.push,
            "application_queryGenerator",
            "api_logs_detailed",
            log_payload
        )
    except Exception as e:
        # Log to file if Mongo push fails, so you don't crash the request
        log.error(f"Failed to push log to MongoDB: {e}")
        
class APILogger:
    """
    Wrapper class to manage logging context for a single API request.
    Reduces repetition in the main application code.
    """
    
    def __init__(self,mongo:Mongo_Db, request:Request):
        self.mongo = mongo
        self.request = request
        self.context: Dict[str, Any] = {}
    
    def set_context(self,**kwargs):
        """
        Set variables that remain constant for the duration of this request.
        Example: user_prompt, database_selection.
        """
        self.context.update(kwargs)
        
    async def log(self,status_code: int, status: str, **kwargs):
        """
        Push a log entry merging the persistent context with specific event details.
        """
        # Combine the fixed context with the specific details of this log
        final_payload = {**self.context, **kwargs}
        
        if 'llm_generated_sql' in final_payload and final_payload['llm_generated_sql']:
            try:
                raw_sql = final_payload['llm_generated_sql']
                final_payload['llm_generated_sql'] = raw_sql.strip().strip('"').encode().decode('unicode_escape')
            except Exception:
                pass
        
        await log_api_call(
            mongo=self.mongo,
            request=self.request,
            status_code=status_code,
            status=status,
            **final_payload
        )