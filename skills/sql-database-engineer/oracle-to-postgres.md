# Oracle → PostgreSQL (and portable SQL)

## Semantic differences that silently change results

These do not raise errors; they change data or results. Check every one of them in the converted code and in Java code that relies on them.

| Topic | Oracle | PostgreSQL | What to do |
| --- | --- | --- | --- |
| Empty string | `''` **is** `NULL` | `''` is an empty string, distinct from `NULL` | Decide one representation; review `IS NULL` checks, unique constraints, `CHECK`s and Java code |
| Concatenation with NULL | `'a' \|\| NULL = 'a'` | `'a' \|\| NULL = NULL` | `concat()` / `concat_ws()` or `COALESCE` |
| Integer division | `5/2 = 2.5` | `5/2 = 2` with integer operands | Cast to `numeric` where decimals are expected (amounts, rates) |
| `DATE` | Includes the time (to the second) | `date` has no time | Map Oracle `DATE` to `timestamp(0)` unless it is really a date |
| Current time | `SYSDATE`/`SYSTIMESTAMP`: current time | `now()`/`CURRENT_TIMESTAMP`: **start of the transaction**; `clock_timestamp()`: real time | Choose deliberately, especially in long transactions and batch jobs |
| End-of-month arithmetic | `ADD_MONTHS(31-JAN, 1)` = 29-FEB; from the last day of a month, the result is the last day of the target month | `+ interval '1 month'` clamps 31-JAN to 29-FEB, but 29-FEB + 1 month = 29-MAR (not 31-MAR) | Write and test a dedicated function when financial dates depend on it |
| Error in a transaction | Statement-level rollback, the transaction continues | The whole transaction is aborted | Review Java and PL/SQL code that catches an exception and continues: use savepoints or restructure |
| Unquoted identifiers | Folded to UPPER case | Folded to lower case | Avoid quoted identifiers; check native queries and JDBC metadata code |
| Implicit conversions | Lenient (`'1' = 1` works) | Strict (`operator does not exist: integer = character varying`) | Fix the types in SQL and in the Java parameter bindings |
| Sorting and collation | Binary order by default (NLS settings) | The database collation (libc/ICU) | Compare `ORDER BY` outputs, case-sensitivity and `LIKE` behaviour |
| `SELECT INTO` with no row | Raises `NO_DATA_FOUND` | No error in PL/pgSQL unless `STRICT` | Use `SELECT … INTO STRICT` where the Oracle code relied on the exception |

## Syntax mapping

| Oracle | PostgreSQL (portable form when there is one) |
| --- | --- |
| `NVL(a, b)`, `NVL2`, `DECODE` | `COALESCE(a, b)` (portable), `CASE` (portable) |
| `ROWNUM <= n` | `FETCH FIRST n ROWS ONLY` (portable on Oracle 12c+), `LIMIT n`, `row_number()` |
| `(+)` outer joins | ANSI `LEFT JOIN` (portable) |
| `CONNECT BY` hierarchies | `WITH RECURSIVE` (Oracle: recursive `WITH` without the keyword) |
| `MINUS` | `EXCEPT` |
| `FROM DUAL` | no `FROM` |
| `seq.NEXTVAL` | `nextval('seq')`, or identity columns |
| `SYSDATE`, `TRUNC(d)`, `ADD_MONTHS` | `now()`/`clock_timestamp()`, `date_trunc('day', ts)` or `::date`, interval arithmetic (see above) |
| `NUMBER` (no precision), `NUMBER(p,s)`, `NUMBER(10)` | `numeric` (slow for keys), `numeric(p,s)`, `integer`/`bigint` (for ids and counters) |
| `VARCHAR2(n BYTE/CHAR)`, `CLOB`, `BLOB`/`RAW` | `varchar(n)` (characters), `text`, `bytea` |
| Packages, package variables | Schemas plus functions; no package state (use parameters, temporary tables or custom settings) |
| Autonomous transactions (often used for logging) | None natively: move the logging to the application, or use `dblink`/`pg_background` |
| Procedures with `COMMIT` | `PROCEDURE` + `CALL` (PostgreSQL 11+); functions cannot commit |
| Synonyms | `search_path` or views |
| Optimiser hints | Ignored (the `pg_hint_plan` extension exists, but fix statistics and indexes instead) |
| `ROWID` | `ctid` is not stable: use primary keys |

## Java / Hibernate side

- Switch the JDBC driver, URL, Hibernate dialect and connection pool settings; review native queries, MyBatis mappers and `@Formula`s. JPQL is mostly portable.
- Sequences: align `allocationSize` with the new sequences; reset them after the data migration (`setval` to `MAX(id)`).
- `@Lob String` can map to PostgreSQL large objects (`oid`) instead of `text`: map it explicitly (`columnDefinition = "text"` or the Hibernate type for long text) per the Hibernate version's docs.
- Enable `reWriteBatchedInserts=true`, and set the fetch size for streaming reads (see `query-performance.md`).

## Migration process

1. **Assess**: inventory schemas, objects, PL/SQL volume, Oracle-specific features (packages, autonomous transactions, `CONNECT BY`, database links, Advanced Queuing, Oracle Text, partitioning) and the application SQL. `ora2pg` produces an assessment report and a migration cost estimate.
2. **Convert the schema**: types (especially `NUMBER` and `DATE`), constraints, indexes, sequences and identity columns; then review the generated DDL by hand.
3. **Convert the code**: PL/SQL to PL/pgSQL or move the logic to the application; fix the semantic differences above, and write tests that pin the Oracle behaviour first.
4. **Migrate the data**: `ora2pg`, `oracle_fdw`, or the cloud provider's migration service; character set conversion (to UTF8); time zones; numeric precision.
5. **Validate**: row counts and per-table checksums or aggregates (sums of amounts, counts per status), sample comparisons, the full application test suite, and side-by-side comparisons of key queries.
6. **Performance**: re-check the plans of the top queries (`pg_stat_statements`), add the missing indexes, tune autovacuum and the memory settings with DBAs.
7. **Cutover**: a rehearsed runbook (freeze, final sync, switch, smoke tests), a go/no-go decision and a rollback plan back to Oracle within a defined window.
