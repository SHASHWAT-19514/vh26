# THE CYBER ARC — Master Prompt Alignment

This repository preserves the existing validated Abhedya-Chakra engine and adds the missing Cyber Arc interfaces without duplicating existing files.

## Added in this alignment pass

- Local case persistence under `cases/ARC-XXXXXXXX/` with `case.json`, `graph.json`, `manifest.json`, and `documents/`.
- `GET /api/system/status` with actual backend, database, graph-engine, and local-AI state.
- `GET /api/ingestion/status` with truthful lifecycle state.
- `GET /api/accounts/search` for indexed account lookup.
- `GET /api/account/{account_id}` and `/transactions` for exact account history.
- `GET /api/transaction/{transaction_id}` for exact transaction evidence.
- `POST /api/cases`, `GET /api/cases`, and `GET /api/cases/{case_id}`.
- Case graph, timeline, evidence, document, and subgraph-export routes.
- CSV and JSON subgraph export under `data/exports/`.
- `GET /api/benchmarks` exposing persisted benchmark artifacts only.
- `benchmarks/benchmark_ingestion.py` with measured stage/runtime/RSS output.
- `benchmarks/benchmark_trace.py` with average/P50/P95/max latency.
- `benchmarks/benchmark_detection.py` requiring explicit labels and predictions; it never fabricates precision/recall.
- `scripts/blind_test.py` for multiple real victim IDs.
- `start.bat` for Windows local startup.
- Centralized frontend API client in `frontend/src/api/client.ts`.
- Direct SPA fallback for `/investigate`, `/cases`, `/timeline`, `/evidence`, `/documents`, and `/benchmarks` paths.
- React views for Command Center, investigation, cases, evidence, and benchmarks.

## Existing engine retained

The repository already contained and continues to use:

- DuckDB-native 2M-row ingestion and normalization.
- Integer account mapping and indexed lookup.
- Set-based features and deterministic risk scoring.
- Velocity, fan-in/fan-out, layer roles, terminal indicators, and connected-component rings.
- Bounded four-hop trace with FIFO flow attribution and residuals.
- Cytoscape graph rendering and timeline payloads.
- Evidence sealing, verification, case diary, freeze requisition, and local PDF generation.
- Ollama-compatible JSON validation with deterministic offline fallback.
- API-key protection, request IDs, rate limiting, size limits, security headers, backups, and systemd deployment.

## Verification completed

- Python tests: 6 passed.
- Frontend Vitest tests: 2 passed.
- React/Vite production build: passed.
- Live search, case creation, graph, timeline, export, benchmark, status, and `/docs` endpoints: passed.
- Live SPA fallback route: passed.

## Important evidence rule

The detection benchmark script requires a real labeled evaluation file. The project does not report precision, recall, or F1 unless labels and predictions are explicitly supplied.
