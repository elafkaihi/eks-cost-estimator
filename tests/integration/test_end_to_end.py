from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from eks_cost_estimator.cli.main import app


runner = CliRunner()


def test_cli_end_to_end_json():
    fixtures = Path("tests/fixtures")
    result = runner.invoke(
        app,
        [
            "estimate",
            str(fixtures / "deployment.yaml"),
            str(fixtures / "statefulset_with_vct.yaml"),
            str(fixtures / "pvc.yaml"),
            str(fixtures / "service_lb.yaml"),
            "--output",
            "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    # Required keys
    assert "baseline" in data
    assert "derived_rates" in data
    assert "workloads" in data
    assert "storage" in data
    assert "totals" in data
    assert data["totals"]["compute_monthly"] >= 0
    assert data["totals"]["storage_monthly"] >= 0
    assert (data["totals"]["compute_monthly"] + data["totals"]["storage_monthly"]) > 0
