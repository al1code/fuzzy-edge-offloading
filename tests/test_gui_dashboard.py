"""Optional Streamlit interaction tests; the command-line core needs no GUI."""

from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

from gui import charts
from gui.dashboard import VIEWS, number
from gui.services import METHODS, context_key, load_bundle, run_method
from src.config import (
    ExperimentConfig,
    GeneticSearchConfig,
    LoadBalanceConfig,
    SwarmSearchConfig,
    SyntheticScenarioConfig,
)
from src.objective import ObjectiveConfig
from src.synthetic import generate_synthetic_dataset

ROOT = Path(__file__).resolve().parents[1]


def widget(elements, label):
    return next(e for e in elements if e.label == label)


@pytest.fixture
def app():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=40).run()
    assert not app.exception
    app.session_state.dataset = generate_synthetic_dataset(
        replace(SyntheticScenarioConfig(), experiment=ExperimentConfig(42, 3, 2))
    )
    app.session_state.settings = (
        ObjectiveConfig(),
        LoadBalanceConfig(),
        GeneticSearchConfig(population_size=4, generations=2),
        SwarmSearchConfig(particle_count=3, iterations=3),
        0,
    )
    app.session_state.epoch += 1
    return app.run()


@pytest.mark.parametrize("view", VIEWS)
def test_all_views_render_without_exceptions(app, view):
    app.radio[0].set_value(view).run()
    assert not app.exception
    assert app.title[0].value == "G\u00f6rev Y\u00f6nlendirme Laboratuvar\u0131"


def test_compare_runs_every_method_using_real_core(app):
    app.radio[0].set_value(VIEWS[3]).run()
    app.multiselect[0].set_value(list(METHODS)).run()
    widget(
        app.button, "Se\u00e7ili \u00e7\u00f6z\u00fcmleri \u00e7al\u0131\u015ft\u0131r"
    ).click().run()
    assert not app.exception
    assert len(app.session_state.runs) == len(METHODS)
    objective, load, genetic, swarm, seed = app.session_state.settings
    for run in app.session_state.runs:
        reference = run_method(
            app.session_state.dataset,
            run.method,
            seed=seed,
            objective=objective,
            load=load,
            genetic=genetic,
            swarm=swarm,
        )
        assert run.evaluation == reference.evaluation
    assert len(app.session_state.run_failures) == 0


def test_failed_method_warning_survives_rerun(app):
    widget(app.number_input, "G\u00f6rev").set_value(6)
    widget(app.button, "Senaryoyu olu\u015ftur").click().run()
    app.radio[0].set_value(VIEWS[3]).run()
    app.multiselect[0].set_value(["Local", "Exact"]).run()
    widget(
        app.button, "Se\u00e7ili \u00e7\u00f6z\u00fcmleri \u00e7al\u0131\u015ft\u0131r"
    ).click().run()
    assert not app.exception
    assert [r.method for r in app.session_state.runs] == ["Local"]
    assert any("Exact" in w.value for w in app.warning)


def test_scenario_and_fuzzy_changes_invalidate_old_runs(app):
    data = app.session_state.dataset
    objective, load, genetic, swarm, seed = app.session_state.settings
    run = run_method(
        data,
        "Analytical",
        seed=seed,
        objective=objective,
        load=load,
        genetic=genetic,
        swarm=swarm,
    )
    app.session_state.runs = [run]
    app.session_state.run_context = context_key(
        data, objective, load, genetic, swarm, seed
    )
    app.radio[0].set_value(VIEWS[1]).run()
    widget(app.slider, "G\u00fcvenlik e\u015fi\u011fi").set_value(0.8)
    widget(app.button, "Bulan\u0131k girdileri uygula").click().run()
    assert not app.exception
    assert app.session_state.edited
    assert not app.session_state.runs
    assert app.session_state.dataset.scenario.security_threshold == 0.8
    widget(app.number_input, "G\u00f6rev").set_value(2)
    widget(app.button, "Senaryoyu olu\u015ftur").click().run()
    assert not app.exception
    assert len(app.session_state.dataset.scenario.tasks) == 2
    assert not app.session_state.edited


def test_single_task_slider_changes_components_not_full_plan(app):
    app.radio[0].set_value(VIEWS[2]).run()
    full_objective = app.metric[0].value
    widget(app.slider, "Tek g\u00f6rev g\u00f6nderim oran\u0131 (%)").set_value(0).run()
    assert widget(app.metric, "Sunucu (s)").value == "0.0000"
    widget(app.slider, "Tek g\u00f6rev g\u00f6nderim oran\u0131 (%)").set_value(
        100
    ).run()
    assert widget(app.metric, "Cihaz (s)").value == "0.0000"
    assert app.metric[0].value == full_objective
    assert not app.exception


def test_invalid_zero_weights_are_rejected_without_losing_settings(app):
    before = app.session_state.settings
    for label in ("S\u00fcre", "Risk", "Y\u00fck"):
        widget(app.number_input, label).set_value(0)
    widget(app.button, "Ayarlar\u0131 uygula").click().run()
    assert not app.exception
    assert app.error
    assert app.session_state.settings == before


def test_run_small_multiseed_protocol_and_restore_saved_plan(
    app, monkeypatch, tmp_path
):
    monkeypatch.setattr("gui.dashboard.ROOT", tmp_path)
    app.radio[0].set_value(VIEWS[4]).run()
    widget(app.multiselect, "Veri seed'leri").set_value([7])
    widget(app.multiselect, "Arama seed'leri").set_value([0])
    widget(app.button, "Deneyi \u00e7al\u0131\u015ft\u0131r ve kaydet").click().run()
    assert not app.exception
    folders = list((tmp_path / "results").glob("*/manifest.json"))
    assert len(folders) == 1
    manifest, rows = load_bundle(folders[0].parent)
    assert manifest["status"] == "complete" and len(rows) == 2
    widget(app.button, "Bu girdiyi ve karar\u0131 incele").click().run()
    assert not app.exception
    assert app.radio[0].value == VIEWS[2]
    assert app.session_state.dataset.configuration.experiment.random_seed == 7
    assert app.session_state.runs[0].evaluation.objective.value == float(
        rows[0]["objective"]
    )
    assert widget(app.number_input, "GA birey").value == 4


def test_invalid_operator_settings_keep_previous_valid_configuration(app):
    before = app.session_state.settings
    widget(app.number_input, "Elit birey").set_value(4)
    widget(app.button, "Ayarlar\u0131 uygula").click().run()
    assert not app.exception
    assert app.error
    assert app.session_state.settings == before


def test_log_timing_figure_uses_points_not_an_undefined_zero_bar():
    spec = charts.bars(
        [
            {"method": "baseline", "seconds": 10.0},
            {"method": "analytical", "seconds": 0.2},
        ],
        "method",
        "seconds",
        y_title="Search seconds",
        log=True,
    ).to_dict()
    assert spec["mark"]["type"] == "point"
    assert spec["encoding"]["y"]["scale"] == {"type": "log", "zero": False}


def test_metric_formatting_retains_tiny_values_and_limits_large_text():
    assert number(0.0) == "0.000000"
    assert number(0.239139) == "0.239139"
    assert number(1e-10) == "1e-10"
    assert number(1e100, 3) == "1e+100"
