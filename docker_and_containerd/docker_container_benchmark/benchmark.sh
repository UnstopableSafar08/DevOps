#!/bin/bash

# Containers
CON1="bell1"
CON2="bell2"

# URLs
URL1="http://localhost:8881/"
URL2="http://localhost:8882/"

# Output file
OUT="benchmark_output.txt"
> "$OUT"   # Clear old file

# Colors for screen (not saved in file)
BOLD="\033[1m"
NC="\033[0m"

log() {
    # Print to screen with colors
    echo -e "${BOLD}$1${NC}"
    # Write to file without colors
    echo "$1" >> "$OUT"
}

write() {
    echo "$1"
    echo "$1" >> "$OUT"
}

log "Benchmarking Docker Containers: $CON1 vs $CON2"
write ""

log "1. Image Sizes:"
docker images | grep bellsoft | tee -a "$OUT"
write ""

log "2. Resource Usage (docker stats snapshot):"
docker stats --no-stream $CON1 $CON2 | tee -a "$OUT"
write ""

log "3. HTTP Latency Test (curl):"
write -n "$CON1: "
curl -w "%{time_total}s\n" -o /dev/null -s $URL1 | tee -a "$OUT"

write -n "$CON2: "
curl -w "%{time_total}s\n" -o /dev/null -s $URL2 | tee -a "$OUT"
write ""

log "4. Server Startup Time:"
write -n "$CON1: "
docker logs $CON1 2>&1 | grep "Server startup" | tail -1 | tee -a "$OUT"

write -n "$CON2: "
docker logs $CON2 2>&1 | grep "Server startup" | tail -1 | tee -a "$OUT"
write ""

log "5. Container Logs (last 5 lines):"
write "--- $CON1 ---"
docker logs $CON1 | tail -5 | tee -a "$OUT"

write "--- $CON2 ---"
docker logs $CON2 | tail -5 | tee -a "$OUT"
write ""

log "6. Container Info Summary:"
docker inspect --format \
'{{.Name}} CPU: {{.HostConfig.NanoCpus}}  MEM: {{.HostConfig.Memory}}' $CON1 $CON2 | tee -a "$OUT"
write ""

log "Benchmark Completed"
write "Output saved to $OUT"

