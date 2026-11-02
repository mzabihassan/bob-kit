# Quality checklist (run once over the whole set, after the export passes)

Do the accuracy spot checks in one command (one `grep -n` per fact); judge the other items from what you wrote, without re-reading the pages. The export has already checked secrets, links and structure.

## Accuracy
- [ ] Re-check five facts at random against their cited files (versions, a port, a command, an endpoint, a role): all match.
- [ ] Every command is labelled verified (run in this session) or not verified; versions come from the scan's sources, not memory.
- [ ] Nothing describes what Spring Boot or Angular projects usually do without evidence from this project.
- [ ] Documentation that the code contradicts is reported as a discrepancy, and the page follows the code.
- [ ] Unknowns are `TBD (who can answer)`; the important ones are in the landing page's open points.

## Usefulness for a newcomer
- [ ] Following Quick start alone, a developer knows what to install, what access to request, what to configure, how to run both sides and how to check it works.
- [ ] "Where to change what" answers the common tasks (endpoint, screen, migration, configuration property) with real example files.
- [ ] The frontend ↔ backend contract (base URL, proxy, authentication, error format) is explicit.
- [ ] Each page starts by saying what it answers; headings are descriptive; tables hold reference data; no framework tutorial.

## Structure and maintenance
- [ ] One landing page; every other page has a parent; titles are unique and prefixed with the project name.
- [ ] No fact is duplicated across pages (the export warns about repeated paragraphs); pages link to each other instead.
- [ ] Each page cites the files it is based on; links to the repository point at the analysed commit.
- [ ] The landing page records `source_commit`, the date and how to update the playbook.

## Safety
- [ ] No secret values, tokens, passwords, private keys, connection strings with credentials, personal or production data (the export fails on common patterns; also read for the rest).
- [ ] Internal hostnames and URLs only where a developer needs them; otherwise the configuration key that holds them.
- [ ] Secrets found committed in the repository are reported to the user by location, not documented.
