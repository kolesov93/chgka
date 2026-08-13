# Production deployment: `example.com/chgka`

This runbook is intentionally specific to the audited VPS. It keeps host Nginx
as the only public listener and runs one private CHGKA Compose project behind
`127.0.0.1:18080`.

## Host layout

```text
/home/kolesov93/apps/chgka/
├── .env.production       # mode 0600, never committed
├── current -> releases/<git-commit>
├── releases/<git-commit>/
├── questions/current/
├── data/chgka.sqlite3
└── backups/chgka-*.sqlite3
```

The backend container runs as UID/GID `1000`, matching `kolesov93` on the
audited VPS. The question pack is read-only. SQLite and backups are bind-mounted
from the host and therefore survive image/container replacement.

## One-time Docker installation

Use Docker's official Ubuntu apt repository. Do not use `get.docker.com`.
Run the commands from the current official guide, then install:

```bash
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker kolesov93
```

Log out and reconnect so the new group is effective, then verify:

```bash
docker version
docker compose version
docker run --rm hello-world
```

Membership in the `docker` group is root-equivalent and was explicitly accepted
for this VPS. Do not expose the Docker socket over TCP.

## Create the first release

From the repository root on the development machine, after all checks and a
commit:

```bash
release=$(git rev-parse --short=12 HEAD)
git archive --format=tar --prefix="$release/" HEAD \
  | ssh vps 'mkdir -p "$HOME/apps/chgka/releases" && tar -xf - -C "$HOME/apps/chgka/releases"'
ssh vps "ln -sfn \"\$HOME/apps/chgka/releases/$release\" \"\$HOME/apps/chgka/current\""
```

On the VPS create persistent directories and initially copy the sample pack:

```bash
mkdir -p ~/apps/chgka/{questions/current,data,backups}
cp -a ~/apps/chgka/current/fixtures/sample_questions/. ~/apps/chgka/questions/current/
```

Copy `deployment/production.env.example` to `~/apps/chgka/.env.production`,
replace `CHGKA_IMAGE_TAG` with the release commit and set a unique password of
at least 12 characters. Then protect it:

```bash
chmod 600 ~/apps/chgka/.env.production
```

Do not print, commit, or send the env file. Validate and start without rendering
its interpolated secret values:

```bash
cd ~/apps/chgka/current
docker compose --env-file ../.env.production -f docker-compose.production.yml config --quiet
docker compose --env-file ../.env.production -f docker-compose.production.yml build
docker compose --env-file ../.env.production -f docker-compose.production.yml run --rm backend \
  python -m validate_pack /questions
docker compose --env-file ../.env.production -f docker-compose.production.yml up -d
docker compose --env-file ../.env.production -f docker-compose.production.yml ps
curl --fail --silent --show-error http://127.0.0.1:18080/healthz
curl --fail --silent --show-error http://127.0.0.1:18080/chgka/play >/dev/null
```

Never run `docker compose config` without `--quiet` while the real env file is
loaded: the rendered output contains `ADMIN_PASSWORD`.

## Connect host Nginx

Install `deployment/nginx/chgka-http-limits.conf` under `/etc/nginx/conf.d/`.
Insert the two locations from `deployment/nginx/chgka-location.conf` inside the
existing HTTPS `server` for `example.com`, before the generic `location /`.

Before editing, copy the existing site file to a dated backup outside
`sites-enabled`. Before every reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

If validation fails, do not reload. Restore the site backup and run `nginx -t`
again. The CHGKA include does not replace or rename the existing `/movieclub`,
`/books`, `/podcasts`, or root locations.

## Backup

`deployment/backup.sh` uses SQLite's online backup API, validates the copy with
`PRAGMA quick_check`, and removes only managed `chgka-*.sqlite3` backups older
than 30 days. It does not stop the backend.

Install a user crontab entry after the first manual successful backup:

```cron
15 4 * * * /home/kolesov93/apps/chgka/current/deployment/backup.sh >>/home/kolesov93/apps/chgka/backups/backup.log 2>&1
```

Manual check:

```bash
~/apps/chgka/current/deployment/backup.sh
ls -lh ~/apps/chgka/backups/chgka-*.sqlite3
```

## Daily operations

All commands in this section manage only CHGKA. Host Nginx stays running because
it also serves the other `example.com` routes.

Connect to the VPS and define a short helper once per shell session:

```bash
ssh vps
cd ~/apps/chgka/current
chgka_compose='docker compose --env-file ../.env.production -f docker-compose.production.yml'
```

Status and health:

```bash
$chgka_compose ps
curl --fail --silent --show-error http://127.0.0.1:18080/healthz
curl --fail --silent --show-error https://example.com/chgka/play >/dev/null
```

Start already-created containers, or create them again from the selected
release if they were removed:

```bash
$chgka_compose up -d
$chgka_compose ps
```

Stop only CHGKA while preserving its containers, images, question pack and
SQLite database:

```bash
$chgka_compose stop
```

`https://example.com/chgka/` returns `502` while CHGKA is stopped; the other host
routes keep working. A full Compose teardown is rarely needed, but is also safe
for the bind-mounted database and pack:

