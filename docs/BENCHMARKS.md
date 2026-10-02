# Benchmarks

## Full real dataset

Measured on the checked-in `data/inbox/VoidHacks8_MuleAccount_2M_Transactions.csv` (274 MB, 2,000,000 data rows) using DuckDB 1.1.3 native parallel CSV scanning and SQL normalization on a Linux host reporting 13.72–19.72 GB RAM depending on the process environment.

| Stage | Result |
|---|---:|
| Raw rows | 2,000,000 |
| Loaded rows | 1,997,748 |
| Rejected rows | 2,252 |
| Accounts | 24,873 |
| Ingestion wall time | 13.174 s |
| Set-based analytics + ring detection | 19.387 s |
| Set-based risk scoring only | 0.303 s |
| Warm 4-hop trace | 0.355 s wall time |
| Warm trace payload | 82 nodes / 87 edges |
| FIFO flow links | 102 |
| Connected-component rings | 2 |
| Peak measured process RSS during trace | 108.3 MB |

The 2M-row ingestion target of 60 seconds passed in this environment. The result is a real measurement for this host and dataset, not a forecast for every laptop.

## Smoke benchmark

The seeded 10,000-row benchmark remains in `benchmarks/results/smoke.json`. Synthetic results are kept separate from the real-data benchmark.
