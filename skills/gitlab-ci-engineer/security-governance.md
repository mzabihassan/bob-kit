# Pipeline security and governance

## Secrets

- Store them as CI/CD variables that are **masked** (and hidden where available), **protected** when only protected branches or tags need them, and **file type** for files (`settings.xml`, `.npmrc`, kubeconfigs, certificates).
- Prefer short-lived credentials: `id_tokens` (OIDC) exchanged with a secret manager (`secrets:` keyword for HashiCorp Vault and supported providers, or the provider's CLI with workload identity / trusted profiles) rather than long-lived tokens in variables.
- Least privilege: project or deploy tokens limited to the scopes and projects needed; separate credentials per environment; production credentials only on protected refs and protected environments.
- Never `echo`, `set -x` or `env` dump in jobs handling secrets; avoid writing secrets to artifacts or caches; never bake them into images (`ARG`/`ENV`, copied files).

## Script injection

Treat values controlled by contributors (`$CI_COMMIT_BRANCH`, `$CI_COMMIT_MESSAGE`, `$CI_MERGE_REQUEST_TITLE`, tag names) as untrusted: always quote them (`"$VAR"`), never `eval` them, never interpolate them into commands that are executed in a privileged context.

## Who can deploy what

- Deployments run only from protected branches or tags (`rules`), use `environment:` with deployment tiers, and production uses **protected environments** with required approvals, not just `when: manual`.
- `resource_group` serialises deployments to the same environment.
- Fork and MR pipelines must not receive secrets or deploy.
- Separation of duties: the approver of a production deployment should not be the author of the change when the organisation requires it.

## Supply chain

- Images from the approved registry, pinned by version (and digest for critical jobs); no `latest`.
- No `curl … | bash` of unpinned scripts; verify checksums of downloaded tools; prefer tools baked into approved images.
- Keep the mandatory security stages (SonarQube, Fortify, Nexus IQ, Sysdig or GitLab security templates) in the path to production; their results gate promotion.
- Publish build provenance, SBOMs or attestations if the organisation requires them; keep artifacts' `expire_in` reasonable.

## Shared templates and components

- Templates used by other projects are owned code: change them through an MR to the template project, version them with tags, document breaking changes and communicate them to consumers.
- Consumers pin a tag (`ref: v3.2.0`, or `@3.2.0` for components); upgrades are explicit changes.
- A local override of a central template (redefining a job or variable) must be justified in a comment and reported to the template owners.

## GitOps boundary (Argo CD)

CI builds, tests, scans and publishes images, then **commits the new version to the GitOps repository** (a bot account with write access to that repository only) or lets Argo CD Image Updater do it. CI does not run `kubectl apply` or `helm upgrade` against clusters managed by Argo CD: that would create drift that Argo CD reverts or reports.
