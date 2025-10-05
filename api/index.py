from http.server import BaseHTTPRequestHandler
import json
import os
import statistics
from collections import defaultdict

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

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Set CORS headers
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
        
        try:
            # Get request body
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            request_data = json.loads(body.decode('utf-8'))
            
            # Load and process data
            region_data = load_and_process_data()
            
            regions = request_data["regions"]
            threshold_ms = request_data["threshold_ms"]
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
            
            # Send response
            self.wfile.write(json.dumps(result).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {"error": str(e)}
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
    
    def do_OPTIONS(self):
        # Handle preflight CORS requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

def handler(request, response):
    """Vercel serverless function handler"""
    import urllib.parse
    
    # Set CORS headers
    response['statusCode'] = 200
    response['headers'] = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST',
        'Access-Control-Allow-Headers': '*'
    }
    
    try:
        if request['httpMethod'] == 'OPTIONS':
            response['body'] = ''
            return response
            
        if request['httpMethod'] != 'POST':
            response['statusCode'] = 405
            response['body'] = json.dumps({"error": "Method not allowed"})
            return response
        
        # Parse request body
        request_data = json.loads(request['body'])
        
        # Load and process data
        region_data = load_and_process_data()
        
        regions = request_data["regions"]
        threshold_ms = request_data["threshold_ms"]
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
        
        response['body'] = json.dumps(result)
        return response
        
    except Exception as e:
        response['statusCode'] = 500
        response['body'] = json.dumps({"error": str(e)})
        return response