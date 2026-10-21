# Defence playbook

## 1. The thesis

One sentence a reviewer can accept: what the commit achieves and why this shape is right *for this context*. Example: "Adds idempotent transfer submission with a unique key constraint, the smallest change that removes the duplicate-payment incident without touching the client contract."

## 2. Kinds of evidence (strongest first)

| Evidence | How to use it |
| --- | --- |
| **A test that proves the behaviour** | Name it, say what it asserts, run it if possible. A test that fails without the commit is the strongest argument there is |
| **The requirement** | Quote the ticket or acceptance criterion the change satisfies; show that extra scope was deliberately left out |
| **Precedent in the codebase** | Point to existing code that does the same thing the same way (`path:line`): consistency is a strong argument against "why not X?" |
| **Official documentation or standards** | Framework docs, the project's `AGENTS.md`/rules, security or style guides (check current docs via Context7 when available) |
| **Measurement** | Benchmarks, query plans, coverage reports, pipeline results: only real numbers, with how they were obtained |
| **Constraints** | Versions in use, backward compatibility, deadlines, other teams' dependencies, licences, platform limits: real and verifiable |
| **Risk analysis** | Small blast radius, easy rollback, feature flag, additive migration: why the risk is acceptable |
| **Reasoned trade-off** | When there is no hard evidence: name the alternatives, what each would cost, and why this one wins. Mark it moderate or weak |

## 3. Key decisions to defend

Look for the choices a reviewer will question: the approach and where the code lives, the scope (what is in, what was left out), abstractions added or avoided, new dependencies, data or contract changes, error handling and retry strategy, test level and coverage, naming that departs from expectations, and anything that differs from the codebase's usual pattern. For each: the decision, the reason, the evidence, the alternatives and why they were rejected.

## 4. Anticipating objections

Attack the commit as a demanding reviewer would, across correctness and edge cases, concurrency and data, security, failure handling, performance, tests, design and naming, consistency with the codebase, and commit hygiene. For each objection, choose the honest response:

| Response | When | Form |
| --- | --- | --- |
| **Rebutted** | The objection is wrong or does not apply | The evidence that shows it (a test, a guard at `path:line`, a constraint that makes the case impossible) |
| **Mitigated** | True, but the risk or cost is acceptable here | Why: the volume, the exposure, an existing safeguard, a follow-up already planned |
| **Conceded** | True and it matters | Agree plainly; propose the smallest fix (snippet) to make **before** the review, or a follow-up ticket if it is out of scope |

Never rebut with "it works on my machine", authority ("the lead said so") without a record, or unverifiable claims.

## 5. Strengthening before the review

Cheap actions that remove attack surface: add the missing test for the obvious edge case, rename a misleading identifier, split an unrelated change into its own commit, remove debug leftovers, add the "why" to the commit message or a code comment, link the ticket. List them with their effort; the user decides.
