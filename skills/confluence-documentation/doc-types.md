# Page types and templates

Use the organisation's Confluence templates and blueprints when they exist. Keep every template short: delete sections that do not apply rather than writing "N/A".

## Which type?

| The reader wants to… | Type |
| --- | --- |
| Learn by doing, step by step (newcomer) | **Tutorial / onboarding** |
| Achieve a specific task (deploy, rotate a secret, restart a batch) | **How-to / runbook** |
| Look up facts (endpoints, properties, error codes, flows) | **Reference** |
| Understand why the system is like this | **Explanation / design**, **ADR** |

## ADR (Architecture Decision Record)

```
Status: Proposed | Accepted | Superseded by <link> · Date · Deciders
Context — the problem and the forces (constraints, requirements, risks), with links.
Decision — what was decided, in one or two sentences.
Options considered — each with pros, cons and why it was or was not chosen.
Consequences — what becomes easier, harder, the follow-up work, the risks accepted.
```
If the project keeps ADRs in the repository, the Confluence page links to them instead of duplicating them.

## Solution / technical design

```
Summary — what is built and why (business goal, ticket or epic link).
Scope — in scope, out of scope.
Context — systems and actors around it (C4 context or container diagram).
Design — components and responsibilities, main flows (sequence diagrams for critical ones), data model, APIs and contracts.
Cross-cutting — security (authentication, authorisation, data classification, encryption), resilience (timeouts, retries, idempotency), observability, performance and capacity.
Deployment — environments, infrastructure, configuration, migration and rollout plan.
Risks and open questions — with owners.
Decisions — links to the ADRs.
```

## Runbook (operations)

```
Service — what it does, criticality, owners and on-call, dashboards and log queries (links).
Dependencies — upstream and downstream systems, and what happens when each fails.
Routine procedures — each as: when to use it · prerequisites · numbered steps with the exact command and the expected result · how to verify · how to roll back.
Alerts — for each alert: meaning, likely causes, first checks, mitigation, escalation.
Known issues — symptoms and workarounds.
Contacts and escalation path.
```
Steps must be executable by someone who does not know the system, at 3 a.m.

## Integration / API guide

```
Purpose and audience · environments and base URLs (non-secret) · authentication and how to obtain credentials (the process, never the credentials) · main use cases with request and response examples · error codes and retry rules (idempotency) · limits and SLAs · versioning and deprecation policy · contacts.
```
Link to the OpenAPI or AsyncAPI specification as the source of truth.

## Onboarding

```
Goal of the first week · access to request (the process) · local setup step by step with the expected result of each step · architecture overview (link to the design) · conventions (link to AGENTS.md and the contribution guide) · a first small task · who to ask.
```

## Release page and post-mortem

Use the structures from the `release-change-management` (`templates.md`) and `production-incident-investigation` (`communication-postmortem.md`) skills when installed; publish the release page under the product's release tree, and the post-mortem under the incident space with restricted access if it contains sensitive details.
