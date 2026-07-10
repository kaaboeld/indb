"""
Object Pool for INDB
Reusable Event objects to reduce GC pressure.
"""

from typing import Generic, TypeVar, List, Optional, Callable
from threading import Lock
from collections import deque

T = TypeVar('T')


class ObjectPool(Generic[T]):
    """
    Generic object pool for reusable objects.
    Reduces garbage collection pressure by reusing objects.
    """
    
    def __init__(
        self,
        factory: Callable[[], T],
        reset: Optional[Callable[[T], None]] = None,
        max_size: int = 1000
    ):
        """
        Initialize object pool.
        
        Args:
            factory: Function to create new objects
            reset: Optional function to reset object state
            max_size: Maximum pool size
        """
        self.factory = factory
        self.reset = reset or (lambda obj: None)
        self.max_size = max_size
        self.pool: deque[T] = deque()
        self.lock = Lock()
        self.created = 0
        self.reused = 0
        self.discarded = 0
    
    def acquire(self) -> T:
        """
        Get object from pool or create new one.
        
        Returns:
            Object instance
        """
        with self.lock:
            if self.pool:
                obj = self.pool.popleft()
                self.reused += 1
                return obj
            else:
                self.created += 1
                return self.factory()
    
    def release(self, obj: T) -> None:
        """
        Return object to pool.
        
        Args:
            obj: Object to return
        """
        with self.lock:
            if len(self.pool) < self.max_size:
                # Reset object state
                self.reset(obj)
                self.pool.append(obj)
            else:
                # Pool is full, discard
                self.discarded += 1
    
    def clear(self) -> None:
        """Clear all pooled objects"""
        with self.lock:
            self.pool.clear()
    
    def stats(self) -> dict:
        """Get pool statistics"""
        with self.lock:
            total = self.created + self.reused
            reuse_rate = (self.reused / total * 100) if total > 0 else 0
            
            return {
                "pool_size": len(self.pool),
                "max_size": self.max_size,
                "created": self.created,
                "reused": self.reused,
                "discarded": self.discarded,
                "reuse_rate": round(reuse_rate, 2),
            }
    
    def __enter__(self):
        """Context manager: acquire object"""
        self._obj = self.acquire()
        return self._obj
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager: release object"""
        self.release(self._obj)


# Event object pool
def create_event():
    """Factory for Event objects"""
    from core.event import Event
    return Event(data={})


def reset_event(event):
    """Reset Event object state"""
    event.id = None
    event.data = {}
    event.timestamp = None
    event.source_id = None
    event.binary_payload = None


# Global Event pool
event_pool = ObjectPool(
    factory=create_event,
    reset=reset_event,
    max_size=1000
)


def get_event():
    """Get Event from pool"""
    return event_pool.acquire()


def return_event(event):
    """Return Event to pool"""
    event_pool.release(event)


def get_event_pool_stats():
    """Get Event pool statistics"""
    return event_pool.stats()


# Example usage
if __name__ == "__main__":
    # Test pool
    print("Testing Event pool...")
    
    # Acquire and release
    for i in range(100):
        event = get_event()
        event.data = {"test": i}
        return_event(event)
    
    # Check stats
    stats = get_event_pool_stats()
    print(f"Pool stats: {stats}")
    print(f"Reuse rate: {stats['reuse_rate']}%")
