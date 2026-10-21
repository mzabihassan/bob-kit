# Templates

Use the organisation's templates when they exist; these are compact defaults. Replace every `<…>`; keep `TBD (owner)` for unknowns.

## Technical changelog (Keep a Changelog style)

```markdown
## [<version>] - <YYYY-MM-DD>
### Breaking changes
- <what changed, who is affected, what they must do> (<MR>)
### Added
- <feature> (<MR>, <ticket>)
### Changed
### Fixed
### Security
- <fix described at the level the disclosure policy allows>
### Database migrations
- <V7__…: additive | destructive, expected duration, ordering>
### Configuration
- <new/changed property per environment; secrets to create (names only)>
### Dependencies
- <framework/runtime upgrades>
```

## Business release notes

```markdown
# <Product> <version> — <date>
**What's new**: <user-visible improvements in plain language, one line each>
**Fixes**: <problems users reported that are now solved>
**What you need to do**: <actions for users or partners, or "nothing">
**Availability**: <deployment window, expected interruption if any>
**Contact**: <support channel>
```

## Change request

| Field | Content |
| --- | --- |
| Title | `<application> <version> deployment to <environment>` |
| Type | Standard, Normal or Emergency (and why) |
| Description | What is deployed: version, main changes, linked MRs and tickets |
| Business justification | Why now; what happens if it is not deployed |
| Configuration items | Applications, services, databases, clusters, integrations affected |
| Impact | Users and systems affected; expected downtime or degradation; dependent teams |
| Risk | Level and the concrete reasons (from the assessment); mitigations |
| Implementation plan | Summary of the runbook steps, owners, duration |
| Test plan and evidence | Environments tested, results, pipeline, gate and scan links |
| Backout plan | Steps, limits, duration, decision point, tested or not |
| Schedule | Window (start, end, time zone), freeze checks |
| Approvals and communication | Required approvers; who is informed, when, through which channel |

## Deployment runbook

```markdown
# Runbook <application> <version> — <environment> — <window>
Roles: implementer <name>, decision maker <name>, DBA <name>, on call <name>
## Pre-checks (T-1 day / T-30 min)
- [ ] Artifact <image@digest> passed the pipeline <link>; approvals <link>
- [ ] Backup or snapshot of <database> taken and verified
- [ ] Monitoring dashboards and alerts open: <links>
## Steps
| # | Time | Action (exact command or GitOps MR) | Owner | Verification |
## Post-checks
- [ ] Smoke tests <list>; key metrics within <thresholds> for <duration>
## Backout (decision point: <criteria>)
| # | Action | Owner | Verification |
## Communication
- Start, end and incident messages to <channels>
```

## Post-implementation review

Outcome (successful, successful with issues, failed or backed out); deviations from the plan and why; incidents and their tickets; metrics after the release; lessons learned and actions with owners and dates.
