# Local deployment and verification

Run from repository root: `docker compose up --build -d backend`. Open http://127.0.0.1:8001. Existing port 8000 is untouched. SQLite persists in mvp_data. Container initializes the explicitly simulated sample data idempotently. This remains a single organization local demo.

`docker compose --profile postgres up -d postgres` prepares PostgreSQL on localhost:5433. Set POSTGRES_PASSWORD before use; default is local-development-only. This is a separate future database, NOT a claim that the MVP PostgreSQL adapter or database migrations have passed. Apply database-role migrations only using their documented entry point. Do not point the current MVP at the future schemas without an adapter.

`docker compose --profile next build next` requires frontend/next/package.json and committed package-lock.json with build/start scripts. The profile is preparatory until frontend delivery. Browser API origin/proxy settings must be supplied by frontend; current backend requires same origin. No cross-origin bypass is configured.

Verification: `python -m pip install -r backend/requirements.txt`, `python -m unittest discover -s tests -p 'test_*.py' -v`, `python infrastructure/verify.py --url http://127.0.0.1:8001`, `node --check frontend/app.js`. Smoke script is read-only. Unit tests use isolated in-memory SQLite; do not launch or stop the shared service.

Backup SQLite: stop only the Compose backend (`docker compose stop backend`), copy /data/local.db from its stopped container using `docker compose cp backend:/data/local.db ./backup.db`, then restart. To restore: stop backend, copy verified backup into /data/local.db, start backend, run readiness and smoke checks. Keep backups outside source control. Test restoration on a separate Compose project and volume before relying on it.

PostgreSQL backup: `docker compose exec -T postgres pg_dump -U finagent -d finagent -Fc -f /tmp/finagent.dump`, then `docker compose cp postgres:/tmp/finagent.dump ./finagent.dump`. Restore into a separate empty database with pg_restore, verify migration version and counts, and only then consider replacement. Do not pipe binary dumps through Windows PowerShell redirection. Backups contain financial data and need restricted storage. Container images, Docker runtime, restore procedures and PostgreSQL integration require execution on a Docker-equipped host.
