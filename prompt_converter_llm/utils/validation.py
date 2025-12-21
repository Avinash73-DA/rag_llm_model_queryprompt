import re
import pandas as pd
from collections import defaultdict

class Validation():
    def __init__(self):
        pass
    
    def join_data(self,data:dict) -> dict | str:
        """
        This Function used for parsing the Databricks Output into Structured format
        """
        if not data:
            # Gracefully handle missing responses
            return {'status': 'ERROR', 'result': 'No data returned from query execution'}

        if data['status'].get('state') == 'SUCCEEDED':
            manifest = data.get('manifest')
            result = data.get('result')
            
            if not result or not result.get('data_array'):
                # Query succeeded but returned no rows
                return {'status': 'SUCCESS', 'result': []}
            
            columns = [col['name'] for col in manifest['schema']['columns']]
            rows = result['data_array']
            
            ## Joining the Headers and Row Values
            SUCCEEDED_OUTPUT = {
                'status':'SUCCESS',
                'result':[dict(zip(columns,row)) for row in rows]
            }
            
            return SUCCEEDED_OUTPUT
        
        elif data['status'].get('state') == 'FAILED':
            ERROR_OUTPUT = {'status':'ERROR',
                            'result':data['status']['error'].get('message')}
            
            return ERROR_OUTPUT
        
    def explain_query_parser(self,data:dict) -> str:
        """
        Used to parse the SQL Resutls from Databricks for Expalin Extended
        """
        if data['status'].get('state') == 'SUCCEEDED':
            PARSED_INFO = data.get('result')['data_array'][0][0]
  
            SUCCEEDED_OUTPUT = {'status':'SUCCESS',
                                    'result':PARSED_INFO}
            
            return SUCCEEDED_OUTPUT
        
        elif data['status'].get('state') == 'FAILED':
            ERROR_OUTPUT = {'status':'ERROR',
                            'result':data['status']['error'].get('message')}
            
            return ERROR_OUTPUT
        
        
    def normalize_slack_output(self,raw_text,name):
        
        # Remove code block markers and trim whitespace
        text = raw_text.strip().replace("```", "")
        
        # Force correct header
        text = re.sub(r"^.*Summary of.*$", 
                    f"Hi @{name} Summary of W34 catchup (Q3 2025)", 
                    text, 
                    flags=re.MULTILINE)
        
        # Standardize section headings
        text = re.sub(r"\*?1\..*Renewal.*", "*1. Accounts coming in for Renewal this Q3*", text)
        text = re.sub(r"\*?2\..*HubSpot.*", "*2. HubSpot pipeline for the quarter*", text)
        text = re.sub(r"\*?3\..*NDR.*", "*3. NDR*", text)
        text = re.sub(r"\*?4\..*GDR.*", "*4. GDR*", text)
        text = re.sub(r"\*?5\..*Churn.*", "*5. Churned Accounts (Q3 2025)*", text)
        
        # Remove duplicate labels like "NDR: NDR: 5.11%"
        text = re.sub(r"(NDR:)\s*NDR:", "NDR:", text)
        text = re.sub(r"(GDR:)\s*GDR:", "GDR:", text)
        
        return text.strip()
    
    def df_coversion(self,df_raw,final):
        df_db = pd.DataFrame(final)
        df_raw = df_raw[['subscription_number','customer_name','mrr']]
        
        joined = pd.merge(
            df_db,
            df_raw,
            left_on='subscription_id',
            right_on='subscription_number',
            how='outer')
        
        ## Casting String to int
        joined['OB_MRR'] = pd.to_numeric(joined['OB_MRR'], errors='coerce')
        joined['mrr'] = pd.to_numeric(joined['mrr'], errors='coerce')

        ## Calculation
        joined['diff'] = abs(joined['OB_MRR'] - joined['mrr'])
        
        filtered_join = joined[(joined['diff'] > 1) | (joined['diff'].isna())]
        
        # filtered_join.head(60)

# Convert DataFrame to HTML
        html_table = filtered_join.to_html(index=False, na_rep='', justify='left')
    
    
        return html_table
    
    def parselist_tables_clean(self,data):
        table_columns = []

        for d in data:
            table_name = d['name']
            
            schema_list = []
            for fields in d.get('columns'):
                schema_list.append({
                    "field_name": fields.get('name',""),
                    "field_schema": fields.get('type_text',"")
                })

            table_columns.append(
                {
                    "table_name":table_name,
                    "schema":schema_list
                }
            )
        
        return table_columns
    
    def clean_catalog(self,data):
        """
        To Get the Names of Catalog Only
        """ 
        catalog_list = []
    
        for d in data:
            if d['name'] not in ("system","samples"):
                catalog_list.append(d.get('name',""))
            
        return catalog_list
        
    def table_names(self,data):
        table_list = []
        
        for t in data:
            infos = {
                "table_name":t['name'],
                "catalog_name":t['catalog_name'],
                "schema_name":t['schema_name']
            }
            table_list.append(infos)
        
        return table_list
    
    def cat_schema_structure(self,data):
        """
        To Get both Catalog and Schema Data in the Single Array
        """
        full_structure = []

        for schema in data:
            if schema.get('name',"") not in ("information_schema"):
                full_structure.append({
                    "catalog": schema.get('catalog_name',""),
                    "Schema": schema.get('name',"")
                })
                
        return full_structure
    
    def table_clean(self,data):
        catalog_name = data.get('catalog_name')
        schema_name = data.get('schema_name')
        table_name = data.get('name',"")
        columns_list = data.get('columns',"")
        description = data.get('comment',"")
            
        schema_list = []
        for field in columns_list:
            schema_list.append({
                "field_name": field.get('name', ""),
                "field_schema": field.get('type_text', "")
            })
            
        final_table = {
            "catalog_name":catalog_name,
            "schema_name":schema_name,
            "table_name":table_name,
            "Description":description,
            "columns":schema_list
        }

        return final_table
    
    def table_clean_v2(data):
        grouped_data = defaultdict(lambda:{
            'catalog_name':None,
            "schema_name":None,
            'table_name':None,
            "table_description":None,
            "columns":[]
        })

        for row in data:
            key = (row['catalog_name'], row['schema_name'], row['table_name'], row['table_comment'])
            grouped_entry = grouped_data[key]
            grouped_entry['catalog_name'] = row['catalog_name']
            grouped_entry['schema_name'] = row['schema_name']
            grouped_entry['table_name'] = row['table_name']
            grouped_entry['table_description'] = row['table_comment']
            grouped_entry['columns'].append({
                'column_name':row['column_name'],
                'data_type':row['data_type']
            })
            
        final_grouped_output = list(grouped_data.values())
        
        return final_grouped_output