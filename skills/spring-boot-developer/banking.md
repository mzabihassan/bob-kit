# Banking and high-integrity systems

Apply when the code moves money, holds balances, books transactions, or integrates with financial systems; many points also fit insurance, billing or any system of record. Never guess a financial rule (rounding, day count, fees, cut-off): ask, or find it in the specification or existing code.

## Money and calculations

- `BigDecimal` only, created from `String` or `BigDecimal.valueOf(...)`, never `new BigDecimal(double)`, never `double`/`float`. Compare with `compareTo` (`equals` is scale-sensitive).
- Keep amount and currency together (a `Money` value object or the project's equivalent); never add amounts in different currencies. Scale follows the currency's minor units (ISO 4217: EUR 2, JPY 0, BHD 3).
- Rounding is a business rule: explicit `RoundingMode` (often `HALF_EVEN` or `HALF_UP` per product or regulation), applied at defined points, not at each intermediate step. Allocations (splitting a fee or instalments) must distribute the remainder so parts sum exactly to the total.
- Interest and fees: day-count convention (ACT/360, ACT/365, 30/360), compounding and accrual frequency come from the product definition.
- FX: rate with its scale, source, timestamp and direction; record the rate used on the transaction.
- Persistence: `NUMERIC/DECIMAL` with enough precision (e.g. `(19,4)` or per standard); JSON amounts as strings or with a documented decimal contract (JavaScript loses precision).

## Time

- Distinguish booking date, value date and business (processing) date. Store instants in UTC (`Instant`/`OffsetDateTime`); represent business dates as `LocalDate` in the bank's reference zone.
- Holiday calendars and cut-off times decide when an operation is executed; inject a `Clock` and a business-calendar service, never `now()` scattered in code.

## Transaction integrity and concurrency

- Double-entry: every movement produces balanced entries (debits = credits). Ledger entries are immutable; corrections are reversals or adjustments, never updates or deletes.
- Balance updates must be safe under concurrency: optimistic locking (`@Version`) with a bounded retry, or pessimistic locks (`SELECT … FOR UPDATE`) acquired in a consistent order (e.g. by account id) to avoid deadlocks, or a guarded update (`UPDATE … SET balance = balance - :amt WHERE id = :id AND balance >= :amt`) checking the affected row count.
- One business operation = one local DB transaction where possible. Know the isolation level in use and its anomalies.
- Model operations as explicit state machines (`PENDING → SENT → CONFIRMED | REJECTED`, plus **`UNKNOWN`** after a timeout). An unknown outcome is resolved by inquiry or reconciliation, never by blindly resending a payment.

## Idempotency and duplicates

- Client-retriable commands carry an idempotency key (or a natural business reference). Enforce uniqueness with a DB constraint, store the request fingerprint and response, replay the stored response on duplicates, reject the same key with a different payload.
- Messaging is at-least-once: consumers deduplicate (processed-message table keyed by message id or business reference, written in the same transaction as the effect).
- DB change + message publication: transactional outbox (or CDC), not "save then send". Avoid XA/2PC unless the platform already mandates it.
- Distributed operations: sagas with explicit compensations, each step idempotent.

## Audit and traceability

- Record who, what, when, from where and why, with before/after values for sensitive changes. Audit data is append-only and protected from modification (separate table/store, restricted rights, optionally hash-chained).
- Propagate a correlation id end to end (API → services → messages → batch → external systems) and log it.
- Maker-checker (four-eyes) for sensitive operations (limits, beneficiaries, manual adjustments) when the domain requires it.

## Sensitive data

- Classify data: card numbers (PAN), IBAN/account numbers, credentials, personal data. Mask in logs and error messages (e.g. last four digits); beware `toString()` on records/Lombok DTOs and exception messages that embed payloads.
- Encrypt in transit (TLS, mTLS between systems) and at rest; field-level encryption or tokenisation for the most sensitive fields; keys in an HSM/KMS/vault.
- Minimise data (GDPR), respect retention obligations, and never use production data in tests or lower environments without approved anonymisation. PCI DSS: keep card data out of systems that do not need it.

## Integrations

- Standards you may meet: ISO 20022 (`pain`, `pacs`, `camt`), SWIFT MT, SEPA, card schemes, open-banking APIs (PSD2). Validate against schemas; keep mapping logic in an anti-corruption layer.
- Legacy and mainframe: IBM MQ (transactional sessions, backout queues for poison messages), fixed-width files, COBOL copybooks, EBCDIC, packed decimals (COMP-3), SFTP exchanges with checksums and control totals.
- Every remote call has a timeout, a retry policy appropriate to its idempotency, and a circuit breaker where failures cascade. Sign or authenticate messages as the counterpart requires.

## Batch processing and reconciliation

- Spring Batch (or the project's framework): restartable jobs, chunk-oriented with explicit skip/retry policies, idempotent writers, the business date as a job parameter, no duplicate run for the same date (job instance uniqueness or a lock).
- Control totals (record count and amount sums) at input and output; fail loudly on mismatch.
- Reconciliation compares internal records with external statements/ledgers; breaks go to an exception queue for investigation, not silent auto-correction.
- Monitor duration against the batch window and alert on failure; provide a documented rerun/recovery procedure.

## Errors and recovery

- Classify failures: technical retryable, business rejection, and unknown outcome. Each has a defined path (retry with backoff, user-facing error, inquiry/reconciliation).
- Never lose a message or a request: DLQ with alerting, and tooling or runbooks to replay safely.
- Prefer failing closed (reject) over proceeding with uncertain data.

## Regulatory awareness

PSD2/SCA, DORA (operational resilience, incident reporting), AML/KYC checks, SOX-style change control, data residency. Flag when a change may touch these; do not claim compliance yourself.

## Tests that matter here

Rounding and allocation tables, boundary amounts, currency scales, end-of-month/holiday/cut-off dates, concurrent updates of the same account, duplicate requests and messages, timeout-then-success scenarios, batch restart after failure mid-chunk, reconciliation with injected breaks.
