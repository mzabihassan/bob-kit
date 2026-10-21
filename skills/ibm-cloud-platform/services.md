# IBM Cloud services for Java/Angular workloads

Check each service's current plans, regional availability and deprecations in the docs before recommending it.

## Runtimes

| Option | Fits | Watch out for |
| --- | --- | --- |
| **Red Hat OpenShift on IBM Cloud (ROKS)** | Enterprise standard platforms, OpenShift tooling (Routes, SCCs, Operators), Argo CD/OpenShift GitOps | Random UIDs (`restricted-v2` SCC), worker pool sizing, version upgrades of the cluster and workers on a schedule |
| **IBM Cloud Kubernetes Service (IKS)** | Plain Kubernetes, lighter platforms | Ingress (ALB) and certificate management, node upgrades |
| **Code Engine** | Serverless containers (apps), batch jobs, functions; small services, event-driven jobs, quick environments | Cold starts (set a minimum scale for latency-sensitive apps), request timeouts, limited networking control compared with clusters; private endpoints and VPC integration per current capabilities |

For long-running Spring Boot services in regulated environments, ROKS or IKS are the usual choice; Code Engine suits batch jobs and lightweight APIs.

## Container Registry (ICR)

- Regional registries with **namespaces**; images scanned by **Vulnerability Advisor**; **retention policies** to purge old images; private endpoints for pulls from private clusters.
- Clusters get an image pull secret for ICR in the `default` namespace (`all-icr-io`): copy it or reference it in other namespaces, or use the organisation's registry access pattern.
- If the organisation uses Sysdig or SCC Workload Protection as the gating scanner, VA results are informational.

## Data services

- **Databases for PostgreSQL** (IBM Cloud Databases): managed HA, automatic backups and point-in-time recovery, read replicas, private endpoints, encryption with customer keys (Key Protect/HPCS). Connections use TLS with the CA certificate from the connection details; credentials come from service credentials, which should be stored in **Secrets Manager**, not in application properties. Size memory, disk and CPU in Terraform; scaling may restart members.
- **Cloud Object Storage (COS)**: buckets with IAM or HMAC credentials, encryption with Key Protect/HPCS, lifecycle rules (archive, expiration), **Object Lock / immutable buckets** (WORM) for regulated retention (audit files, statements), private and direct endpoints.
- **Event Streams** (managed Kafka; the Enterprise plan for private endpoints and customer keys) and **MQ as a Service** for integrations; schema registry where available.

## Secrets and keys

- **Secrets Manager**: secret types (arbitrary, username/password, key-value, IAM credentials with dynamic service-ID API keys, imported, public and private certificates, service credentials), **rotation** policies, **secret groups** for access control. Delivery to workloads: External Secrets Operator (IBM provider) syncing Kubernetes Secrets, the Secrets Manager CSI driver mounting files, or direct API calls from applications using a trusted profile.
- **Key Protect** (HSM-backed, FIPS 140-2 Level 3) for root keys and envelope encryption of COS, Databases, block storage and clusters; **Hyper Protect Crypto Services** (FIPS 140-2 Level 4, keep-your-own-key) when the organisation requires exclusive key control. Key deletion makes data unrecoverable: it is never done casually.

## Observability and audit

- **IBM Cloud Logs** replaces the deprecated Log Analysis and Activity Tracker services (end of support: March 2025). Platform audit events are routed with **Activity Tracker Event Routing** to Cloud Logs (or other targets). Cluster and app logs are shipped with the logging agent.
- **IBM Cloud Monitoring** is based on Sysdig (metrics, dashboards, alerts), and **SCC Workload Protection** on Sysdig Secure (vulnerabilities, posture, runtime threats). The Sysdig guidance in `security-findings-remediation` applies.
- Spring Boot: expose Prometheus metrics via Micrometer for the monitoring agent; JSON logs with a correlation id; no personal data in logs.
