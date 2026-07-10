"""
Load Balancer Management API

Provides endpoints for monitoring and managing the HAProxy load balancer.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
import httpx
import asyncio
from datetime import datetime

router = APIRouter(prefix="/api/v2/loadbalancer", tags=["Load Balancer"])

# HAProxy stats URL (internal Docker network)
HAPROXY_STATS_URL = "http://loadbalancer:8080/stats;csv"
HAPROXY_ADMIN_SOCKET = "/var/run/haproxy.sock"  # If admin socket is enabled


@router.get("/status")
async def get_loadbalancer_status() -> Dict:
    """
    Get current load balancer status and node health.
    
    Returns:
        - Load balancer health
        - Active nodes
        - Traffic distribution
        - Health check status
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Try to fetch HAProxy stats
            try:
                response = await client.get(HAPROXY_STATS_URL)
                stats_csv = response.text
                nodes = parse_haproxy_stats(stats_csv)
            except Exception as e:
                # Fallback: check nodes directly
                nodes = await check_nodes_directly()
            
            # Calculate summary
            total_nodes = len(nodes)
            healthy_nodes = sum(1 for n in nodes if n["status"] == "UP")
            
            return {
                "loadbalancer": {
                    "enabled": True,
                    "type": "HAProxy",
                    "algorithm": "round-robin",
                    "stats_url": "http://localhost:8080/stats",
                },
                "nodes": nodes,
                "summary": {
                    "total_nodes": total_nodes,
                    "healthy_nodes": healthy_nodes,
                    "unhealthy_nodes": total_nodes - healthy_nodes,
                    "health_percentage": (healthy_nodes / total_nodes * 100) if total_nodes > 0 else 0,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get load balancer status: {str(e)}")


@router.get("/nodes")
async def get_nodes() -> List[Dict]:
    """
    Get list of all backend nodes and their status.
    
    Returns list of nodes with:
        - node_id
        - address
        - status (UP/DOWN)
        - health_check_status
        - requests_total
        - response_time_avg
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(HAPROXY_STATS_URL)
                stats_csv = response.text
                return parse_haproxy_stats(stats_csv)
            except:
                # Fallback: check nodes directly
                return await check_nodes_directly()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get nodes: {str(e)}")


@router.get("/stats")
async def get_stats() -> Dict:
    """
    Get detailed load balancer statistics.
    
    Returns:
        - Total requests
        - Requests per node
        - Average response times
        - Error rates
        - Current connections
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(HAPROXY_STATS_URL)
            stats_csv = response.text
            
            # Parse CSV stats
            lines = stats_csv.strip().split('\n')
            if len(lines) < 2:
                return {"error": "No stats available"}
            
            # Parse header
            headers = lines[0].strip('# ').split(',')
            
            # Parse backend stats
            backend_stats = []
            for line in lines[1:]:
                if not line or line.startswith('#'):
                    continue
                values = line.split(',')
                if len(values) >= len(headers):
                    stat = dict(zip(headers, values))
                    if stat.get('svname') not in ['FRONTEND', 'BACKEND']:
                        backend_stats.append(stat)
            
            return {
                "backends": backend_stats,
                "timestamp": datetime.utcnow().isoformat(),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


async def check_nodes_directly() -> List[Dict]:
    """
    Fallback method: Check nodes directly when HAProxy stats are unavailable.
    """
    nodes_config = [
        {"id": "node-1", "host": "indb-node-1", "port": 8000},
        {"id": "node-2", "host": "indb-node-2", "port": 8000},
        {"id": "node-3", "host": "indb-node-3", "port": 8000},
    ]
    
    nodes = []
    async with httpx.AsyncClient(timeout=2.0) as client:
        for node_config in nodes_config:
            try:
                start_time = asyncio.get_event_loop().time()
                response = await client.get(f"http://{node_config['host']}:{node_config['port']}/health")
                response_time = (asyncio.get_event_loop().time() - start_time) * 1000  # ms
                
                nodes.append({
                    "node_id": node_config["id"],
                    "address": f"{node_config['host']}:{node_config['port']}",
                    "status": "UP" if response.status_code == 200 else "DOWN",
                    "response_time_ms": round(response_time, 2),
                    "last_check": datetime.utcnow().isoformat(),
                })
            except Exception as e:
                nodes.append({
                    "node_id": node_config["id"],
                    "address": f"{node_config['host']}:{node_config['port']}",
                    "status": "DOWN",
                    "error": str(e),
                    "last_check": datetime.utcnow().isoformat(),
                })
    
    return nodes


def parse_haproxy_stats(csv_data: str) -> List[Dict]:
    """
    Parse HAProxy CSV stats into structured node data.
    """
    lines = csv_data.strip().split('\n')
    if len(lines) < 2:
        return []
    
    headers = lines[0].strip('# ').split(',')
    nodes = []
    
    for line in lines[1:]:
        if not line or line.startswith('#'):
            continue
        values = line.split(',')
        if len(values) >= len(headers):
            stat = dict(zip(headers, values))
            
            # Only include backend servers, not frontends/backends
            if stat.get('svname') not in ['FRONTEND', 'BACKEND'] and stat.get('pxname') == 'indb_nodes':
                nodes.append({
                    "node_id": stat.get('svname', 'unknown'),
                    "address": f"{stat.get('addr', 'unknown')}",
                    "status": stat.get('status', 'UNKNOWN'),
                    "weight": int(stat.get('weight', 0)),
                    "requests_total": int(stat.get('stot', 0)),
                    "requests_current": int(stat.get('scur', 0)),
                    "response_time_avg": int(stat.get('rtime', 0)),
                    "health_check_status": stat.get('check_status', 'unknown'),
                    "last_status_change": stat.get('lastchg', 'unknown'),
                })
    
    return nodes
