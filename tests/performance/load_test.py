"""
Load Testing for INDB
Benchmark 100k events/sec ingestion performance.
"""

import asyncio
import time
import httpx
from typing import List, Dict, Any
import statistics

BASE_URL = "http://localhost:8003"
TARGET_EVENTS = 100_000
CONCURRENT_REQUESTS = 100


async def send_event(client: httpx.AsyncClient, event_id: int) -> float:
    """
    Send single event and measure latency.
    
    Returns:
        Latency in milliseconds
    """
    start = time.time()
    
    try:
        response = await client.post(
            f"{BASE_URL}/api/v2/events",
            json={
                "data": {
                    "id": event_id,
                    "message": f"Load test event {event_id}",
                    "timestamp": time.time()
                }
            },
            timeout=10.0
        )
        
        latency = (time.time() - start) * 1000  # Convert to ms
        
        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text}")
            return -1
        
        return latency
        
    except Exception as e:
        print(f"Request failed: {e}")
        return -1


async def batch_send(client: httpx.AsyncClient, start_id: int, count: int) -> List[float]:
    """Send batch of events concurrently"""
    tasks = [send_event(client, start_id + i) for i in range(count)]
    return await asyncio.gather(*tasks)


async def run_load_test():
    """
    Main load test: 100k events with concurrent requests.
    """
    print("=" * 60)
    print("INDB Load Test - 100k Events/sec Target")
    print("=" * 60)
    print(f"Target: {TARGET_EVENTS:,} events")
    print(f"Concurrency: {CONCURRENT_REQUESTS}")
    print()
    
    latencies = []
    errors = 0
    
    async with httpx.AsyncClient() as client:
        # Warmup
        print("Warming up...")
        await send_event(client, -1)
        
        # Main test
        print("Starting load test...")
        start_time = time.time()
        
        # Send in batches
        batch_size = CONCURRENT_REQUESTS
        num_batches = TARGET_EVENTS // batch_size
        
        for batch_num in range(num_batches):
            batch_latencies = await batch_send(
                client,
                batch_num * batch_size,
                batch_size
            )
            
            # Track latencies
            for lat in batch_latencies:
                if lat > 0:
                    latencies.append(lat)
                else:
                    errors += 1
            
            # Progress
            if (batch_num + 1) % 10 == 0:
                progress = (batch_num + 1) / num_batches * 100
                print(f"Progress: {progress:.1f}% ({(batch_num + 1) * batch_size:,} events)")
        
        total_time = time.time() - start_time
    
    # Calculate metrics
    successful = len(latencies)
    throughput = successful / total_time
    
    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total Events: {TARGET_EVENTS:,}")
    print(f"Successful: {successful:,}")
    print(f"Errors: {errors}")
    print(f"Total Time: {total_time:.2f}s")
    print()
    print(f"Throughput: {throughput:,.0f} events/sec")
    print()
    print("Latency Statistics:")
    print(f"  Min: {min(latencies):.2f}ms")
    print(f"  Max: {max(latencies):.2f}ms")
    print(f"  Mean: {statistics.mean(latencies):.2f}ms")
    print(f"  Median: {statistics.median(latencies):.2f}ms")
    print(f"  P95: {statistics.quantiles(latencies, n=20)[18]:.2f}ms")
    print(f"  P99: {statistics.quantiles(latencies, n=100)[98]:.2f}ms")
    print()
    
    # Verdict
    if throughput >= 100_000:
        print("✅ SUCCESS: Target 100k events/sec achieved!")
    elif throughput >= 50_000:
        print("⚠️  PARTIAL: 50k+ events/sec (good, but below target)")
    else:
        print("❌ FAILED: Below 50k events/sec")
    
    print("=" * 60)
    
    return {
        "throughput": throughput,
        "latency_mean": statistics.mean(latencies),
        "latency_p95": statistics.quantiles(latencies, n=20)[18],
        "errors": errors,
        "success_rate": successful / TARGET_EVENTS * 100
    }


if __name__ == "__main__":
    print("Starting INDB Load Test...")
    print("Make sure INDB is running on http://localhost:8003")
    print()
    
    try:
        results = asyncio.run(run_load_test())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed: {e}")
