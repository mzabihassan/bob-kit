# Coverage targeting and measurement

## Know which number you are moving

- **Coverage on new code** (default Quality Gate condition, often ≥ 80%) is computed only on lines added or changed in the new-code period (previous version, number of days, or reference branch). Focus on files changed in that period: `git diff --name-only <reference>...HEAD`, or Sonar's new-code view. A few tests on recently changed classes can turn the gate green, while overall coverage barely moves.
- **Overall coverage** moves slowly on large codebases: 1 pp needs about 1% of all lines+conditions covered. Use the script's "max gain pp" to set realistic expectations before starting.
- Sonar combines lines and conditions: coverage ≈ (covered conditions + covered lines) / (total conditions + total lines). Covering branches matters as much as lines.
- Java and Angular are often separate Sonar projects or modules; measure each one separately.

## Find candidates fast

```bash
# scripts/ is relative to this skill's directory (given when the skill is activated)
# Java (Maven / Gradle), after running tests with JaCoCo
python3 scripts/coverage_hotspots.py target/site/jacoco/jacoco.xml --src .
python3 scripts/coverage_hotspots.py $(find . -path '*/jacoco*/*.xml' -not -path '*/node_modules/*') --src .
# Angular, after `ng test --code-coverage` / `jest --coverage` / `vitest run --coverage`
python3 scripts/coverage_hotspots.py $(find coverage -name lcov.info) --src .
# New code only
git diff --name-only origin/main...HEAD > /tmp/changed.txt
python3 scripts/coverage_hotspots.py target/site/jacoco/jacoco.xml --changed /tmp/changed.txt
```

The script ranks files by `max gain / effort`, where effort is a heuristic based on the file's kind, the number of injected dependencies, use of infrastructure (DB, HTTP, files, DOM, timers) and whether a test already exists. It also excludes tests and generated code (add `--exclude` globs if needed). It is a shortlist, not a verdict: open the top candidates and confirm before writing tests.

From SonarQube directly (token in `SONAR_TOKEN`; never print it):
```bash
curl -s -u "$SONAR_TOKEN:" "$SONAR_URL/api/measures/component_tree?component=<projectKey>&metricKeys=uncovered_lines,uncovered_conditions,coverage&qualifiers=FIL&s=metric&metricSort=uncovered_lines&asc=false&ps=50"
# new code: metricKeys=new_uncovered_lines,new_uncovered_conditions,new_coverage
```

## What usually pays off

| Usually quick wins | Usually poor return |
| --- | --- |
| Pure logic: calculators, policies, rules, validators, mappers, utilities, enums with behaviour, pipes, pure functions | Configuration classes, `main`, framework wiring, generated code |
| Services with 1–3 dependencies and branching logic | Services with many collaborators whose logic is mostly delegation |
| Existing test classes missing branches (setup already exists: add cases) | Code needing a new test infrastructure (broker, external system) for a few lines |
| Methods with many uncovered branches reachable through one public entry point (parameterised tests) | Private methods only reachable through complex flows |
| `@ControllerAdvice` exception handlers, controller validation paths (one slice test covers many lines) | UI components dominated by DOM, animations or third-party widgets |
| Angular services with HTTP (one `HttpTestingController` setup, many cases), guards, interceptors, validators, signal-based state | Deep component trees requiring many child mocks |

Also check:
- **Dead code**: unreachable or unused code lowers coverage and maintainability. Removing it (after confirming with usages search) is a legitimate win, but treat it as a production change.
- **Lombok**: with `lombok.addLombokGeneratedAnnotation = true` in `lombok.config`, JaCoCo ignores generated getters/equals. This is a legitimate exclusion of generated code, but it is a team decision: propose it, don't apply it silently.
- **Wrong measurement**: 0% on a module that has tests usually means a report problem (agent not attached, wrong report path, LCOV paths not matching Sonar's sources), not missing tests. Fix the measurement first. It is the cheapest "gain" and it is real.

## Estimate, execute, verify

1. For the chosen batch, note the expected gain (the sum of max gain × the fraction you expect to cover).
2. Write the tests, run them, regenerate the report for the module, rerun the script or read the report.
3. Report the measured delta. If the gain is far below the estimate, find out why (branches not exercised, exclusions, report not refreshed).

## When to stop

Stop and recommend instead when:
- the gate condition is met and the remaining candidates have effort ≥ 3;
- the next gains need production refactoring or new infrastructure;
- the tests you would write could only assert implementation details;
- the session's time budget is reached.
