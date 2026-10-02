# Build Progress

## Completed foundation and production hardening

The service has a DuckDB-native ingestion pipeline, set-based risk scoring, FastAPI API, SQLite evidence/audit store, evidence seals, HTML/PDF reports, API-key authentication, upload streaming/limits, request IDs, rate limits, security headers, readiness/liveness checks, rotating JSON logs, SQLite WAL, backup utility, and a least-privilege systemd deployment unit.

## Remaining specification features implemented

### FIFO flow attribution and residuals

`abhedya.flow` attributes downstream outgoing amounts to earlier incoming lots in FIFO order. Trace responses now include `flow_links`, per-edge residuals, and transaction-level reference IDs.

### Connected-component rings

`abhedya.rings` uses a custom NumPy union-find pass over DuckDB transaction IDs and writes qualifying components to the `rings` table. On the full dataset it detected 2 connected components covering 24,873 accounts in 18.951 seconds.

### Timeline and graph APIs

Trace responses include minute-level timeline events and graph metadata. Dedicated endpoints provide `/api/trace/{victim}/timeline` and `/api/trace/{victim}/graph`.

### Ollama validator

`abhedya.validator` supports optional Ollama JSON-schema output with model and timeout configuration. When Ollama is unavailable, it returns a deterministic, evidence-anchored fallback with reference transaction tokens and explicitly labels the provider.

### React/Vite/Cytoscape frontend

The frontend is now a React 18 + TypeScript + Vite build with Zustand state, Tailwind/PostCSS configuration, Cytoscape layered graph rendering, upload, trace, timeline, FIFO residual table, evidence, and report pages. Vite builds into the FastAPI static serving path.

## Verification

- Full real-data ingestion: 2,000,000 rows scanned; 1,997,748 loaded; 2,252 rejected; 13.174 seconds.
- Risk scoring: 0.303 seconds.
- Risk scoring plus connected-component rings: 19.387 seconds.
- Warm 4-hop trace: approximately 0.35 seconds.
- Full trace: 82 nodes, 87 edges, 102 FIFO flow links, 87 timeline events.
- Live graph, timeline, validator, rings metrics, evidence and report endpoints verified.
- Python tests: 6 passed.
- Frontend Vitest tests: 2 passed.
- Frontend production build: passed.

## Remaining operational work

Organization-level TLS/reverse proxy, firewall policy, SSO integration, backup retention, patch cadence, access review, and legal approval of report templates remain deployment controls rather than unimplemented application features.

## Cyber Arc master-prompt alignment

Added local case manifests and case APIs, account/transaction search, ingestion-state and system-status APIs, graph/timeline/evidence case routes, CSV/JSON subgraph export, benchmark scripts, blind investigation mode, Windows startup, centralized frontend API access, Cyber Arc SPA route fallback, cases and benchmarks views, and the alignment record in `docs/MASTER_PROMPT_ALIGNMENT.md`. Final verification: Python 6 passed, frontend 2 passed, Vite build passed, live search/case/graph/timeline/export/status/benchmark/docs routes passed.
