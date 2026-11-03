# Platform audit guide — Kubernetes (K8S), containers (CTR), delivery (CICD)

Read the manifests as they are rendered: Helm templates take their values from `values.yaml` overridden by `values-<env>.yaml`; Kustomize overlays patch a base. Judge production with the production values. When `helm` is available locally, `helm template <chart> -f values.yaml -f values-prod.yaml` (read-only, no cluster) shows the rendered manifests; otherwise reason from templates and values and say so. Compare with what the backend actually exposes (ports, actuator paths, shutdown timeout, heap). Without cluster access, a manifest proves intent, not the running state: say NOT VERIFIED for runtime-only controls, or use `kind: potential` with a `runtime_check`.

## K8S — workloads and cluster configuration

| Control | Check | Failure scenario when missing |
| --- | --- | --- |
| K8S-01 resources | requests (CPU, memory) and memory limit on every container, init and sidecar included | noisy neighbours, evictions, unschedulable pods, OOMKilled |
| K8S-02 JVM memory | `-Xmx` or `MaxRAMPercentage` (JAVA_OPTS/JAVA_TOOL_OPTIONS in values, Dockerfile ENV) vs memory limit; heap ≤ ~75% of the limit | heap + metaspace + threads > limit: OOMKilled under load, restart loops |
| K8S-03 replicas and spread | production replicas/HPA min ≥ 2; `topologySpreadConstraints` or pod anti-affinity across nodes/zones | one node or zone failure takes the service down |
| K8S-04 HPA | metrics, min/max, max consistent with the database pool budget and quotas; Argo CD `ignoreDifferences` on `/spec/replicas` | scale-out exhausts database connections; Argo CD and HPA fight over replicas |
| K8S-05 readiness | path/port match the app (`/actuator/health/readiness` on the management or server port, context path included) | traffic sent to pods that are not ready; 404/503 during rollouts |
| K8S-06 liveness | liveness on `/actuator/health/liveness`, not on the aggregate `/actuator/health` (which includes the database); thresholds tolerate GC pauses | database hiccup restarts every pod at once (restart storm) |
| K8S-07 startup | `startupProbe` (or initialDelay) longer than JVM start plus migrations | pod killed while Liquibase holds its lock |
| K8S-08 termination | `terminationGracePeriodSeconds` ≥ preStop delay + app shutdown timeout; preStop delay so endpoints deregister first | in-flight requests cut, 502s at every rollout |
| K8S-09 rollout | RollingUpdate `maxUnavailable`/`maxSurge`, `revisionHistoryLimit`, readiness gating | capacity drop during rollout; no quick rollback |
| K8S-10 PDB | `PodDisruptionBudget` for each multi-replica workload | node drain/upgrade evicts all replicas together |
| K8S-11 ConfigMaps | environment config in ConfigMaps/values, not baked in images; no secrets in them | rebuild per environment; secrets readable by anyone with ConfigMap access |
| K8S-12 secrets | plaintext secrets in values, manifests or `kind: Secret` in Git (values hidden by the scan); External Secrets/IBM Secrets Manager/CSI/sealed secrets | credential leak through Git history; no rotation |
| K8S-13 storage | PVC access modes (RWO vs RWX), storage class, size, backup; `emptyDir` used for data that must survive | data lost at restart; pods blocked on RWO volumes across nodes |
| K8S-14 routing | Service ports/targetPort vs containerPort vs app port; Ingress/Route paths, host, TLS, timeouts (`proxy-read-timeout`), body size, rewrite | 404/502, cut uploads, timeouts on long requests |
| K8S-15 security context | runAsNonRoot, allowPrivilegeEscalation=false, capabilities drop ALL, readOnlyRootFilesystem (+ writable emptyDir for /tmp), seccomp RuntimeDefault; OpenShift (IBM ROKS) assigns a random UID: images must not require a fixed one | container escape blast radius; refused pods on restricted clusters |
| K8S-16 service accounts | dedicated SA, `automountServiceAccountToken: false` when unused, minimal Roles | stolen token can act on the cluster |
| K8S-17 network policies | default deny + explicit ingress/egress per app | lateral movement; any pod reaches the database |
| K8S-18 environments | namespaces per environment; diff of values files (the scan's CHK-ENV-DRIFT); prod-only settings present in prod | prod runs with dev sizing or flags |
| K8S-19 dependencies | database, cache, broker, identity provider: managed (IBM Cloud Databases…) or HA in cluster | single replica Keycloak/Redis/PostgreSQL in a pod is a single point of failure |

`../argocd-gitops/workload-manifests.md` details good Spring Boot and Angular manifests when installed alongside this skill.

## CTR — images

| Control | Check |
| --- | --- |
| CTR-01 base image | supported version, minimal runtime (JRE, distroless, UBI minimal, `nginx-unprivileged`), pulled through the JFrog remote/virtual repository, pinned tag or digest |
| CTR-02 multi-stage | build tools and sources only in the build stage |
| CTR-03 non-root | `USER` with a numeric UID in the final stage (official nginx and many JRE images run as root by default) |
| CTR-04 secrets | no `ENV`/`ARG` with secrets, no copied `.npmrc`, `settings.xml`, keys, `.env`; `.dockerignore` excludes them |
| CTR-05 scanning | Xray/Trivy/GitLab container scanning on the built image, failing on a severity threshold before promotion |
| CTR-06 immutable tags | no `latest`/moving tags in values or FROM; tag = version or commit SHA, or digest |
| CTR-07 reproducibility | lockfiles (`package-lock.json`), Maven/Gradle wrapper checksums, dependencies through JFrog |
| CTR-08 surface | only needed `EXPOSE`, no `curl \| sh`, no package managers or shells needed at runtime |
| CTR-09 filesystem | writable paths explicit; no `chmod 777`; works with a read-only root filesystem |
| CTR-10 signals | exec-form `ENTRYPOINT ["java", …]` (shell form keeps `sh` as PID 1: SIGTERM never reaches the JVM, graceful shutdown never runs) |

## CICD — GitLab, JFrog, Argo CD

| Control | Check | Failure scenario |
| --- | --- | --- |
| CICD-01 build/test | stages build, unit, integration tests before packaging | untested artifacts reach environments |
| CICD-02 quality gate | Sonar job not `allow_failure: true`, quality gate wait enabled | gate never blocks |
| CICD-03 SCA | GitLab dependency scanning, `jf audit`/Xray, OWASP with blocking rules | known vulnerable libraries deployed |
| CICD-04 JFrog | `jf rt build-publish`/build info, immutable versions, target repository per maturity | no traceability from running image to commit |
| CICD-05 promotion | promote the same artifact (`jf rt build-promote`, retag) instead of rebuilding per environment | prod runs a binary never tested |
| CICD-06 built = deployed | image name and tag pushed by CI vs `image.repository`/`image.tag` per environment values vs Argo CD source; who updates the tag (commit to the GitOps repo, image updater) | Argo CD deploys `latest` or a tag CI never built |
| CICD-07 chart checks | `helm lint`/`helm template`/kubeconform in CI, chart version bumps | broken manifest discovered at sync |
| CICD-08 Argo CD apps | `targetRevision` (pinned tag/commit or protected branch for prod), `syncPolicy` (automated + `selfHeal` + `prune`, or documented manual), `ignoreDifferences` for HPA replicas, destination namespace | prod follows `HEAD` of a branch anyone can push to; manual drift never corrected |
| CICD-09 GitOps only | `helm upgrade`/`kubectl apply`/`oc` jobs in CI for environments Argo CD manages | drift, overwritten deployments, two sources of truth |
| CICD-10 approvals | protected branches/tags, protected environments in GitLab, `when: manual` restricted to approvers, change gate for prod | anyone with Developer role deploys to production |
| CICD-11 rollback | documented revert of the GitOps commit or previous artifact, tested | slow, improvised rollback during an incident |
| CICD-12 pipeline secrets | masked + protected variables or vault/ID tokens; no secrets in YAML, no `echo $SECRET`, no `set -x` near secrets | credentials in job logs or in Git |

`../gitlab-ci-engineer/security-governance.md` covers secrets, protected environments, supply chain and the GitOps boundary in depth when installed alongside this skill.

## Severity hints

CRITICAL: plaintext production secret in Git, image or pipeline; CI or anyone able to deploy unreviewed code to production. HIGH: liveness on aggregate health, heap above the limit, `latest` in production, no readiness, grace period shorter than shutdown, no image scanning, deployments bypassing Argo CD. MEDIUM: missing PDB/spread, missing network policies, quality gate not blocking. LOW: image size, minor hardening.
