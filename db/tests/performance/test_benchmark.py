
import pytest
import time
import asyncio
from core.kernel import INDBKernel

@pytest.mark.asyncio
async def test_ingest_performance():
    """
    Benchmark ingestion performance.
    With Neural Fusion: ~40 events/sec.
    Without Fusion: > 1000 events/sec.
    """
    kernel = INDBKernel()
    kernel.db._persist = lambda: None  # Disable disk I/O for pure bench
    
    count = 1000
    start_time = time.time()
    
    for i in range(count):
        await kernel.db.ingest(
            raw_data_anchor=[f"bench_{i}", "perf"],
            location="BenchmarkCity",
            ttl=60
        )
        
    duration = time.time() - start_time
    rate = count / duration if duration > 0 else 0
    
    print(f"\nBenchmark Rate: {rate:.2f} events/sec")
    
    # Assert acceptable performance (allow some variance in CI environments)
    # Neural Fusion (Sentence Transformers) is heavy!
    assert rate > 30, f"Performance too low: {rate:.2f} events/sec"
