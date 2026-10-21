# Pipeline troubleshooting

Find the first real error in the log (search for `ERROR`, `FAILED`, `BUILD FAILURE`, `npm ERR!`, `exit code`). Note the runner, image and job duration: they often explain the failure.

## Pipeline or job not created / wrong jobs

| Symptom | Likely cause | Action |
| --- | --- | --- |
| "Pipeline filtered out by workflow rules" / no pipeline | `workflow:rules` do not match this source (push, MR, tag, schedule) | Check `$CI_PIPELINE_SOURCE` and the rule order (first match wins) |
| Two pipelines per push (branch + MR) | Missing workflow rule for open MRs | Add the `$CI_COMMIT_BRANCH && $CI_OPEN_MERGE_REQUESTS → never` rule |
| Job missing | Its `rules` evaluated to `never`, or `changes` did not match | Check `changes`/`compare_to`; remember that `changes` is always true for new branches and tags without `compare_to` |
| `jobs:x config contains unknown keys` / YAML invalid | Typo, wrong indentation, keyword not supported by this GitLab version | Lint; check the keyword against the instance's version |
| `found unexpected ':'` / YAML syntax error near a job name | Job names containing `:` inside flow lists (`needs: [build:jar]`) | Quote them (`needs: ["build:jar"]`) or use block lists |
| `needs` error: job not found | The needed job is not created by the rules in this pipeline | Align the rules or use `needs: optional: true` |

## Permissions, tokens, variables

| Symptom | Cause | Action |
| --- | --- | --- |
| Variable empty in MR pipeline, works on main | **Protected variable** on an unprotected branch, or MR pipeline from a fork | Use an unprotected variable for non-sensitive values, or run sensitive jobs only on protected refs |
| `fatal: could not read Username` / 403 cloning another project | `CI_JOB_TOKEN` not allowed by the target project's job-token allowlist | Ask the target project's maintainers to add this project to its allowlist |
| `401`/`403` from Nexus/Maven/npm registry | Missing or expired credentials in `settings.xml`/`.npmrc`, wrong mirror URL | Check the file-type variable and registry URL; never print the token |
| `x509: certificate signed by unknown authority` / `PKIX path building failed` / `UNABLE_TO_VERIFY_LEAF_SIGNATURE` | Corporate CA not trusted in the job image | Use the approved image with the corporate CA, or import it (JVM truststore, `NODE_EXTRA_CA_CERTS`, `update-ca-certificates`) |
| Deploy job waiting / "environment is protected" | Protected environment needing approval | Expected; request approval from the authorised approvers |

## Runner and infrastructure

| Symptom | Cause | Action |
| --- | --- | --- |
| "This job is stuck… no runners with tags" | `tags` do not match any online runner | Fix the tags or ask the platform team |
| `exit code 137`, `Killed`, `OutOfMemoryError` | Container memory limit | Lower JVM/Node memory (`-Xmx`, `MAVEN_OPTS`, `NODE_OPTIONS=--max-old-space-size`), fewer parallel forks, or a bigger runner class |
| `No space left on device` | Runner disk full, huge caches/artifacts | Smaller artifacts, `expire_in`, cache cleanup; platform team for the runner |
| Job timeout | Slow tests, hanging process, waiting for an external system | Find the hanging step (timestamps in the log); add timeouts to external calls |
| `toomanyrequests` pulling images | Docker Hub rate limit | Use the dependency proxy or the internal registry mirror |
| Cache never restored | Different runners without a shared cache, key changes, `policy: push` | Use artifacts for required data; check the key and policy |

## Build and tests

| Symptom | Cause | Action |
| --- | --- | --- |
| Passes locally, fails in CI | Different JDK/Node version, locale/time zone, missing env var, test order | Reproduce with the same image (`docker run`), `TZ`/`LANG` explicit, check `.nvmrc`/toolchain |
| Karma: `ChromeHeadless` fails to start | No Chrome in the image, or sandbox not allowed in containers | Use an image with Chrome; custom launcher with `--no-sandbox` (project config) |
| Testcontainers: `Could not find a valid Docker environment` | No Docker socket on the runner (DinD often forbidden) | Use the approved Testcontainers setup (remote Docker, Testcontainers Cloud, a dedicated runner) or run those tests in a separate job with the right runner |
| Flaky test (passes on retry) | Shared state, timing, ordering, external dependency | Fix the test; quarantine only with an issue and an owner; no `retry` for test failures |
| Sonar job fails with "Quality Gate failed" | The gate, not the pipeline | See the `sonarqube-java-angular` skill; never `allow_failure` the gate |
| Security job fails (Nexus IQ, Fortify, Sysdig) | Policy violation | See the `security-findings-remediation` skill |
| `npm ci` fails: lockfile out of sync | `package.json` changed without updating the lockfile | Regenerate the lockfile locally with the project's npm version and commit both |

## Quick commands

```bash
glab ci status                 # current pipeline of the branch
glab ci view                   # interactive view
glab ci trace <job-id>         # job log
glab ci lint                   # validate .gitlab-ci.yml
```
API equivalents: `GET /projects/:id/pipelines/:pipeline_id/jobs`, `GET /projects/:id/jobs/:job_id/trace`, `POST /projects/:id/ci/lint`. Authenticate with a token from the environment.
