import uuid
import time
from datetime import datetime, timezone

async def req_creation():
    return {
    "req_id":str(uuid.uuid4()),
    "start_time":datetime.now(timezone.utc).isoformat(),
    "start_perf":time.perf_counter()
    }

async def req_closure(req_instance):
    st_time = req_instance.get("start_perf")
    end_time = time.perf_counter()
    return {
        "req_id":req_instance.get('req_id'),
        "start_time":req_instance.get('start_time'),
        "processed_time":datetime.now(timezone.utc).isoformat(),
        "duration_ms":round((end_time - st_time)*1000,3)
    }