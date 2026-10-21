# Workload manifests for Spring Boot and Angular

Follow the organisation's chart or base templates and its policies (Kyverno/Gatekeeper/OpenShift SCC); these are sensible defaults to check against.

## Spring Boot Deployment (essentials)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payments-api
  labels: { app.kubernetes.io/name: payments-api }
spec:
  replicas: 2
  selector:
    matchLabels: { app.kubernetes.io/name: payments-api }   # immutable: never change it on a live Deployment
  strategy:
    rollingUpdate: { maxUnavailable: 0, maxSurge: 1 }
  template:
    metadata:
      labels: { app.kubernetes.io/name: payments-api }
    spec:
      terminationGracePeriodSeconds: 45
      securityContext:
        runAsNonRoot: true
        seccompProfile: { type: RuntimeDefault }
      containers:
        - name: app
          image: registry.example.internal/payments/payments-api:1.0.0
          ports: [{ name: http, containerPort: 8080 }]
          env:
            - { name: JAVA_TOOL_OPTIONS, value: "-XX:MaxRAMPercentage=75" }
          envFrom:
            - configMapRef: { name: payments-api-config }
            - secretRef: { name: payments-api-secrets }
          resources:
            requests: { cpu: 250m, memory: 768Mi }
            limits: { memory: 768Mi }
          startupProbe:
            httpGet: { path: /actuator/health/liveness, port: http }
            periodSeconds: 5
            failureThreshold: 30            # up to 150 s for JVM startup
          livenessProbe:
            httpGet: { path: /actuator/health/liveness, port: http }
            periodSeconds: 10
          readinessProbe:
            httpGet: { path: /actuator/health/readiness, port: http }
            periodSeconds: 5
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: { drop: [ALL] }
          volumeMounts: [{ name: tmp, mountPath: /tmp }]
      volumes: [{ name: tmp, emptyDir: {} }]
```

Notes:
- **Probes**: Spring Boot exposes liveness and readiness groups (enabled automatically on Kubernetes, or with `management.endpoint.health.probes.enabled=true`). Liveness must not depend on databases or external systems; readiness may. A `startupProbe` protects slow JVM starts.
- **Memory**: size the heap from the container (`MaxRAMPercentage`), keep room for metaspace, threads and direct buffers; requests equal to limits for memory avoid noisy evictions. CPU limits cause throttling at JVM startup: follow the organisation's policy (many set requests only).
- **Graceful shutdown**: `server.shutdown=graceful` and `spring.lifecycle.timeout-per-shutdown-phase` shorter than `terminationGracePeriodSeconds`; a short `preStop` delay (the `sleep` lifecycle action on recent Kubernetes versions, or `sleep` through a shell when the image has one) lets endpoints deregister before shutdown.
- **Availability**: at least 2 replicas, a `PodDisruptionBudget`, `topologySpreadConstraints` across zones or nodes; an HPA on CPU or custom metrics, with its `spec.replicas` excluded from the diff (`ignoreDifferences`) or `replicas` removed from the manifest.
- **Management port**: a separate `management.server.port` keeps actuator endpoints off the public Service and Ingress; expose only `health` (and metrics to the monitoring namespace).

## Angular (static SPA)

- Serve with an unprivileged web server image (e.g. `nginx-unprivileged` on port 8080, or the approved equivalent), with an SPA fallback (`try_files $uri /index.html`), long cache headers for hashed assets and `no-cache` for `index.html`.
- **Build once, configure per environment**: load runtime configuration (API URLs, feature flags) from a mounted `config.json` (ConfigMap) at startup instead of building per environment with `environment.<env>.ts`, so the same image is promoted everywhere.
- Security headers (CSP, `X-Content-Type-Options`, `Referrer-Policy`) in the server config or at the Ingress or Route.

## Configuration and secrets

- ConfigMap changes do not restart pods by themselves: use the Kustomize `configMapGenerator` (its hash suffix triggers a rollout) or a Helm checksum annotation (`checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}`).
- Secrets come from External Secrets Operator (`ExternalSecret` referencing a `SecretStore`/`ClusterSecretStore` backed by IBM Cloud Secrets Manager, Vault…), Sealed Secrets or SOPS, per the organisation. Use the `apiVersion` of the installed operator version.
- Never put credentials in ConfigMaps, `values.yaml` or plain manifests.

## OpenShift specifics (IBM Cloud ROKS)

- The `restricted-v2` SCC assigns a random UID: do not hardcode `runAsUser`; images must work with an arbitrary UID in group 0 (group-writable directories).
- Expose with `Route` (TLS edge or re-encrypt) or Ingress per the platform standard; NetworkPolicies are often default-deny: allow ingress from the router and egress to the database and APIs explicitly.
