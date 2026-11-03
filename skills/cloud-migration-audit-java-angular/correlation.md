# Cross-repository correlation, summary and decision

The agents already receive the cross-repository facts of their domains and cite evidence from several repositories. Your part comes after the draft build: it prints a LEAD line for each check whose hint no finding covers yet, plus conflicts between agents. Work only on those: open the referenced lines of both sides (batched in one turn) and decide. Do not re-audit what the agents covered.

## Checks and what they decide

| Check | Confirm by reading | Typical finding (control) |
| --- | --- | --- |
| CHK-SCHEDULING | each unlocked `@Scheduled` method body: side effects? idempotent? | job duplicated on N replicas (ARCH-01) |
| CHK-POOL-CAPACITY | pool size per profile, HPA max per environment, other services on the same database, the database limit if documented | aggregate connections above the limit (APP-01, often NOT VERIFIED with the computed total) |
| CHK-PROBES | probe paths/ports in the rendered values vs actuator config, context path, management port | liveness on aggregate health (K8S-06), readiness path wrong (K8S-05) |
| CHK-PORTS | `server.port`, `management.server.port`, `containerPort`, Service `targetPort`, nginx `listen`, `EXPOSE` | traffic or probes on the wrong port (K8S-14) |
| CHK-SHUTDOWN | `server.shutdown`, shutdown timeout, `terminationGracePeriodSeconds`, preStop, Dockerfile entrypoint form | requests cut at every rollout (K8S-08, APP-11, CTR-10) |
| CHK-JVM-MEMORY | heap flags in values and image vs memory limit per environment | OOMKilled (K8S-02) |
| CHK-IMAGE-FLOW | tags pushed by CI vs `image.tag` per environment vs Argo CD `targetRevision`; who updates the tag | deployed image never built or moving (CICD-06, CTR-06) |
| CHK-SESSIONS | session use vs Spring Session vs ingress affinity | state lost between pods (ARCH-06) |
| CHK-API-ROUTES | frontend base URLs per environment vs ingress paths/hosts vs backend context path and mappings | 404/CORS in the cloud (WEB-02, WEB-01) |
| CHK-ONPREM-ENDPOINTS | each on-premise host/path: still reachable from the cloud? replaced per environment? | on-premise endpoint left (APP-08, WEB-01) |
| CHK-SCHEMA-MIGRATIONS | destructive changes vs code of the previous release; where migrations run | rolling update breaks old pods (APP-04, APP-03) |
| CHK-DB-ENGINE | the query's flow and whether the target engine changed | query fails on the new engine (APP-05) |
| CHK-SECRETS-IN-GIT | whether the file is used for a real environment (never copy the value) | secret in Git (K8S-12, CICD-12) |
| CHK-GITOPS | which environments the CI job targets and whether Argo CD manages them | GitOps bypass (CICD-09) |
| CHK-ENV-DRIFT | differences that are not intended (sizing, flags, tags) | inconsistent environments (K8S-18) |

Also compare identity settings (frontend issuer/client vs backend `issuer-uri`), CORS allowed origins vs frontend hosts, and timeouts along the chain (ingress `proxy-read-timeout` vs backend client timeouts vs frontend `timeout()`).

## results-correlation.json

Only when a LEAD is confirmed (or a conflict needs your arbitration), in one write:

```json
{"group": "correlation",
 "controls": [{"id": "K8S-06", "status": "NOT DONE", "summary": "Liveness probe on /actuator/health includes the database.",
   "evidence": [{"repo": "air-cd", "file": "helm/air-back/values.yaml", "line": 20, "note": "livenessProbe path /actuator/health"}]}],
 "findings": [{"key": "air-back-liveness-aggregate-health", "control": "K8S-06", "related_controls": ["APP-10"], "severity": "HIGH",
   "kind": "confirmed", "blocker": false, "title": "Liveness probe restarts every pod when the database is slow",
   "repos": ["air-back", "air-cd"],
   "evidence": [{"repo": "air-cd", "file": "helm/air-back/values.yaml", "line": 20, "note": "path: /actuator/health"},
                {"repo": "air-back", "file": "src/main/resources/application.yml", "line": 18, "note": "probes enabled"}],
   "impact": "A database slowdown fails the liveness check on all pods at once: Kubernetes restarts them all.",
   "remediation": "Point the liveness probe at /actuator/health/liveness.", "example": "livenessProbe:\n  httpGet:\n    path: /actuator/health/liveness",
   "validation": "Stop the database in staging: pods turn not-ready but are not restarted.",
   "acceptance": "No pod restart during a database outage.", "effort": "S", "depends_on": [], "runtime_check": ""}],
 "notes": ""}
```

Never copy a secret value, even one you just read in a file: the check rejects it and names its source. `effort` is S, M or L. Every field shown is checked: `summary` on each control, and for findings `key`, `control`, `title`, `severity`, `kind`, `repos`, `evidence`, `impact`, `remediation`, `validation`, `acceptance`. A NOT DONE/PARTIALLY DONE control needs a finding (own or `related_controls`) or a `remediation` on the control. Same control and key as an agent's finding → merged; different statuses → the most conservative is kept and listed as a conflict. Check it with `python3 scripts/audit.py check <out>/work/results-correlation.json --out <out>`.

## summary.json

```json
{"title": "<Application> — cloud migration audit",
 "executive_summary": "Three to five sentences for stakeholders: readiness, the blockers in plain words, what is solid, what must happen next.",
 "architecture": "Components, how they communicate, where they run, how they are built and deployed (from the evidence).",
 "migration_context": "What changed from on-premise (servers, database engine, sessions, scheduling, storage, network) as far as the repositories show.",
 "components": [{"name": "air-back", "repo": "air-back", "description": "Spring Boot 3.3 REST API, 3 replicas in prod"}],
 "key_risks": ["One line per major risk, in business terms."],
 "decision_rationale": "Why the computed decision is right, and what would change it.",
 "access": "What was available: repositories only, or which read-only live access."}
```

Write in the user's language. No secret values, no personal data. Do not restate counts or percentages (blockers, findings, completion): the reports show the computed figures next to your text, and a number written by hand drifts from them when findings are merged.

## Severity and blockers

Severity = impact × likelihood in production after the migration: data integrity or security breach and outage first, then degraded service. `kind: confirmed` when the code or configuration itself shows the defect; `potential` when it depends on runtime facts (then give `runtime_check`). Mark `blocker: true` for issues that must be fixed before go-live even below CRITICAL (for example duplicated financial side effects at the configured replica count).

## Decision

The build applies fixed rules: any blocker → NO-GO; otherwise HIGH findings or gate controls not DONE (including NOT VERIFIED) → CONDITIONAL GO with each one as a condition; otherwise GO. You do not override it: if you disagree, the severity or status is wrong — fix the results and rebuild. Explain the decision in `decision_rationale`.

## Final answer

Five to ten lines: decision and the reason in one sentence; completion and coverage (coverage below ~70% means many controls could not be established: completion is a floor, not an estimate); the blockers; the top five actions with IDs; what needs live access; the five report paths. Point to `cloud-migration-audit.html` for stakeholders.
