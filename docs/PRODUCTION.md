# Production deployment and operations

## Production boundary

The backend is hardened for a **single-process, single-node deployment**. It is suitable for a trusted internal workstation or private network behind a reverse proxy. It must not be exposed directly to the public internet: authentication, TLS termination, firewall policy, and operator identity remain deployment responsibilities.

## Required settings

Copy `.env.example` to a protected environment file and set `ABHEDYA_ENV=production` plus a cryptographically random `ABHEDYA_API_KEY` of at least 32 characters. The application refuses to start in production without that key. Keep the environment file mode `0600`.

Production should also set `ABHEDYA_TRUSTED_HOSTS` to the exact hostnames accepted by the reverse proxy. `ABHEDYA_ALLOWED_ORIGINS` should remain empty when the UI is served by the same origin.

## API security behavior

When `ABHEDYA_API_KEY` is configured, all API routes except `/api/health` and `/api/ready` require either `X-API-Key` or `Authorization: Bearer <key>`. Requests receive a request ID, security headers, structured JSON errors, and a fixed-window per-client rate limit. Uploads are streamed to disk and capped by `ABHEDYA_MAX_UPLOAD_BYTES`; they are never read into memory as one large buffer. Do not embed the API key in the static JavaScript. For the browser UI, terminate TLS at the reverse proxy and configure that proxy to inject the private `X-API-Key` header on requests to `127.0.0.1:8000`; direct API clients should send the key themselves.

## Service installation

The checked-in `deploy/abhedya.service` runs the API as a dedicated unprivileged user with `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, a restrictive umask, and explicit writable data/log paths. The reverse proxy should bind TLS and proxy only to `127.0.0.1:8000`.

```bash
sudo install -d -o abhedya -g abhedya /var/lib/abhedya/data /var/log/abhedya
sudo install -m 0644 deploy/abhedya.service /etc/systemd/system/abhedya.service
sudo install -m 0600 .env.production /etc/abhedya/abhedya.env
sudo systemctl daemon-reload
sudo systemctl enable --now abhedya
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/ready
```

## Dataset lifecycle

For the large dataset, build the DuckDB file offline or during a controlled maintenance window:

```bash
./scripts/run.sh --dataset data/inbox/VoidHacks8_MuleAccount_2M_Transactions.csv
```

The dataset build is a replacement operation and should not run concurrently with investigator traces. Use a staging `ABHEDYA_DATA_DIR`, verify `/api/ready`, then promote the dataset directory during a maintenance window.

## Backups and recovery

SQLite evidence and audit state can be backed up without copying a live partially-written file:

```bash
./scripts/backup.sh
```

Back up the resulting `data/backups/app-*.sqlite` together with the corresponding DuckDB dataset directory, input CSV SHA-256, configuration files, and the benchmark/repair log. Test restoration on a separate directory before relying on a backup.

## Health and incident response

- `/api/health` is a lightweight liveness check and does not require authentication.
- `/api/ready` checks SQLite and the selected DuckDB dataset and does not require authentication.
- `/api/metrics` requires the API key when configured.
- Logs are JSON lines in `logs/app.jsonl`, rotated at 50 MB with five retained files.
- Every API response carries `X-Request-ID`; include it in incident reports.
- Do not delete evidence or audit data as an operational shortcut. Preserve the database and report the request ID.

## Remaining organizational controls

Production use still requires organization-level identity integration, TLS/reverse-proxy configuration, firewall rules, backup retention, patch cadence, access review, and legal approval of report templates. These cannot be safely invented by the application itself.
