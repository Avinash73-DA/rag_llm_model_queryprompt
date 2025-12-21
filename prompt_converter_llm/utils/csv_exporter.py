import csv
from io import StringIO

def csv_downloader(data: list[dict]) -> StringIO:
    output = StringIO()
    
    if not data:
        raise ValueError("No data to export")
    
    ## Defining the header for the csv file
    fieldname = data[0].keys()
    
    writer = csv.DictWriter(output,fieldnames=fieldname)
    writer.writeheader()
    writer.writerows(data)
    
    output.seek(0)
    
    return output