# Frontend and operations audit guide — Angular end to end (WEB), observability and resilience (OPS)

The frontend is judged against what the cloud actually serves: the ingress hosts and paths, the backend context path and CORS configuration, the identity provider clients, and the nginx or ingress headers. Read both sides before concluding; the brief's cross-repository facts put them side by side.

## WEB — Angular and end-to-end integration

| Control | Check | Failure scenario when missing |
| --- | --- | --- |
| WEB-01 configuration | `environment*.ts`, `fileReplacements` in `angular.json`, runtime config (`APP_INITIALIZER`/`provideAppInitializer` loading `assets/config.json` or `env.js` from a ConfigMap); on-premise hosts (`*.intranet`, `*.local`, IPs) | production bundle calls the old on-premise API or identity provider; one image per environment, no promotion |
| WEB-02 API routes | base URL and paths called by services vs ingress paths/hosts vs `server.servlet.context-path` and controller mappings | 404 on API calls behind the ingress; CORS errors from a different host |
| WEB-03 authentication | keycloak-angular/angular-oauth2-oidc/MSAL config: issuer, client ID, redirect and post-logout URIs per environment, `pkceMethod: 'S256'`, silent refresh; backend `spring.security.oauth2.resourceserver.jwt.issuer-uri` matching the issuer | login loops, invalid redirect URI, tokens rejected by the backend (issuer mismatch) |
| WEB-04 token handling | tokens in `localStorage`/`sessionStorage` (XSS exposure), interceptor adding the bearer token to every URL (leaks to third parties), cookie flags | token theft; token sent to external domains |
| WEB-05 CORS/CSRF | backend `@CrossOrigin`/`CorsConfiguration` allowed origins vs cloud frontend hosts; wildcard with credentials; CSRF settings vs cookie- or token-based auth | blocked calls in the cloud, or any site can call the API with the user's cookies |
| WEB-06 headers | CSP, HSTS, X-Content-Type-Options, frame-ancestors/X-Frame-Options, Referrer-Policy in nginx or ingress annotations | clickjacking, XSS impact, mixed content |
| WEB-07 routing | nginx `try_files $uri $uri/ /index.html`; `<base href>`/`baseHref` matching the ingress path | deep links and refresh return 404 |
| WEB-08 caching | `Cache-Control: no-cache` for `index.html` (and runtime config), long `immutable` caching for hashed bundles (`outputHashing: all`) | users keep an old UI after a deployment, calling removed API versions |
| WEB-09 rollout compatibility | API contract changes in the same release as the UI change; versioned endpoints | during a rolling update old UI hits new API (or the reverse) and breaks |
| WEB-10 affinity | websocket/SSE, server-side session use, ingress affinity annotations | reconnections land on another pod and lose state |
| WEB-11 container | `nginx-unprivileged` or `USER` set, listening on 8080, read-only friendly config | root nginx refused by restricted policies (OpenShift) |
| WEB-12 error handling | interceptors/`catchError`, `timeout()`, user feedback, retry only on idempotent calls | blank screens or duplicate submissions when a pod restarts |

## OPS — observability, resilience and operations

Most OPS controls depend on the platform: the repositories show configuration (ServiceMonitor, PrometheusRule, logging agents, runbooks), not whether alerts reach someone or backups restore. Report what the repositories prove; mark the rest NOT VERIFIED with the evidence needed (dashboard link, alert routing, restore test report).

| Control | Evidence in repositories | Evidence needed beyond them |
| --- | --- | --- |
| OPS-01 logs | stdout JSON logs with trace IDs (APP-12), logging agent/annotations, ingress access logs | logs searchable in IBM Cloud Logs (or ELK) by correlation ID |
| OPS-02 metrics | ServiceMonitor/PodMonitor or scrape annotations, actuator `prometheus` exposure, dashboards as code | metrics visible in IBM Cloud Monitoring/Prometheus |
| OPS-03 tracing | OpenTelemetry/Micrometer Tracing config, frontend trace propagation | end-to-end trace from the ingress to the database |
| OPS-04 alerts | PrometheusRule/Sysdig alert definitions: availability, 5xx rate, latency, restarts, OOMKilled, saturation, certificate expiry | routing to an on-call rota, tested |
| OPS-05 synthetic | synthetic checks as code | external probes running |
| OPS-06 backups | backup CronJobs, IBM Cloud Databases backup/PITR settings in Terraform, Velero/COS versioning | a restore tested recently, RPO agreed |
| OPS-07 DR | DR runbook, multi-zone cluster/database settings | RTO/RPO agreed and exercised |
| OPS-08 deployment monitoring | rollout checks in CI/Argo CD (health assessment, notifications), rollback runbook | rollback exercised |
| OPS-09 capacity | load tests (Gatling/JMeter/k6) and their results, sizing notes | thresholds validated against production volumes |
| OPS-10 documentation | runbooks, troubleshooting guides, architecture docs updated for the cloud | owners confirm they are current |
| OPS-11 failure tests | chaos experiments, game-day reports | pod kill, node drain, database failover exercised |

## Severity hints

CRITICAL: no backup or no restore ever tested for production data; production frontend still pointing at on-premise endpoints on a main journey. HIGH: tokens leakable to other domains, wildcard CORS with credentials, no alerting on availability, issuer mismatch between frontend and backend, stale UI after each deployment calling removed APIs. MEDIUM: missing security headers, no synthetic monitoring, missing runbooks. LOW: UI error-handling polish.
