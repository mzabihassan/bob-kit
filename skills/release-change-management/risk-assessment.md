# Impact and risk assessment

## Dimensions

| Dimension | Lower risk | Higher risk |
| --- | --- | --- |
| Blast radius | One internal feature, few users | Core flows (payments, login), many users, shared services or libraries |
| Data | No schema change, additive migrations | Destructive or long-locking migrations, data backfills, format changes of persisted data |
| Reversibility | Redeploying the previous version restores the service | Rollback impossible or lossy (migrations, external side effects already sent, messages consumed) |
| Contracts | Additive or internal | Breaking APIs, messages or files; consumers must deploy in step |
| Dependencies | Self-contained | Coordinated releases with other teams, partners or infrastructure changes |
| Evidence | Green pipeline, tests covering the change, passed gates, tested in a production-like environment | Failing or waived gates, untested paths, no pre-production run |
| Timing | Quiet period, inside the agreed window | Business peaks, month-end, quarter or year-end closing, payment cut-offs, regulatory deadlines, change freezes |
| Novelty | Familiar change type, experienced team | First use of a technology, large framework upgrade, new infrastructure |

**Overall level**: the highest dimension that cannot be mitigated drives the level (Low, Medium or High). Explain it in one or two sentences with the concrete items (e.g. "High: migration V7 rewrites the `payments` table (~40 M rows) and the old version cannot read the new format").

## Change type (ITIL-style; follow the organisation's definitions)

- **Standard**: pre-approved, repeatable, low risk (e.g. a routine deployment through the usual pipeline with no data or contract change), only if the organisation's standard-change catalogue covers it.
- **Normal**: needs assessment and approval (CAB or delegated approvers): anything with a migration, a contract change, infrastructure changes or a Medium or High risk.
- **Emergency**: restores service or fixes an urgent security issue; expedited approval, with a retrospective review. Not a shortcut for late planning.

## Mitigations

Feature flags (deploy dark, enable progressively), canary or blue-green deployments, deployment outside business hours or peaks, expand/contract migrations, backups or snapshots before data changes, extra monitoring and alerts during and after the deployment, smoke tests, a named on-call engineer and decision maker, partner communication in advance.

## Backout strategies (be explicit about limits)

| Change | Backout | Limits to state |
| --- | --- | --- |
| Application code | Redeploy the previous image (GitOps: `git revert` of the version bump) | Data written in the new format, messages already published, cache contents |
| Feature behind a flag | Turn the flag off | Side effects already executed |
| Configuration | Revert the configuration commit | Secrets rotated in between |
| Database migration | Forward fix; schema kept compatible with the previous version (expand/contract) | Restoring a backup loses the data written since: last resort, business decision |
| Infrastructure | Revert the IaC change and re-apply | Recreated resources (new IPs, lost data on deleted volumes) |
| External integrations | Coordinate with the partner | Messages or payments already exchanged need reconciliation |

State whether the backout has been tested (and where), its estimated duration, and the decision point (e.g. "if smoke tests fail or the error rate exceeds X% within 30 minutes").

## Go/no-go criteria

Pipeline green for the exact artifact; Quality Gate and security gates passed or waivers approved; tests in a production-like environment passed; migrations rehearsed on production-like volumes; backout plan reviewed (and tested if High risk); approvals obtained; monitoring and alerts ready; support and business informed; no conflicting change in the same window.
