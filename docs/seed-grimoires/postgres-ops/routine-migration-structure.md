# Routine — Safe migration structure

Every schema change ships as a single migration file with an explicit
up/down pair. The migration is the unit of review, the unit of deploy,
and the unit of rollback.

## When to apply

- Any change that adds/drops/alters tables, columns, indexes,
  constraints, or enums.
- Any data backfill that writes to production tables.

## Structure

One file, one concern, one downtime story.

```
migrations/
├── 20260418_1030__add_kindreds_archived_at.sql
├── 20260418_1105__backfill_kindreds_archived_at.sql
└── 20260418_1200__drop_kindreds_legacy_status.sql
```

Notice: three files for one conceptual change ("move from `status`
enum to `archived_at` nullable timestamp"). Splitting like this lets
each step deploy independently and lets old app code keep running
between them.

## Rules

### 1. Online-safe DDL

On Postgres 12+, most DDL takes an `ACCESS EXCLUSIVE` lock briefly —
but that brief lock can still block every connection. Use
`CREATE INDEX CONCURRENTLY`, `ADD CONSTRAINT ... NOT VALID` followed
by `VALIDATE CONSTRAINT`, and `SET lock_timeout = '2s'` to fail fast
rather than queue.

### 2. Reversible down

Every migration has a `down` path that restores the previous state.
For irreversible operations (dropping a column containing data), the
`down` MUST fail loudly rather than silently recreate the column
empty. Your team's rollback plan for that migration is a restore
from backup, not a `down` script.

### 3. No data + schema in the same file

Separate DDL migrations from DML backfills. Backfills run in batches
with a `LIMIT` + `WHERE id > $last_id` loop. They commit every batch.
They can be paused, resumed, and re-run idempotently.

### 4. Zero-downtime sequence for column rename

Never `ALTER COLUMN RENAME`. Instead:

1. Add the new column (nullable, no default).
2. Deploy app code that writes to both columns.
3. Backfill the new column from the old.
4. Deploy app code that reads from the new column.
5. Stop writing to the old column.
6. Drop the old column.

Six deploys, not one. Each deploy is safely reversible.

## Pre-merge checklist

- [ ] Migration has both `up` and `down`.
- [ ] `down` either restores state fully or fails with a clear
  message.
- [ ] If DDL on a large table, locks are bounded (`lock_timeout`).
- [ ] If data backfill, it's in a separate migration and runs in
  batches.
- [ ] Tested against a production-sized replica.

## Done when

- Migration applies cleanly on staging.
- Downgrade applies cleanly on staging.
- Post-migration application smoke test passes.
