# Communication and post-mortem

## Timeline (keep it from the first minute)

```
09:42 UTC  First alert: payments-api 5xx > 5% (Sysdig alert <link>)
09:47 UTC  Incident declared SEV2, IC: <role or name per policy>, channel <…>
09:51 UTC  Found: payments-api 1.9.0 deployed at 09:38 (Argo CD history)
09:55 UTC  Hypothesis: new ledger client timeout config → ruled out (config unchanged, logs show pool exhaustion)
10:02 UTC  Thread dumps: all request threads waiting on HikariPool.getConnection; DB shows a lock held by the V7 migration backfill
10:05 UTC  Mitigation approved by IC: stop the backfill job; 10:07 error rate back below 0.1%
```

Record facts, decisions (who approved what) and the results of each test, with UTC timestamps.

## Status update (internal)

```
[SEV2] Card payments partially failing — update #3, 10:10 UTC
Impact: ~30% of card payments failed between 09:42 and 10:07 UTC; now recovered.
Current status: mitigated (backfill job stopped). Monitoring for 30 minutes.
Next steps: reschedule the backfill in batches; reconcile the failed payments with operations.
Next update: 10:40 UTC or earlier if anything changes.
```

Cadence per severity (e.g. every 30 minutes for SEV1–2) as the organisation defines it. External or customer communication goes through the designated owners only.

## Post-mortem (blameless)

1. **Summary**: what happened, in three sentences.
2. **Impact**: duration, users, transactions or customers affected (quantified), SLO or SLA consumption, financial or regulatory impact, data consistency checks done.
3. **Timeline**: from the triggering change to full recovery, including detection and response delays.
4. **Root cause and contributing factors**: the technical cause, and the conditions that allowed it (missing test, review gap, unclear runbook, alert threshold, capacity). Ask "why" until you reach things the organisation can change; avoid "human error" as a cause.
5. **Detection**: how it was detected (alert, customer, staff), and how it could be detected sooner.
6. **Response**: what went well, what slowed the response (access, missing dashboards, unclear ownership).
7. **Actions**: each with an owner, a due date and a type (prevent, detect sooner, mitigate faster), prioritised; link the tickets. Prefer a few completed actions over a long wish list.

Language: describe systems, decisions and information available at the time ("the migration was not tested on production-sized data"), not people ("X forgot to test").

## Regulated environments

Major incidents may have reporting obligations (e.g. DORA for EU financial entities, internal risk and compliance reporting) with strict deadlines and classification criteria. Flag early that the incident may qualify and involve the designated owners; do not decide on regulatory reporting yourself.
