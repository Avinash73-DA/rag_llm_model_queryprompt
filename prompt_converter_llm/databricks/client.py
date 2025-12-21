import requests
import logging as log
import time

class Databricks:
    def __init__(self, d_key, warehouse_key,db_domain):
        self.d_key = d_key
        self.warehouse_key = warehouse_key
        self.domain = db_domain
        
    def headers(self):
        return {
            "Authorization": f"Bearer {self.d_key}",
            "Content-Type": "application/json"
        }
        
    def execute_query(self,query_statement:str) -> dict:
        url = f"https://{self.domain}/api/2.0/sql/statements"
        tries, max_tries = 1, 5
        
        payload = {
            "statement": query_statement,
            "warehouse_id": self.warehouse_key,
            "wait_timeout": "0s" 
        }
        
        while tries <= max_tries:
            try:
                response = requests.post(url, headers=self.headers(), json=payload, timeout=30)
                
                if response.status_code == 200:
                    log.info("Databricks query submitted successfully.")
                    return response.json()  
                else:
                    log.error(f"Error on Attempt {tries}: {response.status_code} --> {response.text}")

            except requests.exceptions.RequestException as e:
                log.error(f"Request failed on Attempt {tries}: {e}")
            
            time.sleep(2 ** tries)
            tries += 1

        log.error(f"Failed to submit query after {max_tries} attempts.")
        return None

    def fetch_results(self, data:dict) -> dict:
        if not data or not data.get('statement_id'):
            log.error("Invalid data provided to fetch_results, no statement_id found.")
            return None
            
        url = f"https://{self.domain}/api/2.0/sql/statements/{data.get('statement_id')}"
        tries, max_tries = 1, 10
        
        while tries <= max_tries:
            try:
                response = requests.get(url, headers=self.headers(), timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    state = result.get('status', {}).get('state')

                    if state == "SUCCEEDED":
                        log.info("Query succeeded. Fetching results.")
                        return result 
                    
                    elif state in ("FAILED", "CANCELED", "CLOSED"):
                        log.error(f"Query failed with state: {state}. Response: {result['status']['error'].get('message')}")
                        return result
                    
                    elif state in ("PENDING", "RUNNING"):
                        log.info(f"Query is still {state}. Waiting... (Attempt {tries})")
                    
                    else:
                        log.warning(f"Received unknown state: {state}")

                else:
                    log.error(f"Error on Attempt {tries}: {response.status_code} --> {response.text}")

            except requests.exceptions.RequestException as e:
                log.error(f"Request failed on Attempt {tries}: {e}")

            time.sleep(min(30, 2 ** tries))
            tries += 1
        
        log.warning(f"Maximum retries ({max_tries}) reached while polling for results.")
        return None 
            
    def insert_file(self,file_name,data_bytes):
        url = f"https://{self.domain}/api/2.0/fs/files/{file_name}"
        tries = 0
        
        while tries < 5:
            try:
                response = requests.put(url,headers=self.headers(),data=data_bytes)
                
                if response.status_code in [200,204]:
                    log.info(f"Data Loaded Databricks Path: {file_name}")
                    return response

                else:
                    log.error(f"Failed to insert file. Status code: {response.status_code}, Response: {response.content}")
                    tries += 1
                    time.sleep(5)
            except Exception as e:
                log.error(f"Error Occurred: {e}")
                tries += 1
                time.sleep(5)
                
        print("Max retries reached. File upload failed.")
        return None
    
    def get_catalogs(self):
        url = f"https://{self.domain}/api/2.1/unity-catalog/catalogs"
        
        all_catalogs = []
        page_token = None

        while True:
            
            catalogs_params = {
                "max_results": 0 
            }
            if page_token:
                catalogs_params['page_token'] = page_token

            tries, max_tries = 1, 5
            response = None 
            
            while tries <= max_tries:
                try:
                    response = requests.get(url, headers=self.headers(), params=catalogs_params)
                    
                    if response.status_code == 200:
                        log.info(f"Database Connection Established for Catalog")
                        break 
                    else:
                        log.error(f"Error on Attempt {tries}: {response.status_code} --> {response.content}")
                        tries += 1
                        time.sleep(2 ** tries)
                        
                except Exception as e:
                        log.error(f"Error on Attempt {tries}: {e}")
                        tries += 1
                        time.sleep(2 ** tries)
  
            if response and response.status_code == 200:
                data = response.json()
                
                all_catalogs.extend(data.get('catalogs', []))
                
                page_token = data.get('next_page_token')
                
                if not page_token:
                    return all_catalogs
            else:
                log.warning(f"Maximum Retries Reached: {max_tries} while fetching a page.")
                return None
            
    def get_schema(self,catalog):
            url = f"https://{self.domain}/api/2.1/unity-catalog/schemas"
            
            all_schema = []
            page_token = None

            while True:
                
                schema_params = {
                    "catalog_name":catalog,
                    "max_results": 0 
                }
                
                if page_token:
                    schema_params['page_token'] = page_token

                tries, max_tries = 1, 5
                response = None 
                
                while tries <= max_tries:
                    try:
                        response = requests.get(url, headers=self.headers(), params=schema_params)
                        
                        if response.status_code == 200:
                            log.info(f"Database Connection Established for Schema")
                            break 
                        else:
                            log.error(f"Error on Attempt {tries}: {response.status_code} --> {response.content}")
                            tries += 1
                            time.sleep(2 ** tries)
                            
                    except Exception as e:
                            log.error(f"Error on Attempt {tries}: {e}")
                            tries += 1
                            time.sleep(2 ** tries)
    
                if response and response.status_code == 200:
                    data = response.json()
                    
                    all_schema.extend(data.get('schemas', []))
                    
                    page_token = data.get('next_page_token')
                    
                    if not page_token:
                        return all_schema
                else:
                    log.warning(f"Maximum Retries Reached: {max_tries} while fetching a page.")
                    return None
                
                
    def get_listtables(self,catalog,schema):
            url = f"https://{self.domain}/api/2.1/unity-catalog/tables"
            
            all_table = []
            page_token = None

            while True:
                
                table_params = {
                    "catalog_name":catalog,
                    "schema_name":schema,
                    "max_results": 0 
                }
                
                if page_token:
                    table_params['page_token'] = page_token

                tries, max_tries = 1, 5
                response = None 
                
                while tries <= max_tries:
                    try:
                        response = requests.get(url, headers=self.headers(), params=table_params)
                        
                        if response.status_code == 200:
                            log.info(f"Database Connection Established for Tables")
                            break 
                        else:
                            log.error(f"Error on Attempt {tries}: {response.status_code} --> {response.content}")
                            tries += 1
                            time.sleep(2 ** tries)
                            
                    except Exception as e:
                            log.error(f"Error on Attempt {tries}: {e}")
                            tries += 1
                            time.sleep(2 ** tries)
    
                if response and response.status_code == 200:
                    data = response.json()
                    
                    all_table.extend(data.get('tables', []))
                    
                    page_token = data.get('next_page_token')
                    
                    if not page_token:
                        return all_table
                else:
                    log.warning(f"Maximum Retries Reached: {max_tries} while fetching a page.")
                    return None
                
                
    def get_table(self,catalog,schema,table_name):
        full_name = f"{catalog}.{schema}.{table_name}"
        
        url = f"https://{self.domain}///api/2.1/unity-catalog/tables/{full_name}"
        
        tries,max_tries=1,5
        
        while tries <= max_tries:
            try:
                response = requests.get(url,headers=self.headers())
                
                if response.status_code == 200:
                    log.info(f"Database Connection Established for {table_name}")
                    return response.json()
                else:
                    log.error(f"Error on Attempt {tries}: {response.status_code} --> {response.content}")
                    tries += 1
                    time.sleep(2 ** tries)
                    
            except Exception as e:
                log.error(f"Error on Attempt {tries}: {e}")
                tries += 1
                time.sleep(2 ** tries)
                
        log.critical(f"All {max_tries} attempts to fetch schema for {full_name} failed.")
        return None