# Query performance

## Get the real plan

| | Oracle | PostgreSQL |
| --- | --- | --- |
| Estimated plan | `EXPLAIN PLAN FOR …; SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY);` | `EXPLAIN …` |
| Actual plan with row counts | Run with `/*+ GATHER_PLAN_STATISTICS */`, then `SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY_CURSOR(NULL, NULL, 'ALLSTATS LAST'));` | `EXPLAIN (ANALYZE, BUFFERS) …`. It **executes** the statement: wrap DML in `BEGIN … ROLLBACK` |
| Find the costly statements | `V$SQL` / `V$SQLSTATS` (elapsed time, executions, buffer gets); AWR/ASH only if the Diagnostics Pack is licensed | `pg_stat_statements` (total/mean time, calls, rows); `auto_explain` for slow plans |
| Plan of a running query | `DBMS_XPLAN.DISPLAY_CURSOR(sql_id)` | `EXPLAIN` with the same parameters; `pg_stat_activity` for what is running |

Read the plan for the **largest gap between estimated and actual rows**: that is where the optimiser went wrong, usually because of stale or missing statistics, correlated columns, functions on columns or skewed data. Then look at the most expensive operation (full scans of large tables inside loops, nested loops over large row sources, sorts or hashes spilling to disk).

Use the real bind values. Oracle uses bind peeking and adaptive cursor sharing; PostgreSQL switches prepared statements to a generic plan after five executions (`plan_cache_mode`). A plan captured with literals may differ from the application's plan.

## Indexing

- Index the columns used by selective filters and joins; **index foreign keys** used in joins, and in Oracle also to avoid table locks when the parent row is deleted or its key updated.
- Composite index column order: equality columns first, then range or sort columns; one composite index often beats several single-column ones.
- Covering indexes: PostgreSQL `INCLUDE (…)`; in Oracle, add the columns to the index. Index-only access avoids table lookups.
- Expression or function-based indexes for `UPPER(col)`, `TRUNC(date_col)`, or better, rewrite the predicate so it can use the plain column.
- PostgreSQL partial indexes (`WHERE status = 'PENDING'`) for hot subsets; in Oracle, function-based indexes that return NULL for rows to exclude.
- Before adding an index: check the existing ones (a prefix of an existing composite index may already serve), the write rate of the table and the index size. Oracle invisible indexes let you test an index without affecting other plans.

## Frequent anti-patterns and their fix

- A function or implicit conversion on an indexed column (`WHERE TO_CHAR(id) = :x`, comparing `VARCHAR2` with a number, a PostgreSQL type mismatch from a Java binding) → compare the column with a value of the same type.
- Leading wildcard `LIKE '%abc'` → full-text or trigram index (`pg_trgm`, Oracle Text), or a different search design.
- `OR` across different columns → `UNION ALL` of indexable branches, or a better index.
- `NOT IN (subquery)` with NULLs → `NOT EXISTS`.
- `COUNT(*)` to test existence → `EXISTS`, or `FETCH FIRST 1 ROW ONLY`.
- Deep `OFFSET` pagination → keyset pagination (`WHERE (created_at, id) < (:lastCreated, :lastId) ORDER BY created_at DESC, id DESC FETCH FIRST :n ROWS ONLY`).
- `SELECT *` on wide tables → only the needed columns; this enables index-only scans and smaller transfers.
- ORM N+1 queries → fetch joins, entity graphs, batch fetching (`hibernate.default_batch_fetch_size`) or DTO projections.
- Correlated subqueries executed per row on large sets → a join or window functions.

## Statistics

Stale statistics are a top cause of bad plans after bulk loads or migrations. Oracle: `DBMS_STATS.GATHER_TABLE_STATS` (scheduled job by default; histograms for skewed columns). PostgreSQL: `ANALYZE` (autovacuum usually does it; tune it for big, fast-changing tables; extended statistics `CREATE STATISTICS` for correlated columns). On shared databases, statistics changes are a DBA decision.

## Throughput (Java side)

- JDBC fetch size: the Oracle driver fetches 10 rows per round trip by default (raise it for large reads); the PostgreSQL driver loads the **whole result set into memory** unless `fetchSize` is set **and** autocommit is off (streaming).
- Batch writes: JDBC batching (`hibernate.jdbc.batch_size`, ordered inserts and updates), PostgreSQL `reWriteBatchedInserts=true`, `COPY` for bulk loads; Oracle array binding, `FORALL`/`BULK COLLECT` in PL/SQL. Commit in chunks for very large jobs.
- Connection pool (HikariCP): small pools usually perform better than large ones; size from the database's capacity, not the thread count. Set statement and lock timeouts so a stuck query does not exhaust the pool.
- Partitioning (range by date, list by tenant) helps very large tables with partition pruning and maintenance (dropping old partitions), not as a general speed-up. In Oracle it is a licensed option.
