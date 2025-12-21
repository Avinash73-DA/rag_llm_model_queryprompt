from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GEMINI_2_0_API_KEY:str
    DATABRICKS_KEY:str
    DATABRICKS_WAREHOUSE_KEY:str
    DATABRICKS_DOMAIN:str
    MONGO_URL:str
    MONGO_USER:str
    MONGO_PASSWORD:str
    
    class Config:
        env_file = Path(__file__).resolve().parent.parent / ".env"
        
settings = Settings()