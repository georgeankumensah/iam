# Backup & Restore Drill — IAM 3.0

## Backup Strategy

| Component | Method | Frequency | Retention |
|-----------|--------|-----------|-----------|
| PostgreSQL | `pg_dump --format=custom` + GPG-encrypted → S3 | Daily (02:00 GMT) | 30 days (S3 lifecycle) |
| Zitadel | Zitadel export API (manual trigger) | Weekly | 90 days |
| Redis | RDB snapshot (K8s PV snapshot) | Hourly | 24 hours |
| K8s Secrets | Sealed Secrets / Vault | On change | Git history |

## Restore Drill

### Prerequisites
```bash
aws s3 ls s3://clet-iam-backups/postgres/
gpg --decrypt backup-2026-06-25-020000.pgdump.gpg > backup.pgdump
```

### Full Restore Steps

#### 1. Scale down API to prevent writes
```bash
kubectl scale deployment iam-django --replicas=0 -n iam-system
kubectl scale deployment iam-celery-worker --replicas=0 -n iam-system
kubectl scale deployment iam-celery-beat --replicas=0 -n iam-system
```

#### 2. Restore PostgreSQL
```bash
# Option A — new DB instance
pg_restore --format=custom --no-owner --no-acl --dbname=postgresql://user:pass@new-host/iam backup.pgdump

# Option B — replace existing DB
psql -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE datname = 'iam' AND pid <> pg_backend_pid();"
dropdb iam
createdb iam
pg_restore --format=custom --no-owner --no-acl --dbname=iam backup.pgdump
```

#### 3. Verify data integrity
```bash
python manage.py check_zitadel_drift  # must exit 0
python manage.py shell -c "from django.contrib.auth import get_user_model; print(get_user_model().objects.count())"
```

#### 4. Scale up API
```bash
kubectl scale deployment iam-django --replicas=3 -n iam-system
kubectl scale deployment iam-celery-worker --replicas=2 -n iam-system
kubectl scale deployment iam-celery-beat --replicas=1 -n iam-system
```

#### 5. Smoke tests
```bash
curl -f https://iam-api.clet.gov.gh/health/live
curl -f https://iam-api.clet.gov.gh/health/ready
python manage.py check_zitadel_drift
```

## Expected RTO

| Tier | Target |
|------|--------|
| RPO | ≤ 24 hours (daily backup) |
| RTO | ≤ 30 minutes (restore + verify) |

## Quarterly Drill

1. Schedule a date with the team.
2. Spin up a staging environment from the latest backup.
3. Follow the Full Restore Steps above.
4. Log results in this repo: `doc/ops/drill-log-{YYYY-QQ}.md`.
5. If RTO > 30 min, identify bottleneck and update this doc.
