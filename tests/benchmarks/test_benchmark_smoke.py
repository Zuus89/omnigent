"""Fast smoke test for the HTTP-journey benchmark harness.

Runs the real harness (boots an ``omnigent server``, no runner / no LLM /
no Databricks) with tiny counts and asserts the report shape and threshold
logic. Runs on the normal CI lane — no creds, no ``databricks`` marker.

The measurement and schema layers also get direct unit checks so their logic
is covered without paying the server-boot cost.
"""

from __future__ import annotations

import argparse
from typing import cast

import pytest

from dev.benchmarks.omnigent import run as bench_run
from dev.benchmarks.omnigent.journeys import ALL_JOURNEYS
from dev.benchmarks.omnigent.measure import RunResult, aggregate, check_thresholds
from dev.benchmarks.omnigent.schema import SCHEMA_VERSION, build_report

_SMOKE_JOURNEYS = ["list_sessions", "create_session", "get_session", "load_conversation_history"]


def _d(value: object) -> dict[str, object]:
    """Narrow an opaque report node to a dict for indexing (test-side JSON nav)."""
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def _smoke_args(**overrides: object) -> argparse.Namespace:
    """Tiny-count args so the smoke run boots the server once and finishes fast."""
    base = {
        "journeys": _SMOKE_JOURNEYS,
        "iterations": 2,
        "requests": 5,
        "concurrency": 1,
        "runs": 1,
        "warmup": 1,
        "output": None,
        "min_rps": None,
        "max_p50_ms": None,
        "max_p99_ms": None,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


# ── pure-layer unit checks (no server) ───────────────────────


def test_percentile_and_throughput() -> None:
    r = RunResult(latencies_ms=[10.0, 20.0, 30.0, 40.0], wall_time=2.0)
    assert r.n_success == 4
    assert r.percentile(50) == 20.0  # ceil-index: idx = ceil(0.5*4)-1 = 1
    assert r.percentile(100) == 40.0
    assert r.throughput == 2.0  # 4 successes / 2.0s


def test_aggregate_summary_keys() -> None:
    runs = [RunResult(latencies_ms=[5.0, 15.0], wall_time=1.0) for _ in range(2)]
    block = aggregate(runs)
    run_rows = cast(list[dict[str, object]], block["runs"])
    assert len(run_rows) == 2
    assert set(_d(block["summary"])) == {
        "avg_mean_ms",
        "avg_p50_ms",
        "avg_p95_ms",
        "avg_p99_ms",
        "avg_rps",
    }
    assert run_rows[0]["n_success"] == 2


def test_check_thresholds_pass_and_fail() -> None:
    runs = [RunResult(latencies_ms=[10.0, 10.0], wall_time=1.0)]
    assert check_thresholds(runs, min_rps=None, max_p50_ms=1000.0, max_p99_ms=None)
    assert not check_thresholds(runs, min_rps=None, max_p50_ms=0.001, max_p99_ms=None)


def test_build_report_shape() -> None:
    block = aggregate([RunResult(latencies_ms=[1.0], wall_time=1.0)])
    block["kind"] = "latency"
    report = build_report(
        {"list_sessions": block},
        generated_at="2026-07-08T00:00:00+00:00",
        config={"iterations": 2},
        harness="http-only",
    )
    assert report["schema_version"] == SCHEMA_VERSION
    assert report["generated_at"] == "2026-07-08T00:00:00+00:00"
    assert set(report) >= {
        "schema_version",
        "generated_at",
        "git_sha",
        "git_branch",
        "host",
        "harness",
        "config",
        "journeys",
    }
    assert "list_sessions" in _d(report["journeys"])


# ── end-to-end smoke (boots the server) ──────────────────────


@pytest.mark.timeout(180)
async def test_benchmark_smoke_end_to_end() -> None:
    """Boot the server, run every HTTP journey once, validate the report."""
    report, passed = await bench_run.run_benchmark(_smoke_args())

    assert passed  # no thresholds supplied → vacuously passes
    assert report["schema_version"] == SCHEMA_VERSION
    assert _d(report["config"])["with_runner"] is False

    journeys = _d(report["journeys"])
    for name in _SMOKE_JOURNEYS:
        assert name in ALL_JOURNEYS
        block = _d(journeys[name])
        assert block["kind"] == "latency"
        run_rows = cast(list[dict[str, object]], block["runs"])
        assert run_rows, f"{name} produced no runs"
        # Zero failures — a failure here means the HTTP path itself broke.
        assert run_rows[0]["n_failures"] == 0, f"{name}: {run_rows[0]['failures']}"
        assert cast(float, _d(block["summary"])["avg_p50_ms"]) >= 0.0


@pytest.mark.timeout(180)
async def test_benchmark_smoke_threshold_failure_exits_nonzero() -> None:
    """An impossible p50 bound trips the threshold gate (passed=False)."""
    _, passed = await bench_run.run_benchmark(
        _smoke_args(journeys=["list_sessions"], max_p50_ms=0.0001)
    )
    assert not passed
