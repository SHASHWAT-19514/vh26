# Architecture

The service is a single-process FastAPI application. SQLite stores application metadata while each dataset owns a DuckDB file. The static UI is served by FastAPI, so the default run path is offline and requires no Node process at runtime. Analytics modules are intentionally separated from storage and API modules so the hot path can be replaced with narrow NumPy arrays and CSR adjacency structures without changing the API contract.
