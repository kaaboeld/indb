
from core.kernel import INDBKernel
import sys

try:
    kernel = INDBKernel()
    print("Kernel initialized")
    
    # Add a dummy event if empty
    if not kernel.db.memory:
        print("Adding dummy event")
        kernel.db.ingest(["test", "token"], "DebugLocation")
    
    raw_events = kernel.db.memory
    print(f"Events count: {len(raw_events)}")
    
    mood = "Neutral"
    print(f"Scanning with mood: {mood}")
    
    events = kernel.db.scan("", "", context_mood=mood, events_to_scan=raw_events)
    print(f"Scan successful. Result count: {len(events)}")

except Exception as e:
    print(f"❌ Error caught: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
