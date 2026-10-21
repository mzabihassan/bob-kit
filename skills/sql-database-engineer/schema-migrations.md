# Schema migrations and data changes

## Rules of the migration tool

- Flyway: versioned `V<n>__<desc>.sql` (immutable once applied; checksum validation), repeatable `R__` for views and procedures; Liquibase: changesets identified by `id` + `author` + file, never modified once applied. Follow the project's naming, folder layout and changelog structure.
- A mistake in an applied migration is fixed with a **new** migration (forward fix). Do not plan on automatic down-migrations in production.
- Keep one logical change per migration; separate schema changes from large data backfills.

## Expand → migrate → contract (zero downtime)

During a rolling deployment the old and new application versions run against the same schema. Every step must work with both.

| Change | Safe sequence |
| --- | --- |
| Add a column | Add nullable (or with a default) → deploy the code that writes it → backfill → add `NOT NULL` later |
| Rename a column or table | Add the new one → write to both (application or trigger) → backfill → read from the new one → stop writing the old one → drop it in a later release |
| Change a type | New column with the new type, same process as a rename |
| Drop a column | Stop using it in the code (and in JPA mappings) first → drop it in a later release |
| Add `NOT NULL` or `UNIQUE` on existing data | Clean the data first; then add the constraint in a way that limits locking (below) |
| Split or merge tables | Expand/contract with dual writes, or a view over the new structure during the transition |

## Engine specifics

**PostgreSQL**
- DDL is transactional (a failed migration rolls back completely), but most `ALTER TABLE` statements take an `ACCESS EXCLUSIVE` lock: set `lock_timeout` (e.g. `SET lock_timeout = '5s'`) so the migration fails fast instead of queueing behind long transactions and blocking all traffic.
- `ADD COLUMN … DEFAULT <constant>` is fast since PostgreSQL 11 (no table rewrite); volatile defaults and most type changes rewrite the table.
- `CREATE INDEX CONCURRENTLY` (and `DROP INDEX CONCURRENTLY`) avoids blocking writes but cannot run inside a transaction: in Flyway, mark the script as non-transactional (script configuration `executeInTransaction=false`, per the version's docs); in Liquibase, use `runInTransaction="false"`. If it fails, it leaves an `INVALID` index to drop.
- `NOT NULL` on a large table: add `CHECK (col IS NOT NULL) NOT VALID`, then `VALIDATE CONSTRAINT` (lighter lock); on PostgreSQL 12+ a validated check lets `SET NOT NULL` skip the full scan. Same for foreign keys: `NOT VALID`, then `VALIDATE`.

**Oracle**
- **DDL commits implicitly**: a migration script with several DDL statements can be left half-applied. Keep one DDL per migration where possible, and make scripts re-runnable or easy to complete.
- Adding a column with a default is a metadata-only change (11g for `NOT NULL` columns, 12c for nullable ones).
- `CREATE INDEX … ONLINE` and online table redefinition (`DBMS_REDEFINITION`) depend on the edition (Enterprise). Check before relying on them.
- Invisible columns and indexes, and edition-based redefinition, can support zero-downtime changes if the organisation uses them.
- Watch `ORA-00054` (resource busy): set `DDL_LOCK_TIMEOUT` for the session instead of retrying blindly.

## Backfills and data fixes

- Backfill large tables in batches (by key range, with a commit per batch), outside the schema migration transaction or as a separate job; make it restartable and idempotent (`WHERE new_col IS NULL`).
- Production data fixes: a reviewed script, a preliminary `SELECT COUNT(*)` with the same predicate, an explicit transaction with the expected count checked before commit, an audit trail (ticket, who, when), and a way back (backup, Oracle Flashback Query, or a compensating script). Executed through the change process, usually by DBAs.
- Never put production data in migration scripts that also run in other environments, unless it is reference data.

## Validate a migration

1. Run it on an empty database (Testcontainers, same engine and major version) through the application's normal startup or test suite.
2. Run it on a copy of the current schema with realistic volumes when locks or durations matter, and measure the duration.
3. Check that the **previous** application version still works against the migrated schema (rolling deployment).
4. Check that the JPA mappings validate (`spring.jpa.hibernate.ddl-auto=validate` in a test), and that indexes and constraints exist as expected.
