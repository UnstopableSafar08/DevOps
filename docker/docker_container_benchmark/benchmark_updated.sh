#!/bin/bash

RED="\033[0;31m"
GREEN="\033[0;32m"
CYAN="\033[0;36m"
YELLOW="\033[1;33m"
NC="\033[0m"

OUTPUT="benchmark_output.txt"
> "$OUTPUT"

echo -e "${CYAN}Docker Container Benchmark Script${NC}"
echo

echo -ne "${YELLOW}Enter the container initial name: ${NC}"
read BASE

echo -ne "${YELLOW}Enter total number of containers: ${NC}"
read COUNT

echo -e "${GREEN}Starting benchmark for $COUNT containers...${NC}"
echo "===== Benchmark Started $(date) =====" >> "$OUTPUT"

for ((i=1; i<=COUNT; i++)); do
    C="${BASE}${i}"

    echo -e "\n=== Benchmark for $C ===" >> "$OUTPUT"

    echo -e "${CYAN}Checking container: $C${NC}"

    # If container does not exist skip
    if ! docker ps --format '{{.Names}}' | grep -w "$C" >/dev/null; then
        echo -e "${RED}Container not found: $C${NC}"
        echo "Container not found" >> "$OUTPUT"
        continue
    fi

    echo -e "${YELLOW}Ensuring sysbench is installed inside $C${NC}"

    docker exec "$C" sh -c "which sysbench >/dev/null 2>&1 || apt-get update && apt-get install -y sysbench" >/dev/null 2>&1

    echo -e "${GREEN}Running CPU benchmark on $C${NC}"
    echo -e "--- CPU Benchmark ---" >> "$OUTPUT"
    docker exec "$C" sysbench cpu --threads=2 run >> "$OUTPUT"

    echo -e "${GREEN}Running Memory benchmark on $C${NC}"
    echo -e "--- Memory Benchmark ---" >> "$OUTPUT"
    docker exec "$C" sysbench memory run >> "$OUTPUT"

    echo -e "${GREEN}Running File I/O benchmark on $C${NC}"
    docker exec "$C" sh -c "
        mkdir -p /tmp/sysbench_test
        cd /tmp/sysbench_test
        sysbench fileio --file-total-size=1G prepare
        sysbench fileio --file-total-size=1G --file-test-mode=rndrw run
        sysbench fileio --file-total-size=1G cleanup
    " >> "$OUTPUT"

    echo -e "${GREEN}Completed benchmark for $C${NC}"
done

echo "===== Benchmark Completed $(date) =====" >> "$OUTPUT"

echo -e "${GREEN}Benchmark finished. Results stored in $OUTPUT${NC}"

