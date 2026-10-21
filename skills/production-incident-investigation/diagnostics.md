# Diagnostics and evidence capture

Read-only commands unless stated otherwise. Capture evidence **before** any restart, and store dumps where the organisation allows (they may contain personal data and secrets).

## JVM (Spring Boot)

| Need | Command |
| --- | --- |
| Thread dump (blocked threads, deadlocks, pool saturation) | `jcmd <pid> Thread.print -l` (take 3 dumps ~10 s apart to see what is stuck); or `GET /actuator/threaddump` if exposed internally; or `kill -3 <pid>` (the dump goes to stdout, so to the pod logs) |
| Heap and GC state | `jcmd <pid> GC.heap_info`; GC logs if enabled (`-Xlog:gc*`); Micrometer metrics `jvm_memory_used_bytes`, `jvm_gc_pause_seconds` |
| Recording for CPU and allocation issues | `jcmd <pid> JFR.start duration=120s filename=/tmp/incident.jfr` (low overhead), then copy the file out |
| Heap dump (memory leaks) | `jcmd <pid> GC.heap_dump /tmp/heap.hprof`: pauses the JVM and writes a file the size of the heap; contains personal data. Only with approval and enough disk space |
| JVM flags and system properties | `jcmd <pid> VM.flags`, `jcmd <pid> VM.system_properties` |

In containers the JVM is usually PID 1. Images without a shell or JDK tools (distroless, JRE-only): use an ephemeral debug container sharing the process namespace, `kubectl debug -it <pod> --image=<approved-jdk-image> --target=<container>`. The JDK tools must run as the same user as the target JVM, and attaching requires access to its `/tmp`; when that is not possible, use the actuator endpoints or `kill -3` from the debug container. Creating a debug container is a change to the pod: it needs approval in production.

Reading a thread dump: many threads `BLOCKED` on the same monitor → lock contention; `http-nio-*` threads all waiting in `HikariPool.getConnection` → database pool exhaustion; threads in `SocketInputStream.read` towards one host → a slow dependency without a timeout; `Found one Java-level deadlock` → a deadlock with both stacks.

## Kubernetes / OpenShift

```bash
kubectl -n <ns> get pods -o wide                         # restarts, nodes, readiness
kubectl -n <ns> describe pod <pod>                       # last state (OOMKilled, exit codes), probe failures, events
kubectl -n <ns> logs <pod> -c <container> --previous     # logs of the crashed instance
kubectl -n <ns> get events --sort-by=.lastTimestamp
kubectl -n <ns> top pods                                 # needs metrics-server
kubectl -n <ns> rollout history deploy/<name>
kubectl get nodes; kubectl describe node <node>          # pressure conditions, allocatable resources
```
Check CPU throttling and memory against limits in Sysdig / IBM Cloud Monitoring; check NetworkPolicies and Services or Endpoints when traffic does not arrive (`kubectl -n <ns> get endpoints <svc>`).

## Database

- PostgreSQL: `pg_stat_activity` (long-running and `idle in transaction` sessions, wait events), `pg_blocking_pids(pid)` for blocking chains, `pg_stat_statements` for the statements consuming the most time, connection count against `max_connections`.
- Oracle: `V$SESSION` (status, `BLOCKING_SESSION`, `EVENT`, `SQL_ID`), `V$SQL` for the costly statements, alert log entries (`ORA-00060` deadlocks, `ORA-01555`, tablespace full).
- Killing a session or cancelling a query is a production change: propose it with the blocking evidence; DBAs usually execute it. Details are in the `sql-database-engineer` skill (`concurrency-transactions.md`) if installed.

## Network and TLS

```bash
nslookup <host>; getent hosts <host>                     # DNS from inside the pod (debug container if needed)
curl -sv --max-time 5 https://<host>/health -o /dev/null # TLS handshake, status, timing
echo | openssl s_client -connect <host>:443 -servername <host> 2>/dev/null | openssl x509 -noout -subject -issuer -enddate
```

## Logs

Start from one failing request: find its correlation or trace id in the error, then query all services for it (IBM Cloud Logs or the organisation's log platform) to build the request's path. Group errors by exception type and message over time to see when each started; the first new error type after the start time is a strong clue. Compare with the same window the day or week before.

## Frontend (Angular / React)

Browser console and network tab of an affected user (or a synthetic check): chunk-loading errors after a release (an old `index.html` cached, assets removed), CSP violations, failed API calls (status, CORS), wrong runtime configuration. Check the CDN or web-server cache headers for `index.html`.
