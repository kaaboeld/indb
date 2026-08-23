"""
Memory-Mapped Storage for INDB
Fast binary access using memory-mapped files.
"""

import os
import mmap
import struct
from typing import Optional, List, Dict, Any
import msgpack

# Same location as every other store: a relative "indb.bin" here pointed at the working
# directory instead of DATA_DIR, so it mapped a different file than the engine writes.
from storage.format import DB_FILE


class MemoryMappedStore:
    """
    Memory-mapped file storage for fast read access.
    Provides zero-copy reads for large datasets.
    """
    
    def __init__(self, filepath: str = DB_FILE, read_only: bool = True):
        """
        Initialize memory-mapped storage.
        
        Args:
            filepath: Path to binary file
            read_only: If True, open in read-only mode (safer)
        """
        self.filepath = filepath
        self.read_only = read_only
        self.file = None
        self.mmap = None
    
    def __enter__(self):
        """Context manager entry"""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    def open(self) -> None:
        """Open file and create memory mapping"""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")
        
        # Open file
        mode = "rb" if self.read_only else "r+b"
        self.file = open(self.filepath, mode)
        
        # Create memory map
        access = mmap.ACCESS_READ if self.read_only else mmap.ACCESS_WRITE
        self.mmap = mmap.mmap(self.file.fileno(), 0, access=access)
    
    def close(self) -> None:
        """Close memory map and file"""
        if self.mmap:
            self.mmap.close()
            self.mmap = None
        if self.file:
            self.file.close()
            self.file = None
    
    def read_all(self) -> bytes:
        """
        Read entire file from memory map.
        Zero-copy operation - very fast!
        
        Returns:
            File contents as bytes
        """
        if not self.mmap:
            raise RuntimeError("Memory map not opened")
        
        return self.mmap[:]
    
    def read_chunk(self, offset: int, size: int) -> bytes:
        """
        Read specific chunk from memory map.
        
        Args:
            offset: Byte offset to start reading
            size: Number of bytes to read
            
        Returns:
            Chunk data
        """
        if not self.mmap:
            raise RuntimeError("Memory map not opened")
        
        return self.mmap[offset:offset + size]
    
    def get_size(self) -> int:
        """Get file size"""
        if not self.mmap:
            raise RuntimeError("Memory map not opened")
        
        return self.mmap.size()
    
    def search(self, pattern: bytes) -> List[int]:
        """
        Search for byte pattern in memory map.
        Fast sequential scan.
        
        Args:
            pattern: Byte pattern to search for
            
        Returns:
            List of offsets where pattern was found
        """
        if not self.mmap:
            raise RuntimeError("Memory map not opened")
        
        offsets = []
        offset = 0
        
        while True:
            offset = self.mmap.find(pattern, offset)
            if offset == -1:
                break
            offsets.append(offset)
            offset += 1
        
        return offsets


def load_with_mmap(master_key: bytes) -> List[Dict[str, Any]]:
    """
    Load events using memory-mapped file for fast access.
    
    Args:
        master_key: Master encryption key
        
    Returns:
        List of events
    """
    from core.encryption import FileEncryptor
    
    try:
        with MemoryMappedStore(DB_FILE, read_only=True) as store:
            # Read encrypted data (zero-copy!)
            encrypted = store.read_all()
            
            if not encrypted:
                return []
            
            # Decrypt
            decrypted = FileEncryptor.decrypt_file(encrypted, master_key)
            
            # Deserialize
            data = msgpack.unpackb(decrypted, raw=False)
            
            # Convert to events
            events = []
            for item in data:
                if isinstance(item, dict):
                    if item.get('_type') == 'FusedEvent':
                        try:
                            from services.fusion import FusedEvent
                            events.append(FusedEvent.from_dict(item))
                        except ImportError:
                            from core.event import Event
                            events.append(Event.from_dict(item))
                    else:
                        from core.event import Event
                        events.append(Event.from_dict(item))
                else:
                    events.append(item)
            
            return events
            
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"Memory-mapped load error: {e}")
        return []


# Benchmark utility
def benchmark_mmap_vs_regular():
    """
    Compare memory-mapped vs regular file I/O.
    Run this to see performance difference.
    """
    import time
    from storage.binary import load_decrypted, MASTER_KEY
    
    # Regular I/O
    start = time.time()
    events_regular = load_decrypted()
    regular_time = time.time() - start
    
    # Memory-mapped I/O
    start = time.time()
    events_mmap = load_with_mmap(MASTER_KEY)
    mmap_time = time.time() - start
    
    print(f"Regular I/O: {regular_time:.4f}s")
    print(f"Memory-mapped I/O: {mmap_time:.4f}s")
    print(f"Speedup: {regular_time / mmap_time:.2f}x")
    print(f"Events loaded: {len(events_regular)}")


if __name__ == "__main__":
    benchmark_mmap_vs_regular()
