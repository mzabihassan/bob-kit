# Concurrency and transactions

## Isolation in practice

| | Oracle | PostgreSQL |
| --- | --- | --- |
| Default | READ COMMITTED (statement-level consistent snapshot) | READ COMMITTED (snapshot per statement) |
| Stronger levels | SERIALIZABLE (transaction-level snapshot; `ORA-08177` on conflicting updates) | REPEATABLE READ (snapshot; `40001` on conflicting updates), SERIALIZABLE (SSI; may fail with `40001`) |
| Readers vs writers | Readers never block writers and writers never block readers (MVCC) | Same |
| Error inside a transaction | Only the failed statement is rolled back; the transaction continues | **The whole transaction is aborted** until `ROLLBACK` (or a rollback to a savepoint) |

Consequences: at READ COMMITTED, a "read, check, then write" sequence is a race condition (lost updates, double spending). Protect it with one of the patterns below. Code that retries on serialization failures must restart the **whole** transaction.

## Patterns for concurrent updates

- **Atomic conditional update**: `UPDATE account SET balance = balance - :amt WHERE id = :id AND balance >= :amt`, then check the affected row count. Simplest and fastest when the rule fits in one statement.
- **Optimistic locking**: a version column (`@Version` in JPA); on conflict, `OptimisticLockException`, then retry a bounded number of times or report a conflict to the user. Good for low-contention aggregates.
- **Pessimistic locking**: `SELECT … FOR UPDATE` (JPA `@Lock(PESSIMISTIC_WRITE)`), with `NOWAIT` or a wait timeout (`WAIT n` in Oracle, `lock_timeout` in PostgreSQL). Lock rows **in a consistent order** (e.g. by id) to avoid deadlocks; keep the transaction short.
- **Work queues**: `SELECT … FOR UPDATE SKIP LOCKED` (both engines) lets several workers take different rows without blocking each other.
- **Uniqueness and idempotency**: enforce them with a unique constraint (business reference, idempotency key) and handle the violation (`ORA-00001`, `23505`) as the "already processed" path. Do not rely on a prior `SELECT`.
- **Upsert**: PostgreSQL `INSERT … ON CONFLICT (…) DO UPDATE/NOTHING` (atomic). Oracle `MERGE` is not protected against a concurrent insert of the same key: be ready to catch `ORA-00001` and retry, or lock first.
- **Application-level mutual exclusion**: PostgreSQL advisory locks (`pg_try_advisory_xact_lock`), Oracle `DBMS_LOCK`, or a lock table (ShedLock for scheduled jobs).

## Deadlocks and blocking

- Deadlocks: `ORA-00060` (Oracle writes a trace file with the deadlock graph), `40P01` in PostgreSQL (details in the server log). Typical causes: rows or tables locked in a different order by two code paths, unindexed foreign keys (Oracle), and updates of the same rows from parallel batch threads. Fix the ordering or the partitioning of the work; do not just add retries.
- Blocking chains: Oracle `V$SESSION` (`BLOCKING_SESSION`), `DBA_BLOCKERS`/`DBA_WAITERS`; PostgreSQL `pg_stat_activity` with `pg_blocking_pids(pid)`, `pg_locks`. Look for sessions **idle in transaction**: they hold locks while doing nothing (often an application that opened a transaction and then made a remote call).

## Long transactions

- PostgreSQL: they prevent vacuum from cleaning dead rows (table and index bloat) and hold locks; set `idle_in_transaction_session_timeout` and `statement_timeout` where appropriate.
- Oracle: long-running queries on changing data can fail with `ORA-01555 snapshot too old` (undo retention); long DML transactions hold row locks and generate large undo.
- In Spring: keep `@Transactional` boundaries tight, with no HTTP or messaging calls inside a transaction, and batch jobs commit per chunk.

## Sequences and identifiers

Sequences are not transactional: gaps are normal (rollbacks, caching, restarts). Never use them for business numbering that must be gapless (invoice numbers): use a dedicated counter row updated under lock, or the regulatory numbering mechanism the domain requires. Align the JPA `allocationSize` with the sequence `INCREMENT BY`.
