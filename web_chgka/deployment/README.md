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
git archive --format=tar --prefix="$release/" HEAD:web_chgka \
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

## Update and rollback

Create a new immutable release directory with `git archive`, build its images
under a new `CHGKA_IMAGE_TAG`, validate the pack, then switch `current` and run
`up -d`. Take a SQLite backup before the switch.

Rollback uses the previous release symlink and its previous image tag. Because
the database schema currently migrates only forward by additive `CREATE TABLE
IF NOT EXISTS` statements, verify compatibility before rolling application code
back across a future schema-changing release.

Useful diagnostics that do not reveal the env file:

```bash
cd ~/apps/chgka/current
docker compose --env-file ../.env.production -f docker-compose.production.yml ps
docker compose --env-file ../.env.production -f docker-compose.production.yml logs --tail=100 backend frontend
ss -lnt | grep 18080
```

Expected host binding is exactly `127.0.0.1:18080`; backend port `8000` must not
appear as a host listener.
