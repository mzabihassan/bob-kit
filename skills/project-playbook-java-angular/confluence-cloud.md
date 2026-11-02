# Delivering the playbook to Confluence Cloud

The Markdown pages in the repository are the source of truth; Confluence receives an export. `scripts/confluence_export.py` validates the pages and writes, next to them by default (`<output-folder>/confluence/`):

- `playbook.html`: all pages with a navigation tree and, per page, **Copy title** and **Copy page for Confluence** buttons;
- `manifest.json`: titles, hierarchy, labels and a hash per page, used to list what changed at the next export.

Both are generated: commit `manifest.json` (it records what was last exported) and either commit `playbook.html` or suggest ignoring it in git; do not edit them by hand.

Options: `--source-url` links file references to the repository at a fixed commit (GitLab `…/-/blob/<sha>`, GitHub `…/blob/<sha>`; `label=URL` per repository); `--space-url https://<site>.atlassian.net/wiki/display/<SPACE>` turns page links into links by title (check one after pasting); `--mermaid-js <url-or-path>` when the browser cannot reach the default CDN; `--check` validates without writing.

## Paste procedure (tell the user)

1. Open `playbook.html` in a desktop browser (Chrome, Edge or Firefox).
2. Create the landing page first, then each child page under its parent, in the order of the tree.
3. For each page: **Copy title** → Confluence title field; **Copy page for Confluence** → page body with Ctrl/Cmd+V (not "paste as plain text").
4. Diagrams: if an image did not paste, click **PNG** under the diagram in the preview and drag the file onto the page. The Mermaid source stays in an expand below it.
5. Add the labels shown above each page; type `/toc` at the top of long pages and `/children` on the landing page; publish.

What becomes native (checked against the Confluence editor's schema, `@atlaskit/adf-schema`): headings, paragraphs, bold, italic, strike, inline code, links, ordered, bullet and nested lists, tables with header rows, code blocks with their language, info/tip/note/warning/error panels, expands and status lozenges. Known limits: a file reference cannot be both code-formatted and a link in Confluence, so linked references are pasted as plain links; images given as data URIs may be dropped by the editor (hence the PNG fallback); page links become plain text unless `--space-url` is used; macros (table of contents, children, page properties) are added by hand after pasting.

## Publishing through an MCP server (only on explicit request)

With the Atlassian Rovo MCP server or `mcp-atlassian` configured:

1. Find the space and parent page with the user; search for existing pages by title and by the `playbook` label (CQL, e.g. `space = "KEY" AND label = "playbook"`) to update instead of duplicating.
2. Check which body formats the server accepts (Markdown, storage format or ADF). Send each page's Markdown without its front matter and title line when Markdown is accepted; panels, expands and status lozenges may come out as plain text through a Markdown converter: create the landing page first, show it to the user, and switch to the copy-paste bundle if the result is poor.
3. Create pages in tree order (parents first), add the labels, and add a version comment on updates.
4. On an update, change only the pages that the export lists as new or changed; before overwriting, compare the Confluence version with the last exported content and bring manual edits back into the Markdown (or into a `<!-- keep -->` section) first.

Every MCP write is visible to readers immediately: show the list of pages to create or update and wait for confirmation.

## Keeping the playbook current

- The landing page's `source_commit` records the analysed commit. To update: run the skill again; the scan's `--since` section lists the changed areas and the pages to review, and the export lists the pages whose content changed.
- Edits should go into the Markdown files (reviewed like code); sections a team writes by hand start with `<!-- keep -->` and are never rewritten by the skill.
- A Confluence page edited directly drifts from the source: say so in its "About this playbook" note and merge such edits back at the next update.
