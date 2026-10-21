# SonarQube issues, hotspots and Quality Gate

## Two severity models

- **Standard Experience** (classic): issue types **Bug**, **Vulnerability**, **Code Smell** (plus **Security Hotspots**, reviewed separately); severities **Blocker > Critical > Major > Minor > Info**.
- **Multi-Quality Rule (MQR) mode** (SonarQube Server 10.8+/2025.x, SonarQube Cloud): each issue has an impact on one or more software qualities (**Security**, **Reliability**, **Maintainability**), with impact severities **Blocker > High > Medium > Low > Info**, plus a Clean Code attribute (consistency, intentionality, adaptability, responsibility).

Map them roughly as: Vulnerability ≈ Security, Bug ≈ Reliability, Code Smell ≈ Maintainability. Use the model the instance displays and quote rule keys (`java:S2259`, `typescript:S1854`), which are stable across both.

## Getting the list

Prefer, in order: a SonarQube MCP server if configured; SonarQube for IDE (connected mode) for local verification; the Web API (token in `SONAR_TOKEN`, never echoed):

```bash
# Open issues, highest impact first (MQR); for classic use &severities=BLOCKER,CRITICAL,MAJOR&types=BUG,VULNERABILITY
curl -s -u "$SONAR_TOKEN:" "$SONAR_URL/api/issues/search?components=<projectKey>&issueStatuses=OPEN,CONFIRMED&impactSeverities=BLOCKER,HIGH&ps=100"
curl -s -u "$SONAR_TOKEN:" "$SONAR_URL/api/hotspots/search?projectKey=<projectKey>&status=TO_REVIEW"
curl -s -u "$SONAR_TOKEN:" "$SONAR_URL/api/qualitygates/project_status?projectKey=<projectKey>"
# add &branch=<name> or &pullRequest=<id> as needed; &inNewCodePeriod=true for new-code issues
```

Parameter names vary between versions (e.g. `componentKeys` vs `components`); check `/api/webservices/list` or the docs for the instance. Without Sonar access, work from the user's export or screenshots, and from the rule descriptions.

## Triage before fixing

| Category | Action |
| --- | --- |
| Real, high impact (security, data loss, crash, wrong result) | Fix first, even if it takes effort; plan it if large |
| Real, cheap (≤ a few lines, local) | Fix in batches, grouped by rule; one rule at a time is easier to review |
| Real but expensive (architecture, wide refactor) | Recommend with cost and risk; do not start without agreement |
| Low value (cosmetic, in untouched stable code) | Fix only in files you are already changing, or leave |
| False positive / accepted by design | Explain why; the user marks it in SonarQube (**False Positive** or **Accept**, formerly *Won't Fix*) with the justification. `// NOSONAR` only if the team allows it, always with a reason |

Read the rule description and the surrounding code before fixing: a "fix" that changes behaviour is worse than the issue.

## Frequent issues and their minimal fix

Java:
- `S2259` null dereference → guard at the right level or fix the source of null; don't sprinkle `!= null` everywhere.
- `S2095` resource not closed → try-with-resources.
- `S2142` `InterruptedException` swallowed → restore with `Thread.currentThread().interrupt()` and stop/rethrow.
- `S112` generic exceptions / `S1166`-style swallowed exceptions → throw a specific exception, keep the cause, log once.
- `S3655` `Optional.get()` without check → `orElseThrow(...)`, `map`, `ifPresent`.
- `S3776` cognitive complexity → guard clauses, extract well-named methods, a lookup table instead of nested `if`/`switch`; only if tests cover the method (add them first).
- `S1192` duplicated string literals → a constant when the literals have the same meaning. Different meanings stay separate.
- `S2885` non-thread-safe static fields (`SimpleDateFormat`) → `DateTimeFormatter`.
- `S1874` deprecated API → the documented replacement for the project's version (check via Context7).
- Unused code (`S1068`, `S1144`, `S1481`, `S1172`) → remove after a usages search (watch for reflection, Spring, serialization).
- Tests: `S2699` tests without assertions, `S5778` several calls inside `assertThrows` lambdas → fix while you're there; they count against maintainability.

TypeScript/Angular:
- `S1854` dead stores, `S1128` unused imports, `S1186` empty functions → remove or document intent.
- `S3358` nested ternaries, `S3776` complexity → extract functions, early returns.
- `S4144` identical functions, duplicated blocks → extract only if they truly represent the same rule.
- `S2933` members never reassigned → `readonly`.
- `S6268`-style Angular sanitizer bypass (`bypassSecurityTrust*`) → remove or restrict to trusted constants with justification.

Rule keys vary by language plugin version; trust the key shown by the instance.

## Security hotspots

Hotspots need a **review**, not necessarily a code change. For each one: determine if the code is exploitable in context, fix it if so (e.g. parameterised SQL, no hard-coded credentials, strong hashing such as bcrypt/Argon2 for passwords, `SecureRandom` for tokens, explicit CORS origins, CSRF enabled for browser sessions, no debug features in production); otherwise document why it is safe so the user can mark it **Safe**/**Acknowledged**. Gates often require 100% of hotspots reviewed on new code.

## Duplications

Fix real duplication of logic (extract a shared method/class within the right module). Duplicated test setup is often better solved with fixtures or builders. Excluding generated code or DTO boilerplate from CPD (`sonar.cpd.exclusions`) is legitimate only if the team agrees. Propose it; never hide real duplication.

## Quality Gate failures

1. Read which conditions fail (`project_status`): new coverage, new issues/ratings, duplication, unreviewed hotspots.
2. Fix the cheapest path to green for each failing condition first, but never by deleting tests, excluding real code or suppressing real issues.
3. Confirm with a new analysis (CI or a local scanner run if available). Until then, report the gate as "expected to pass, not verified".

## Integrity rules

No mass `// NOSONAR`, no quality profile changes, no exclusions of production code, no lowered thresholds to get a green gate. If the gate is unrealistic for legacy code, say so and suggest a team discussion (e.g. "Clean as You Code", focusing the gate on new code).
