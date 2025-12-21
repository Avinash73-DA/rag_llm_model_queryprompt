import pytest
from utils.validation import Validation

@pytest.fixture
def validator():
    return Validation()


### VALIDATION -- join_data() ###
def test_join_data_success(validator):
    input_data = {
        "statement_id": "01f0de27-2f0e-1f96-bcb8-3ddb450486a2",
        "status": {
            "state": "SUCCEEDED"
        },
        "manifest": {
            "format": "JSON_ARRAY",
            "schema": {
            "column_count": 10,
            "columns": [
                {
                "name": "catalog_name",
                "type_text": "STRING",
                "type_name": "STRING",
                "position": 0
                },
                {
                "name": "schema_name",
                "type_text": "STRING",
                "type_name": "STRING",
                "position": 1
                },
                {
                "name": "table_name",
                "type_text": "STRING",
                "type_name": "STRING",
                "position": 2
                },
                {
                "name": "column_name",
                "type_text": "STRING",
                "type_name": "STRING",
                "position": 3
                },
                {
                "name": "data_type",
                "type_text": "STRING",
                "type_name": "STRING",
                "position": 4
                },
                {
                "name": "ordinal_position",
                "type_text": "INT",
                "type_name": "INT",
                "position": 5
                },
                {
                "name": "is_nullable",
                "type_text": "STRING",
                "type_name": "STRING",
                "position": 6
                },
                {
                "name": "column_comment",
                "type_text": "STRING",
                "type_name": "STRING",
                "position": 7
                },
                {
                "name": "table_comment",
                "type_text": "STRING",
                "type_name": "STRING",
                "position": 8
                },
                {
                "name": "table_created_at",
                "type_text": "TIMESTAMP",
                "type_name": "TIMESTAMP",
                "position": 9
                }
            ]
            },
            "total_chunk_count": 1,
            "chunks": [
            {
                "chunk_index": 0,
                "row_offset": 0,
                "row_count": 1
            }
            ],
            "total_row_count": 1,
            "truncated": False
        },
        "result": {
            "chunk_index": 0,
            "row_offset": 0,
            "row_count": 1,
            "data_array": [
            [
                "cta_project",
                "dimensions",
                "cta_stations",
                "stop_id",
                "STRING",
                "0",
                "YES",
                None,
                None,
                "2025-07-22T19:55:12.879Z"
            ]
            ]
        }
        }
    
    response = validator.join_data(input_data)
    
    ## Test Pass Cases
    assert response['status'] == 'SUCCESS'
    assert len(response['result']) == 1
    assert response['result'][0] == {'catalog_name': 'cta_project','schema_name': 'dimensions','table_name': 'cta_stations','column_name': 'stop_id','data_type': 'STRING','ordinal_position': '0','is_nullable': 'YES','column_comment': None,'table_comment': None,'table_created_at': '2025-07-22T19:55:12.879Z'}
    
def test_join_data_failure_on_notablefound(validator):
    input_data = {
        "statement_id": "01f0de2a-f499-1204-bab2-7fb852b6fbc0",
            "status": {
                "state": "FAILED",
                "error": {
                "error_code": "BAD_REQUEST",
                "message": "[TABLE_OR_VIEW_NOT_FOUND] The table or view `cta_project`.`util`.`db_metadata_snapshot` cannot be found. Verify the spelling and correctness of the schema and catalog.\nIf you did not qualify the name with a schema, verify the current_schema() output, or qualify the name with the correct schema and catalog.\nTo tolerate the error on drop use DROP VIEW IF EXISTS or DROP TABLE IF EXISTS. SQLSTATE: 42P01; line 1 pos 14"
                },
                "sql_state": "42P01"
            }
        }
    
    response = validator.join_data(input_data)
    
    ## Test Pass Cases
    assert response['status'] == 'ERROR'
    assert response['result'] == '[TABLE_OR_VIEW_NOT_FOUND] The table or view `cta_project`.`util`.`db_metadata_snapshot` cannot be found. Verify the spelling and correctness of the schema and catalog.\nIf you did not qualify the name with a schema, verify the current_schema() output, or qualify the name with the correct schema and catalog.\nTo tolerate the error on drop use DROP VIEW IF EXISTS or DROP TABLE IF EXISTS. SQLSTATE: 42P01; line 1 pos 14'


