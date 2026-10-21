# Fortify (SAST)

## Getting the findings

Use what the project already has; check commands with `--help` for the installed version.
- **SSC / Fortify on Demand**: issues per application version, with audit history. CLI `fcli` (e.g. `fcli ssc issue list --av "<app>:<version>"`, `fcli fod ...`) with a session created from environment variables.
- **FPR file** (scan result, a zip containing `audit.fvdl`): open it in Audit Workbench, or summarise it with `FPRUtility` or `BIRTReportGenerator` if installed. An exported PDF/CSV report from the user also works.
- **Local rescan**: reuse the CI job's commands. The usual pattern is `sourceanalyzer -b <id> -clean`, then the translation step (build integration such as the Maven/Gradle plugin, or `sourceanalyzer -b <id> <sources>`), then `sourceanalyzer -b <id> -scan -f result.fpr`. A local scan may use different rule packs than CI; confirm with the CI scan.

## Reading an issue

- **Priority** ("Fortify Priority Order"): Critical (high impact, high likelihood), High (high impact, low likelihood), Medium (low impact, high likelihood), Low. Gates usually block on Critical and High.
- **Category** (`SQL Injection`, `Log Forging`…) plus kingdom; confidence; and for dataflow issues, the **trace from source to sink**. Read the whole trace: the fix belongs where untrusted data can be validated or neutralised, often at the boundary, not necessarily at the sink.
- **Analysis tags** commonly used: *Not an Issue*, *Reliability Issue*, *Bad Practice*, *Suspicious*, *Exploitable*. Audits live in SSC/FPR, not in code, so the user or security team applies them.

## Frequent categories in Java/Spring and Angular

| Category | Real fix |
| --- | --- |
| SQL Injection (JDBC, JPA, Hibernate, native queries) | Bind parameters (`:param`, `?`, Criteria API). Dynamic `ORDER BY`/column names → allow-list mapping, never concatenation |
| Log Forging | Do not log raw user input; neutralise CR/LF or rely on the project's encoder (e.g. a JSON/structured log layout that escapes). One central helper, not ad-hoc replaces |
| Privacy Violation / System Information Leak | Do not log or return PII, credentials, stack traces or internal details; mask (last four digits), generic error responses via `@ControllerAdvice` |
| Password Management: Hardcoded Password / Password in Configuration File, Key Management: Hardcoded Key | Move to a secret store or environment injection (Vault, IBM Secrets Manager, Kubernetes secrets); remove from git history only through the team's process |
| Path Manipulation | Resolve against a fixed base directory, normalise, and check `resolved.startsWith(base)`; prefer ids mapped to files over user-supplied paths |
| Cross-Site Scripting (Reflected / Persistent / DOM) | Backend: return JSON with the correct content type, encode in server-side templates. Angular/React: rely on default escaping; remove `innerHTML`/`dangerouslySetInnerHTML`/`bypassSecurityTrust*` with untrusted data or sanitise explicitly |
| Header Manipulation / Open Redirect | Validate redirect targets against an allow-list or use relative paths; never echo user input in headers without validation |
| Mass Assignment: Insecure Binder Configuration | Bind requests to dedicated DTOs, not JPA entities; or restrict allowed fields |
| XML External Entity Injection | Disable DTDs and external entities on the parser factory (`FEATURE_SECURE_PROCESSING`, `disallow-doctype-decl`) |
| Dynamic Code Evaluation: Unsafe Deserialization | Avoid Java native serialization of untrusted data; restrict Jackson polymorphic typing (no default typing; use an allow-list) |
| Server-Side Request Forgery | Allow-list of hosts or URLs; never fetch a user-supplied URL directly |
| Insecure Randomness | `SecureRandom` for tokens, ids and secrets |
| Weak Cryptographic Hash / Weak Encryption | bcrypt/Argon2/PBKDF2 for passwords; SHA-256+ for integrity; AES-GCM; follow the organisation's crypto standard |
| Cookie Security, Cross-Site Request Forgery | `Secure`, `HttpOnly`, `SameSite` on cookies; CSRF protection on for browser sessions (Spring Security); justify a disabled CSRF only for stateless token APIs |
| Access Control: Database (IDOR) | Check ownership or authorisation of the requested record in the query or service, not only the role |
| Unreleased Resource, Null Dereference, Poor Error Handling: Overly Broad Catch | Try-with-resources; real null handling; catch specific exceptions and do not swallow them |
| Denial of Service: Regular Expression | Simplify the regex, bound the input length |

## Scanner-specific cautions

- Fortify may not recognise a custom validator as a cleanser. If the code is genuinely safe, propose *Not an Issue* with the reasoning, or suggest a custom cleanse rule to the security team. Do not add pointless wrappers to break the taint trace.
- Fixing at the sink only (e.g. escaping) when a parameterised API exists is not acceptable for injection categories.
- Many issues in one category often share a single root cause (a helper that builds queries, a logging utility): fix the helper, then rescan.
- Test code and generated code are often in the scan scope: propose scan-scope changes to the team rather than fixing generated files.
