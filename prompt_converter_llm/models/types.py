from pydantic import BaseModel
from typing import List, Optional

class Db_Define(BaseModel):
    Database:str
    
class Db_Schema(BaseModel):
    catalog:str
    
class TableList(BaseModel):
    catalog:str
    schema:str
    
class Table(BaseModel):
    catalog:str
    schema:str
    table_name:str
    
class Sql_Query(BaseModel):
    query_statement:str
    
    
class Llm_query(BaseModel):
    db_selection:str
    user_input:str
    selected_tables: List[dict]
    
class TableSearchResults(BaseModel):
    catalog: str
    schema: str
    table: str
    comment: Optional[str] = None

class CsvReportRequests(BaseModel):
    data:List[dict]
    filename:Optional[str] = "report.csv"