###### -------- #######


## validation - explain_query_parser ##
def test_explain_query_on_success(validator):
    input_data = {
        "statement_id": "01f0de2d-cc2d-12c8-b009-83b6a135d0ef",
        "status": {
                "state": "SUCCEEDED"
            },
            "manifest": {
                "format": "JSON_ARRAY",
                "schema": {
                "column_count": 1,
                "columns": [
                    {
                    "name": "plan",
                    "type_text": "STRING",
                    "type_name": "STRING",
                    "position": 0
                    }
                ]
                },
                "total_chunk_count": 1,
                "chunks": [
                {
                    "chunk_index": 0,
                    "row_offset": 0,
                    "row_count": 1
                }
                ],
                "total_row_count": 1,
                "truncated": False
            },
            "result": {
                "chunk_index": 0,
                "row_offset": 0,
                "row_count": 1,
                "data_array": [
                [
                    "== Physical Plan ==\nCollectLimit 1\n+- ColumnarToRow\n   +- PhotonResultStage\n      +- PhotonScan parquet cta_project.utils.db_metadata_snapshot[catalog_name#13037,schema_name#13038,table_name#13039,column_name#13040,data_type#13041,ordinal_position#13042,is_nullable#13043,column_comment#13044,table_comment#13045,table_created_at#13046] DataFilters: [], DictionaryFilters: [], Format: parquet, Location: PreparedDeltaFileIndex(1 paths)[s3://dbstorage-prod-rnqrb/uc/096e61b3-8511-4da1-a921-3f757ca7b5e9..., OptionalDataFilters: [], PartitionFilters: [], ReadSchema: struct<catalog_name:string,schema_name:string,table_name:string,column_name:string,data_type:stri..., RequiredDataFilters: []\n\n\n== Photon Explanation ==\nPhoton does not fully support the query because:\n\t\tUnsupported node: CollectLimit 1.\n\nReference node:\n\tCollectLimit 1\n\n== Optimizer Statistics (table names per statistics state) ==\n  missing = \n  partial = \n  full    = db_metadata_snapshot\n"
                ]
                ]
            }
        }
    
    response = validator.explain_query_parser(input_data)
    
    ## Tests Checks ##
    assert response['status'] == 'SUCCESS'
    
    # We compare the string directly, not a list or dictionary.
    expected_string = input_data['result']['data_array'][0][0]
    assert response['result'] == expected_string
    
def test_explain_query_on_failure(validator):
    input_data ={
        "statement_id": "01f0de2f-e643-1b0c-b586-5a93b48dbae7",
        "status": {
            "state": "SUCCEEDED"
            },
            "manifest": {
                "format": "JSON_ARRAY",
                "schema": {
                "column_count": 1,
                "columns": [
                    {
                    "name": "plan",
                    "type_text": "STRING",
                    "type_name": "STRING",
                    "position": 0
                    }
                ]
                },
                "total_chunk_count": 1,
                "chunks": [
                {
                    "chunk_index": 0,
                    "row_offset": 0,
                    "row_count": 8
                }
                ],
                "total_row_count": 8,
                "truncated": False
            },
            "result": {
                "chunk_index": 0,
                "row_offset": 0,
                "row_count": 8,
                "data_array": [
                [
                    "Error occurred during query planning: "
                ],
                [
                    "[TABLE_OR_VIEW_NOT_FOUND] The table or view `cta_project`.`util`.`db_metadata_snapshot` cannot be found. Verify the spelling and correctness of the schema and catalog."
                ],
                [
                    "If you did not qualify the name with a schema, verify the current_schema() output, or qualify the name with the correct schema and catalog."
                ],
                [
                    "To tolerate the error on drop use DROP VIEW IF EXISTS or DROP TABLE IF EXISTS. SQLSTATE: 42P01; line 1 pos 22;"
                ],
                [
                    "'GlobalLimit 1"
                ],
                [
                    "+- 'LocalLimit 1"
                ],
                [
                    "   +- 'Project [*]"
                ],
                [
                    "      +- 'UnresolvedRelation [cta_project, util, db_metadata_snapshot], [], false"
                ]
                ]
            }
        }
    
    response = validator.explain_query_parser(input_data)
    
    ## Tests Checks ##
    assert response['status'] == 'SUCCESS'
    assert response['result'] == "Error occurred during query planning: "