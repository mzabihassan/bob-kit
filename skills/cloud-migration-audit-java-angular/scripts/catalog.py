"""Control catalog of the cloud migration audit: what is assessed, per domain, with stable IDs.

Each control is a requirement of a Java/Spring Boot + Angular application running as several
containers on Kubernetes (IBM Cloud), deployed by GitLab CI, JFrog and Argo CD. Agents assess every
control of their domain (DONE, PARTIALLY DONE, NOT DONE, NOT VERIFIED, NOT APPLICABLE) with
evidence, and raise findings for what is missing or risky.

Fields: id (stable, never reused), domain, title, done (what DONE requires), applies (when the
control is applicable), severity (default severity of a finding when the control is NOT DONE),
runtime (True: full verification needs live access to a cluster, cloud account, JFrog or Argo CD),
gate (True: the control must be DONE, or verified, before a GO; NOT VERIFIED makes it a condition).
Standard library only.
"""

DOMAINS = {
    "ARCH": "Cloud architecture and multi-instance compatibility",
    "APP": "Spring Boot and database",
    "K8S": "Kubernetes and cloud infrastructure",
    "CTR": "Docker and container security",
    "CICD": "GitLab CI/CD, JFrog and Argo CD",
    "WEB": "Angular and end-to-end integration",
    "OPS": "Observability, resilience and operations",
}

# Agent groups: six specialised agents for large estates, three for small ones (see SKILL.md).
GROUPS = {
    "6": {"backend": ["ARCH", "APP"], "kubernetes": ["K8S"], "containers": ["CTR"], "delivery": ["CICD"],
          "frontend": ["WEB"], "operations": ["OPS"]},
    "3": {"backend": ["ARCH", "APP"], "platform": ["K8S", "CTR", "CICD"], "frontend-ops": ["WEB", "OPS"]},
}
GUIDES = {"ARCH": "audit-backend.md", "APP": "audit-backend.md", "K8S": "audit-platform.md", "CTR": "audit-platform.md",
          "CICD": "audit-platform.md", "WEB": "audit-frontend-ops.md", "OPS": "audit-frontend-ops.md"}

STATUSES = ["DONE", "PARTIALLY DONE", "NOT DONE", "NOT VERIFIED", "NOT APPLICABLE"]
SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


def C(cid, title, done, applies="always", severity="HIGH", runtime=False, gate=False):
    return {"id": cid, "domain": cid.split("-")[0], "title": title, "done": done, "applies": applies,
            "severity": severity, "runtime": runtime, "gate": gate}


