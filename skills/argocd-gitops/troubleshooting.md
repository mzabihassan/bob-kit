# Argo CD troubleshooting

## Commands (read-only)

```bash
argocd app get <app> --show-operation      # sync and health status, conditions, last operation
argocd app diff <app>                       # live vs desired
argocd app manifests <app> [--source live]  # rendered desired (or live) manifests
argocd app history <app>                    # deployed revisions
argocd app resources <app>                  # resource tree with health
kubectl -n argocd get application <app> -o yaml   # status.conditions, operationState
kubectl -n <ns> get events --sort-by=.lastTimestamp
kubectl -n <ns> describe pod <pod>; kubectl -n <ns> logs <pod> [-c <container>] --previous
```
Flags vary by version: check `--help`.

## Application-level states

| State | Typical causes | Action |
| --- | --- | --- |
| **ComparisonError** / Unknown | Helm or Kustomize rendering error (missing values file, template error, wrong chart version), repository credentials, wrong `path`/`targetRevision` | Reproduce the rendering locally with the same versions; check the repository connection in Argo CD |
| **OutOfSync** that never settles | Fields mutated by controllers or webhooks (defaults, injected sidecars, HPA replicas, `caBundle`), differences in normalisation between the manifest and the live object | Find the field in `argocd app diff`; fix the manifest to match the defaults, use `ServerSideApply=true`, or a **narrow** `ignoreDifferences` for fields owned by another controller |
| OutOfSync after a manual change | Someone used `kubectl`; self-heal is off | Bring the change into Git or let Argo CD revert it; never both silently |
| **Sync failed** | Immutable field changed (Deployment `selector`, Job `spec`, Service `clusterIP`), admission webhook or policy denial (Kyverno, Gatekeeper, OpenShift SCC), CRD missing, AppProject forbids the kind or namespace, quota exceeded | Read the operation message; recreate the resource deliberately (or `Replace=true` on that resource only); fix the manifest to satisfy the policy; order CRDs with sync waves; ask the platform team for project or quota changes |
| **Degraded** | Pods failing (see below), a failed Job, Ingress or Route errors | Go to the failing resource |
| **Progressing** forever | Rollout not completing (readiness never true), PVC `Pending`, LoadBalancer not provisioned, `progressDeadlineSeconds` reached | `kubectl rollout status`, describe the new pods, PVC events |
| **Missing** | Resource not created yet, or pruned | Check the sync result and prune settings |
| Hook stuck or failed | The PreSync Job is failing (migration error, missing secret) or a hook was left behind | Logs of the hook Job; `hook-delete-policy: BeforeHookCreation` to avoid leftovers |
| Deletion stuck | Finalizers (`resources-finalizer.argocd.argoproj.io`, PVC protection, operators) | Find which finalizer blocks and why; removing finalizers by hand needs agreement |

## Pod-level failures

| Symptom | Cause | Action |
| --- | --- | --- |
| `ImagePullBackOff` / `ErrImagePull` | Tag does not exist, wrong registry, missing pull secret, registry rate limit | Check the tag in the registry, `imagePullSecrets`, the internal mirror |
| `CrashLoopBackOff` | Application error at startup (configuration, missing secret, DB unreachable, migration failure) | `kubectl logs --previous`; for Spring Boot, look for the first `APPLICATION FAILED TO START` cause |
| `OOMKilled` (exit 137) | Container memory limit too low, or JVM heap not sized to the container | `-XX:MaxRAMPercentage` (e.g. 70–75) instead of a fixed `-Xmx` larger than the limit; review the limit with metrics |
| Restarts under load or at startup | Liveness probe too aggressive or hitting a slow endpoint; JVM startup slower than `initialDelaySeconds` | Use a `startupProbe`; liveness on `/actuator/health/liveness`, readiness on `/actuator/health/readiness`; do not include external dependencies in liveness |
| `CreateContainerConfigError` | Missing ConfigMap or Secret key | Check the names; for External Secrets, check the `ExternalSecret` status and the store connection |
| Permission denied writing files | `readOnlyRootFilesystem` or a random UID (OpenShift) | Mount an `emptyDir` for `/tmp` and caches; make files group-writable (GID 0) for OpenShift |
| Pod `Pending` | Insufficient resources, node selectors or affinity, PVC not bound, quota | `kubectl describe pod` events |

## Rollback

1. Preferred: `git revert` of the offending commit in the GitOps repository, then let the normal sync apply it. This keeps the history and selfHeal consistent.
2. Emergency: `argocd app rollback <app> <history-id>` requires auto-sync to be disabled for that application and leaves Git out of date. Agree on it, then revert in Git and re-enable auto-sync right after.
3. Database migrations are not rolled back by Argo CD: use forward fixes compatible with both versions.