```bash
$chgka_compose down
```

Restarting either service interrupts the live game and invalidates in-memory
admin/player sessions. The game history in SQLite remains:

```bash
$chgka_compose restart
```

## Logs

Show the latest logs from both containers, follow them live, or limit output to
one service/time window:

```bash
$chgka_compose logs --tail=100 backend frontend
$chgka_compose logs --follow --tail=100 backend frontend
$chgka_compose logs --follow backend
$chgka_compose logs --since=30m backend frontend
```

`Ctrl+C` stops following logs; it does not stop the containers. Docker uses the
bounded `local` log driver, so old container output is rotated automatically.

Host Nginx and scheduled-backup diagnostics:

```bash
sudo journalctl -u nginx --since '30 minutes ago'
sudo tail -n 100 /var/log/nginx/error.log
tail -n 100 ~/apps/chgka/backups/backup.log
```

Useful network diagnostic:

```bash
ss -lnt | grep 18080
```

Expected host binding is exactly `127.0.0.1:18080`; backend port `8000` must not
appear as a host listener.

## Deploy a new application version

Deploy only a committed `web` revision whose GitHub CI is green. From the Git
repository root on the development laptop:

```bash
git switch web
git status --short
git pull --ff-only
release=$(git rev-parse --short=12 HEAD)
git archive --format=tar --prefix="$release/" HEAD \
  | ssh vps 'mkdir -p "$HOME/apps/chgka/releases" && tar -xf - -C "$HOME/apps/chgka/releases"'
echo "$release"
```

`git status --short` must be empty. Keep the printed 12-character release ID for
the VPS commands below. Then connect to the VPS and paste that ID without angle
brackets:

```bash
ssh vps
deploy_root=$HOME/apps/chgka
release=PASTE_12_CHARACTER_RELEASE_ID_HERE
release_dir=$deploy_root/releases/$release
env_file=$deploy_root/.env.production
compose_file=$release_dir/docker-compose.production.yml

test -f "$compose_file"
grep -q '^CHGKA_IMAGE_TAG=' "$env_file"

CHGKA_IMAGE_TAG="$release" docker compose \
  --project-name chgka \
  --project-directory "$release_dir" \
  --env-file "$env_file" \
  --file "$compose_file" \
  config --quiet

CHGKA_IMAGE_TAG="$release" docker compose \
  --project-name chgka \
  --project-directory "$release_dir" \
  --env-file "$env_file" \
  --file "$compose_file" \
  build

CHGKA_IMAGE_TAG="$release" docker compose \
  --project-name "chgka-validate-$release" \
  --project-directory "$release_dir" \
  --env-file "$env_file" \
  --file "$compose_file" \
  run --rm backend python -m validate_pack /questions

CHGKA_IMAGE_TAG="$release" docker compose \
  --project-name "chgka-validate-$release" \
  --project-directory "$release_dir" \
  --env-file "$env_file" \
  --file "$compose_file" \
  down
```

At this point the new images exist, but production still runs the old version.
Back up SQLite, remember the current release for rollback, switch the symlink and
image tag, and recreate only changed services:

```bash
"$deploy_root/current/deployment/backup.sh"
readlink -f "$deploy_root/current"
grep '^CHGKA_IMAGE_TAG=' "$env_file"

ln -sfn "$release_dir" "$deploy_root/current"
sed -i "s/^CHGKA_IMAGE_TAG=.*/CHGKA_IMAGE_TAG=$release/" "$env_file"

cd "$deploy_root/current"
docker compose --env-file ../.env.production -f docker-compose.production.yml up -d
docker compose --env-file ../.env.production -f docker-compose.production.yml ps
curl --fail --silent --show-error http://127.0.0.1:18080/healthz
curl --fail --silent --show-error https://example.com/chgka/play >/dev/null
```

Finish with the focused smoke for the feature being released. Do not deploy
during a live game: replacing the backend clears the runtime game and sessions.
The production env, persistent pack, SQLite and backups are not replaced by this
procedure.

## Roll back the application

Use the release ID printed by `readlink` before the update. Old images are kept
for this purpose:

```bash
ssh vps
deploy_root=$HOME/apps/chgka
previous=PASTE_PREVIOUS_12_CHARACTER_RELEASE_ID_HERE
env_file=$deploy_root/.env.production

test -f "$deploy_root/releases/$previous/docker-compose.production.yml"
ln -sfn "$deploy_root/releases/$previous" "$deploy_root/current"
sed -i "s/^CHGKA_IMAGE_TAG=.*/CHGKA_IMAGE_TAG=$previous/" "$env_file"

cd "$deploy_root/current"
docker compose --env-file ../.env.production -f docker-compose.production.yml up -d
docker compose --env-file ../.env.production -f docker-compose.production.yml ps
curl --fail --silent --show-error http://127.0.0.1:18080/healthz
```

If the old image was manually deleted, run `docker compose ... build` from the
selected release before `up -d`. Database migrations currently only add tables
with `CREATE TABLE IF NOT EXISTS`; before rolling back across a future
schema-changing release, verify database compatibility separately.
