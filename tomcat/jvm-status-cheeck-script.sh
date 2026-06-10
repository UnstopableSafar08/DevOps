#!/bin/bash
#
#
# Copyright (c) 2017 Sagar Malla
#
# Modified to show memory in GB and display configured max values

RUNONCE=0
SHOW_HEADERS=1
SHOW_LONG=0
commandline_args=("$@")

parse_options() {
  for var in "${commandline_args[@]}"; do
      if [ $var = "-h" ] || [ $var = "-help" ]
      then
          echo "usage: ./jpsstat.sh [options]"
          echo ""
          echo "[OPTIONS] :"
          echo "    -l"
          echo "        Displays the full package name for the application's main class or the full path name to the application's JAR file."
          echo ""
          echo "    -1 | --once"
          echo "        Just run the script once, do not continuously refresh"
          echo ""
          echo "    -H | --no-headers"
          echo "        Do not display the text header with the field names"
          echo ""
          echo "    -h | -help"
          echo "        Display this help menu"
          echo ""
          echo "/********* Output Format *****************"
          echo " * PID       : Process Id"
          echo " * Name      : Process Name"
          echo " * CurHeap   : Heap memory currently in use (MB / GB)"
          echo " * MaxHeapU  : Max Heap memory used so far (MB / GB)"
          echo " * CfgMaxHeap: Configured Max Heap (-Xmx) (MB / GB)"
          echo " * CurRAM    : Current RAM used (MB / GB)"
          echo " * MaxRAMU   : Max RAM used so far (MB / GB)"
          echo " * SysRAM    : Total system RAM (GB)"
          echo " * %_CPU     : Current CPU use by PID"
          echo " */"
          exit 0
      elif [ $var = "-1" ] || [ $var = "--once" ]
      then
          RUNONCE=1
      elif [ $var = "-H" ] || [ $var = "--no-headers" ]
      then
          SHOW_HEADERS=0
      elif [ $var = "-l" ]
      then
          SHOW_LONG=1
      fi
  done
}

parse_options

# Get total system RAM in MB and GB
SYS_RAM_MB=$(awk '/MemTotal/ {printf "%d", $2/1024}' /proc/meminfo 2>/dev/null || echo "0")
SYS_RAM_GB=$(awk -v m=$SYS_RAM_MB 'BEGIN {printf "%.2f", m/1024}')

# Helper: format MB into "MB/GB" string
fmt_mem() {
    local mb=$1
    awk -v m="$mb" 'BEGIN {printf "%d MB (%.2f GB)", m, m/1024}'
}

# Helper: get configured Max Heap (-Xmx) in MB for a pid
get_max_heap_cfg() {
    local pid=$1
    local maxbytes
    maxbytes=$(jcmd $pid VM.flags 2>/dev/null | grep -oE 'MaxHeapSize=[0-9]+' | head -n1 | cut -d= -f2)
    if [ -z "$maxbytes" ]; then
        # fallback try jinfo
        maxbytes=$(jinfo -flag MaxHeapSize $pid 2>/dev/null | grep -oE '[0-9]+' | head -n1)
    fi
    if [ -z "$maxbytes" ] || [ "$maxbytes" = "0" ]; then
        echo "0"
    else
        awk -v b="$maxbytes" 'BEGIN {printf "%d", b/1024/1024}'
    fi
}

echo "System Total RAM: ${SYS_RAM_MB} MB (${SYS_RAM_GB} GB)"
echo ""

if [ $SHOW_HEADERS -eq 1 ]; then
    printf "%-6s %-30s %-20s %-20s %-20s %-20s %-20s %-6s\n" \
        "PID" "Name" "CurHeap" "MaxHeapUsed" "CfgMaxHeap(-Xmx)" "CurRAM" "MaxRAMUsed" "%_CPU"
    printf "%-6s %-30s %-20s %-20s %-20s %-20s %-20s %-6s\n" \
        "-----" "------------------------------" "--------------------" "--------------------" "--------------------" "--------------------" "--------------------" "------"
fi

declare -A prev_pid_max_heap=()
declare -A prev_pid_max_ram=()
declare -A pid_cfg_max_heap=()

PREV_LINES=0

