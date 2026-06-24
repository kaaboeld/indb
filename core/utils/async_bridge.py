
import asyncio
import threading
from typing import Any, Coroutine

def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    """
    Helper to run an async coroutine from a synchronous context (e.g., gRPC thread).
    Creates a new event loop for the operation and closes it afterwards.
    
    Warning: This is blocking.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(coro)
        
        # Cleanup tasks
        pending = asyncio.all_tasks(loop)
        if pending:
            loop.run_until_complete(asyncio.gather(*pending))
        
        loop.close()
        return result
    except Exception as e:
        raise e
