import hashlib
import json
from dataclasses import replace

import pytest

from experiments.proposed.contribution_audit import run_audit
from src.config import ExperimentConfig, SyntheticScenarioConfig
from src.fuzzy_controller import calculate_assessment_uncertainty
from src.fuzzy_security import SecurityPerspectives
from src.models import TriangularFuzzyNumber


def test_aggregated_width_does_not_claim_to_measure_expert_disagreement():
    first = TriangularFuzzyNumber(0.0, 0.0, 0.0)
    second = TriangularFuzzyNumber(1.0, 1.0, 1.0)
    assessments = tuple(SecurityPerspectives(n, n, n) for n in (first, second))
    assert calculate_assessment_uncertainty(assessments, (0.5, 0.5)) == 0


def test_ablation_holds_locations_fixed_and_retains_unconstrained_optimum(tmp_path):
    output = tmp_path / "ablation"
    rows = run_audit(
        output,
        data_seeds=(42,),
        scenario_config=replace(
            SyntheticScenarioConfig(), experiment=ExperimentConfig(42, 3, 2)
        ),
    )
    assert len(rows) == 12
    for factor in (0.5, 1.0, 2.0):
        group = [r for r in rows if r["link_rate_factor"] == factor]
        baseline = next(r for r in group if r["method"] == "Unconstrained")
        assert len({r["locations"] for r in group}) == 1
        assert len({r["load_variance"] for r in group}) == 1
        for row in group:
            assert row["objective"] >= baseline["objective"] - 1e-12
            caps = json.loads(row["ratio_caps"])
            if caps is not None:
                assert all(
                    x <= caps[f"task-{i + 1:04d}"] + 1e-12
                    for i, x in enumerate(json.loads(row["ratios"]))
                )
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "complete"
    assert all(
        hashlib.sha256((output / path).read_bytes()).hexdigest() == digest
        for path, digest in manifest["artifact_sha256"].items()
    )
    with pytest.raises(FileExistsError):
        run_audit(output)


@pytest.mark.parametrize("seeds", [(), (42, 42), (-1,), (True,)])
def test_invalid_audit_seeds_fail_before_creating_results(tmp_path, seeds):
    output = tmp_path / "invalid"
    with pytest.raises((ValueError, TypeError)):
        run_audit(output, data_seeds=seeds)
    assert not output.exists()
