```bash
# ── Thread count (quick) ──────────────────────────────────────────────────────
ps -eLf | grep <pid> | wc -l                                                  # OS-level thread count
cat /proc/<pid>/status | grep Threads                                         # kernel thread count

# ── jstack ────────────────────────────────────────────────────────────────────
jstack <pid>                                                                  # full thread dump
jstack -l <pid>                                                               # include lock info
jstack <pid> | grep '"' | awk -F'"' '{print $2}' | sort | uniq -c | sort -nr | head -20   # top thread names by count
jstack <pid> | grep -E '".*"' | wc -l                                        # total named threads
jstack <pid> | grep -c "java.lang.Thread.State"                              # total thread states
jstack <pid> | grep "java.lang.Thread.State" | sort | uniq -c | sort -nr    # threads grouped by state
jstack <pid> | grep -A1 "java.lang.Thread.State" | grep -v "^--$"           # name + state pairs

# ── jcmd ──────────────────────────────────────────────────────────────────────
jcmd <pid> Thread.print                                                       # full thread dump (preferred over jstack)
jcmd <pid> Thread.print | grep '^"' | wc -l                                  # count of named threads
jcmd <pid> Thread.print | grep "java.lang.Thread.State" | sort | uniq -c    # threads by state
jcmd <pid> VM.native_memory                                                   # native memory including thread memory
jcmd <pid> GC.heap_info                                                       # heap info (context for thread pressure)

# ── jps (find pid first) ──────────────────────────────────────────────────────
jps -l                                                                        # list all JVM pids with main class
jps -lv                                                                       # include JVM flags

# ── top / ps ─────────────────────────────────────────────────────────────────
top -H -p <pid>                                                               # per-thread CPU in real time
ps -T -p <pid>                                                                # all threads of a process
ps -T -p <pid> -o pid,tid,pcpu,pmem,comm                                     # threads with CPU/mem stats

# ── /proc (no JDK tools needed) ───────────────────────────────────────────────
ls /proc/<pid>/task | wc -l                                                   # thread count via procfs
cat /proc/<pid>/task/<tid>/status                                             # per-thread status
```

The most useful combos in practice:

- **Find blocked/waiting threads fast** → `jstack <pid> | grep "java.lang.Thread.State" | sort | uniq -c | sort -nr`
- **Spot CPU-hogging thread** → `top -H -p <pid>` to get TID → convert TID to hex → grep in `jstack` output: `jstack <pid> | grep -A30 "nid=0x<hex>"`
- **No JDK on PATH** → fall back to `/proc/<pid>/task` and `ps -T`