while true
do

    declare -A curr_pid_name=()
    declare -A curr_pid_max_heap=()
    declare -A curr_pid_max_ram=()

    IFS=$'\n'
    DATA=
    if [ $SHOW_LONG -eq 1 ]; then
        DATA=($(jps -l))
    else
        DATA=($(jps))
    fi

    # move cursor up to overwrite previous output
    if [ $PREV_LINES -gt 0 ] && [ $RUNONCE -eq 0 ]; then
        tput cuu $PREV_LINES
        tput ed
    fi

    CURR_LINES=0
    IFS=$' '
    for LINE in "${DATA[@]}"
    do
        read -ra TOKENS <<< "$LINE"
        TOKENS[1]=${TOKENS[1]##*[\\ /]}

        if [ "${TOKENS[1]}" == "Jps" ] || [ "${TOKENS[1]}" == "sun.tools.jps.Jps" ] || [ "${TOKENS[1]}" == "Jstat" ] || [ "${TOKENS[1]}" == "sun.tools.jstat.Jstat" ] ||  [ -z "${TOKENS[1]}" ]
        then
            continue
        fi
        pid=${TOKENS[0]}
        curr_pid_name["$pid"]=${TOKENS[1]:-"<no name>"}

        # current heap in MB
        HEAP_MEMORY=$( (jstat -gc $pid 2>/dev/null || echo "0 0 0 0 0 0 0 0 0") | tail -n 1 | awk '{sum=$3+$4+$6+$8; print sum/1024}' )
        HEAP_MEMORY=${HEAP_MEMORY%.*}
        [ -z "$HEAP_MEMORY" ] && HEAP_MEMORY=0

        if [ ${prev_pid_max_heap["$pid"]+_} ] && [ $HEAP_MEMORY -lt ${prev_pid_max_heap[$pid]} ]; then
            curr_pid_max_heap["$pid"]=${prev_pid_max_heap["$pid"]}
        else
            curr_pid_max_heap["$pid"]=$HEAP_MEMORY
        fi

        # current RAM (RSS) in MB
        RAM_MEMORY=$(( $(cut -d' ' -f2 /proc/$pid/statm 2>/dev/null || echo "0") / 256 ))
        # statm 2nd field is resident pages; assume 4KB pages -> /256 to MB
        if [ ${prev_pid_max_ram["$pid"]+_} ] && [ $RAM_MEMORY -lt ${prev_pid_max_ram[$pid]} ]; then
            curr_pid_max_ram["$pid"]=${prev_pid_max_ram["$pid"]}
        else
            curr_pid_max_ram["$pid"]=$RAM_MEMORY
        fi

        # Configured Max heap (cache per pid)
        if [ -z "${pid_cfg_max_heap[$pid]}" ]; then
            pid_cfg_max_heap[$pid]=$(get_max_heap_cfg $pid)
        fi
        CFG_MAX_HEAP=${pid_cfg_max_heap[$pid]}

        cpuuse=$( (ps -p $pid -o %cpu= 2>/dev/null || echo "0") | tr -d ' ' )
        cpuuse=${cpuuse%.*}
        [ -z "$cpuuse" ] && cpuuse=0

        printf "%-6s %-30s %-20s %-20s %-20s %-20s %-20s %5i\n" \
            "$pid" \
            "${curr_pid_name[$pid]:0:30}" \
            "$(fmt_mem $HEAP_MEMORY)" \
            "$(fmt_mem ${curr_pid_max_heap[$pid]})" \
            "$(fmt_mem $CFG_MAX_HEAP)" \
            "$(fmt_mem $RAM_MEMORY)" \
            "$(fmt_mem ${curr_pid_max_ram[$pid]})" \
            "$cpuuse"
        CURR_LINES=$((CURR_LINES + 1))
    done

    PREV_LINES=$CURR_LINES

    unset prev_pid_max_heap
    declare -A prev_pid_max_heap
    unset prev_pid_max_ram
    declare -A prev_pid_max_ram

    for pid in "${!curr_pid_max_heap[@]}"; do
        prev_pid_max_heap[$pid]=${curr_pid_max_heap[$pid]}
    done
    for pid in "${!curr_pid_max_ram[@]}"; do
        prev_pid_max_ram[$pid]=${curr_pid_max_ram[$pid]}
    done

    if [ $RUNONCE -eq 1 ]; then
        exit
    fi

    sleep 1
done
