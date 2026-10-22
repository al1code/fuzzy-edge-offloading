"""Compare unrestricted, constant-cap, security-only, and full S/U policies.

Uses fixed locations to isolate policy effects from location-search quality.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path
from statistics import mean

from experiments.proposed.uncertainty_mamdani_comparison import (
    DEFAULT_DATA_SEEDS,
    derive_task_caps,
    derive_task_uncertainties,
    scaled_scenario,
)
from src.config import SyntheticScenarioConfig
from src.dataset_io import dataset_fingerprint, write_dataset
from src.evaluation import derive_normalization
from src.fuzzy_controller import evaluate_uncertainty_aware_offloading
from src.optimizers.locations import evaluate_locations_exact
from src.synthetic import generate_synthetic_dataset
from src.validation import validate_integer


def run_audit(output: Path, *, data_seeds=DEFAULT_DATA_SEEDS, scenario_config=None):
    """Record 3 link conditions and 4 policy ablations per independent dataset."""

    output = Path(output)
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    data_seeds = tuple(data_seeds)
    if not data_seeds or len(set(data_seeds)) != len(data_seeds):
        raise ValueError("data_seeds must be nonempty and unique")
    for seed in data_seeds:
        validate_integer(seed, "data_seed")
    config = SyntheticScenarioConfig() if scenario_config is None else scenario_config
    if not isinstance(config, SyntheticScenarioConfig):
        raise TypeError("scenario_config must be a SyntheticScenarioConfig")
    output.mkdir(parents=True)
    root = Path(__file__).resolve().parents[2]
    sources = [
        *root.joinpath("src").rglob("*.py"),
        *root.joinpath("experiments").rglob("*.py"),
    ]
    manifest = {
        "experiment": "fixed-location-policy-ablation-v1",
        "status": "running",
        "data_seeds": list(data_seeds),
        "scenario_config": asdict(config),
        "conditions": "0.5x, 1x, 2x wireless rates; normalization fixed within each condition",
        "locations": "round-robin, unchanged across policies; resources reserved even at ratio zero",
        "solver": "exact affine endpoint ratios for these fixed locations; not BOALBFS",
        "constant_cap": "mean of full policy caps on the same dataset; diagnostic comparator, not fitted using results",
        "security_only": "same Mamdani rule base with U held at zero; not a calibrated alternative",
        "source_sha256": {
            str(p.relative_to(root)).replace("\\", "/"): hashlib.sha256(
                p.read_bytes()
            ).hexdigest()
            for p in sorted(sources)
        },
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    rows = []
    for seed in data_seeds:
        dataset = generate_synthetic_dataset(
            replace(config, experiment=replace(config.experiment, random_seed=seed))
        )
        write_dataset(dataset, output / "datasets" / f"seed_{seed}.json")
        full_caps = derive_task_caps(dataset)
        uncertainty = derive_task_uncertainties(dataset)
        security_caps = {
            t.task.task_id: evaluate_uncertainty_aware_offloading(
                t.security_level, 0
            ).allowed_offloading_ratio
            for t in dataset.scenario.tasks
        }
        constant_caps = dict.fromkeys(full_caps, mean(full_caps.values()))
        policies = {
            "Unconstrained": None,
            "Constant mean cap": constant_caps,
            "Security only": security_caps,
            "Full Mamdani": full_caps,
        }
        locations = tuple(
            i % len(dataset.scenario.servers) + 1
            for i in range(len(dataset.scenario.tasks))
        )
        for factor in (0.5, 1.0, 2.0):
            scenario = scaled_scenario(dataset.scenario, factor)
            normalization = derive_normalization(scenario)
            for method, caps in policies.items():
                result = evaluate_locations_exact(
                    scenario, locations, normalization=normalization, ratio_caps=caps
                )
                rows.append(
                    {
                        "data_seed": seed,
                        "sha256": dataset_fingerprint(dataset),
                        "link_rate_factor": factor,
                        "method": method,
                        "objective": result.objective.value,
                        "total_latency_seconds": result.total_latency_seconds,
                        "total_security_risk": result.total_security_risk,
                        "uncertainty_weighted_exposure": sum(
                            t.offloading_risk * uncertainty[t.decision.task_id]
                            for t in result.tasks
                        ),
                        "load_variance": result.objective.load_variance,
                        "mean_offloading_ratio": mean(
                            t.decision.offloading_ratio for t in result.tasks
                        ),
                        "mean_allowed_cap": 1.0
                        if caps is None
                        else mean(caps.values()),
                        "locations": json.dumps(locations),
                        "ratios": json.dumps(
                            [t.decision.offloading_ratio for t in result.tasks]
                        ),
                        "ratio_caps": json.dumps(caps),
                    }
                )
    with (output / "runs.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest["status"] = "complete"
    manifest["artifact_sha256"] = {
        str(p.relative_to(output)).replace("\\", "/"): hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
        for p in sorted(output.rglob("*"))
        if p.is_file() and p != manifest_path
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({"runs": len(run_audit(args.output)), "output": str(args.output)}))
