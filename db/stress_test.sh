#!/bin/bash
# INDB Comprehensive Stress Test
# Tests: Raft stability, Prism/Instinct performance, Node failure recovery

set -e

LOGFILE="/tmp/indb_stress_test_$(date +%s).log"
RESULTS_FILE="/tmp/stress_test_results.json"

echo "=== INDB Comprehensive Stress Test ===" | tee -a "$LOGFILE"
echo "Start Time: $(date)" | tee -a "$LOGFILE"
echo "" | tee -a "$LOGFILE"

# Phase 1: Baseline Metrics
echo "Phase 1: Collecting Baseline Metrics" | tee -a "$LOGFILE"
BASELINE_EVENTS=$(curl -s "http://localhost:8000/api/v2/events?limit=1" | jq -r '.meta.pagination.total')
BASELINE_RAFT=$(curl -s "http://localhost:8000/raft/status" | jq '{state: .state, term: .term, leader: .leader}')
echo "Baseline Events: $BASELINE_EVENTS" | tee -a "$LOGFILE"
echo "Baseline Raft: $BASELINE_RAFT" | tee -a "$LOGFILE"
echo "" | tee -a "$LOGFILE"

# Phase 2: Load Test (5000 events)
echo "Phase 2: Loading 1000 New Events" | tee -a "$LOGFILE"
START_TIME=$(date +%s)
SUCCESS_COUNT=0
FAIL_COUNT=0

for i in {1..1000}; do
    RESPONSE=$(curl -s -X POST http://localhost:8000/api/v2/events \
        -H "Content-Type: application/json" \
        -d "{
            \"raw_data_anchor\": [\"stress\", \"test\", \"event\", \"$i\"],
            \"location\": \"stress_test/batch_2\",
            \"ttl\": 3600
        }" 2>&1)
    
    if echo "$RESPONSE" | grep -q "event_id"; then
        ((SUCCESS_COUNT++))
    else
        ((FAIL_COUNT++))
    fi
    
    # Progress every 100 events
    if [ $((i % 100)) -eq 0 ]; then
        echo "Progress: $i/1000 (Success: $SUCCESS_COUNT, Fail: $FAIL_COUNT)" | tee -a "$LOGFILE"
    fi
done

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
THROUGHPUT=$(echo "scale=2; $SUCCESS_COUNT / $DURATION" | bc)

echo "" | tee -a "$LOGFILE"
echo "Load Test Results:" | tee -a "$LOGFILE"
echo "  Success: $SUCCESS_COUNT/5000 ($(echo "scale=2; $SUCCESS_COUNT * 100 / 5000" | bc)%)" | tee -a "$LOGFILE"
echo "  Failed: $FAIL_COUNT" | tee -a "$LOGFILE"
echo "  Duration: ${DURATION}s" | tee -a "$LOGFILE"
echo "  Throughput: ${THROUGHPUT} events/sec" | tee -a "$LOGFILE"
echo "" | tee -a "$LOGFILE"

# Phase 3: Prism/Instinct Parallel Queries
echo "Phase 3: Parallel Prism/Instinct Queries (50 concurrent)" | tee -a "$LOGFILE"
SEED=$(curl -s "http://localhost:8000/api/v2/events?limit=1" | jq -r '.data[0].id')

PRISM_START=$(date +%s)
PRISM_SUCCESS=0
PRISM_FAIL=0

for i in {1..50}; do
    (
        RESPONSE=$(curl -s -X POST http://localhost:8000/api/v2/prism/synthesize \
            -H "Content-Type: application/json" \
            -d "{\"query\": \"$SEED\", \"radius\": 0.2, \"limit\": 5}" 2>&1)
        
        if echo "$RESPONSE" | grep -q "event"; then
            echo "PRISM_SUCCESS" >> /tmp/prism_results.txt
        else
            echo "PRISM_FAIL" >> /tmp/prism_results.txt
        fi
    ) &
done
wait

PRISM_SUCCESS=$(grep -c "PRISM_SUCCESS" /tmp/prism_results.txt 2>/dev/null || echo 0)
PRISM_FAIL=$(grep -c "PRISM_FAIL" /tmp/prism_results.txt 2>/dev/null || echo 0)
PRISM_END=$(date +%s)
PRISM_DURATION=$((PRISM_END - PRISM_START))

echo "Prism Results:" | tee -a "$LOGFILE"
echo "  Success: $PRISM_SUCCESS/50" | tee -a "$LOGFILE"
echo "  Failed: $PRISM_FAIL/50" | tee -a "$LOGFILE"
echo "  Duration: ${PRISM_DURATION}s" | tee -a "$LOGFILE"
rm -f /tmp/prism_results.txt
echo "" | tee -a "$LOGFILE"

# Instinct queries
INSTINCT_START=$(date +%s)
INSTINCT_SUCCESS=0
INSTINCT_FAIL=0

