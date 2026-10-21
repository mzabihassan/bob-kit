# Triage playbook

## First 15 minutes

1. Impact: who is affected, how many, since when, which functions (e.g. "card payments fail for ~30% of requests since 09:42 UTC").
2. Severity per the organisation's matrix; incident commander, channel, next update time.
3. **What changed** in the last hours (table below); the most recent change near the start time is the first suspect.
4. Signals for the affected services: errors, latency, traffic, saturation.
5. An obvious safe mitigation? Propose it now (rollback, flag off, failover).

## What changed

| Source | Read-only check |
| --- | --- |
| Deployments | `argocd app history <app>`; `git log --since="6 hours ago"` in the GitOps repository; `kubectl rollout history deploy/<name>`; recent pipelines (`glab ci list`) |
| Configuration and flags | GitOps commits to values or ConfigMaps; the feature-flag service's audit log; secrets rotated in Secrets Manager |
| Infrastructure | Terraform or Schematics runs, cluster or worker upgrades, node replacements, IAM or context-based restriction changes, network rules |
| Certificates | `echo \| openssl s_client -connect <host>:443 -servername <host> 2>/dev/null \| openssl x509 -noout -enddate`; certificate expiry alerts |
| Dependencies | Status pages of IBM Cloud services and partners; downstream teams' channels |
| Data and load | Traffic graphs (campaigns, month-end, batch overlap), data volume growth, a new large customer or file |
| Scheduled work | Batch jobs and cron schedules (time zone and DST changes), database maintenance, backups |

## Signals (the golden signals per service)

- **Errors**: HTTP 5xx and 4xx rates by endpoint; exceptions grouped by type and message in IBM Cloud Logs (filter by service, then by correlation id to follow one request across services).
- **Latency**: p50, p95 and p99 by endpoint; a rising p99 with a stable p50 points to contention (locks, pools, GC).
- **Traffic**: requests per second against the usual pattern; a drop can mean an upstream failure, not a quiet day.
- **Saturation**: CPU (and CPU **throttling**), memory, JVM heap and GC, thread pools, HikariCP connections (`hikaricp_connections_pending`, `…_active`), Kafka consumer lag, database sessions and locks, disk.
- Kubernetes: `kubectl get pods -o wide`, `kubectl get events --sort-by=.lastTimestamp`, restarts and `OOMKilled`.

## Symptom → likely causes

| Symptom | Check first |
| --- | --- |
| Latency up, errors up, DB-backed endpoints | `HikariPool-… Connection is not available, request timed out`: pool exhausted by slow queries, locks or leaks → database sessions, blocking chains, long transactions |
| Latency spikes, CPU high | GC pauses (heap near the limit), CPU throttling (limits too low), a hot loop or expensive request pattern → thread dump, GC metrics |
| Pods restarting | `OOMKilled` (heap or native memory vs the container limit), liveness probe failing under load, startup failure after a config change → `kubectl describe`, `logs --previous` |
| 5xx right after a deployment | The new version: errors in its logs, config or secret missing, migration problem → roll back first if impact is high |
| 401/403 everywhere | Expired or rotated credentials, identity provider issue, IAM or CBR change, clock skew on tokens |
| TLS handshake errors | Expired certificate, a new CA not in the truststore, hostname mismatch |
| Timeouts to one dependency | Dependency degraded, network or DNS change, firewall or NetworkPolicy, connection pool to it exhausted |
| Messages piling up | Consumer down or crashing on a poison message (DLQ), consumer lag from slow processing, rebalancing loops |
| Batch did not run or ran twice | Scheduler lock (ShedLock) stuck or missing, time zone or DST, pod restarts during the job, two instances without a lock |
| Database errors | Max connections reached, disk or tablespace full, deadlocks, failover in progress, long-running migration |
| Frontend blank page or broken after a release | Chunk load errors (cached `index.html` pointing to removed assets), CSP blocking scripts, wrong runtime configuration or API URL |
| Only some users or regions affected | One zone or node, one tenant's data, one partner, a canary or feature-flag cohort, a CDN edge |
