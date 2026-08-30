#!/usr/bin/env bash
set -euo pipefail

ROOT="${REASONREADER_ROOT:-/srv/reasonreader/prod}"
cd "$ROOT"
set -a
# shellcheck disable=SC1091
source .env
set +a

if [[ -f "${HOME}/.ssh/reasonreader_deploy" ]]; then
  export GIT_SSH_COMMAND="ssh -i ${HOME}/.ssh/reasonreader_deploy -o IdentitiesOnly=yes"
fi
git fetch origin
git reset --hard origin/main

docker compose -f docker-compose.prod.yml --env-file .env up -d --build

echo "waiting for postgres"
for _ in $(seq 1 30); do
  if docker compose -f docker-compose.prod.yml --env-file .env exec -T postgres \
    pg_isready -U "${POSTGRES_USER:-reasonreader}" -d "${POSTGRES_DB:-won}" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

apply_sql() {
  docker compose -f docker-compose.prod.yml --env-file .env exec -T postgres \
    psql -U "${POSTGRES_USER:-reasonreader}" -d "${POSTGRES_DB:-won}" -v ON_ERROR_STOP=1
}

if ! docker compose -f docker-compose.prod.yml --env-file .env exec -T postgres \
  psql -U "${POSTGRES_USER:-reasonreader}" -d "${POSTGRES_DB:-won}" -tAc \
  "SELECT 1 FROM information_schema.tables WHERE table_name='users'" | grep -q 1; then
  apply_sql < web/drizzle/0000_init.sql
fi

if ! docker compose -f docker-compose.prod.yml --env-file .env exec -T postgres \
  psql -U "${POSTGRES_USER:-reasonreader}" -d "${POSTGRES_DB:-won}" -tAc \
  "SELECT 1 FROM information_schema.tables WHERE table_name='tutor_events'" | grep -q 1; then
  apply_sql < web/drizzle/0001_tutor_events.sql
fi

echo "deployed $(git rev-parse --short HEAD)"
