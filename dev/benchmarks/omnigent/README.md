# Omnigent performance benchmark

Baseline, repeatable latency/throughput numbers for key Omnigent user
journeys, so we can track them over time and catch regressions. Modeled on
MLflow's `dev/benchmarks/gateway/` workflow.

The harness boots a real `omnigent server` against a throwaway SQLite DB,
drives the selected journeys under load, prints latency/throughput tables, and
writes a versioned JSON report. **v1 benchmarks the HTTP/API surface only** —
no runner, no LLM — so runs are fast and low-noise.

## Run it

```bash
# All journeys, sequential latency (100 iterations × 3 runs each).
uv run --no-sync dev/benchmarks/omnigent/run.py

# A subset, writing a report for CI artifact upload.
uv run --no-sync dev/benchmarks/omnigent/run.py \
    --journeys list_sessions,load_conversation_history \
    --iterations 200 --runs 3 --output bench.json

# Throughput mode: >1 concurrency drives concurrency-safe journeys as load.
uv run --no-sync dev/benchmarks/omnigent/run.py \
    --requests 500 --concurrency 25 --runs 3

# CI gating: exit 1 if a threshold is breached.
uv run --no-sync dev/benchmarks/omnigent/run.py --max-p50-ms 25 --max-p99-ms 100
```

`--no-sync` runs against the already-installed venv. (A bare `uv run` may try to
rebuild the project, which fails in a git worktree without a Node web-UI build;
`OMNIGENT_SKIP_WEB_UI=true uv sync` prepares the venv once, then use
`--no-sync`.)

Key flags (`--help` for all): `--journeys A,B`, `--iterations N` (per latency
run), `--requests N` / `--concurrency N` (throughput), `--runs N`, `--warmup N`,
`--output FILE`, `--min-rps` / `--max-p50-ms` / `--max-p99-ms` (CI thresholds).

## Journeys (v1 — all pure HTTP, runner-free)

| Journey | Operation timed |
| --- | --- |
| `list_sessions` | `GET /v1/sessions` — session-list read |
| `create_session` | `POST /v1/sessions` then `DELETE` — session create |
| `get_session` | `GET /v1/sessions/{id}` — single-session snapshot |
| `load_conversation_history` | `GET /v1/sessions/{id}/items` — history read |

`load_conversation_history` seeds its history over HTTP via the
`external_conversation_item` event (appends items without starting a task), so
no runner or LLM is involved. Add a journey by registering a `Journey` in
`journeys.py`.

## Output → Databricks → dashboard

The harness writes JSON only. Storage and charting live in Databricks:

```
run.py --output bench.json   →   GitHub Actions artifact   →   Databricks notebook (ETL)   →   Delta table   →   AI/BI dashboard
        (this repo)                    (CI, follow-up)              (workspace, yours)
```

The repo's contract is the **JSON schema** below. A workspace notebook (owned
outside this repo, modeled on MLflow's gateway ETL) pulls the CI artifacts via
the GitHub API, flattens each run's `summary` + `runs` + metadata, and
`saveAsTable`s into a Delta table the dashboard reads. `sample_output.json` is a
committed, faithful example so the notebook can be written against a real
document without running the harness.

### JSON schema (`schema.py`, `SCHEMA_VERSION`)

```jsonc
{
  "schema_version": 1,
  "generated_at": "<ISO-8601 UTC>",
  "git_sha": "<HEAD sha>",
  "git_branch": "<branch>",
  "host": {"platform": "...", "python": "...", "cpu_count": 12},
  "harness": "http-only",
  "config": {"iterations": 100, "requests": 500, "concurrency": 1,
             "runs": 3, "warmup": 10, "with_runner": false},
  "journeys": {
    "<journey name>": {
      "kind": "latency" | "throughput",
      "runs": [                       // one per --runs
        {"n_success": N, "n_failures": N, "failures": {"HTTP 500": 1},
         "wall_time_s": …, "mean_ms": …, "p50_ms": …, "p95_ms": …,
         "p99_ms": …, "max_ms": …, "rps": …}
      ],
      "summary": {"avg_mean_ms": …, "avg_p50_ms": …, "avg_p95_ms": …,
                  "avg_p99_ms": …, "avg_rps": …}    // averaged across runs
    }
  }
}
```

The per-journey `summary` + `runs` shape mirrors MLflow's gateway benchmark, so
the same ETL flatten works — keyed by `journey` (and `harness`) instead of
`backend`. Bump `SCHEMA_VERSION` on any breaking shape change so the notebook
can branch on it.

## Layout

| File | Role |
| --- | --- |
| `run.py` | CLI orchestrator + entrypoint |
| `journeys.py` | `Journey` dataclass, latency/throughput runners, registry |
| `environment.py` | server (± runner + mock LLM) lifecycle |
| `measure.py` | `RunResult`, percentile, aggregation, thresholds, tables |
| `schema.py` | `SCHEMA_VERSION`, `build_report`, git/host metadata |
| `sample_output.json` | committed example of the JSON contract |

The smoke test is `tests/benchmarks/test_benchmark_smoke.py` (boots the server
with tiny counts; runs on the normal CI lane, no creds).

## Follow-ups (not in v1)

- **Phase 2 — full-stack agent-turn journeys.** `environment.py` already
  implements a `with_runner=True` mode that additionally spawns a zero-latency
  mock LLM (`tests/server/integration/mock_llm_server.py`) and a sibling
  `runner`, and routes the server-side policy classifier at the mock. Phase 2
  is additive: flip `_WITH_RUNNER = True` in `run.py` and register full-turn
  journeys (create-session-and-drive-a-turn, tool-calling, streaming,
  interrupt, multi-turn). The shared framework (`measure.py`, `schema.py`, the
  `Journey` runners) is reused unchanged. The `with_runner=True` path is written
  but unexercised until phase 2 adds a full-turn smoke test.
- **CI workflow.** A scheduled/dispatch GitHub Actions job that runs the
  harness and uploads `--output` as an artifact (the notebook's source). Model
  on MLflow's `gateway-benchmark.yml`.
- **Simulated provider latency.** The mock LLM returns at ~zero latency (right
  for measuring app overhead). A fixed per-response delay knob would let phase-2
  turns model end-user wall-clock; it's a one-field change threaded through
  `mock_llm_server.py` behind the `configure_mock` seam.
