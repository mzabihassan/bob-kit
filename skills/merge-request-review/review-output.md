# Review output

## Structure

1. **Verdict**: *Approve*, *Approve with suggestions*, *Changes requested* (at least one blocking finding) or *Needs discussion* (design or scope question). One line explaining why.
2. **Summary**: what the change does and how risky it is, in two or three sentences; what was verified (tests run, pipeline status) and what was not.
3. **Findings**, grouped by severity, each with:
   - location `path/to/File.java:42` (or the diff hunk);
   - the problem and a concrete failure scenario;
   - the suggested fix (a code snippet or a GitLab suggestion when it is small);
   - *verified* or *suspected*.
4. **Questions** for the author, when intent is unclear (not disguised findings).
5. **Good points**: one to three specific things done well (tests, design choices). Skip generic praise.

For a small change, compress this into a few lines; for a release range, add a list of risky items (migrations, configuration, dependency upgrades, breaking changes) at the top.

## Severity

| Label | Meaning | Blocking |
| --- | --- | --- |
| **Blocker** | Bug, security issue, data loss or corruption, broken contract or migration, failing build | Yes |
| **Major** | Likely defect or significant risk (race, missing error handling, missing tests for risky logic, performance on a hot path) | Usually yes |
| **Minor** | Maintainability, convention or test-quality issue | No |
| **Nit** | Small style or wording point not covered by tooling; use sparingly | No |

## Comment wording (when posting to GitLab)

- Prefix each comment with its kind and whether it blocks, e.g. `issue (blocking):`, `suggestion (non-blocking):`, `question:`, `nit:`. Teams that use Conventional Comments will recognise it.
- Be specific and neutral: describe the code and the consequence ("this query runs once per order line"), not the person.
- One topic per thread; for repeated occurrences, comment once and list the other locations.
- Small fixes as GitLab suggestions, which the author can apply in one click:

````markdown
```suggestion:-0+0
BigDecimal fee = amount.multiply(rate).setScale(2, RoundingMode.HALF_EVEN);
```
````

## Publishing (only when asked)

- Prefer draft comments (the user reviews and submits them): `POST /projects/:id/merge_requests/:iid/draft_notes`, or a single summary note via `glab mr note <iid> -m "…"`. Line comments use the discussions API with a `position` (base, head and start SHAs from the MR's `diff_refs`).
- Do not approve, request changes, resolve threads or merge unless explicitly asked.
