# Page set, templates and Markdown conventions

Write the pages in the playbook language (translate the headings below). Keep each page under ~1,500 words; if a topic needs more, make it a child page. Delete sections with nothing project-specific instead of writing "N/A".

## Page set

Three Markdown files in the output folder, each holding several pages one after the other (Bob writes one file per turn and every turn re-bills the context, so fewer, larger writes cost less). The export splits them into Confluence pages, in file order. Titles start with the project name because Confluence titles are unique per space.

| File | Page `id` | Title | Parent |
| --- | --- | --- | --- |
| `playbook-1-onboarding.md` | `home` | `<Project> – Developer Playbook` | — (landing page) |
| | `quick-start` | `<Project> – Quick start` | landing |
| | `product-domain` | `<Project> – Product and domain` | landing |
| `playbook-2-design.md` | `architecture` | `<Project> – Architecture` | landing |
| | `apis-integrations` | `<Project> – APIs and integrations` | landing |
| | `codebase-guide` | `<Project> – Codebase guide` | landing |
| `playbook-3-delivery.md` | `development-workflow` | `<Project> – Development workflow and conventions` | landing |
| | `cicd-environments` | `<Project> – CI/CD and environments` | landing |
| | `operations` | `<Project> – Operations and observability` | landing |
| | `troubleshooting` | `<Project> – Troubleshooting` | landing |

Small projects may merge APIs into Architecture and Operations into CI/CD. Every page starts with its own front matter, directly after the previous page:

```
---
id: architecture
title: <Project> – Architecture
parent: <Project> – Developer Playbook
labels: <project>, playbook, architecture
---
# <Project> – Architecture

<One or two sentences: what this page answers and for whom.>
```

The landing page has no `parent` and adds `source_commit: <sha>` (one per repository if several) and `generated: <YYYY-MM-DD>` to its front matter. Pages link to each other with `[text](page:<id>)`.

## Verification labels

Facts with a cited source need no label. Label what is not plainly read from the code:

- `{{status:green:Verified}}` commands run successfully in this session (Quick start, tests).
- `{{status:blue:Documented}}` taken from project docs, not checked in the code.
- `{{status:yellow:Inferred}}` deduced from names or structure; confirm before relying on it.
- `TBD (who can answer)` for unknowns; collect the important ones in the landing page's open points.

Translate the label text with the page language (e.g. Vérifié, Documenté, Déduit). Commands not run carry `{{status:neutral:Not verified}}`.

## Markdown that converts to native Confluence elements

| Write | Becomes in Confluence |
| --- | --- |
| `##`, `###` headings (the `#` title line is used as the page title) | Headings; they build `/toc` |
| Pipe tables with a header row | Table with header row |
| ```` ```bash ```` fenced blocks with a language | Code block with that language |
| `> [!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]`, `[!CAUTION]` blockquotes | Info, tip, note, warning, error panels |
| `<details><summary>Title</summary>` … `</details>` | Expand |
| `{{status:green:Text}}` (neutral, purple, blue, red, yellow, green) | Status lozenge |
| `[text](page:architecture)` | Link to the page (plain text unless `--space-url` is given) |
| `` `path/File.java:42` `` | Link to the file at the commit when `--source-url` is given |
| ```` ```mermaid ```` with a first line `%% title: …` | Diagram rendered in the preview, pasted as an image or added from its PNG |

Give every fenced block a language; use ```` ```text ```` for trees, logs and plain output. Avoid raw HTML other than `<details>`, nested tables, and headings deeper than `###`.

## Diagrams

Three to five per playbook, each drawn only from verified relations: a system context (landing or architecture), the containers and main components (architecture), one or two sequence diagrams of key workflows (product and domain), the pipeline and deployment flow (CI/CD). An entity diagram only for ten entities or fewer. Prefer `flowchart` and `sequenceDiagram`; keep labels short and break lines with `<br/>`.

## Templates

**00 Home** — Purpose (what the system does, for whom, in three sentences) · System context diagram · Key facts table (stack and versions with sources, repositories, environments, owning team from `CODEOWNERS` or `TBD`) · How to use this playbook (the pages with one line each, newcomers start with Quick start) · Open points (top `TBD`s with who can answer) · About this playbook (source commit, date, how to regenerate it with this skill, which sections are kept by hand).

**01 Quick start** — Prerequisites (tools with versions and source; access to request: the process, never credentials) · Get the code · Configure (environment variables by name with what they are for, profiles, local services to start) · Run the backend · Run the frontend (proxy, URL) · Check it works (expected log line, URL, health endpoint) · Run the tests (unit, integration, frontend, e2e) · First-day checklist · Common problems (link to Troubleshooting). Each command block is labelled verified or not verified.

**02 Product and domain** — What the product does and its users · Key features (table: feature, frontend route, API, main backend class) · Main workflows (sequence diagram + numbered steps, with the classes involved) · Domain glossary (term, meaning, where in the code) · Business rules visible in code (validation, statuses, limits) with locations.

**03 Architecture** — Overview diagram · Architectural style and module responsibilities · Backend structure (layers or features, transactions, validation, error handling) · Frontend structure (bootstrap, routing and lazy loading, state, UI kit, i18n) · Frontend ↔ backend communication (base URL per environment, dev proxy, authentication flow and token handling, error format, CORS) · Data (database, schema migrations, main entities) · Security model (authentication, roles and where they are enforced) · Key design decisions (link the ADRs; otherwise "decisions visible in code", labelled inferred) · Known technical debt and constraints.

**04 APIs and integrations** — API conventions (base path, versioning, pagination, error body, authentication) · Endpoint groups (table: group, base path, controller, purpose; full list = the OpenAPI spec or Swagger UI path) · Outbound integrations (system, protocol, client class, configuration key, failure handling) · Messaging (topics/queues, producers, consumers, payload classes).

**05 Codebase guide** — Annotated repository tree (two levels, only meaningful folders) · Entry points · Core services and components · Where to change what (table: "I need to…" → location → example file) · Generated code and what not to edit · Naming conventions observed.

**06 Development workflow and conventions** — Branching and merge requests (from the git conventions and templates; label inferred when deduced from history) · Commit message convention · Code style and enforcement (formatter, linters, hooks) · Architectural rules enforced by tools · Testing strategy (levels, frameworks, naming, test data, coverage gates) with commands · Recipes: add an endpoint, add a screen, add a migration, add a configuration property, each as numbered steps referencing an existing example · Definition of done if the project has one.

**07 CI/CD and environments** — Pipeline diagram and stages (jobs, gates, artifacts) · Templates included from elsewhere · How a change reaches each environment (deployment mechanism, promotion, approvals) · Environments table (name, purpose, profile/values file, URL `TBD` unless documented, data, who can deploy) · Configuration per environment and where secrets come from (the mechanism, never values) · Rollback.

**08 Operations and observability** — Health, readiness and info endpoints · Logs (format, correlation id, where to read them) · Metrics and dashboards · Tracing · Alerts and on-call (links, `TBD`) · Scheduled jobs and batch · Operational considerations (time zones, cut-offs, rate limits, data retention) · Runbooks (links).

**09 Troubleshooting** — Table or sections: symptom → cause → fix → source, from the quick-start verification, the README and issues met; grows over time.
