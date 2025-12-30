#!/bin/bash

# Docker Benchmark Script
# Author: Sagar Malla
# Email: sagarmalla08
# Date: 15-11-2025
# DESCRIPTION:
#   This script benchmarks Docker containers dynamically based on a name pattern.
#   It measures CPU, Memory, and Disk performance and generates a summary report.

OUTPUT_FILE="benchmark_output.txt"
> $OUTPUT_FILE

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Docker Container Benchmark Script${NC}"
echo ""

read -p "Enter the container initial name (e.g., bell for bell1, bell2,...): " PREFIX
read -p "Enter total number of containers: " TOTAL

echo ""
echo -e "${GREEN}Starting benchmark for $TOTAL containers...${NC}" | tee -a $OUTPUT_FILE

declare -a CPU_EVENTS MEM_THRU DISK_READ DISK_WRITE

for ((i=1;i<=TOTAL;i++)); do
    CONTAINER_NAME="${PREFIX}${i}"
    echo ""
    echo -e "${YELLOW}Processing container: $CONTAINER_NAME${NC}" | tee -a $OUTPUT_FILE

    # Check if container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
        echo -e "${RED}Container $CONTAINER_NAME is not running. Skipping...${NC}" | tee -a $OUTPUT_FILE
        continue
    fi

    echo "=== Benchmark for $CONTAINER_NAME ===" >> $OUTPUT_FILE

    # CPU Benchmark
    echo -e "${GREEN}--- CPU Benchmark ---${NC}" | tee -a $OUTPUT_FILE
    CPU_OUT=$(docker exec $CONTAINER_NAME sysbench cpu --threads=2 --time=10 run)
    EVENTS=$(echo "$CPU_OUT" | awk -F: '/events per second/ {gsub(/ /,"",$2); print $2}')
    CPU_EVENTS[$i]=$EVENTS
    echo "$CPU_OUT" >> $OUTPUT_FILE

    # Memory Benchmark
    echo -e "${GREEN}--- Memory Benchmark ---${NC}" | tee -a $OUTPUT_FILE
    MEM_OUT=$(docker exec $CONTAINER_NAME sysbench memory --threads=1 --time=10 run)
    MEM_VAL=$(echo "$MEM_OUT" | awk '/MiB\/sec/ {print $2; exit}')
    MEM_THRU[$i]=$MEM_VAL
    echo "$MEM_OUT" >> $OUTPUT_FILE

    # Disk Benchmark
    echo -e "${GREEN}--- Disk Benchmark ---${NC}" | tee -a $OUTPUT_FILE
    docker exec $CONTAINER_NAME sysbench fileio --threads=1 --file-total-size=1G --time=10 --file-test-mode=rndrw prepare
    DISK_OUT=$(docker exec $CONTAINER_NAME sysbench fileio --threads=1 --file-total-size=1G --time=10 --file-test-mode=rndrw run)
    READ_VAL=$(echo "$DISK_OUT" | awk '/read, MiB\/s:/ {print $3}')
    WRITE_VAL=$(echo "$DISK_OUT" | awk '/written, MiB\/s:/ {print $3}')
    DISK_READ[$i]=$READ_VAL
    DISK_WRITE[$i]=$WRITE_VAL
    docker exec $CONTAINER_NAME sysbench fileio --threads=1 --file-total-size=1G cleanup
    echo "$DISK_OUT" >> $OUTPUT_FILE

    echo -e "${GREEN}Completed benchmark for $CONTAINER_NAME${NC}" | tee -a $OUTPUT_FILE
done

# Print summary table
echo "" | tee -a $OUTPUT_FILE
echo "===== Docker Container Benchmark Summary =====" | tee -a $OUTPUT_FILE
printf "%-10s | %-15s | %-25s | %-15s | %-15s\n" "Container" "CPU Events/sec" "Memory Throughput (MiB/sec)" "Disk Read (MiB/s)" "Disk Write (MiB/s)" | tee -a $OUTPUT_FILE
echo "-----------------------------------------------------------------------------------------------" | tee -a $OUTPUT_FILE

for ((i=1;i<=TOTAL;i++)); do
    printf "%-10s | %-15s | %-25s | %-15s | %-15s\n" \
    "${PREFIX}${i}" "${CPU_EVENTS[$i]}" "${MEM_THRU[$i]}" "${DISK_READ[$i]}" "${DISK_WRITE[$i]}" | tee -a $OUTPUT_FILE
done

echo "" | tee -a $OUTPUT_FILE
echo "===== Benchmark Completed $(date) =====" | tee -a $OUTPUT_FILE