CONTROLS = [
    # A. Cloud architecture and multi-instance compatibility
    C("ARCH-01", "Scheduled jobs run once across replicas",
      "Every @Scheduled/timer job either holds a distributed lock (ShedLock, DB lock), runs in Quartz clustered mode, "
      "uses leader election, or is moved to a Kubernetes CronJob/external scheduler; duplicate execution is harmless otherwise.",
      "the backend schedules work", "HIGH", gate=True),
    C("ARCH-02", "Distributed lock configuration is safe",
      "Lock provider backed by a shared store with its table/migration; lockAtMostFor longer than the job and shorter than "
      "the acceptable outage; lock released or expiring after a pod crash; lock names unique.",
      "a distributed lock is used", "MEDIUM"),
    C("ARCH-03", "Quartz runs clustered", "JDBC JobStore with isClustered=true, shared tables, misfire handling.",
      "Quartz is used", "HIGH"),
    C("ARCH-04", "No shared mutable state in the JVM used as source of truth",
      "Static or singleton mutable collections/counters are only caches or per-instance technical state; business state "
      "lives in the database or a shared store.", severity="HIGH", gate=True),
    C("ARCH-05", "Caches are consistent across instances",
      "Local caches hold reference data with a bounded TTL or explicit invalidation acceptable per instance, or a "
      "distributed cache (Redis, Hazelcast) is used for data that must be consistent.", "caching is used", "MEDIUM"),
    C("ARCH-06", "No dependency on HTTP session affinity",
      "Stateless authentication (tokens) or externalised sessions (Spring Session on Redis/JDBC); no business state in "
      "HttpSession unless replicated; no reliance on sticky sessions.", "the backend serves HTTP", "HIGH", gate=True),
    C("ARCH-07", "No local filesystem for durable or shared data",
      "Uploads, exports, generated files and shared temporary data use object storage (COS) or a shared volume with the "
      "right access mode; local disk only for per-request scratch.", severity="HIGH", gate=True),
    C("ARCH-08", "State-changing operations and consumers are idempotent",
      "Retries, double submits and duplicate message deliveries cannot create duplicates or double side effects "
      "(idempotency keys, unique constraints, dedup tables).", "the backend changes state", "HIGH"),
    C("ARCH-09", "Background work survives pod restarts",
      "@Async/in-memory queued work is either short and drained at shutdown or persisted (outbox, broker, job table) "
      "and resumable.", "asynchronous processing exists", "MEDIUM"),
    C("ARCH-10", "Message consumption is safe with several instances",
      "Consumer groups/partitions or exclusive queues give the intended parallelism and ordering; poison messages and "
      "redelivery are handled.", "message listeners exist", "HIGH"),
    C("ARCH-11", "Batch jobs are single-execution and restartable",
      "Spring Batch JobRepository in the shared database, job parameters preventing concurrent instances, restart "
      "after failure.", "batch jobs exist", "MEDIUM"),
    C("ARCH-12", "Concurrent updates are controlled in the database",
      "Optimistic (@Version) or pessimistic DB locking and constraints protect shared data; JVM synchronized/locks are "
      "not relied upon across instances.", "the backend changes shared data", "HIGH"),
    C("ARCH-13", "No instance identity assumptions",
      "No hostname/IP/JVM-local counters used as business identifiers or for routing; IDs from the DB or UUIDs.",
      severity="MEDIUM"),

    # E. Spring Boot and database
    C("APP-01", "Aggregate connection pools fit database capacity",
      "Pool size x maximum replicas (HPA max, during rolling updates +surge) for every service sharing the database stays "
      "below the database connection limit with headroom.", "a relational database is used", "HIGH", runtime=True, gate=True),
    C("APP-02", "Connection pool is tuned for the cloud",
      "Hikari maximumPoolSize, connectionTimeout, maxLifetime below network/firewall idle timeouts, keepalive; leak "
      "detection in non-prod.", "a relational database is used", "MEDIUM"),
    C("APP-03", "Schema migrations are safe with concurrent startups",
      "Liquibase/Flyway run once (lock table, or a dedicated Job/init step), a stuck lock after a crash is recoverable, "
      "startup time covered by probes.", "schema migrations run", "HIGH", gate=True),
    C("APP-04", "Migrations are compatible with rolling deployments",
      "Expand/contract: no drop/rename/type change used by the previous version in the same release; old and new pods "
      "run against the same schema.", "schema migrations run", "HIGH"),
    C("APP-05", "Database engine compatibility is complete",
      "No vendor-specific SQL of the former engine (e.g. Oracle NVL, ROWNUM, SYSDATE, DUAL, CONNECT BY) left in native "
      "queries, changelogs or functions; dialect, sequences, types and case sensitivity checked.",
      "the database engine changed during the migration", "HIGH"),
    C("APP-06", "Outbound calls have timeouts",
      "Every HTTP/SOAP/JDBC/broker client used for remote calls sets connect and read timeouts.", "remote calls exist", "HIGH"),
    C("APP-07", "Remote calls are resilient",
      "Retries with backoff only on idempotent calls, circuit breakers/bulkheads for slow or failing dependencies, "
      "sensible fallbacks.", "remote calls exist", "MEDIUM"),
    C("APP-08", "Configuration is externalised",
      "No hardcoded hosts, ports, paths, credentials or on-premise endpoints in code or packaged config; environment-"
      "specific values come from env/ConfigMaps/Secrets; profiles are consistent.", severity="HIGH", gate=True),
    C("APP-09", "TLS and certificates are cloud-managed",
      "Truststores/certificates mounted from secrets or the platform, rotation possible without rebuild, no disabled "
      "certificate or hostname verification.", "TLS is used", "HIGH"),
    C("APP-10", "Health endpoints fit Kubernetes probes",
      "Liveness and readiness health groups available; liveness excludes external dependencies; actuator exposure "
      "limited (separate management port or restricted endpoints).", "the backend runs on Kubernetes", "HIGH"),
    C("APP-11", "Graceful shutdown is enabled",
      "server.shutdown=graceful (default from Spring Boot 3.4) and a shutdown timeout compatible with the pod's "
      "termination grace period; listeners and executors stop cleanly.", severity="MEDIUM"),
    C("APP-12", "Logs are cloud-ready",
      "Logs to stdout (no file appenders), structured (JSON) or parseable, with trace/correlation IDs in every line.",
      severity="MEDIUM"),
    C("APP-13", "Metrics and tracing are instrumented",
      "Micrometer metrics exposed for scraping; tracing (Micrometer Tracing/OpenTelemetry) propagates context on "
      "inbound and outbound calls.", severity="MEDIUM"),
    C("APP-14", "Startup and dependency failures are handled",
      "The application starts or becomes not-ready (instead of crash-looping) when a dependency is down; readiness "
      "reflects critical dependencies; no blocking remote calls in constructors.", severity="MEDIUM"),
    C("APP-15", "Transactions and events are consistent",
      "No reliance on XA/global transactions; DB writes plus message publishing use an outbox or equivalent; "
      "transaction boundaries are explicit.", "the backend writes data and publishes events or calls services", "MEDIUM"),
    C("APP-16", "Secrets are injected at runtime",
      "Credentials come from env/mounted Kubernetes Secrets fed by a secret manager; rotation does not need a rebuild.",
      severity="HIGH", gate=True),

    # B. Kubernetes and cloud infrastructure
    C("K8S-01", "Resource requests and limits are set",
      "Every container defines CPU and memory requests and a memory limit consistent with the JVM/Node footprint.",
      severity="HIGH", gate=True),
    C("K8S-02", "JVM memory matches the container limit",
      "Heap sized relative to the container (MaxRAMPercentage) or a fixed -Xmx well below the memory limit, leaving "
      "room for metaspace, threads and buffers.", "a JVM runs in a container", "HIGH", gate=True),
    C("K8S-03", "Production runs several replicas spread across failure domains",
      "At least 2 replicas (or HPA min >= 2) with anti-affinity or topology spread across nodes/zones.", severity="HIGH",
      gate=True),
    C("K8S-04", "Autoscaling is configured and bounded",
      "HPA with realistic min/max and metrics; max replicas consistent with database capacity and quotas; replicas not "
      "fighting the GitOps diff.", severity="MEDIUM"),
    C("K8S-05", "Readiness probes target the right endpoint",
      "Readiness probe on the application's readiness endpoint and port, with sane period/threshold.", severity="HIGH",
      gate=True),
    C("K8S-06", "Liveness probes cannot cause restart storms",
      "Liveness does not depend on databases or external systems; thresholds tolerate GC pauses and load.",
      severity="HIGH"),
    C("K8S-07", "Slow starts are protected",
      "startupProbe (or adequate initialDelay) covers JVM start and schema migrations.", severity="MEDIUM"),
    C("K8S-08", "Termination is graceful",
      "terminationGracePeriodSeconds >= preStop delay + application shutdown timeout; preStop lets endpoints "
      "deregister.", severity="MEDIUM"),
    C("K8S-09", "Rolling updates and rollback are safe",
      "RollingUpdate with maxUnavailable that keeps capacity, revision history kept, readiness gating the rollout.",
      severity="MEDIUM"),
    C("K8S-10", "Disruptions keep the service available",
      "PodDisruptionBudget for every multi-replica workload, compatible with node drains.", severity="MEDIUM"),
    C("K8S-11", "Configuration is in ConfigMaps, not in images",
      "Environment configuration in ConfigMaps/values per environment; no secrets in ConfigMaps or values.",
      severity="MEDIUM"),
    C("K8S-12", "Secrets come from a secret manager, not Git",
      "No plaintext secrets in manifests, values or Secret objects in Git; External Secrets/Secrets Manager/CSI or "
      "sealed secrets.", severity="CRITICAL", gate=True),
    C("K8S-13", "Persistent storage is correct", "PVC access mode, storage class, capacity and backup match the usage.",
      "persistent volumes are used", "HIGH"),
    C("K8S-14", "Service, ingress and routing are consistent",
      "Ports, paths, TLS, timeouts and body sizes of Service/Ingress/Route match the applications.", severity="HIGH",
      gate=True),
    C("K8S-15", "Pods run with a restricted security context",
      "runAsNonRoot, allowPrivilegeEscalation=false, dropped capabilities, read-only root filesystem where possible, "
      "seccomp RuntimeDefault.", severity="HIGH"),
    C("K8S-16", "Service accounts and RBAC follow least privilege",
      "Dedicated service account, token not mounted when unused, minimal Roles.", severity="MEDIUM"),
    C("K8S-17", "Network policies restrict traffic", "Default deny with explicit ingress/egress rules per workload.",
      severity="MEDIUM"),
    C("K8S-18", "Environments are isolated and consistent",
      "Namespaces/clusters per environment; values per environment differ only where intended.", severity="MEDIUM"),
    C("K8S-19", "Dependencies have no single point of failure",
      "Databases, caches, brokers and identity provider are managed or highly available.", severity="HIGH", runtime=True),

    # C. Docker and container security
    C("CTR-01", "Base images are supported, minimal and trusted",
      "Supported versions from the internal registry/JFrog mirror, minimal runtime images (JRE/distroless/unprivileged "
      "nginx), pinned versions.", severity="HIGH"),
    C("CTR-02", "Images are built in multiple stages",
      "Build tools, sources and caches stay out of the runtime image.", severity="LOW"),
    C("CTR-03", "Containers run as non-root", "USER with a numeric non-root UID in the image (and runAsNonRoot in pods).",
      severity="HIGH", gate=True),
    C("CTR-04", "No secrets in images", "No credentials, keys, .npmrc/settings.xml with tokens, or secret ENV/ARG baked into "
      "layers.", severity="CRITICAL", gate=True),
    C("CTR-05", "Images are scanned before deployment",
      "Container scanning (JFrog Xray, Trivy, GitLab) with a blocking threshold before promotion.", severity="HIGH",
      gate=True),
    C("CTR-06", "Image references are immutable and traceable",
      "No 'latest' or moving tags in deployments; tags or digests tie each image to a commit/build.", severity="HIGH",
      gate=True),
    C("CTR-07", "Dependencies are reproducible and from trusted sources",
      "Lockfiles, wrapper checksums, dependencies through JFrog remote repositories.", severity="MEDIUM"),
    C("CTR-08", "Image surface is minimal", "Only needed ports and packages; no curl|sh, no debug tools in runtime.",
      severity="LOW"),
    C("CTR-09", "Filesystem layout works read-only",
      "Writable paths explicit (tmp/emptyDir), no world-writable files, no reliance on writing to the image filesystem.",
      severity="LOW"),
    C("CTR-10", "Process receives signals", "Exec-form ENTRYPOINT (or an init) so SIGTERM reaches the JVM/nginx.",
      severity="MEDIUM"),

    # D. GitLab CI/CD, JFrog and Argo CD
    C("CICD-01", "Pipelines build and test", "Build, unit and integration tests run on every change before packaging.",
      severity="HIGH"),
    C("CICD-02", "Quality gate blocks", "SonarQube (or equivalent) quality gate fails the pipeline on protected branches.",
      severity="MEDIUM"),
    C("CICD-03", "Dependencies are scanned", "SCA (JFrog Xray/audit, GitLab dependency scanning, OWASP) with a blocking policy.",
      severity="HIGH"),
    C("CICD-04", "Artifacts are versioned in JFrog with build info",
      "Images/artifacts published to JFrog with immutable versions and build info linking commit, pipeline and artifact.",
      severity="MEDIUM", runtime=True),
    C("CICD-05", "The same artifact is promoted across environments",
      "Build once; promotion (JFrog promotion or tag) instead of rebuilding per environment.", severity="MEDIUM"),
    C("CICD-06", "What is built is what is deployed",
      "Image name/tag produced by CI matches what Helm values/Argo CD deploy per environment.", severity="HIGH", gate=True),
    C("CICD-07", "Helm charts are validated", "Chart versioning, helm lint/template validation in CI, values per environment.",
      "Helm is used", "LOW"),
    C("CICD-08", "Argo CD applications are well configured",
      "Pinned target revisions for production, sync policy (automated with prune/selfHeal or documented manual), "
      "ignoreDifferences for HPA-managed replicas, correct destination.", "Argo CD is used", "MEDIUM"),
    C("CICD-09", "Deployments go through GitOps only",
      "No helm/kubectl deployments from CI to Argo CD-managed environments; drift is visible and corrected.",
      "Argo CD is used", "HIGH"),
    C("CICD-10", "Production deployments are approved and protected",
      "Protected branches/tags/environments, manual approval or change gate for production.", severity="HIGH", gate=True),
    C("CICD-11", "Rollback is defined", "Rollback by Git revert/previous artifact, documented and exercised.", severity="MEDIUM"),
    C("CICD-12", "Pipelines do not expose secrets",
      "Masked/protected CI variables or vault integration; no secrets in pipeline files or echoed in logs.",
      severity="CRITICAL", gate=True),

    # F. Angular and end-to-end integration
    C("WEB-01", "Frontend configuration per environment does not require on-premise values",
      "API base URLs and identity settings come from runtime configuration or relative paths, or per-environment builds "
      "with cloud values; no on-premise hostnames.", severity="HIGH", gate=True),
    C("WEB-02", "Frontend API routes match the cloud ingress",
      "The paths the frontend calls are exposed by the ingress and the backend context path.", severity="HIGH", gate=True),
    C("WEB-03", "Authentication flow is configured for the cloud",
      "OIDC/SAML issuer, client, redirect URIs and logout per environment; PKCE for public clients; token refresh.",
      "the frontend authenticates users", "HIGH"),
    C("WEB-04", "Tokens and cookies are handled safely",
      "No tokens in localStorage when avoidable; tokens sent only to the own API; Secure/HttpOnly/SameSite cookies.",
      "the frontend authenticates users", "MEDIUM"),
    C("WEB-05", "CORS and CSRF are consistent",
      "Allowed origins list the cloud frontends (no wildcard with credentials); CSRF protection matches the auth model.",
      severity="MEDIUM"),
    C("WEB-06", "Security headers and CSP are served",
      "CSP, HSTS, X-Content-Type-Options, frame-ancestors, Referrer-Policy at nginx or ingress.", severity="MEDIUM"),
    C("WEB-07", "SPA routing fallback and base href work behind the ingress",
      "Deep links fall back to index.html; base href matches the ingress path.", severity="MEDIUM"),
    C("WEB-08", "Caching does not serve stale application versions",
      "Hashed assets cached long, index.html (and runtime config) not cached.", severity="MEDIUM"),
    C("WEB-09", "Old frontend and new backend coexist during rollouts",
      "API changes are backward compatible or versioned; frontend tolerates both versions during rolling updates.",
      severity="MEDIUM"),
    C("WEB-10", "No session affinity needed by the frontend",
      "No server-side session, websocket or SSE flow that needs a sticky backend without configured affinity.",
      severity="MEDIUM"),
    C("WEB-11", "Frontend container is unprivileged",
      "nginx runs as non-root on an unprivileged port, with minimal configuration.", severity="MEDIUM"),
    C("WEB-12", "Backend unavailability is handled in the UI",
      "HTTP errors and timeouts are handled with feedback and safe retries.", severity="LOW"),

    # G. Observability, resilience and operations
    C("OPS-01", "Logs are centralised and searchable",
      "Logs shipped to IBM Cloud Logs/ELK with correlation IDs searchable across frontend, backend and ingress.",
      severity="HIGH", runtime=True, gate=True),
    C("OPS-02", "Metrics are scraped and visualised", "ServiceMonitor/annotations scrape the apps; dashboards exist.",
      severity="MEDIUM", runtime=True),
    C("OPS-03", "Distributed tracing works end to end", "Traces from ingress/frontend to backend and dependencies.",
      severity="LOW", runtime=True),
    C("OPS-04", "Alerts detect incidents",
      "Alert rules on availability, error rate, latency, restarts and saturation, routed to on-call.", severity="HIGH",
      runtime=True, gate=True),
    C("OPS-05", "Synthetic monitoring checks user journeys", "External probes on public endpoints and login.",
      severity="LOW", runtime=True),
    C("OPS-06", "Backups are configured and restores tested",
      "Database (and persistent volume/object storage) backups with tested restore and defined RPO.", severity="CRITICAL",
      runtime=True, gate=True),
    C("OPS-07", "Disaster recovery is defined", "RTO/RPO agreed, multi-zone or recovery procedure tested.",
      severity="HIGH", runtime=True),
    C("OPS-08", "Deployments are monitored and reversible",
      "Rollout monitoring and a documented, tested rollback procedure.", severity="MEDIUM"),
    C("OPS-09", "Capacity is planned and load-tested",
      "Scaling thresholds and resource sizes backed by load tests representative of production.", severity="MEDIUM"),
    C("OPS-10", "Operations are documented", "Runbooks and troubleshooting guides for the cloud platform.",
      severity="MEDIUM"),
    C("OPS-11", "Failure scenarios are tested", "Pod kill, node drain, dependency outage and database failover exercised.",
      severity="MEDIUM", runtime=True),
]
BY_ID = {c["id"]: c for c in CONTROLS}
