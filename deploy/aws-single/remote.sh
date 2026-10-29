#!/usr/bin/env bash
# Runs ON the server as root, sent by deploy.sh through Systems Manager.
#   remote.sh <bucket> <git-sha> <domain> <secret-arn> <ecr-repo-url>
# Unpacks the code bundle from S3, writes .env from Secrets Manager, starts the app,
# builds + pushes the SageMaker image, and installs the nightly backup.
set -euo pipefail
export PATH=/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
BUCKET=$1 SHA=$2 DOMAIN=$3 SECRET=$4 ECR=$5
export AWS_REGION=us-east-2 AWS_DEFAULT_REGION=us-east-2
APP=/opt/rytera/app
DIR=$APP/deploy/aws-single

command -v aws >/dev/null || snap install aws-cli --classic >/dev/null

mkdir -p "$APP"
aws s3 cp "s3://$BUCKET/deploy/$SHA.tar.gz" /tmp/rytera-code.tar.gz --only-show-errors
tar -xzf /tmp/rytera-code.tar.gz -C "$APP" && rm -f /tmp/rytera-code.tar.gz

# Secrets: Secrets Manager is the source of truth. First run moves the secrets that
# the old SSH deploy generated in ~ubuntu/app into it; otherwise new ones are made once.
current=$(aws secretsmanager get-secret-value --secret-id "$SECRET" --query SecretString --output text 2>/dev/null || echo "")
if [ -z "$current" ] || [ "$current" = "None" ]; then
  old=/home/ubuntu/app/deploy/aws-single/.env
  declare -A s=()
  if [ -f "$old" ]; then
    while IFS='=' read -r k v; do [ -n "$k" ] && s[$k]=$v; done < "$old"
  fi
  : "${s[POSTGRES_PASSWORD]:=$(openssl rand -hex 24)}"
  : "${s[SECRET_KEY]:=$(openssl rand -hex 32)}"
  : "${s[ENCRYPTION_KEY]:=$(python3 -c 'import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())')}"
  : "${s[INTEGRATION_GATEWAY_API_KEY]:=rytera-gw-$(openssl rand -hex 24)}"
  json=$(POSTGRES_PASSWORD=${s[POSTGRES_PASSWORD]} SECRET_KEY=${s[SECRET_KEY]} ENCRYPTION_KEY=${s[ENCRYPTION_KEY]} \
    INTEGRATION_GATEWAY_API_KEY=${s[INTEGRATION_GATEWAY_API_KEY]} python3 -c \
    'import json,os;print(json.dumps({k:os.environ[k] for k in ("POSTGRES_PASSWORD","SECRET_KEY","ENCRYPTION_KEY","INTEGRATION_GATEWAY_API_KEY")}))')
  aws secretsmanager put-secret-value --secret-id "$SECRET" --secret-string "$json" >/dev/null
  current=$json
  echo "Secrets stored in Secrets Manager."
fi

ml_endpoint=""
status=$(aws sagemaker describe-endpoint --endpoint-name rytera-ml --query EndpointStatus --output text 2>/dev/null || echo "none")
[ "$status" = "InService" ] && ml_endpoint=rytera-ml

umask 077
{
  echo "$current" | python3 -c 'import json,sys;[print(f"{k}={v}") for k,v in json.load(sys.stdin).items()]'
  echo "DOMAIN=$DOMAIN"
  echo "AWS_REGION=$AWS_REGION"
  echo "S3_UPLOADS_BUCKET=$BUCKET"
  echo "SAGEMAKER_ML_ENDPOINT=$ml_endpoint"
} > "$DIR/.env"

cd "$DIR"
docker compose up -d --build --remove-orphans
echo "App up (ML: ${ml_endpoint:-in-process})."

# SageMaker image = the app image with the inference entrypoint.
registry=${ECR%%/*}
aws ecr get-login-password | docker login --username AWS --password-stdin "$registry" >/dev/null
docker build -q -f Dockerfile.sagemaker -t "$ECR:$SHA" . >/dev/null
docker push -q "$ECR:$SHA" >/dev/null
echo "ML image pushed: $ECR:$SHA"

# Nightly database backup to S3 (kept 30 days by the bucket lifecycle rule).
install -m 755 "$DIR/backup.sh" /usr/local/bin/rytera-backup
echo "17 3 * * * root BUCKET=$BUCKET /usr/local/bin/rytera-backup >> /var/log/rytera-backup.log 2>&1" > /etc/cron.d/rytera-backup

docker image prune -f >/dev/null
