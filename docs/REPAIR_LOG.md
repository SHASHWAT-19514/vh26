# Emergency Repair Log

## 0. Reality map

### Runtime

- Backend entry point: `abhedya/app.py`, FastAPI/Uvicorn on port 8000.
- Static frontend: `static/index.html`, `static/app.js`, and `static/styles.css`, served by FastAPI. No React/Vite/TypeScript package exists in the current checkout.
- API base: frontend uses relative `fetch('/api/...')`; production same-origin wiring is correct.
- Runtime network: no CDN or external runtime calls found in the current static assets.
- Current health check: `GET /api/health` returned HTTP 200 with `status=ok`.
- Current OpenAPI check: `GET /openapi.json` returned HTTP 200, 4,653 bytes.
- Current frontend check: `GET /` returned HTTP 200, 6,879 bytes; `/static/app.js` and `/static/styles.css` are referenced.
- Existing regression suite: `python3 -m pytest -q` returned `2 passed`.

### Frontend-to-backend map

| Frontend call | Backend route | Match | Finding |
|---|---|---:|---|
| `GET /api/health` | `GET /api/health` | Yes | Response shape is consumed for status only. |
| `GET /api/metrics` | `GET /api/metrics` | Yes | Metrics are shown when a dataset is loaded. |
| `POST /api/datasets/upload` multipart `file` | `POST /api/datasets/upload` | Yes | Real ingestion path. |
| `GET /api/trace/{victim}?max_hops=4` | `GET /api/trace/{victim}` | Partial | Frontend requires exactly 12 digits; real data uses 12-character alphanumeric IDs. |
| `POST /api/evidence?victim=...&max_hops=4` | `POST /api/evidence` | Yes | Uses last trace victim. |
| `POST /api/reports/{evidence_id}?kind=...` | `POST /api/reports/{evidence_id}` | Yes | Template report path. |

## Root causes observed before repair

### R1 — Real account identifiers are rejected

- **Symptom:** The application appears empty or cannot trace real accounts.
- **Evidence:** The attached real-data sample is `AIRP10001015,IPOS10001297`; current `abhedya/ingest.py` uses `re.fullmatch(r'\\d{12}', sa)` and `re.fullmatch(r'\\d{12}', ra)`. Current `static/app.js` uses `/^\\d{12}$/` for victim input.
- **Impact:** Most real rows would be rejected as `BAD_ACCOUNT`; the UI would reject valid real victims before calling the backend.
- **Fix:** Changed ingestion and trace validation to `[A-Za-z0-9]{12}` and changed the UI validation/copy to accept letters or digits. Trace path parameters are URL-encoded.
- **Verification:** The real-data sample loaded `1000` rows with `0` rejects and `771` accounts. Live upload returned the same result; `GET /api/trace/AIRP10001015?max_hops=4` returned `2` nodes and `1` edge in `8.88 ms`.
- **Status:** Fixed and verified on the real-data sample.

### R2 — Health response lacks dataset state required for empty-state diagnosis

- **Symptom:** Health reports service status but not whether a real dataset is loaded or how many rows are available.
- **Evidence:** Current `/api/health` response contains `status`, `service`, `version`, `offline`, `config_hash`, `python`, and `uptime_s`, but no `dataset_loaded`, `rows`, or `rejected` fields.
- **Fix:** Added `dataset_loaded`, `dataset_id`, and `rows` fields to `/api/health`.
- **Verification:** After live upload, health returned `dataset_loaded=true`, `dataset_id=default`, and `rows=1000`.
- **Status:** Fixed and verified.

### R3 — Current implementation is static HTML rather than the requested React/Vite stack

- **Symptom:** No frontend build, TypeScript diagnostics, Vite proxy, or prebuilt `dist` exists.
- **Evidence:** Repository recon found no `package.json`; frontend entry is `static/index.html` with plain JavaScript.
- **Status:** Confirmed architectural gap; migration is larger and will be tracked separately from the minimal real-data repair.

### R4 — Error handling is not sufficiently structured

- **Symptom:** Upload and report handlers translate arbitrary exceptions to plain strings, and the frontend often reduces failures to a generic toast.
- **Evidence:** `abhedya/app.py` catches `Exception` in upload and returns `HTTPException(400, str(exc))`; frontend `catch` blocks do not consistently display HTTP status and server detail.
- **Status:** Confirmed; fix after the account-format repair.

### R5 — Python per-row ingestion and per-account analytics were too slow

- **Symptom:** The original implementation took `3.544 s` for 1,000 real rows and `380.324 s` for analytics over 24,873 accounts.
- **Fix:** Replaced the Python `csv.DictReader` hot path with DuckDB parallel `read_csv`, SQL normalization/deduplication/account aggregation, and set-based SQL risk scoring.
- **Verification:** The full 2,000,000-row CSV loaded `1,997,748` rows with `2,252` rejects in `13.174 s`; analytics completed in `0.303 s`.
- **Status:** Fixed and measured.

### R6 — Evidence verification failed in FastAPI worker threads

- **Symptom:** `GET /api/evidence/{id}/verify` returned HTTP 500 after a successful evidence build.
- **Evidence:** Uvicorn traceback showed `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread`.
- **Fix:** Opened the single-process SQLite app connection with `check_same_thread=False`.
- **Verification:** Full-real evidence verification returned `{"valid":true}`; both Case Diary and Freeze Requisition endpoints returned HTTP 200 and generated HTML/PDF files.
- **Status:** Fixed and verified.

## Out-of-scope concerns

- Full React 18/Vite 5/Tailwind/Zustand/Cytoscape migration is not a minimal patch and is not claimed verified here.
- The official 2M-row benchmark, CSR/mmap graph, SciPy components, Ollama validator, and Playwright suite remain NOT VERIFIED until implemented and run.
