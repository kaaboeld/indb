"""
Psycho demo — show what removing the observer's valuation does to a route.

Ingests a small fork (a short chain through a node the observer says costs them
something, and a longer chain around it), then asks for the route twice.

    INDB_API_URL=http://127.0.0.1:8000 INDB_API_KEY=... python3 scripts/psycho_demo.py
"""
import json
import os
import urllib.request

BASE = os.environ.get("INDB_API_URL", "http://127.0.0.1:8000").rstrip("/")
KEY = os.environ.get("INDB_API_KEY", "")
V2 = f"{BASE}/api/v2"
TS = 1_700_000_000
MONTH = 40 * 86400  # keeps Echo's cyclic bonus out of the picture


def call(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if KEY:
        headers["X-API-Key"] = KEY
    req = urllib.request.Request(f"{V2}{path}", data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def ingest(tokens, location, month):
    body = {"raw_data_anchor": tokens, "location": location, "timestamp": TS + month * MONTH}
    return call("POST", "/events", body)["data"]["id"]


def route_of(path_block):
    return " → ".join(h["location"] for h in path_block["path"]) or "(none)"


print("Ingesting the fork...")
start = ingest(["alpha", "origin"], "route/start", 0)
ingest(["alpha", "omega", "harm"], "route/gate", 1)
ingest(["alpha", "long"], "route/detour-a", 2)
ingest(["long", "omega"], "route/detour-b", 3)
goal = ingest(["omega", "terminus"], "route/goal", 4)

result = call("POST", "/psycho/path", {
    "from": start,
    "to": goal,
    "profile": "psychopath",
    "compare_to": "neutral",
    "token_weights": {"harm": -6.0},
})

ablation = result["ablation"]
baseline = ablation["baseline_path"]
probe = ablation["probe_path"]

print()
print("The observer says passing through 'harm' costs them 6.0.")
print()
print(f"  neutral    (valuation honoured) : {route_of(baseline)}")
print(f"                                    cost {baseline['total_cost']}, {baseline['hop_count']} hops")
print(f"  psychopath (valuation ablated)  : {route_of(probe)}")
print(f"                                    cost {probe['total_cost']}, {probe['hop_count']} hops")
print()
for key in (
    "identical_route",
    "shared_prefix",
    "hop_delta",
    "probe_cost_on_baseline_scale",
    "detour_cost",
    "baseline_route_barrier",
    "probe_route_barrier",
    "barrier_walked_into",
):
    print(f"  {key:30} {ablation[key]}")
print()
print("verdict:", ablation["verdict"])