for i in {1..50}; do
    (
        RESPONSE=$(curl -s -X POST http://localhost:8000/api/v2/prism/instinct \
            -H "Content-Type: application/json" \
            -d "{\"query\": \"$SEED\", \"adrenaline\": 0.7, \"radius\": 0.2, \"limit\": 5}" 2>&1)
        
        if echo "$RESPONSE" | grep -q "instinct"; then
            echo "INSTINCT_SUCCESS" >> /tmp/instinct_results.txt
        else
            echo "INSTINCT_FAIL" >> /tmp/instinct_results.txt
        fi
    ) &
done
wait

INSTINCT_SUCCESS=$(grep -c "INSTINCT_SUCCESS" /tmp/instinct_results.txt 2>/dev/null || echo 0)
INSTINCT_FAIL=$(grep -c "INSTINCT_FAIL" /tmp/instinct_results.txt 2>/dev/null || echo 0)
INSTINCT_END=$(date +%s)
INSTINCT_DURATION=$((INSTINCT_END - INSTINCT_START))

echo "Instinct Results:" | tee -a "$LOGFILE"
echo "  Success: $INSTINCT_SUCCESS/50" | tee -a "$LOGFILE"
echo "  Failed: $INSTINCT_FAIL/50" | tee -a "$LOGFILE"
echo "  Duration: ${INSTINCT_DURATION}s" | tee -a "$LOGFILE"
rm -f /tmp/instinct_results.txt
echo "" | tee -a "$LOGFILE"

# Phase 4: Node Failure Test
echo "Phase 4: Node Failure Recovery Test" | tee -a "$LOGFILE"
echo "Stopping node-3..." | tee -a "$LOGFILE"
docker stop indb-node-3 >> "$LOGFILE" 2>&1

sleep 5

# Test cluster still works
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v2/events \
    -H "Content-Type: application/json" \
    -d "{\"raw_data_anchor\": [\"post\", \"failure\", \"test\"], \"location\": \"test\", \"ttl\": 3600}")

if echo "$RESPONSE" | grep -q "event_id"; then
    echo "✅ Cluster operational with 2/3 nodes" | tee -a "$LOGFILE"
    CLUSTER_STATUS="OPERATIONAL"
else
    echo "❌ Cluster failed with 2/3 nodes" | tee -a "$LOGFILE"
    CLUSTER_STATUS="FAILED"
fi

# Restart node
echo "Restarting node-3..." | tee -a "$LOGFILE"
docker start indb-node-3 >> "$LOGFILE" 2>&1
sleep 10

FINAL_RAFT=$(curl -s "http://localhost:8000/raft/status" | jq '{state: .state, term: .term, leader: .leader}')
echo "Final Raft Status: $FINAL_RAFT" | tee -a "$LOGFILE"
echo "" | tee -a "$LOGFILE"

# Final Metrics
FINAL_EVENTS=$(curl -s "http://localhost:8000/api/v2/events?limit=1" | jq -r '.meta.pagination.total')
NEW_EVENTS=$((FINAL_EVENTS - BASELINE_EVENTS))

echo "=== Final Summary ===" | tee -a "$LOGFILE"
echo "Total Events Added: $NEW_EVENTS" | tee -a "$LOGFILE"
echo "Load Test Success Rate: $(echo "scale=2; $SUCCESS_COUNT * 100 / 5000" | bc)%" | tee -a "$LOGFILE"
echo "Prism Success Rate: $(echo "scale=2; $PRISM_SUCCESS * 100 / 50" | bc)%" | tee -a "$LOGFILE"
echo "Instinct Success Rate: $(echo "scale=2; $INSTINCT_SUCCESS * 100 / 50" | bc)%" | tee -a "$LOGFILE"
echo "Cluster Resilience: $CLUSTER_STATUS" | tee -a "$LOGFILE"
echo "" | tee -a "$LOGFILE"
echo "End Time: $(date)" | tee -a "$LOGFILE"
echo "Full log: $LOGFILE" | tee -a "$LOGFILE"

# Generate JSON results
cat > "$RESULTS_FILE" <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "baseline_events": $BASELINE_EVENTS,
  "final_events": $FINAL_EVENTS,
  "load_test": {
    "total": 5000,
    "success": $SUCCESS_COUNT,
    "failed": $FAIL_COUNT,
    "duration_seconds": $DURATION,
    "throughput_per_sec": $THROUGHPUT
  },
  "prism_test": {
    "total": 50,
    "success": $PRISM_SUCCESS,
    "failed": $PRISM_FAIL,
    "duration_seconds": $PRISM_DURATION
  },
  "instinct_test": {
    "total": 50,
    "success": $INSTINCT_SUCCESS,
    "failed": $INSTINCT_FAIL,
    "duration_seconds": $INSTINCT_DURATION
  },
  "cluster_resilience": "$CLUSTER_STATUS"
}
EOF

echo "Results saved to: $RESULTS_FILE"
cat "$RESULTS_FILE"
