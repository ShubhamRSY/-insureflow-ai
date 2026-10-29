#!/usr/bin/env bash
# Nightly Postgres dump to s3://$BUCKET/backups/ (installed by remote.sh as /usr/local/bin/rytera-backup).
# Restore: aws s3 cp s3://$BUCKET/backups/<file> - | gunzip | docker compose exec -T db psql -U insureflow insureflow
set -euo pipefail
export PATH=/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export AWS_REGION=us-east-2
cd /opt/rytera/app/deploy/aws-single
f=/tmp/rytera-$(date -u +%Y-%m-%dT%H%M).sql.gz
docker compose exec -T db pg_dump -U insureflow --clean --if-exists insureflow | gzip > "$f"
aws s3 cp "$f" "s3://$BUCKET/backups/$(basename "$f")" --only-show-errors
rm -f "$f"
echo "$(date -u) backup ok: $(basename "$f")"
