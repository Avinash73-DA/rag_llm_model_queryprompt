import pytest
from io import StringIO
from utils.csv_exporter import csv_downloader 

# -------------------------------------------------------------------
# 1. TEST: Happy Path (Valid Data)
# -------------------------------------------------------------------
def test_csv_downloader_success():
    # Input Data
    data = [
        {"name": "Alice", "role": "Admin", "id": 101},
        {"name": "Bob", "role": "User", "id": 102}
    ]

    # Execute
    output_file = csv_downloader(data)

    # Convert the StringIO object back to a string to check content
    content = output_file.getvalue()
    
    # Assertions
    # 1. Check if headers exist
    assert "name,role,id" in content
    
    # 2. Check if data rows exist (Note: CSV adds newlines \r\n)
    assert "Alice,Admin,101" in content
    assert "Bob,User,102" in content

    # 3. Check exact formatting (Optional but stricter)
    # Use strip() to ignore trailing newlines if you don't care about them
    expected_csv = "name,role,id\r\nAlice,Admin,101\r\nBob,User,102\r\n"
    # Note: csv module defaults to \r\n on many systems, sometimes just \n. 
    # Normalizing newlines is safer:
    assert content.replace('\r\n', '\n') == expected_csv.replace('\r\n', '\n')

# -------------------------------------------------------------------
# 2. TEST: Error Handling (Empty Data)
# -------------------------------------------------------------------
def test_csv_downloader_empty_list():
    empty_data = []

    # We expect a ValueError with the message "No data to export"
    with pytest.raises(ValueError, match="No data to export"):
        csv_downloader(empty_data)

# -------------------------------------------------------------------
# 3. TEST: Edge Case (Single Row)
# -------------------------------------------------------------------
def test_csv_downloader_single_row():
    data = [{"col1": "val1"}]
    
    output_file = csv_downloader(data)
    content = output_file.getvalue().strip() # .strip() removes the last newline
    
    assert content == "col1\r\nval1" or content == "col1\nval1"