# Repository structure, sync and promotion

Follow the existing layout. When there is none, a common and reviewable structure is:

```
apps/payments/
  base/                     # Deployment, Service, ConfigMap, … (or a Helm chart reference)
  overlays/
    dev/kustomization.yaml  # namespace, replicas, resources, image tag for dev
    staging/…
    prod/…
argocd/
  projects/payments.yaml    # AppProject
  appsets/payments.yaml     # ApplicationSet generating one Application per environment
```

Prefer **one folder per environment on one branch** over one branch per environment: diffs between environments stay visible, and promotion is a reviewable change of one value.

## ApplicationSet per environment

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: payments
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
    - list:
        elements:
          - { env: dev,  server: "https://kubernetes.default.svc" }
          - { env: prod, server: "https://prod-api.example.internal:6443" }
  template:
    metadata:
      name: "payments-{{.env}}"
    spec:
      project: payments
      source:
        repoURL: https://gitlab.example.internal/platform/payments-gitops.git
        targetRevision: main
        path: "apps/payments/overlays/{{.env}}"
      destination:
        server: "{{.server}}"
        namespace: "payments-{{.env}}"
      syncPolicy:
        automated: { prune: true, selfHeal: true }   # prod often uses manual sync or sync windows instead
        syncOptions: [CreateNamespace=true]
```

Other generators: `git` (directories or files: one Application per folder), `cluster` (one per registered cluster), `matrix`/`merge` (combinations). Multi-source Applications (`sources:` with `ref: values` and `$values/...`) let you combine a chart from a Helm registry with values from Git.

## Helm and Kustomize

- Helm: pin the chart version (`targetRevision: 1.4.2` for chart repositories); keep values per environment (`values-dev.yaml`, `values-prod.yaml`) minimal, overriding only what differs. Render with `helm template <release> <chart> -f values.yaml -f values-<env>.yaml`.
- Kustomize: the base holds what is common; overlays hold patches, `images:` (name, `newTag` or `digest`), replicas and resources. Render with `kubectl kustomize apps/payments/overlays/<env>`.
- Do not mix both for the same resources unless the repository already does (Helm + Kustomize post-rendering is harder to debug).

## Promotion

1. CI builds once, scans, and publishes `image:<sha>` (or a digest).
2. CI (bot) or Argo CD Image Updater updates the **dev** overlay (`images[].newTag`, or the Helm `image.tag`).
3. Promotion to staging and prod is a merge request that copies the **same** tag or digest to the next environment's file, with the approvals the organisation requires; change records for prod if needed.
4. Release notes reference the tag, commit and MR.

## Sync behaviour

- `automated` with `prune` (deletes resources removed from Git) and `selfHeal` (reverts manual drift). Understand both before enabling them on existing applications: prune can delete resources that were only ever created by hand.
- **Sync waves** (`argocd.argoproj.io/sync-wave: "-1"`) order resources, e.g. ConfigMaps and Secrets before Deployments, CRDs before custom resources.
- **Hooks** (`argocd.argoproj.io/hook: PreSync|Sync|PostSync|SyncFail`, `argocd.argoproj.io/hook-delete-policy: BeforeHookCreation`) for jobs such as database migrations or smoke tests. A PreSync migration job runs before the new pods start: the migration must be compatible with the old version that is still running (expand/contract).
- Useful `syncOptions`: `CreateNamespace=true`, `ServerSideApply=true` (large CRDs, fields managed by several controllers), `PruneLast=true`, `RespectIgnoreDifferences=true`, `ApplyOutOfSyncOnly=true` for large applications. `Replace=true` deletes and recreates resources: avoid it unless necessary.
- `ignoreDifferences` only for fields legitimately owned by something else (an HPA's `spec.replicas`, webhook `caBundle`s injected by cert-manager), as narrowly as possible:

```yaml
ignoreDifferences:
  - group: apps
    kind: Deployment
    jsonPointers: [/spec/replicas]
```

## AppProjects and governance

AppProjects restrict `sourceRepos`, `destinations` (cluster plus namespace), allowed cluster-scoped kinds (`clusterResourceWhitelist`), and roles; **sync windows** implement change freezes (e.g. no prod syncs outside the agreed window). Changes to AppProjects, repository credentials and RBAC belong to the platform team.
