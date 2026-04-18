# Routine — Backup and restore

Two independent backup strategies running in parallel: logical dumps
for exactness and portability, plus WAL-based point-in-time recovery
(PITR) for RPO.

## Targets

- **RPO** (recovery point objective): ≤ 5 minutes of data loss.
- **RTO** (recovery time objective): ≤ 60 minutes from incident
  declaration to application read-write.

## Logical dumps (portable)

Daily, via cron on the replica (never the primary):

```bash
pg_dump \
  --host=$REPLICA_HOST \
  --username=$BACKUP_USER \
  --format=custom \
  --jobs=4 \
  --file=/backups/prod-$(date +%Y%m%dT%H%M).dump \
  $DB_NAME
```

- `--format=custom` gives selective restore + compression.
- `--jobs=4` parallelises table dumps.
- Run on replica so primary write throughput is unaffected.
- Encrypt at rest (the filesystem does it, or `gpg --encrypt` the
  dump file).
- Ship to cold storage (S3 Glacier, GCS Coldline) with lifecycle
  rules pruning anything older than 90 days.

## PITR (low RPO)

- Enable `wal_level = replica` and `archive_mode = on`.
- `archive_command` ships WAL segments to object storage:

  ```
  archive_command = 'aws s3 cp %p s3://pg-wal/$CLUSTER_ID/%f --only-show-errors'
  ```

- Take a `pg_basebackup` weekly. Keep last 4 bases + all WAL since
  the oldest base.
- Monitor `pg_stat_archiver.last_archived_time`. Alert if lag > 5 min.

## Restore drills

Run these on a quarterly cadence. Not drills = not working backups.

### Logical dump drill

1. Spin up a scratch Postgres instance.
2. `pg_restore --jobs=4 --dbname=scratch_db /backups/prod-YYYYMMDD.dump`
3. Run smoke queries (row counts per major table, recent-row
   timestamps).
4. Destroy scratch instance.

### PITR drill

1. Spin up a scratch instance from the most recent basebackup.
2. Set `recovery_target_time = 'YYYY-MM-DD HH:MM:SS UTC'` — pick a
   time 2 hours ago.
3. Restart in recovery mode; watch it replay WAL up to the target.
4. Confirm data matches a known row at that timestamp.

Record drill outcome + elapsed wall time. If RTO exceeds the 60-min
target, the drill fails even if the restore eventually completes.

## Incident runbook

On a real incident:

1. Declare the incident. Stop writes (flip app to read-only or
   maintenance page).
2. Decide: logical dump (known exact state) or PITR (minimum data
   loss). PITR almost always wins unless the logical dump is fresher
   than the last known-good state.
3. Restore to a new instance (never the live one).
4. Validate with the smoke queries from the drill.
5. Flip DNS / connection string to the new instance.
6. Post-mortem within 48 hours. Include the observed RPO and RTO.

## Done when

- Daily dumps running, last dump age < 26 hours.
- WAL archive lag < 5 min, monitored.
- Most recent drill ≤ 90 days ago, both types pass.
