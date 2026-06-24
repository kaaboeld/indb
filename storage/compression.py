"""
LZ4 Compression Layer for INDB Storage
Optional compression for space savings with minimal performance impact.
"""

import lz4.frame
from typing import Optional

# Compression settings
COMPRESSION_LEVEL = 4  # 1-16, higher = better compression but slower
BLOCK_SIZE = lz4.frame.BLOCKSIZE_MAX4MB


def compress(data: bytes, level: int = COMPRESSION_LEVEL) -> bytes:
    """
    Compress data using LZ4.
    
    Args:
        data: Raw data to compress
        level: Compression level (1-16)
        
    Returns:
        Compressed data
    """
    return lz4.frame.compress(
        data,
        compression_level=level,
        block_size=BLOCK_SIZE
    )


def decompress(data: bytes) -> bytes:
    """
    Decompress LZ4 data.
    
    Args:
        data: Compressed data
        
    Returns:
        Decompressed data
    """
    return lz4.frame.decompress(data)


def compress_if_beneficial(data: bytes, threshold: float = 0.9) -> tuple[bytes, bool]:
    """
    Compress data only if compression ratio is beneficial.
    
    Args:
        data: Raw data
        threshold: Minimum compression ratio to use (0.9 = 10% savings)
        
    Returns:
        (data, compressed) tuple
    """
    compressed = compress(data)
    ratio = len(compressed) / len(data)
    
    if ratio < threshold:
        return compressed, True
    else:
        return data, False


def get_compression_ratio(original_size: int, compressed_size: int) -> float:
    """Calculate compression ratio as percentage"""
    return (1 - compressed_size / original_size) * 100


# Integration with binary storage
def save_with_compression(
    data: bytes,
    compress_enabled: bool = True,
    min_size: int = 1024
) -> tuple[bytes, dict]:
    """
    Save data with optional compression.
    
    Args:
        data: Data to save
        compress_enabled: Enable compression
        min_size: Minimum size to compress (bytes)
        
    Returns:
        (data, metadata) tuple
    """
    metadata = {
        "original_size": len(data),
        "compressed": False,
        "compression_ratio": 0.0
    }
    
    # Skip compression for small files
    if not compress_enabled or len(data) < min_size:
        return data, metadata
    
    # Compress
    compressed, is_compressed = compress_if_beneficial(data)
    
    if is_compressed:
        metadata["compressed"] = True
        metadata["compressed_size"] = len(compressed)
        metadata["compression_ratio"] = get_compression_ratio(
            len(data), len(compressed)
        )
        return compressed, metadata
    else:
        return data, metadata


def load_with_decompression(data: bytes, is_compressed: bool) -> bytes:
    """
    Load data with optional decompression.
    
    Args:
        data: Data to load
        is_compressed: Whether data is compressed
        
    Returns:
        Decompressed data
    """
    if is_compressed:
        return decompress(data)
    else:
        return data


# Benchmark utility
def benchmark_compression(data: bytes) -> dict:
    """
    Benchmark compression performance.
    
    Args:
        data: Test data
        
    Returns:
        Performance metrics
    """
    import time
    
    # Compression
    start = time.time()
    compressed = compress(data)
    compress_time = time.time() - start
    
    # Decompression
    start = time.time()
    decompressed = decompress(compressed)
    decompress_time = time.time() - start
    
    # Verify
    assert data == decompressed, "Decompression mismatch!"
    
    ratio = get_compression_ratio(len(data), len(compressed))
    
    return {
        "original_size": len(data),
        "compressed_size": len(compressed),
        "compression_ratio": round(ratio, 2),
        "compress_time": round(compress_time * 1000, 2),  # ms
        "decompress_time": round(decompress_time * 1000, 2),  # ms
        "compress_speed": round(len(data) / compress_time / 1024 / 1024, 2),  # MB/s
        "decompress_speed": round(len(data) / decompress_time / 1024 / 1024, 2),  # MB/s
    }


if __name__ == "__main__":
    # Test compression
    import msgpack
    
    # Create test data
    test_events = [
        {"id": i, "data": {"message": f"Event {i}" * 10}}
        for i in range(1000)
    ]
    
    data = msgpack.packb(test_events)
    
    print("LZ4 Compression Benchmark")
    print("=" * 50)
    
    metrics = benchmark_compression(data)
    for key, value in metrics.items():
        print(f"{key}: {value}")
    
    print("\nConclusion:")
    if metrics["compression_ratio"] > 30:
        print("✅ Excellent compression!")
    elif metrics["compression_ratio"] > 10:
        print("✅ Good compression")
    else:
        print("⚠️  Low compression (data may not be compressible)")
