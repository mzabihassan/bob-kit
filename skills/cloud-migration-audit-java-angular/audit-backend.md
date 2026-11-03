# Backend audit guide — distributed architecture (ARCH) and Spring Boot/database (APP)

Start from the brief's leads, read the exact lines, then follow the call chain only as far as the judgement needs. Replica counts come from the infrastructure repository (Helm values per environment, HPA max): a defect that is harmless with 1 replica is real when production runs more. When the brief's leads show nothing for a control, search once (`grep -rn`) before concluding NOT VERIFIED or NOT APPLICABLE.

## ARCH — multi-instance behaviour

| Control | Look at | DONE | Typical failure after migration |
| --- | --- | --- | --- |
| ARCH-01 scheduled jobs | every `@Scheduled`, `TaskScheduler`, `Timer`, `@EnableScheduling`; ShedLock `@SchedulerLock`, Quartz, Kubernetes `CronJob` | each job locked, clustered, leader-elected, moved to a CronJob, or proven harmless when run N times in parallel | N replicas send N e-mails, generate N invoices, run N exports, or fight over the same rows |
| ARCH-02 lock config | `@EnableSchedulerLock(defaultLockAtMostFor)`, `LockProvider` bean (`JdbcTemplateLockProvider` with `usingDbTime()`), the `shedlock` table in the migrations, `lockAtMostFor`/`lockAtLeastFor`, unique lock names | lock table created by a migration, `lockAtMostFor` > job duration, DB time used | lock never taken (no `@EnableSchedulerLock` or table missing → exception swallowed), job runs twice after a pod kill, or stays blocked for hours |
| ARCH-03 Quartz | `spring.quartz.job-store-type=jdbc`, `org.quartz.jobStore.isClustered=true`, table scripts | clustered JDBC store | in-memory RAMJobStore: every pod fires every trigger |
| ARCH-04 shared state | `static` mutable collections/counters, singleton beans with mutable fields, in-memory maps used to decide business logic (rate limits, sequences, "already processed" sets) | only caches or per-instance technical state | each pod has its own truth: limits multiplied by N, duplicates, lost updates after restart |
| ARCH-05 caches | `@Cacheable` with Caffeine/ConcurrentMapCache, hand-made maps, TTLs, eviction on update | reference data with short TTL, or a distributed cache for data that must be consistent | pod A updates, pod B serves the stale value until restart |
| ARCH-06 sessions | `HttpSession`, `@SessionScope`, `@SessionAttributes`, `server.servlet.session.*`, Spring Session dependency and store, ingress affinity annotations | stateless tokens, or Spring Session on Redis/JDBC | user state lost or mixed when the load balancer sends the next request to another pod; logouts on every rollout |
| ARCH-07 filesystem | `new File`, `Files.write`, `Paths.get`, upload/export directories, `java.io.tmpdir` used across requests, mounted volumes (`emptyDir` is per pod and ephemeral) | object storage (COS) or a shared volume with ReadWriteMany for shared files; local disk only within one request | file written by pod A not found by pod B; files lost at every restart; disk fills the node |
| ARCH-08 idempotency | POST/PUT handlers creating records, payment or notification calls, message listeners; unique constraints, idempotency keys, dedup tables | duplicates impossible or harmless | client retry after a timeout or a redelivered message creates a second order/payment |
| ARCH-09 background work | `@Async`, executors, in-memory queues, `CompletableFuture` | short tasks drained at shutdown, or persisted (outbox, job table, broker) | work in flight lost when Kubernetes stops the pod during a rollout |
| ARCH-10 consumers | `@KafkaListener` group IDs and concurrency, JMS/MQ listeners (shared vs exclusive), ordering needs, DLQ | consumer group/queue semantics give the intended parallelism; poison messages go to a DLQ | N pods each consume every message (topic subscription instead of shared queue), or ordering broken |
| ARCH-11 batch | Spring Batch `JobRepository` datasource, job parameters, `JobLauncher` triggers | job repository in the shared DB, single instance per job, restartable | two pods launch the same job; a failed job cannot restart |
| ARCH-12 concurrency | `synchronized`, `ReentrantLock` protecting DB updates; `@Version`, `SELECT … FOR UPDATE`, constraints | DB-level control | JVM lock protects one pod only: lost updates between pods |
| ARCH-13 identity | hostname/IP as ID or for routing, JVM counters for IDs | DB sequences/UUIDs | colliding IDs between pods; IDs reset at restart |

