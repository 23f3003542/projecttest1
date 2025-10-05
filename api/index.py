from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import statistics
from typing import List
from collections import defaultdict
from mangum import Mangum

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

class MetricsRequest(BaseModel):
    regions: List[str]
    threshold_ms: int

def load_and_process_data():
    """Load data and group by region"""
    data_file = os.path.join(os.path.dirname(__file__), "data.json")
    try:
        with open(data_file, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        # Fallback for local development
        data_file = os.path.join(os.path.dirname(__file__), "..", "q-vercel-latency.json")
        with open(data_file, "r") as f:
            data = json.load(f)
    
    # Group data by region
    region_data = defaultdict(lambda: {"latencies": [], "uptimes": []})
    for record in data:
        region_data[record["region"]]["latencies"].append(record["latency_ms"])
        region_data[record["region"]]["uptimes"].append(record["uptime_pct"])
    
    return region_data

@app.post("/")
async def get_metrics(request: MetricsRequest):
    region_data = load_and_process_data()
    regions = request.regions
    threshold_ms = request.threshold_ms
    result = {}
    for region in regions:
        if region not in region_data:
            continue
        latencies = region_data[region]["latencies"]
        uptimes = region_data[region]["uptimes"]
        avg_latency = statistics.mean(latencies)
        # Calculate p95
        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)
        p95_index = int(0.95 * (n - 1))
        p95_latency = sorted_latencies[p95_index]
        avg_uptime = statistics.mean(uptimes)
        breaches = sum(1 for l in latencies if l > threshold_ms)
        result[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 2),
            "breaches": breaches
        }
    return result

handler = Mangum(app)