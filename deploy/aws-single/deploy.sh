#!/usr/bin/env bash
# Create (first run) or update the single AWS server and deploy the committed code.
#   AWS_PROFILE=rytera-deploy deploy/aws-single/deploy.sh
# Ships `git archive HEAD` only: local .env and untracked files never leave this machine.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

KEY=~/.ssh/rytera_aws
TF=infra/aws-single
[ -f "$KEY" ] || ssh-keygen -t ed25519 -N "" -f "$KEY" -C rytera-aws >/dev/null

terraform -chdir="$TF" init -input=false >/dev/null
terraform -chdir="$TF" apply -input=false -auto-approve \
  -var "ssh_public_key=$(cat "$KEY.pub")" \
  -var "ssh_cidr=$(curl -fsS https://checkip.amazonaws.com)/32"

IP=$(terraform -chdir="$TF" output -raw ip)
URL=$(terraform -chdir="$TF" output -raw url)
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 "ubuntu@$IP")

echo "Waiting for the server to finish installing Docker..."
until "${SSH[@]}" 'command -v docker >/dev/null && docker compose version >/dev/null' 2>/dev/null; do sleep 10; done

echo "Uploading code ($(git rev-parse --short HEAD))..."
git archive --format=tar.gz HEAD | "${SSH[@]}" 'mkdir -p ~/app && tar -xzf - -C ~/app'

"${SSH[@]}" "DOMAIN=${URL#https://} bash -s" <<'REMOTE'
set -euo pipefail
cd ~/app/deploy/aws-single
# Secrets are generated once on the server and never copied anywhere.
if [ ! -f .env ]; then
  umask 077
  {
    echo "DOMAIN=$DOMAIN"
    echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)"
    echo "SECRET_KEY=$(openssl rand -hex 32)"
    echo "ENCRYPTION_KEY=$(python3 -c 'import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())')"
  } > .env
fi
sudo docker compose up -d --build
sudo docker image prune -f >/dev/null
REMOTE

echo "Waiting for $URL ..."
for _ in $(seq 1 60); do
  curl -fsS "$URL/health" >/dev/null 2>&1 && { echo "Live: $URL/dashboard"; exit 0; }
  sleep 10
done
echo "Not answering yet. Logs: ssh -i $KEY ubuntu@$IP 'cd ~/app/deploy/aws-single && sudo docker compose logs --tail 50'"
exit 1
