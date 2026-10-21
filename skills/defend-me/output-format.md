# Output format

Write it in the user's language. Persuasive, precise, no filler.

```markdown
# Defence of <short-sha> — "<commit subject>"

**Thesis:** <one sentence>.
**Overall position:** <Strong | Defensible with fixes | Weak> — <why, in one line>.

## Key decisions
1. **<decision>** — <reason>.
   Evidence: <test / requirement / precedent `path:line` / doc / measurement> · strong
   Alternatives rejected: <alternative> because <reason>.

## Objections and responses
| Objection | Response | Evidence | Status |
| --- | --- | --- | --- |
| <what a reviewer will say> | <answer> | <checkable reference> | Rebutted / Mitigated / Conceded |

## Concessions and fixes before review
- <point conceded> → <smallest fix, effort> (or follow-up ticket)

## Drafts
### MR description
<What, why, how it was tested, risks and rollback, what is deliberately out of scope.>
### Improved commit message (if needed)
### Replies to review comments
> <reviewer comment>
<Reply: thank briefly if appropriate; answer with evidence; agree and commit to a fix when they are right; ask a clarifying question when the comment is ambiguous.>
```

Rules for the content:
- Every Key decision and every Rebutted objection has a checkable piece of evidence; without one it is at most Mitigated, labelled as a reasoned trade-off.
- Put the strongest arguments first; do not pad with weak ones.
- Replies to reviewers stay courteous and short, never defensive or ironic; when the reviewer is right, the reply says so in its first sentence.

Example:

> **Objection:** "No retry on the ledger call: a network glitch fails the transfer."
> **Response:** Deliberate. The ledger API is not idempotent (`LedgerClient.post`, no idempotency key), so a blind retry can book the debit twice; the failure is surfaced to the user, who can resubmit safely with the same idempotency key (`TransferController.java:41`, covered by `resubmitWithSameKeyIsIgnored`).
> **Status:** Rebutted · strong.
