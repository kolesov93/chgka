#!/bin/sh
set -eu

deploy_root=${CHGKA_DEPLOY_ROOT:-"$HOME/apps/chgka"}
compose_file="$deploy_root/current/docker-compose.production.yml"
env_file="$deploy_root/.env.production"

if [ ! -f "$compose_file" ]; then
    echo "Production Compose file not found: $compose_file" >&2
    exit 1
fi
if [ ! -f "$env_file" ]; then
    echo "Production env file not found: $env_file" >&2
    exit 1
fi

exec docker compose \
    --project-directory "$deploy_root/current" \
    --env-file "$env_file" \
    --file "$compose_file" \
    exec -T backend \
    python -m backup_database /data/chgka.sqlite3 /backups --retain-days 30
