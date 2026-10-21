# Confluence structure, macros and formats

## Finding pages (CQL)

```
space = "PAY" AND type = page AND title ~ "runbook" ORDER BY lastmodified DESC
space in ("PAY", "OPS") AND text ~ "payments-api" AND type = page
label = "adr" AND space = "ARCH" ORDER BY created DESC
ancestor = 123456 AND type = page
lastmodified < now("-365d") AND space = "PAY" AND type = page
```

The fourth query lists all pages under a parent (by page id); the fifth finds pages not modified for a year (candidates for review). CQL has no comment syntax: copy queries without annotations.

Through the MCP server's search tool, or the REST search endpoint (`/wiki/rest/api/search?cql=…` on Cloud, `/rest/api/search?cql=…` on Data Center).

## Structure

- Place the page in the space's tree under the right parent (e.g. `Payments › Operations › Runbooks`); the title says what the page is (`Runbook – payments-api`, `ADR-012 – Idempotent transfers`).
- Labels for discoverability and reports (`runbook`, `adr`, `design`, `payments-api`); follow the space's label conventions.
- **Page Properties** macro at the top (owner, status, last review date, related system) so that **Page Properties Report** pages can list, for example, every runbook and its review date.

## Useful macros (storage format)

Confluence stores pages as XHTML "storage format" on both Cloud and Data Center; Cloud's editor uses the Atlassian Document Format (ADF) internally and its REST API also accepts storage format. MCP servers often accept Markdown and convert it: check what the server supports before writing macros.

```xml
<ac:structured-macro ac:name="toc"/>

<ac:structured-macro ac:name="info">
  <ac:rich-text-body><p>Applies to payments-api 2.x only.</p></ac:rich-text-body>
</ac:structured-macro>
<!-- also: note, warning, tip -->

<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">bash</ac:parameter>
  <ac:plain-text-body><![CDATA[kubectl -n payments rollout status deploy/payments-api]]></ac:plain-text-body>
</ac:structured-macro>

<ac:structured-macro ac:name="status">
  <ac:parameter ac:name="colour">Green</ac:parameter>
  <ac:parameter ac:name="title">ACCEPTED</ac:parameter>
</ac:structured-macro>

<ac:structured-macro ac:name="jira">
  <ac:parameter ac:name="jqlQuery">project = PAY AND fixVersion = "2.4.0"</ac:parameter>
</ac:structured-macro>

<ac:structured-macro ac:name="expand">
  <ac:parameter ac:name="title">Full error list</ac:parameter>
  <ac:rich-text-body><p>…</p></ac:rich-text-body>
</ac:structured-macro>
```

- The Jira macro needs the Jira–Confluence application link; it shows live ticket lists instead of copied ones that go stale.
- **Excerpt** and **Excerpt Include** reuse one piece of content (e.g. a contact list) on several pages instead of copying it.
- Diagrams: use what the instance has (draw.io or Gliffy apps, a Mermaid or PlantUML app); otherwise attach an exported image **and** keep the diagram source (e.g. `.drawio`, `.puml`) in the repository or as an attachment so it can be edited. Native Confluence has no Mermaid rendering.

## Writing style for Confluence pages

- Short paragraphs, descriptive headings (they build the table of contents), numbered steps for procedures, tables for reference data.
- Commands and code in code blocks with the language set; placeholders in `<angle-brackets>`.
- Screenshots only when the UI is the subject; they go stale quickly: date them.
- Links: to the repository (a path at a tag or commit, not a moving branch, for stable references), to tickets, to dashboards; avoid "click here".
