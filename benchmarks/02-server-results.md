# 02 — llama-server Locust Load Test Results

Locust load tests were run for 60 seconds with a ramp-up rate of 1 user per second, targeting `http://localhost:8000/v1/chat/completions` served by the native `llama-server.exe` with `--parallel 4 --cont-batching`.

## Results Table

| Concurrency | Total RPS | E2E P50 (ms) | E2E P95 (ms) | E2E P99 (ms) | Failures |
|---|---|---|---|---|---|
| **10** | 0.22 | 29000 | 50000 | 50000 | 0 (0.00%) |
| **50** | 0.23 | 25000 | 39000 | 39000 | 0 (0.00%) |

## Details - 10 Users

- **Total Requests:** 13
- **Failed Requests:** 0 (0.00%)
- **Response Times (ms):**
  - Min: 17129
  - Max: 49733
  - Avg: 29538
  - Median (P50): 29000
  - P95: 50000
  - P99: 50000

## Details - 50 Users

- **Total Requests:** 11
- **Failed Requests:** 0 (0.00%)
- **Response Times (ms):**
  - Min: 7955
  - Max: 39042
  - Avg: 25690
  - Median (P50): 25000
  - P95: 39000
  - P99: 39000