## APP — Spring Boot and database in the cloud

| Control | Look at | DONE |
| --- | --- | --- |
| APP-01 pool capacity | `spring.datasource.hikari.maximum-pool-size` (default 10) × max replicas (HPA max, + `maxSurge` pods during rollouts) for every service on the same database vs the database limit | the product stays under the limit with headroom; the limit is known (provider plan or DBA). Without the limit: NOT VERIFIED, with the computed total in the summary |
| APP-02 pool tuning | `connection-timeout`, `max-lifetime` (below firewall/proxy idle timeouts), `keepalive-time`, `leak-detection-threshold` | explicit values adapted to the network path |
| APP-03 migrations at startup | Liquibase/Flyway enabled in the app, lock table (`DATABASECHANGELOGLOCK`, Flyway lock), startup time vs probes; a Kubernetes Job or init step running migrations instead | migrations run once; a lock left by a killed pod is recoverable (documented release); probes tolerate the duration |
| APP-04 rolling compatibility | `dropColumn`, `renameColumn`, `modifyDataType`, `DROP`/`RENAME` in changelogs vs code of the previous release | expand → migrate → contract across releases |
| APP-05 engine compatibility | native queries, `@Query(nativeQuery = true)`, JDBC templates, changelog SQL, functions: `NVL`, `ROWNUM`, `SYSDATE`, `DUAL`, `DECODE`, `CONNECT BY`, `(+)`, `VARCHAR2`, `NUMBER(p)`, `MINUS`, sequences `.NEXTVAL`, empty string = NULL semantics, case of quoted identifiers | none left, or the former engine is still the target (then NOT APPLICABLE) |
| APP-06 timeouts | `RestTemplate` (no timeouts by default), `WebClient`, `RestClient`, Feign, SOAP clients, JDBC `socketTimeout`, `spring.http.client.*` | connect and read timeouts on every remote call |
| APP-07 resilience | Resilience4j/Spring Retry annotations and config; retries only on idempotent calls; fallbacks | slow or failing dependencies cannot exhaust threads |
| APP-08 externalised config | hardcoded hosts/ports/paths (`*.intranet`, `*.local`, IPs, `C:\`, `/opt/app/…`), `application-prod.yml` with literal endpoints, profiles | environment values from env/ConfigMap/Secret; no on-premise endpoint left |
| APP-09 TLS | truststore/keystore paths and how they reach the pod, `javax.net.ssl.*`, trust-all managers, disabled hostname verification | certificates from secrets/platform, rotation without rebuild, verification on |
| APP-10 health | `management.endpoint.health.probes.enabled` (automatic on Kubernetes), health groups, exposure, `management.server.port` | liveness/readiness groups used by the probes; liveness without external dependencies |
| APP-11 shutdown | `server.shutdown=graceful` (default from Spring Boot 3.4), `spring.lifecycle.timeout-per-shutdown-phase` (default 30s), listeners/executors stop | in-flight requests finish within the pod's grace period |
| APP-12 logs | logback/log4j2 appenders (file appenders are an on-premise leftover), JSON/structured logging (`logging.structured.format.console` from Boot 3.4, logstash encoder), trace IDs in the pattern | stdout, parseable, correlation IDs |
| APP-13 metrics/tracing | Micrometer registry, `management.tracing`, OpenTelemetry agent, propagation on clients | scrapeable metrics, propagated traces |
| APP-14 dependency failures | readiness including critical dependencies (`management.endpoint.health.group.readiness.include`), lazy connections, retries at startup | not-ready instead of crash loop |
| APP-15 transactions/events | DB write + message publish in one method without outbox; XA/JTA | outbox or equivalent; no XA reliance |
| APP-16 secrets | `${DB_PASSWORD}` placeholders vs literals, Spring Cloud Vault/IBM Secrets Manager integration | injected at runtime, rotation without rebuild |

For database migrations and engine differences, `../sql-database-engineer/schema-migrations.md` and `../sql-database-engineer/oracle-to-postgres.md` go deeper when installed alongside this skill.

## Severity hints

CRITICAL: duplicated money movements or notifications, data loss, a query that fails on the new engine on a main flow, a secret in Git usable in production. HIGH: duplicate jobs with side effects, session loss on main journeys, files lost between pods, no timeouts on a critical dependency, pool total above the database limit. MEDIUM: stale caches of reference data, missing graceful shutdown with short requests, file logging. Lower when the affected flow is rare or protected elsewhere; say why.
