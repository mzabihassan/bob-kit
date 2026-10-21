# Critique lenses

Ask every question that applies to the commit. A question becomes a finding only if you can answer it with evidence.

## 1. The approach

- What problem does this commit solve, according to its message and diff? Does the code actually solve *that* problem, or a nearby one?
- Is this the simplest change that could work? What would a change half this size look like?
- Is it in the right place (layer, module, service), or does it leak logic where it does not belong?
- Does the codebase already have a utility, pattern or component that does this? Was it ignored or duplicated?
- Does it introduce an abstraction, configuration option or dependency nobody needs yet? Or does it miss one the code clearly needs (third copy of the same logic)?
- What did the author not do that the change obviously required: migration, documentation, configuration per environment, feature flag, backward compatibility?

## 2. Correctness and edge cases

- What happens with null, empty, zero, negative, maximum and duplicate inputs? With unexpected enum values or new types?
- Boundaries: off-by-one, inclusive or exclusive ranges, pagination, end of month, leap years, time zones, DST, locale, rounding and money precision.
- Ordering and timing: what if this runs twice, concurrently, out of order, or is retried after a partial failure?
- Does the change silently alter existing behaviour for callers that were not touched?

## 3. Data, transactions and concurrency

- Transaction boundaries, remote calls inside transactions, lost updates, race conditions, idempotency of retried operations.
- Schema or data changes: are they backward compatible with the version still running? Reversible? Safe on large tables?

## 4. Security

- Untrusted input reaching queries, paths, commands, logs, HTML or redirects; missing authorisation or object-ownership checks; secrets or personal data committed, logged or returned; weakened security configuration.

## 5. Failure handling and operability

- What happens when a dependency is slow, down or returns garbage? Timeouts, retries (only for idempotent operations), fallbacks.
- Swallowed exceptions, lost causes, misleading error messages, logs that are useless or leak data, missing metrics for something that will fail in production.

## 6. Performance

- New queries in loops (N+1), unbounded result sets or collections, repeated expensive work, blocking calls on request or UI threads, memory retained longer than needed. Only when it plausibly matters at real volumes.

## 7. Tests

- Is there a test that fails without this commit? If not, what stops the next commit from breaking it?
- Do the tests assert outcomes, or just call the code (coverage without verification)? Do they mock the very thing they claim to test?
- Which edge cases and failure paths from lenses 2–5 are untested?
- Are the tests deterministic (time, randomness, ordering, shared state)?

## 8. Design, naming and readability

- Do names say what things are and do, or do they lie ("validate" that also saves, "util" that holds business rules)?
- Functions doing several things, deep nesting, boolean flag parameters, magic numbers, comments explaining *what* instead of *why*, dead code, commented-out code, TODOs without owner.
- Consistency with the codebase's conventions, architecture and `AGENTS.md`/rules. Deviations without a reason are findings.

## 9. The commit itself

- **Message**: does the subject say what changed and the body why? Is it accurate about what the diff really does? Does it reference the ticket if the project requires it?
- **Atomicity**: one logical change? Refactoring mixed with behaviour changes, formatting noise burying the real diff, unrelated files?
- **Leftovers**: debug logs, `System.out`/`console.log`, disabled tests, temporary flags, local configuration, generated files or binaries that do not belong.
- **Revertability**: could this commit be reverted alone without breaking the build or other commits?
