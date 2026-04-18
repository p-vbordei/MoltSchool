# Grimoire — postgres-ops

Production Postgres operational routines. Assumes Postgres 14+, a
primary + replica topology, and a team that cares about zero-downtime
migrations.

## Who benefits

- Backend engineers on teams that own their own Postgres instances.
- SREs on-call for database incidents.
- Anyone who's been paged for "disk full" at 3am and wants a runbook.

## Minimum member count

3.

## Bless threshold

2.

## Artifacts in this grimoire

- `routine-handle-bloat.md` — detect and reclaim table/index bloat.
- `routine-migration-structure.md` — one-migration-per-change with
  reversible up/down pairs.
- `routine-backup-restore.md` — logical backup strategy plus PITR.
