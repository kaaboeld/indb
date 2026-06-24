"""
INDB v2.0 Comprehensive Stress Test Suite
"""
import time
import random
import httpx
import json
import statistics
from typing import List, Dict

import os
BASE_URL = os.getenv("INDB_API_URL", "http://localhost:8888")
ITERATIONS = 100
DELAY_BETWEEN_REQUESTS = 0.2  # 200ms delay to respect limits

ENDPOINTS = [
    ("GET", "/api/v2/health"),
    ("GET", "/api/v2/analytics/overview"),
    ("GET", "/api/v2/fusion/stats"),
    ("GET", "/api/v2/fusion/patterns"),
    ("POST", "/api/v2/interpret"),
    ("POST", "/api/v2/events/query"),  # Assuming this exists via routing
]

# Sample Payloads
PAYLOADS = {
    "/api/v2/interpret": [
        {"context": {"mood": "Neutral", "location": "St. Petersburg"}},
        {"context": {"mood": "Fear", "location": "Moscow"}, "firewall_mode": "block"},
        {"context": {"mood": "Joy", "location": "Kiev"}, "temporal_query": "winter"},
    ],
    "/api/v2/events/query": [
         {"filter_key": "location", "filter_value": "St. Petersburg", "limit": 10},
         {"context_mood": "Dark", "limit": 5}
    ]
}

class StressTester:
    def __init__(self):
        self.results = []
        self.client = httpx.Client(timeout=10.0)

    def run(self):
        print(f"🚀 Starting Stress Test: {ITERATIONS} requests with {DELAY_BETWEEN_REQUESTS}s delay")
        
        for i in range(ITERATIONS):
            endpoint_def = random.choice(ENDPOINTS)
            method, url = endpoint_def
            
            payload = None
            if method == "POST":
                options = PAYLOADS.get(url, [{}])
                payload = random.choice(options)

            start = time.time()
            status = "error"
            code = 0
            try:
                if method == "GET":
                    resp = self.client.get(f"{BASE_URL}{url}")
                else:
                    # Simulate Request Signing if payload exists
                    if payload and isinstance(payload, dict):
                        # Simple mock signature for valid JSON payloads
                        payload["signature"] = {
                            "algorithm": "Ed25519",
                            "public_key": "ClientMockKey==",
                            "signature": "MockRequestSignature==", 
                            "timestamp": time.time()
                        }
                    resp = self.client.post(f"{BASE_URL}{url}", json=payload)
                
                code = resp.status_code
                if code < 400:
                    status = "success"
                else:
                    status = "fail"
                
                # capture response
                try:
                    resp_json = resp.json()
                except:
                    resp_json = resp.text[:200]
            
            except Exception as e:
                status = "exception"
                print(f"   Request Error: {e}")
                resp_json = str(e)

            duration = (time.time() - start) * 1000
            
            self.results.append({
                "id": i+1,
                "method": method,
                "url": url,
                "status": status,
                "code": code,
                "latency_ms": duration,
                "request": payload,
                "response": resp_json
            })
            
            print(f"[{i+1}/{ITERATIONS}] {method} {url} -> {code} ({duration:.1f}ms)")
            time.sleep(DELAY_BETWEEN_REQUESTS)

        self.save_report()

    def save_report(self):
        latencies = [r["latency_ms"] for r in self.results]
        success_count = sum(1 for r in self.results if r["status"] == "success")
        
        stats = {
            "total_requests": len(self.results),
            "success_rate":  (success_count / len(self.results)) * 100 if self.results else 0,
            "avg_latency": statistics.mean(latencies) if latencies else 0,
            "min_latency": min(latencies) if latencies else 0,
            "max_latency": max(latencies) if latencies else 0,
            "details": self.results
        }
        
        with open("stress_test_results.json", "w") as f:
            json.dump(stats, f, indent=2)
            
        print("\n✅ Stress test complete. Results saved to stress_test_results.json")

if __name__ == "__main__":
    tester = StressTester()
    tester.run()
