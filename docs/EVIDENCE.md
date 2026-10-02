# Evidence layer

`abhedya.evidence.build` creates canonical JSON from the trace payload, hashes the canonical content with SHA-256, and stores it append-only in SQLite. Verification recomputes the hash before report generation. The current report renderer keeps values evidence-derived and labels missing balances as estimates.
