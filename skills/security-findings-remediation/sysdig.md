# Sysdig Secure (images, posture, runtime)

## Three kinds of findings

| Kind | Where the fix lives |
| --- | --- |
| **Image vulnerabilities**: OS packages from the base image, language packages (jars, npm modules) inside the image | `Dockerfile` / base image choice; the application build (see `nexus-iq.md`) for language packages |
| **Posture / compliance**: Dockerfile best practices, Kubernetes manifests (CIS, NIST, internal policies) | Dockerfile, Helm charts or Kustomize in the GitOps repository, never by editing the live cluster |
| **Runtime threat events** (Falco-based rules: shell in container, unexpected outbound connection, sensitive file read…) | Usually not a code fix: treat as a potential incident (see below) |

## Getting the data

- The Sysdig UI or an export from the user (vulnerabilities per image or workload, with *fix available*, *in use* and *exploit* indicators).
- CLI scan as CI does it: `SECURE_API_TOKEN=… sysdig-cli-scanner --apiurl <https://your-region.sysdig.com> <image>:<tag>` (token only from the environment; check `--help` for policy and output options of the installed version).

## Prioritise image vulnerabilities

Prefer, in order: vulnerabilities that **fail the image policy** in CI, then **exploitable** (public exploit, CISA KEV) **and in use** (package loaded at runtime, per Sysdig's runtime insights), then **fix available**. A package that is never loaded and has no fix is the lowest priority, and a candidate for a time-boxed risk acceptance proposed to the security team.

## Image remediation, cheapest first

1. **Rebuild on the latest patch of the same base image** (tags are re-published with OS fixes; refresh pinned digests). Many OS CVEs disappear without any other change. Use Renovate or Dependabot for automated base-image updates if the team uses them.
2. **Use a smaller, more suitable base image**: JRE rather than JDK (e.g. a `*-jre` Temurin or UBI OpenJDK runtime image), UBI minimal or micro, or distroless where the organisation allows; `nginx-unprivileged` (or the approved equivalent) for static Angular/React builds. Stay within the organisation's approved image catalogue.
3. **Multi-stage builds**: build tools, Maven/npm caches and compilers stay in the build stage; the final stage contains only the runtime and the artifact.
4. **Remove what is not needed** in the final image: package managers, shells or `curl` if policy requires, documentation and test files.
5. Package upgrades inside the Dockerfile (`microdnf update`, `apt-get upgrade`) only if the image policy accepts them; a newer base image is cleaner and reproducible.
6. **Language packages** found in the image (e.g. a vulnerable jar inside the Spring Boot fat jar): fix in Maven/Gradle/npm, then rebuild.

Also check: `USER` non-root, no secrets in `ENV`/`ARG` or layers, `.dockerignore` excluding `.git`, credentials and local configuration, and an explicit, reproducible tag or digest.

## Kubernetes posture (in Helm values or manifests in the GitOps repo)

`securityContext`: `runAsNonRoot: true`, `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true` (add an `emptyDir` for `/tmp` and caches the app writes to; Spring Boot needs a writable temp directory), `capabilities: { drop: [ALL] }`, `seccompProfile: { type: RuntimeDefault }`; resource requests and limits; no `privileged`, `hostNetwork`, `hostPath`; images by digest from the approved registry. Validate with a deployment to a non-production environment: read-only filesystems and dropped capabilities can break startup.

## Runtime events

Do not "fix" them in code by reflex. Gather the event details (rule, container, process, command line, time), compare with expected behaviour (an operator `kubectl exec` session, a known integration endpoint), and if it is unexplained, stop and escalate through the incident process. Rule tuning and exceptions are the security team's decision; you may propose an exception with evidence when the behaviour is legitimate.
