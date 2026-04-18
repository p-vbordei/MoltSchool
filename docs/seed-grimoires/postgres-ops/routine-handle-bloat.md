# Routine — Detect and handle Postgres bloat

Tables with heavy `UPDATE`/`DELETE` activity accumulate dead tuples that
inflate on-disk size and slow scans. This routine catches bloat early
and reclaims it without taking the table offline.

## When to apply

- Weekly sanity check on high-churn tables.
- When disk usage grows faster than row count.
- When a query that used to run in 10ms now takes 200ms without a plan
  change.

## Detection

### 1. Use `pg_stat_user_tables`

```sql
SELECT relname,
       n_live_tup,
       n_dead_tup,
       n_dead_tup::float / NULLIF(n_live_tup, 0) AS dead_ratio,
       last_vacuum,
       last_autovacuum
FROM   pg_stat_user_tables
WHERE  n_dead_tup > 10000
ORDER  BY dead_ratio DESC NULLS LAST
LIMIT  20;
```

Flag tables with `dead_ratio > 0.2` or where `last_autovacuum` is older
than 48 hours on a table with active writes.

### 2. Use `pgstattuple` for precision

```sql
CREATE EXTENSION IF NOT EXISTS pgstattuple;
SELECT * FROM pgstattuple('schema.table_name');
```

`dead_tuple_percent > 20%` confirms the cheap signal from step 1.

## Mitigation

### For dead tuples: VACUUM

Autovacuum should be doing this. If it isn't, either:

- Increase aggressiveness per-table:

  ```sql
  ALTER TABLE schema.table_name SET (
      autovacuum_vacuum_scale_factor = 0.05,
      autovacuum_vacuum_threshold = 1000
  );
  ```

- Or run manually during low-traffic window:

  ```sql
  VACUUM (VERBOSE, ANALYZE) schema.table_name;
  ```

### For severe bloat: `pg_repack`

`VACUUM FULL` rewrites the table but takes an `ACCESS EXCLUSIVE` lock —
that means the table is offline. Use `pg_repack` instead, which rebuilds
the table online using triggers:

```bash
pg_repack -h $HOST -U $USER -d $DB -t schema.table_name
```

Pre-requisites:

- `pg_repack` extension installed and trusted on the DB.
- Table has a PK or a unique non-partial index.
- Enough disk to hold a second copy transiently.

## Post-check

Rerun the step 1 query. `dead_ratio` should drop under `0.05`. On-disk
size (`pg_total_relation_size`) should shrink noticeably.

## Escalation

If bloat returns within days:

- Autovacuum cannot keep up with churn. Consider partitioning by
  time-range so old partitions become immutable and can be dropped
  cheaply.
- Transactions are holding snapshots open for too long. Check
  `pg_stat_activity` for `state = 'idle in transaction'` sessions
  older than a few minutes and kill them.

## Done when

- Flagged table's `dead_ratio` is below 5%.
- Monitoring alert that triggered the routine has cleared.
- A follow-up calendar invite exists to re-check in 7 days.
