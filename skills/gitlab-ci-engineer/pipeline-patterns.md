# Pipeline patterns

Use the organisation's templates or components first (`include: project:` / `include: component:`); these patterns fill the gaps. Use the approved internal images and registry mirrors instead of the public images shown here.

## Skeleton: Spring Boot + Angular + image + security + GitOps

```yaml
workflow:
  rules:                                   # one pipeline per change, no branch+MR duplicates
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH && $CI_OPEN_MERGE_REQUESTS
      when: never
    - if: $CI_COMMIT_BRANCH
    - if: $CI_COMMIT_TAG

stages: [test, quality, package, security, deploy]

default:
  interruptible: true                      # newer pushes cancel obsolete pipelines

variables:
  MAVEN_OPTS: "-Dmaven.repo.local=$CI_PROJECT_DIR/.m2/repository"
  MAVEN_CLI_OPTS: "--batch-mode --no-transfer-progress --settings $MAVEN_SETTINGS"  # MAVEN_SETTINGS: file-type variable

.maven:
  image: maven:3.9-eclipse-temurin-21
  cache:
    key: { files: [pom.xml] }
    paths: [.m2/repository]

backend:verify:
  extends: .maven
  stage: test
  needs: []
  script: mvn $MAVEN_CLI_OPTS verify
  artifacts:
    when: always
    reports: { junit: "**/target/surefire-reports/TEST-*.xml" }
    paths: ["**/target/site/jacoco/jacoco.xml", "target/*.jar"]
    expire_in: 1 week

frontend:test-build:
  image: node:22                           # needs Chrome for Karma; use the approved image
  stage: test
  needs: []
  cache:
    key: { files: [frontend/package-lock.json] }
    paths: [frontend/.npm]
  script:
    - cd frontend
    - npm ci --cache .npm --prefer-offline
    - npm test -- --watch=false --code-coverage   # adapt to the project's script and runner
    - npm run build -- --configuration production
  artifacts:
    paths: [frontend/coverage/, frontend/dist/]
    expire_in: 1 week

sonar:
  extends: .maven
  stage: quality
  needs: ["backend:verify", "frontend:test-build"]
  variables: { GIT_DEPTH: "0" }            # full history for new-code detection and blame
  script: mvn $MAVEN_CLI_OPTS sonar:sonar -Dsonar.qualitygate.wait=true

image:build:
  stage: package
  needs: ["backend:verify", "frontend:test-build"]
  # use the organisation's builder (Buildah, BuildKit, or a template); avoid privileged Docker-in-Docker
  script: ./ci/build-image.sh "$CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA"
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH || $CI_COMMIT_TAG

# security:nexus-iq, security:fortify, security:sysdig — from the central security templates

deploy:dev:
  stage: deploy
  needs: ["image:build"]                   # plus the security jobs that must pass
  resource_group: deploy-dev               # one deployment at a time
  environment: { name: dev }
  script: ./ci/bump-gitops.sh dev "$CI_COMMIT_SHORT_SHA"   # commit the new tag to the GitOps repo
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

Production promotion follows the same GitOps step on a tag or release, with a **protected environment** (required approvals) instead of an ad-hoc `when: manual`.

## Rules and structure

- Prefer `rules:` to `only/except`. Put shared conditions in hidden jobs and reuse them with `extends` or `!reference [.rules, mr]`.
- Monorepos: `rules: changes:` (with `compare_to` for branch pipelines) or parent-child pipelines (`trigger: include:`) per component; `needs: optional: true` when a needed job may not exist.
- `needs: []` lets independent jobs start immediately; stages remain for readability.
- Tag pipelines and default-branch pipelines produce deployable artifacts; MR pipelines validate.
- Reusable logic: CI/CD components with `spec: inputs:` on recent GitLab versions; otherwise `include: project:` with a pinned `ref` (tag), never a moving branch, for templates other teams depend on.

## Speed without losing correctness

- Cache dependencies by lockfile (`pom.xml`, `package-lock.json`, `gradle.lockfile`); cache the npm cache directory rather than `node_modules`; use `policy: pull` in jobs that only read the cache.
- Pass build outputs between jobs as **artifacts** (cache is best-effort and can be missing).
- Maven: `--batch-mode --no-transfer-progress`, a repository mirror (Nexus) in `settings.xml`, `-T 1C` only if the build is thread-safe. Run only affected modules in MR pipelines when the project supports it (`-pl ... -am`).
- Use smaller test images, parallelise long suites (`parallel:` with test splitting) only when they really are the bottleneck.
- `retry:` only for infrastructure failures (`when: [runner_system_failure, stuck_or_timeout_failure, api_failure]`), never to hide flaky tests.

## Reports GitLab understands

`artifacts:reports:junit` (test results in MRs), `coverage:` regex or `artifacts:reports:coverage_report` (Cobertura; JaCoCo format on recent versions) for MR diff coverage, `dotenv` to pass variables to later jobs, and security report formats when the GitLab security templates are used.
