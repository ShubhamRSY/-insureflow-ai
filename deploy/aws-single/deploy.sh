#!/usr/bin/env bash
# Create/update the AWS setup and deploy the committed code (git HEAD).
#   AWS_PROFILE=rytera-deploy ALERT_EMAIL=you@company.com deploy/aws-single/deploy.sh
# Optional: SSH_CIDR=1.2.3.4/32 opens SSH for debugging (closed by default; use
# `aws ssm start-session --target <instance-id>` instead).
# Ships `git archive HEAD` only: local .env and untracked files never leave this machine.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
: "${ALERT_EMAIL:?Set ALERT_EMAIL to the address for alarms and budget alerts}"
export AWS_REGION=us-east-2 AWS_DEFAULT_REGION=us-east-2

TF=infra/aws-single
KEY=~/.ssh/rytera_aws
[ -f "$KEY" ] || ssh-keygen -t ed25519 -N "" -f "$KEY" -C rytera-aws >/dev/null
VARS=(-var "ssh_public_key=$(cat "$KEY.pub")" -var "alert_email=$ALERT_EMAIL" -var "ssh_cidr=${SSH_CIDR:-}")
apply() { terraform -chdir="$TF" apply -input=false -auto-approve "${VARS[@]}" | grep -E "Apply complete|Error|error" || true; }
out() { terraform -chdir="$TF" output -raw "$1"; }

terraform -chdir="$TF" init -input=false >/dev/null
echo "== AWS resources"
apply
BUCKET=$(out bucket) SECRET=$(out secret_arn) ECR=$(out ecr_repo) ID=$(out instance_id) URL=$(out url)
SHA=$(git rev-parse --short HEAD)

echo "== Upload code $SHA"
git archive --format=tar.gz HEAD | aws s3 cp - "s3://$BUCKET/deploy/$SHA.tar.gz" --only-show-errors

MODEL_DATA=""
if [ -d ml_models ]; then
  # Re-upload the models only when the files changed.
  hash=$(find ml_models -type f -exec stat -f '%N %z %m' {} + | sort | shasum | cut -c1-12)
  MODEL_DATA="s3://$BUCKET/models/$hash/model.tar.gz"
  if ! aws s3 ls "$MODEL_DATA" >/dev/null 2>&1; then
    echo "== Upload ML models ($(du -sh ml_models | cut -f1))"
    COPYFILE_DISABLE=1 tar -C ml_models -czf - . | aws s3 cp - "$MODEL_DATA" --only-show-errors
  fi
fi

run_on_server() {
  local cmd_id status
  cmd_id=$(aws ssm send-command --instance-ids "$ID" --document-name AWS-RunShellScript --timeout-seconds 3600 \
    --parameters "{\"executionTimeout\":[\"3600\"],\"commands\":[\"export PATH=/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\",\"command -v aws >/dev/null || snap install aws-cli --classic >/dev/null\",\"aws s3 cp s3://$BUCKET/deploy/$SHA.tar.gz - --region us-east-2 | tar -xzO deploy/aws-single/remote.sh > /tmp/rytera-remote.sh\",\"bash /tmp/rytera-remote.sh $BUCKET $SHA ${URL#https://} $SECRET $ECR\"]}" \
    --query Command.CommandId --output text)
  while :; do
    sleep 10
    status=$(aws ssm get-command-invocation --command-id "$cmd_id" --instance-id "$ID" --query Status --output text 2>/dev/null || echo Pending)
    case $status in Pending | InProgress | Delayed) ;; *) break ;; esac
  done
  aws ssm get-command-invocation --command-id "$cmd_id" --instance-id "$ID" --query '[StandardOutputContent,StandardErrorContent]' --output text | tail -20
  [ "$status" = Success ] || { echo "Server step failed: $status"; exit 1; }
}

echo "== Wait for Systems Manager on the server"
for _ in $(seq 1 60); do
  [ "$(aws ssm describe-instance-information --filters "Key=InstanceIds,Values=$ID" --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null)" = Online ] && break
  sleep 10
done

echo "== Build and start on the server (first build takes ~10 min)"
run_on_server

if [ -n "$MODEL_DATA" ]; then
  echo "== SageMaker endpoint (create/update takes ~5-10 min)"
  # ponytail: the endpoint is updated on every deploy so ML code changes reach it; skip when only UI changed if deploys get slow.
  printf 'ml_image      = "%s"\nml_model_data = "%s"\n' "$ECR:$SHA" "$MODEL_DATA" > "$TF/ml.auto.tfvars"
  apply
  aws sagemaker wait endpoint-in-service --endpoint-name rytera-ml
  echo "== Switch the app to SageMaker predictions"
  run_on_server
fi

echo "== Check $URL"
for _ in $(seq 1 30); do
  curl -fsS "$URL/health" >/dev/null 2>&1 && { echo "Live: $URL/dashboard"; exit 0; }
  sleep 10
done
echo "Not answering yet. Logs: CloudWatch log group /rytera/single (region us-east-2)"
exit 1
