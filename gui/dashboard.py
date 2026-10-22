"""Turkish local dashboard for inspecting and running the existing models."""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from gui import charts
from gui.services import (
    METHODS,
    UNCERTAINTY_MAMDANI_METHOD,
    bundle_configuration,
    bundle_statistics,
    context_key,
    evaluate_manual,
    export_run,
    list_bundles,
    load_bundle,
    mamdani_policy_for_dataset,
    plan_rows,
    restore_bundle_run,
    run_method,
    run_uncertainty_mamdani,
    summary_row,
    update_assessment,
)
from src.config import (
    ExperimentConfig,
    FuzzySecurityConfig,
    GeneticSearchConfig,
    LoadBalanceConfig,
    PositiveRange,
    SwarmSearchConfig,
    SyntheticScenarioConfig,
)
from src.dataset_io import dataset_fingerprint, dataset_from_json, dataset_to_json
from src.fuzzy_controller import (
    RULE_BASE,
    evaluate_uncertainty_aware_offloading,
)
from src.fuzzy_security import (
    SecurityPerspectives,
    assess_security,
    calculate_offloading_risk,
    calculate_security_risk,
)
from src.latency import calculate_task_latency
from src.models import TriangularFuzzyNumber
from src.objective import ObjectiveConfig
from src.synthetic import generate_synthetic_dataset

ROOT = Path(__file__).resolve().parents[1]
VIEWS = (
    "Senaryo",
    "Bulan\u0131k G\u00fcvenlik",
    "G\u00f6rev ve Sunucular",
    "\u00c7\u00f6z\u00fcm Kar\u015f\u0131la\u015ft\u0131rmas\u0131",
    "Deney Kay\u0131tlar\u0131",
    "Mamdani Katk\u0131s\u0131",
    "Projeyi Anla",
)
COMPARISON_METHODS = METHODS + (UNCERTAINTY_MAMDANI_METHOD,)
LABELS = {
    "task_id": "G\u00f6rev",
    "server": "Sunucu",
    "ratio_percent": "G\u00f6nderim (%)",
    "local_seconds": "Cihaz (s)",
    "transmission_seconds": "\u0130letim (s)",
    "edge_seconds": "Sunucu (s)",
    "total_seconds": "Toplam (s)",
    "security_risk": "G\u00f6rev riski",
    "offloading_risk": "G\u00f6nderim riski",
    "method": "Y\u00f6ntem",
    "objective": "Ama\u00e7 F",
    "latency_seconds": "G\u00f6rev s\u00fcreleri (s)",
    "model_risk": "Model riski",
    "load_variance": "Y\u00fck varyans\u0131",
    "search_seconds": "Arama (s)",
    "ga_evaluations": "GA aday\u0131",
    "plan_evaluations": "Tam-plan hesab\u0131",
    "endpoint_tests": "Ek u\u00e7-nokta hesab\u0131",
    "infeasible_evaluations": "Uygunsuz aday",
}
METHOD_LABELS = {
    "Local": "Local / tamamen cihazda",
    "Edge": "Edge / tamamen sunucuda",
    "BOALBFS": "BOALBFS / GA + SA-PSO",
    "Analytical": "Katk\u0131 / GA + analitik oran",
    "Exact": "Kesin kontrol / k\u00fc\u00e7\u00fck senaryo",
    UNCERTAINTY_MAMDANI_METHOD: "Önerilen / belirsizlik-duyarlı Mamdani",
}
PERSPECTIVES = {
    "task_data": "G\u00f6rev verisi",
    "task_type": "G\u00f6rev t\u00fcr\u00fc",
    "terminal_lifecycle": "Terminal ya\u015fam d\u00f6ng\u00fcs\u00fc",
}


def number(value, decimals=6):
    if abs(value) >= 1e6 or 0 < abs(value) < 10**-decimals:
        return f"{value:.4g}"
    return f"{value:.{decimals}f}"


def table(records, **kwargs):
    frame = pd.DataFrame(records)
    st.dataframe(
        frame.rename(columns=LABELS), hide_index=True, width="stretch", **kwargs
    )


def weighted_inputs(label, values, key):
    columns = st.columns(len(values))
    raw = [
        c.number_input(
            name,
            min_value=0.0,
            max_value=100.0,
            value=float(v) * 100,
            step=1.0,
            format="%.4f",
            key=f"{key}_{i}",
        )
        for i, (c, name, v) in enumerate(zip(columns, label, values, strict=True))
    ]
    if sum(raw) == 0:
        raise ValueError(
            "A\u011f\u0131rl\u0131klar\u0131n tamam\u0131 s\u0131f\u0131r olamaz."
        )
    return tuple(v / sum(raw) for v in raw)


def install_dataset(dataset, *, edited=False, source="generated"):
    if len(dataset.scenario.tasks) > 140 or len(dataset.scenario.servers) > 9:
        raise ValueError("GUI s\u0131n\u0131r\u0131: 140 g\u00f6rev, 9 sunucu.")
    st.session_state.dataset = dataset
    st.session_state.runs = []
    st.session_state.run_failures = []
    st.session_state.edited = edited
    st.session_state.input_source = source
    st.session_state.epoch += 1


def sidebar():
    data = st.session_state.dataset
    cfg = data.configuration
    prefix = f"scenario_{st.session_state.epoch}"
    with st.sidebar:
        st.header("Fuzzy Security Lab")
        view = st.radio(
            "\u00c7al\u0131\u015fma g\u00f6r\u00fcn\u00fcm\u00fc",
            VIEWS,
            key="view",
            label_visibility="collapsed",
        )
        with st.expander("Yeni ba\u015flayanlar i\u00e7in", expanded=True):
            st.markdown(
                "**\u00d6nerilen ilk deneme**  \n"
                "Seed `42`, 3 g\u00f6rev, 2 sunucu ile ba\u015fla. "
                "Sonra sadece bir parametreyi de\u011fi\u015ftirip sonucu kar\u015f\u0131la\u015ft\u0131r."
            )
            st.caption(
                "Seed'i de\u011fi\u015ftirirsen veri de\u011fi\u015fir. G\u00fcvenlik e\u015fi\u011fi, "
                "ama\u00e7 a\u011f\u0131rl\u0131klar\u0131 ve arama b\u00fct\u00e7esi ayn\u0131 kal\u0131rsa "
                "kar\u015f\u0131la\u015ft\u0131rma daha adil olur."
            )
        st.divider()
        with st.form("scenario_form", border=False):
            st.subheader("Senaryo girdileri")
            st.caption(
                "Bu b\u00f6l\u00fcm veri \u00fcretir. Sunumda ilk olarak seed, g\u00f6rev "
                "ve sunucu say\u0131s\u0131n\u0131 de\u011fi\u015ftirmen yeterlidir."
            )
            seed = st.number_input(
                "Veri seed",
                min_value=0,
                value=cfg.experiment.random_seed,
                key=prefix + "seed",
                help="Ayn\u0131 seed ve s\u00fcr\u00fcmler ayn\u0131 sentetik girdileri \u00fcretir.",
            )
            a, b = st.columns(2)
            tasks = a.number_input(
                "G\u00f6rev", 1, 140, cfg.experiment.task_count, key=prefix + "tasks"
            )
            servers = b.number_input(
                "Sunucu", 1, 9, cfg.experiment.server_count, key=prefix + "servers"
            )
            threshold = st.slider(
                "G\u00fcvenlik e\u015fi\u011fi",
                0.0,
                1.0,
                cfg.security_threshold,
                0.01,
                key=prefix + "threshold",
            )
            changes = {}
            with st.expander("Kaynaklar ve kablosuz ba\u011flant\u0131"):
                specs = (
                    (
                        "local_cpu_cycles_per_second",
                        "Cihaz CPU (milyar \u00e7evrim/s)",
                        1e9,
                    ),
                    (
                        "allocated_edge_cpu_cycles_per_second",
                        "G\u00f6rev CPU tahsisi (milyar \u00e7evrim/s)",
                        1e9,
                    ),
                    (
                        "server_cpu_capacity_cycles_per_second",
                        "Sunucu CPU (milyar \u00e7evrim/s)",
                        1e9,
                    ),
                    ("server_memory_capacity_mb", "Sunucu belle\u011fi (MB)", 1.0),
                    ("bandwidth_capacity_hz", "Sunucu bant kapasitesi (MHz)", 1e6),
                    ("transmission_power_watts", "\u0130letim g\u00fcc\u00fc (W)", 1.0),
                    (
                        "noise_density_watts_per_hz",
                        "G\u00fcr\u00fclt\u00fc (W/Hz)",
                        1.0,
                    ),
                    ("deadline_seconds", "Deadline metaverisi (s)", 1.0),
                    ("inventory_link_rate_mbps", "Envanter h\u0131z\u0131 (Mbps)", 1.0),
                )
                for name, label, scale in specs:
                    changes[name] = (
                        st.number_input(
                            label,
                            min_value=1e-20,
                            value=float(getattr(cfg, name)) / scale,
                            format="%.5g",
                            key=prefix + name,
                        )
                        * scale
                    )
                st.caption(
                    "Mbps envanter alan\u0131 kablosuz h\u0131z de\u011fildir. Deadline mevcut modelde k\u0131s\u0131t de\u011fil, metaveridir."
                )
            with st.expander("G\u00f6rev ve kanal da\u011f\u0131l\u0131mlar\u0131"):
                for name, label, scale in (
                    ("data_size_mb", "Veri (MB)", 1),
                    ("cpu_cycles_per_bit", "CPU (\u00e7evrim/bit)", 1),
                    ("task_bandwidth_hz", "G\u00f6rev bant tahsisi (MHz)", 1e6),
                    ("task_memory_mb", "G\u00f6rev belle\u011fi (MB)", 1),
                    ("channel_gain", "Kanal kazanc\u0131", 1),
                ):
                    bounds = getattr(cfg, name)
                    st.markdown(f"**{label}**")
                    left, right = st.columns(2)
                    low = left.number_input(
                        "Alt",
                        min_value=1e-12,
                        value=bounds.low / scale,
                        format="%.5g",
                        key=prefix + name + "low",
                    )
                    high = right.number_input(
                        "\u00dcst",
                        min_value=1e-12,
                        value=bounds.high / scale,
                        format="%.5g",
                        key=prefix + name + "high",
                    )
                    changes[name] = (low * scale, high * scale)
            submitted = st.form_submit_button(
                "Senaryoyu olu\u015ftur",
                icon=":material/refresh:",
                width="stretch",
                type="primary",
            )
        if submitted:
            try:
                for name in (
                    "data_size_mb",
                    "cpu_cycles_per_bit",
                    "task_bandwidth_hz",
                    "task_memory_mb",
                    "channel_gain",
                ):
                    changes[name] = PositiveRange(*changes[name])
                new_cfg = replace(
                    cfg,
                    experiment=ExperimentConfig(seed, tasks, servers),
                    security_threshold=threshold,
                    **changes,
                )
                install_dataset(generate_synthetic_dataset(new_cfg))
                st.rerun()
            except (TypeError, ValueError, OverflowError) as exc:
                st.error(f"Senaryo olu\u015fturulamad\u0131: {exc}")
        with st.expander("Ama\u00e7 ve arama ayarlar\u0131"):
            st.caption(
                "Girilen ağırlıklar toplamlarına bölünür. Örneğin 1 / 1 / 1 "
                "ile 30 / 30 / 30 aynı tercihi verir. Geçerli yüzdeler üst "
                "özetin altında gösterilir."
            )
            st.caption(
                "Ama\u00e7 a\u011f\u0131rl\u0131klar\u0131 F'nin hangi bile\u015fene "
                "daha fazla \u00f6nem verdi\u011fini; GA/SA-PSO ayarlar\u0131 ise "
                "arama kalitesi ve maliyetini belirler."
            )
            objective, load, genetic, swarm, seed = st.session_state.settings
            with st.form("settings_form", border=False):
                st.markdown("**Ama\u00e7 a\u011f\u0131rl\u0131klar\u0131 (%)**")
                try:
                    ow = weighted_inputs(
                        ("S\u00fcre", "Risk", "Y\u00fck"),
                        tuple(asdict(objective).values()),
                        f"ow_{st.session_state.epoch}",
                    )
                    st.markdown(
                        "**Kaynak y\u00fck a\u011f\u0131rl\u0131klar\u0131 (%)**"
                    )
                    lw = weighted_inputs(
                        ("CPU", "Bant", "Bellek"),
                        tuple(asdict(load).values()),
                        f"lw_{st.session_state.epoch}",
                    )
                    valid = True
                except ValueError as exc:
                    st.error(str(exc))
                    valid = False
                search_seed = st.number_input(
                    "Arama seed", min_value=0, value=seed, key=prefix + "search_seed"
                )
                pop = st.number_input(
                    "GA birey",
                    2,
                    30,
                    genetic.population_size,
                    key=prefix + "population",
                )
                generations = st.number_input(
                    "GA nesil", 0, 30, genetic.generations, key=prefix + "generations"
                )
                particles = st.number_input(
                    "SA-PSO par\u00e7ac\u0131k",
                    2,
                    24,
                    swarm.particle_count,
                    key=prefix + "particles",
                )
                iterations = st.number_input(
                    "SA-PSO iterasyon",
                    0,
                    60,
                    swarm.iterations,
                    key=prefix + "iterations",
                )
                ga_tab, swarm_tab = st.tabs(
                    ("GA operat\u00f6rleri", "SA-PSO dinami\u011fi")
                )
                ga_changes, swarm_changes = {}, {}
                with ga_tab:
                    ga_changes["elite_count"] = st.number_input(
                        "Elit birey", 1, 29, genetic.elite_count, key=prefix + "elite"
                    )
                    for name, label in (
                        ("crossover_high", "\u00c7aprazlama \u00fcst"),
                        ("crossover_low", "\u00c7aprazlama alt"),
                        ("mutation_high", "Mutasyon \u00fcst"),
                        ("mutation_low", "Mutasyon alt"),
                    ):
                        ga_changes[name] = st.number_input(
                            label,
                            0.0,
                            1.0,
                            getattr(genetic, name),
                            0.01,
                            format="%.4f",
                            key=prefix + name,
                        )
                    st.caption(
                        "Adaptif olas\u0131l\u0131k s\u0131n\u0131rlar\u0131; \u00fcst > alt, elit say\u0131s\u0131 < birey say\u0131s\u0131 olmal\u0131d\u0131r."
                    )
                with swarm_tab:
                    for name, label in (
                        ("inertia_high", "Atalet \u00fcst"),
                        ("inertia_low", "Atalet alt"),
                        ("cognitive", "Bireysel \u00e7ekim"),
                        ("social", "S\u00fcr\u00fc \u00e7ekimi"),
                        ("velocity_limit", "H\u0131z s\u0131n\u0131r\u0131"),
                        (
                            "initial_temperature",
                            "Ba\u015flang\u0131\u00e7 s\u0131cakl\u0131\u011f\u0131",
                        ),
                        ("cooling_rate", "So\u011futma katsay\u0131s\u0131"),
                    ):
                        swarm_changes[name] = st.number_input(
                            label,
                            min_value=0.0,
                            max_value=1.0
                            if name.startswith("inertia") or name == "cooling_rate"
                            else None,
                            value=getattr(swarm, name),
                            step=0.01,
                            format="%.4f",
                            key=prefix + name,
                        )
                    st.caption(
                        "Atalet: h\u0131z\u0131n korunmas\u0131. \u00c7ekimler: bireysel/s\u00fcr\u00fc en iyisine y\u00f6nelme. S\u0131cakl\u0131k ve so\u011futma: daha k\u00f6t\u00fc aday\u0131 kabul etme davran\u0131\u015f\u0131."
                    )
                applied = st.form_submit_button(
                    "Ayarlar\u0131 uygula", icon=":material/check:", disabled=not valid
                )
            if applied:
                try:
                    st.session_state.settings = (
                        ObjectiveConfig(*ow),
                        LoadBalanceConfig(*lw),
                        replace(
                            genetic,
                            population_size=pop,
                            generations=generations,
                            **ga_changes,
                        ),
                        replace(
                            swarm,
                            particle_count=particles,
                            iterations=iterations,
                            **swarm_changes,
                        ),
                        search_seed,
                    )
                    st.session_state.runs = []
                    st.session_state.run_failures = []
                    st.rerun()
                except (TypeError, ValueError) as exc:
                    st.error(f"Ayarlar ge\u00e7ersiz: {exc}")
        st.caption(
            "Sentetik veriler. Ger\u00e7ek fabrika veya sald\u0131r\u0131 kayd\u0131 de\u011fildir."
        )
    return view


def overview(data):
    st.subheader("Girdiler ve veri kayna\u011f\u0131")
    st.caption(
        "Bir cihaz\u0131n i\u015fi cihazda m\u0131, sunucuda m\u0131, k\u0131smen ikisinde mi yap\u0131lmal\u0131? Karar; hesaplama/iletim s\u00fcresi, belirsiz uzman g\u00f6r\u00fc\u015flerinden hesaplanan g\u00fcvenlik riski ve sunucu y\u00fck dengesiyle de\u011ferlendirilir."
    )
    left, right = st.columns([2, 1])
    with left:
        records = [
            {
                "G\u00f6rev": t.task.task_id,
                "Veri (MB)": t.task.data_size_mb,
                "CPU i\u015fi (milyar \u00e7evrim)": t.task.required_cpu_cycles / 1e9,
                "G\u00fcvenlik S": t.security_level,
                "Bant tahsisi (MHz)": t.bandwidth_hz / 1e6,
                "Bellek tahsisi (MB)": t.memory_mb,
            }
            for t in data.scenario.tasks
        ]
        st.dataframe(
            pd.DataFrame(records), hide_index=True, width="stretch", height=350
        )
    with right:
        st.markdown("**Mevcut girdi kimli\u011fi**")
        st.code(dataset_fingerprint(data), language=None, wrap_lines=True)
        st.caption(
            "SHA-256 ayn\u0131 girdiyi tan\u0131mlar; verinin ger\u00e7ek d\u00fcnyadan geldi\u011fini kan\u0131tlamaz."
        )
        st.download_button(
            "Girdileri indir",
            dataset_to_json(data),
            "scenario.json",
            "application/json",
            icon=":material/download:",
            width="stretch",
        )
        uploaded = st.file_uploader(
            "Kay\u0131tl\u0131 senaryo JSON", type="json", max_upload_size=8
        )
        if uploaded and st.button("Senaryoyu y\u00fckle", icon=":material/upload:"):
            try:
                parsed = dataset_from_json(uploaded.getvalue().decode("utf-8"))
                if len(parsed.scenario.tasks) > 140 or len(parsed.scenario.servers) > 9:
                    raise ValueError(
                        "GUI s\u0131n\u0131r\u0131: 140 g\u00f6rev, 9 sunucu."
                    )
                install_dataset(parsed, source="snapshot")
                st.rerun()
            except (ValueError, TypeError, UnicodeError) as exc:
                st.error(f"Girdi do\u011frulanamad\u0131: {exc}")
    a, b = st.columns(2)
    with a:
        st.altair_chart(
            charts.security_scores(records, data.scenario.security_threshold),
            width="stretch",
        )
    with b:
        st.markdown("**Sabit normalizasyon**")
        st.metric(
            "S\u00fcre referans\u0131 T_ref",
            number(data.normalization.latency_seconds, 4) + " s",
        )
        st.metric("Risk referans\u0131 R_ref", number(data.normalization.security_risk))
        st.caption(
            "Referanslar karardan ba\u011f\u0131ms\u0131z hesaplan\u0131r. Bir senaryodaki t\u00fcm y\u00f6ntemler ayn\u0131 \u00f6l\u00e7ekleri kullan\u0131r. Bunlar belgeli proje varsay\u0131mlar\u0131d\u0131r."
        )
    with st.expander("Kay\u0131tl\u0131 parametreler, birimler ve s\u00fcr\u00fcmler"):
        st.json(
            {
                "configuration": asdict(data.configuration),
                "generation_runtime": asdict(data.runtime),
            }
        )


def fuzzy_view(data):
    st.subheader("Uzman g\u00f6r\u00fc\u015f\u00fcnden g\u00fcvenlik riskine")
    index = st.selectbox(
        "G\u00f6rev",
        range(len(data.scenario.tasks)),
        format_func=lambda i: data.scenario.tasks[i].task.task_id,
        key=f"fuzzy_task_{st.session_state.epoch}",
    )
    raw = data.expert_assessments[index]
    config = data.configuration
    with st.form(f"fuzzy_form_{st.session_state.epoch}_{index}", border=False):
        edits = {}
        tabs = st.tabs(tuple(PERSPECTIVES.values()))
        for (name, label), tab in zip(PERSPECTIVES.items(), tabs, strict=True):
            with tab:
                frame = pd.DataFrame(
                    [
                        {
                            "Uzman": f"Uzman {i + 1}",
                            "Alt": getattr(a, name).low,
                            "En olas\u0131": getattr(a, name).modal,
                            "\u00dcst": getattr(a, name).high,
                        }
                        for i, a in enumerate(raw)
                    ]
                )
                edits[name] = st.data_editor(
                    frame,
                    hide_index=True,
                    disabled=["Uzman"],
                    width="stretch",
                    column_config={
                        c: st.column_config.NumberColumn(
                            min_value=0.0, max_value=1.0, step=0.01, format="%.4f"
                        )
                        for c in ("Alt", "En olas\u0131", "\u00dcst")
                    },
                    key=f"triangle_{st.session_state.epoch}_{index}_{name}",
                )
        st.markdown("**Uzman a\u011f\u0131rl\u0131klar\u0131 (%)**")
        try:
            ew = weighted_inputs(
                tuple(f"Uzman {i + 1}" for i in range(len(raw))),
                config.expert_weights,
                f"experts_{st.session_state.epoch}_{index}",
            )
            st.markdown("**Perspektif a\u011f\u0131rl\u0131klar\u0131 (%)**")
            pw = weighted_inputs(
                tuple(PERSPECTIVES.values()),
                tuple(asdict(config.security).values()),
                f"perspectives_{st.session_state.epoch}_{index}",
            )
            valid = True
        except ValueError as exc:
            st.error(str(exc))
            valid = False
        threshold = st.slider(
            "G\u00fcvenlik e\u015fi\u011fi",
            0.0,
            1.0,
            config.security_threshold,
            0.01,
            key=f"lab_threshold_{st.session_state.epoch}_{index}",
        )
        apply = st.form_submit_button(
            "Bulan\u0131k girdileri uygula",
            icon=":material/check:",
            type="primary",
            disabled=not valid,
        )
    if apply:
        try:
            assessments = tuple(
                SecurityPerspectives(
                    **{
                        name: TriangularFuzzyNumber(
                            *edits[name]
                            .iloc[i][["Alt", "En olas\u0131", "\u00dcst"]]
                            .astype(float)
                        )
                        for name in PERSPECTIVES
                    }
                )
                for i in range(len(raw))
            )
            install_dataset(
                update_assessment(
                    data,
                    index,
                    assessments,
                    expert_weights=ew,
                    perspective_config=FuzzySecurityConfig(*pw),
                    threshold=threshold,
                ),
                edited=True,
                source=st.session_state.get("input_source", "generated"),
            )
            st.rerun()
        except (TypeError, ValueError) as exc:
            st.error(f"Bulan\u0131k de\u011ferler ge\u00e7ersiz: {exc}")
    result = assess_security(
        raw,
        expert_weights=config.expert_weights,
        security_threshold=config.security_threshold,
        config=config.security,
    )
    a, b = st.columns(2)
    with a:
        perspective = st.selectbox(
            "Perspektif", tuple(PERSPECTIVES), format_func=PERSPECTIVES.get
        )
        st.altair_chart(
            charts.triangles(raw, result.aggregated_perspectives, perspective),
            width="stretch",
        )
        st.caption(
            "\u00dc\u00e7genler belirsiz uzman de\u011ferlendirmelerini temsil eder. \u00dcyelik derecesi sald\u0131r\u0131 olas\u0131l\u0131\u011f\u0131 de\u011fildir."
        )
    with b:
        st.metric("G\u00fcvenlik puan\u0131 S", f"{result.security_level:.6f}")
        st.metric("G\u00f6rev riski mu", f"{result.security_risk:.6f}")
        st.caption(
            f"E\u015fik: {config.security_threshold:.2f}. S e\u015fikten d\u00fc\u015f\u00fckse risk pozitiftir; e\u015fikte veya \u00fcst\u00fcnde s\u0131f\u0131rd\u0131r."
        )
        st.latex(r"q_k=\frac{a_k+4b_k+c_k}{6},\quad S=\sum_k\eta_kq_k")
        st.latex(
            r"\mu=\begin{cases}1-e^{-(\theta-S)}&S<\theta\\0&S\geq\theta\end{cases}"
        )
    st.markdown("**Hesap izi: Denklem 11\u201314**")
    table(
        [
            {
                "Perspektif": label,
                "Birle\u015fik alt": getattr(result.aggregated_perspectives, name).low,
                "Birle\u015fik en olas\u0131": getattr(
                    result.aggregated_perspectives, name
                ).modal,
                "Birle\u015fik \u00fcst": getattr(
                    result.aggregated_perspectives, name
                ).high,
                "D\u00f6n\u00fc\u015f\u00fcm q": getattr(result, name + "_score"),
                "A\u011f\u0131rl\u0131k eta": getattr(
                    config.security, name + "_weight"
                ),
            }
            for name, label in PERSPECTIVES.items()
        ]
    )
    st.caption(
        "Ortak uzman/perspektif a\u011f\u0131rl\u0131klar\u0131 ve e\u015fik t\u00fcm g\u00f6revlerin puan\u0131n\u0131 etkiler. Bir g\u00f6revin \u00fc\u00e7genleri yaln\u0131zca o g\u00f6revde de\u011fi\u015fir. Yeni normalizasyon hesaplan\u0131r ve eski arama sonu\u00e7lar\u0131 kald\u0131r\u0131l\u0131r."
    )
    curve = [
        {
            "S": i / 100,
            "Risk": calculate_security_risk(i / 100, config.security_threshold),
            "Seri": "Risk",
        }
        for i in range(101)
    ]
    st.altair_chart(
        charts.lines(
            curve,
            "S",
            "Risk",
            "Seri",
            x_title="G\u00fcvenlik puan\u0131 S",
            y_title="Model riski mu",
        ),
        width="stretch",
    )
    st.caption(
        "Bu model a\u011f\u0131rl\u0131kl\u0131 \u00fc\u00e7gensel fuzzy de\u011ferlendirmedir; ayr\u0131 Mamdani/Sugeno kural motoru de\u011fildir."
    )


def mamdani_view(data, run, settings):
    """Show the project's proposed uncertainty-aware decision layer live."""

    _, load, genetic, swarm, seed = settings
    st.subheader("Özgün katkı: belirsizlik-duyarlı Mamdani denetleyicisi")
    st.caption(
        "Makaledeki üçgensel uzman değerlendirmesi ve BOALBFS baseline olarak korunur. "
        "Bu ek katman, aynı güvenlik puanındaki iki görevin değerlendirme "
        "belirsizliği farklıysa aynı aktarım oranına izin vermemesini sağlar."
    )
    st.info(
        "Bu ekran makalenin yeniden üretimi değildir: projeye eklenen Type-1 "
        "Mamdani uzantısını gösterir. AND=min, kural birleştirme=max ve "
        "durulaştırma=centroid uygulanır."
    )

    index = st.selectbox(
        "İncelenen görev",
        range(len(data.scenario.tasks)),
        format_func=lambda i: data.scenario.tasks[i].task.task_id,
        key=f"mamdani_task_{st.session_state.epoch}",
    )
    policy = mamdani_policy_for_dataset(data)
    task_policy = policy[index]
    task = data.scenario.tasks[index]
    task_id = task.task.task_id

    a, b, c = st.columns(3)
    a.metric("Makale güvenlik puanı S", number(task_policy.security_level))
    b.metric("Değerlendirme belirsizliği U", number(task_policy.assessment_uncertainty))
    c.metric(
        "Veri kaynaklı izinli üst oran",
        f"%{100 * task_policy.allowed_offloading_ratio:.2f}",
    )
    st.caption(
        "U, uzmanlar ağırlıklandırıldıktan sonra üç perspektifteki üçgen "
        "genişliklerinin ortalamasıdır. Saldırı olasılığı veya uzmanlar arası "
        "istatistiksel anlaşmazlık olarak yorumlanmaz."
    )
    st.latex(
        r"U_i=\frac{1}{3}\sum_{k=1}^{3}(\overline{s}_{ik}-\underline{s}_{ik}),"
        r"\qquad 0\le x_i\le \bar{x}_i"
    )

    st.markdown("#### Canlı 'ne olurdu?' denetimi")
    left, right = st.columns(2)
    live_security = left.slider(
        "Güvenlik puanı S",
        0.0,
        1.0,
        float(task_policy.security_level),
        0.01,
        key=f"mamdani_security_{st.session_state.epoch}_{index}",
    )
    live_uncertainty = right.slider(
        "Belirsizlik U",
        0.0,
        1.0,
        float(task_policy.assessment_uncertainty),
        0.01,
        key=f"mamdani_uncertainty_{st.session_state.epoch}_{index}",
    )
    decision = evaluate_uncertainty_aware_offloading(live_security, live_uncertainty)
    st.caption(
        "Bu iki sürgü yalnız kural motorunu denemek içindir; senaryoyu veya "
        "optimizasyonda kullanılan görev sınırlarını değiştirmez. Gerçek görev "
        "girdisini değiştirmek için Bulanık Güvenlik ekranındaki formu uygula."
    )
    st.metric(
        "Canlı izinli en yüksek offloading oranı x̄",
        f"%{100 * decision.allowed_offloading_ratio:.2f}",
        help="Önerilen BOALBFS bu görev için yalnızca 0 ile bu üst sınır arasında arar.",
    )

    input_records = (
        [
            {
                "Değişken": "Güvenlik S",
                "Küme": {"low": "Düşük", "medium": "Orta", "high": "Yüksek"}[d.label],
                "Üyelik derecesi": d.value,
            }
            for d in decision.security_memberships
        ]
        + [
            {
                "Değişken": "Belirsizlik U",
                "Küme": {"low": "Düşük", "medium": "Orta", "high": "Yüksek"}[d.label],
                "Üyelik derecesi": d.value,
            }
            for d in decision.uncertainty_memberships
        ]
        + [
            {
                "Değişken": "Çıktı x̄",
                "Küme": {
                    "restricted": "Kısıtlı",
                    "low": "Düşük",
                    "medium": "Orta",
                    "high": "Yüksek",
                }[d.label],
                "Üyelik derecesi": d.value,
            }
            for d in decision.output_memberships
        ]
    )
    st.altair_chart(
        charts.bars(
            input_records,
            "Küme",
            "Üyelik derecesi",
            group="Değişken",
            y_title="Üyelik derecesi",
        ),
        width="stretch",
    )
    table(input_records)

    label = {
        "low": "Düşük",
        "medium": "Orta",
        "high": "Yüksek",
        "restricted": "Kısıtlı",
    }
    st.markdown("#### Çalışan Mamdani kuralları")
    table(
        [
            {
                "Eğer güvenlik": label[rule.security_label],
                "ve belirsizlik": label[rule.uncertainty_label],
                "ise izin": label[rule.output_label],
                "Kural gücü (min)": rule.strength,
            }
            for rule in decision.active_rules
        ]
    )
    with st.expander("Dokuz kuralın tamamı"):
        table(
            [
                {
                    "Güvenlik S / Belirsizlik U": label[security],
                    **{
                        label[uncertainty]: label[RULE_BASE[(security, uncertainty)]]
                        for uncertainty in ("low", "medium", "high")
                    },
                }
                for security in ("low", "medium", "high")
            ]
        )
        st.caption(
            "Üyelik fonksiyonları: girişlerde düşük=(0,0,0.5), orta=(0.25,0.5,0.75), "
            "yüksek=(0.5,1,1). Çıktı kümeleri kısıtlı/düşük/orta/yüksek olarak "
            "tanımlanır; sayısal centroid kod tarafından hesaplanır."
        )

    plan_task = next(
        item for item in run.evaluation.tasks if item.decision.task_id == task_id
    )
    plan_ratio = plan_task.decision.offloading_ratio
    st.markdown("#### Ekrandaki planla ilişki")
    p_left, p_right, p_last = st.columns(3)
    p_left.metric("Gösterilen plan", run.method)
    p_right.metric("Planın oranı", f"%{100 * plan_ratio:.2f}")
    p_last.metric(
        "Bu görevin veri kaynaklı cap'i",
        f"%{100 * task_policy.allowed_offloading_ratio:.2f}",
    )
    if plan_ratio <= task_policy.allowed_offloading_ratio + 1e-12:
        st.success("Gösterilen plan bu görev için Mamdani üst sınırına uyuyor.")
    else:
        st.warning(
            "Gösterilen plan baseline olabilir; bu nedenle Mamdani üst sınırını "
            "uygulamıyor. Aşağıdaki kontrollü karşılaştırma önerilen planı üretir."
        )

    if st.button(
        "Baseline ve önerilen Mamdani çözümünü çalıştır",
        icon=":material/play_arrow:",
        type="primary",
        key=f"run_mamdani_comparison_{st.session_state.epoch}",
    ):
        runs = []
        failures = []
        with st.status(
            "Aynı seed ve bütçeyle çözümler hesaplanıyor...", expanded=True
        ) as status:
            for method, runner in (
                (
                    "BOALBFS baseline",
                    lambda: run_method(
                        data,
                        "BOALBFS",
                        seed=seed,
                        genetic=genetic,
                        swarm=swarm,
                        objective=settings[0],
                        load=load,
                    ),
                ),
                (
                    "Önerilen Mamdani",
                    lambda: run_uncertainty_mamdani(
                        data,
                        seed=seed,
                        genetic=genetic,
                        swarm=swarm,
                        objective=settings[0],
                        load=load,
                    ),
                ),
            ):
                try:
                    st.write(method)
                    runs.append(runner())
                except (ValueError, TypeError, OverflowError) as exc:
                    failures.append(f"{method}: {exc}")
            status.update(
                label="Mamdani karşılaştırması tamamlandı",
                state="complete",
                expanded=False,
            )
        st.session_state.runs = runs
        st.session_state.run_failures = failures
        st.session_state.run_context = context_key(data, *settings)
        st.rerun()


def display_plan(data, run):
    tabs = st.tabs(
        (
            "G\u00f6rev kararlar\u0131",
            "Sunucu y\u00fckleri",
            "Puan\u0131n bile\u015fenleri",
        )
    )
    with tabs[0]:
        table(plan_rows(run.evaluation), height=320)
        st.caption(
            "Se\u00e7ili sunucuda oran 0 olsa bile rezervasyon vard\u0131r. Local ise sunucu se\u00e7ilmez ve oran 0'd\u0131r."
        )
    with tabs[1]:
        loads = [
            {"Sunucu": s.server_id, **asdict(s.load)} for s in run.evaluation.servers
        ]
        chart_data = [
            {"Sunucu": r["Sunucu"], "Kaynak": name, "Kullan\u0131m (%)": 100 * r[field]}
            for r in loads
            for field, name in (
                ("cpu_utilization", "CPU"),
                ("bandwidth_utilization", "Bant"),
                ("memory_utilization", "Bellek"),
            )
        ]
        st.altair_chart(
            charts.bars(
                chart_data,
                "Sunucu",
                "Kullan\u0131m (%)",
                group="Kaynak",
                y_title="Rezerve kaynak / kapasite (%)",
            ),
            width="stretch",
        )
        table(loads)
        st.caption(
            "Y\u00fck rezervasyonlar\u0131 g\u00f6nderim oran\u0131yla \u00e7arp\u0131lmaz; kapasite a\u015f\u0131m\u0131 kabul edilmez. Bo\u015f sunucular varyansa dahildir."
        )
    with tabs[2]:
        p = run.evaluation
        st.latex(r"F=w_T\frac{T}{T_{ref}}+w_R\frac{R}{R_{ref}}+w_L Var(\Gamma)")
        table(
            [
                {
                    "Bile\u015fen": name,
                    "A\u011f\u0131rl\u0131kl\u0131 katk\u0131": value,
                }
                for name, value in (
                    ("S\u00fcre", p.objective.latency_term),
                    ("Risk", p.objective.risk_term),
                    ("Y\u00fck", p.objective.load_term),
                )
            ]
        )
        st.json(asdict(p.objective))
        st.caption(
            "F bir ba\u015far\u0131 y\u00fczdesi de\u011fildir. D\u00fc\u015f\u00fck F tercih edilir; tek bir bile\u015fenin de iyile\u015fti\u011fini garanti etmez."
        )


def task_view(data, run, objective, load):
    st.subheader("Kararlar, rezervasyonlar ve iletim")
    display_plan(data, run)
    index = st.selectbox(
        "\u0130ncelenen g\u00f6rev",
        range(len(data.scenario.tasks)),
        format_func=lambda i: data.scenario.tasks[i].task.task_id,
    )
    task = data.scenario.tasks[index]
    server = st.selectbox(
        "\u0130ncelenen sunucu",
        data.scenario.servers,
        format_func=lambda s: s.server.server_id,
    )
    link = next(
        l
        for l in data.scenario.links
        if l.task_id == task.task.task_id and l.server_id == server.server.server_id
    )
    a, b, c = st.columns(3)
    a.metric("Kablosuz h\u0131z", f"{link.rate_bits_per_second / 1e6:.3f} Mbps")
    b.metric("Veri boyutu", f"{task.task.data_size_mb:.3f} MB")
    c.metric(
        "CPU i\u015fi", f"{task.task.required_cpu_cycles / 1e9:.3f} milyar \u00e7evrim"
    )
    percent = st.slider("Tek g\u00f6rev g\u00f6nderim oran\u0131 (%)", 0, 100, 40, 5)
    inspected = calculate_task_latency(
        task.task,
        offloading_ratio=percent / 100,
        local_cpu_cycles_per_second=task.local_cpu_cycles_per_second,
        edge_cpu_cycles_per_second=server.allocated_cpu_cycles_per_second,
        transmission_rate_bits_per_second=link.rate_bits_per_second,
    )
    for column, label, value in zip(
        st.columns(4),
        ("Cihaz (s)", "\u0130letim (s)", "Sunucu (s)", "Toplam (s)"),
        (
            inspected.local_seconds,
            inspected.transmission_seconds,
            inspected.edge_seconds,
            inspected.total_seconds,
        ),
        strict=True,
    ):
        column.metric(label, number(value, 4))
    st.caption(
        "Tek g\u00f6rev incelemesi; yukar\u0131daki tam plan de\u011fi\u015fmez."
    )
    ratios = []
    risk = calculate_security_risk(
        task.security_level, data.scenario.security_threshold
    )
    for i in range(21):
        ratio = i / 20
        t = calculate_task_latency(
            task.task,
            offloading_ratio=ratio,
            local_cpu_cycles_per_second=task.local_cpu_cycles_per_second,
            edge_cpu_cycles_per_second=server.allocated_cpu_cycles_per_second,
            transmission_rate_bits_per_second=link.rate_bits_per_second,
        )
        ratios.append(
            {
                "Oran (%)": 100 * ratio,
                "S\u00fcre (s)": t.total_seconds,
                "Risk": calculate_offloading_risk(risk, ratio, 1),
                "Seri": "Se\u00e7ili sunucu",
            }
        )
    a, b = st.columns(2)
    with a:
        st.altair_chart(
            charts.lines(
                ratios,
                "Oran (%)",
                "S\u00fcre (s)",
                "Seri",
                x_title="G\u00f6nderim oran\u0131 (%)",
                y_title="Tek g\u00f6revin toplam s\u00fcresi (s)",
            ),
            width="stretch",
        )
    with b:
        st.altair_chart(
            charts.lines(
                ratios,
                "Oran (%)",
                "Risk",
                "Seri",
                x_title="G\u00f6nderim oran\u0131 (%)",
                y_title="Tek g\u00f6revin g\u00f6nderim riski",
            ),
            width="stretch",
        )
    st.caption(
        "Bu e\u011friler tek g\u00f6rev / sabit sunucu i\u00e7indir. Mevcut modelde cihaz, iletim ve sunucu s\u00fcreleri toplan\u0131r; paralel bitirme zaman\u0131 hesaplanmaz."
    )
    with st.expander("Kablosuz ba\u011flant\u0131 girdileri"):
        st.latex(r"r=b\log_2\left(1+\frac{p g^2}{b\zeta}\right)")
        table(
            [
                {
                    "G\u00f6rev": l.task_id,
                    "Sunucu": l.server_id,
                    "H\u0131z (Mbps)": l.rate_bits_per_second / 1e6,
                    "Kanal kazanc\u0131": g,
                }
                for l, g in zip(data.scenario.links, data.channel_gains, strict=True)
            ]
        )
    with st.expander("Elle plan: sunucu ve g\u00f6nderim oranlar\u0131"):
        frame = pd.DataFrame(
            [
                {k: r[k] for k in ("task_id", "server", "ratio_percent")}
                for r in plan_rows(run.evaluation)
            ]
        )
        edited = st.data_editor(
            frame,
            hide_index=True,
            width="stretch",
            disabled=["task_id"],
            column_config={
                "task_id": st.column_config.TextColumn("G\u00f6rev"),
                "server": st.column_config.SelectboxColumn(
                    "Sunucu",
                    options=["Local"]
                    + [s.server.server_id for s in data.scenario.servers],
                    required=True,
                ),
                "ratio_percent": st.column_config.NumberColumn(
                    "G\u00f6nderim (%)", min_value=0.0, max_value=100.0, step=5.0
                ),
            },
            key=f"manual_{st.session_state.epoch}_{run.method}",
        )
        if st.button("Elle plan\u0131 de\u011ferlendir", icon=":material/calculate:"):
            try:
                manual = evaluate_manual(
                    data, edited.to_dict("records"), objective=objective, load=load
                )
                st.session_state.manual = (
                    context_key(data, *st.session_state.settings),
                    json.dumps(edited.to_dict("records")),
                    manual,
                )
            except (ValueError, TypeError) as exc:
                st.error(f"Plan kabul edilmedi: {exc}")
        saved = st.session_state.get("manual")
        if saved and saved[:2] == (
            context_key(data, *st.session_state.settings),
            json.dumps(edited.to_dict("records")),
        ):
            table([summary_row(saved[2])])
            display_plan(data, saved[2])
            _, _, genetic, swarm, seed = st.session_state.settings
            st.download_button(
                "Elle plan + girdiler JSON",
                export_run(
                    data,
                    saved[2],
                    objective=objective,
                    load=load,
                    genetic=genetic,
                    swarm=swarm,
                    seed=seed,
                    edits=st.session_state.edited,
                    source=st.session_state.get("input_source", "generated"),
                ),
                "manual_plan.json",
                "application/json",
                icon=":material/download:",
            )


def compare_view(data, settings):
    objective, load, genetic, swarm, seed = settings
    st.subheader("Ayn\u0131 girdilerle \u00e7\u00f6z\u00fcm arama")
    chosen = st.multiselect(
        "Y\u00f6ntemler",
        COMPARISON_METHODS,
        default=["Local", "BOALBFS", UNCERTAINTY_MAMDANI_METHOD],
        format_func=METHOD_LABELS.get,
    )
    a, b, c = st.columns(3)
    a.metric("GA aday b\u00fct\u00e7esi", genetic.evaluation_budget)
    b.metric("SA-PSO / aday en fazla", swarm.evaluation_budget)
    c.metric(
        "Kesin kontrol aday\u0131",
        f"{(2 * len(data.scenario.servers) + 1) ** len(data.scenario.tasks):.3g}",
    )
    st.caption(
        "Analitik oran sabit konumda kesindir; GA'n\u0131n sunucu se\u00e7imi global optimum garantisi vermez. E\u015fit GA b\u00fct\u00e7esi e\u015fit hesap miktar\u0131 de\u011fildir."
    )
    if st.button(
        "Se\u00e7ili \u00e7\u00f6z\u00fcmleri \u00e7al\u0131\u015ft\u0131r",
        icon=":material/play_arrow:",
        type="primary",
        disabled=not chosen,
    ):
        runs = []
        failures = []
        with st.status(
            "\u00c7\u00f6z\u00fcmler hesaplan\u0131yor...", expanded=True
        ) as status:
            for method in chosen:
                st.write(METHOD_LABELS[method])
                try:
                    if method == UNCERTAINTY_MAMDANI_METHOD:
                        runs.append(
                            run_uncertainty_mamdani(
                                data,
                                seed=seed,
                                genetic=genetic,
                                swarm=swarm,
                                objective=objective,
                                load=load,
                            )
                        )
                    else:
                        runs.append(
                            run_method(
                                data,
                                method,
                                seed=seed,
                                genetic=genetic,
                                swarm=swarm,
                                objective=objective,
                                load=load,
                            )
                        )
                except (ValueError, TypeError, OverflowError) as exc:
                    failures.append(f"{method}: {exc}")
            status.update(
                label="Kar\u015f\u0131la\u015ft\u0131rma tamamland\u0131",
                state="complete",
                expanded=False,
            )
        st.session_state.runs = runs
        st.session_state.run_failures = failures
        st.session_state.run_context = context_key(data, *settings)
        st.rerun()
    runs = current_runs(data, settings)
    if st.session_state.get("run_context") == context_key(data, *settings):
        for failure in st.session_state.get("run_failures", []):
            st.warning(failure)
    if not runs:
        st.info("Bu girdi ve ayarlarda kay\u0131tl\u0131 arama sonucu yok.")
        return
    records = [summary_row(r) for r in runs]
    table(records)
    result_charts(records)
    histories = [
        {"Nesil": i, "En iyi F": v, "Y\u00f6ntem": r.method}
        for r in runs
        for i, v in enumerate(r.history)
    ]
    if histories:
        st.altair_chart(
            charts.lines(
                histories,
                "Nesil",
                "En iyi F",
                "Y\u00f6ntem",
                x_title="GA nesli (0 = ba\u015flang\u0131\u00e7)",
                y_title="En iyi bulunan F",
            ),
            width="stretch",
        )
    st.caption(
        "Arama s\u00fcresi g\u00f6revlerin toplam s\u00fcresi de\u011fildir. Tek senaryodaki bu \u00e7al\u0131\u015ft\u0131rma, \u00e7oklu-seed deney ortalamas\u0131 veya makalenin sonucu olarak sunulmaz."
    )


def current_runs(data, settings):
    return (
        st.session_state.runs
        if st.session_state.get("run_context") == context_key(data, *settings)
        else []
    )


def result_charts(records, *, aggregate=False):
    st.caption(
        "Grafik rehberi: F, süre, risk ve yük varyansında düşük değer tercih edilir. "
        "Arama maliyeti yalnızca algoritmanın çözüm arama süresidir."
    )
    results, cost = st.tabs(("S\u00fcre, risk ve denge", "Arama maliyeti"))
    with results:
        specs = (
            ("objective", "Ama\u00e7 F (d\u00fc\u015f\u00fck daha iyi)"),
            ("latency_seconds", "G\u00f6rev s\u00fcreleri toplam\u0131 (s)"),
            ("model_risk", "Toplam model riski"),
            ("load_variance", "Sunucu y\u00fck varyans\u0131"),
        )
        for start in (0, 2):
            for column, (field, title) in zip(
                st.columns(2), specs[start : start + 2], strict=True
            ):
                with column:
                    st.altair_chart(
                        charts.bars(
                            records,
                            "method",
                            field,
                            y_title=("Ortalama / " if aggregate else "") + title,
                        ),
                        width="stretch",
                    )
    with cost:
        st.altair_chart(
            charts.bars(
                records,
                "method",
                "search_seconds",
                y_title="Karar arama s\u00fcresi (s, log)",
                log=True,
            ),
            width="stretch",
        )
        st.caption(
            "Bu s\u00fcre algoritman\u0131n karar\u0131 aramas\u0131d\u0131r; g\u00f6revlerin hesaplama s\u00fcresi de\u011fildir. Donan\u0131m ve arama b\u00fct\u00e7esine ba\u011fl\u0131d\u0131r."
        )


def interface_guide(view):
    """Describe the selected dashboard view."""

    guides = {
        "Senaryo": "Seed, görev/sunucu sayısı ve model parametreleri burada belirlenir. Aynı seed aynı sentetik girdileri üretir.",
        "Bulanık Güvenlik": "Üçgen uzman değerlendirmeleri birleştirilir; güvenlik puanı ve model riski hesaplanır. Bu ekran Mamdani kural motorundan ayrıdır.",
        "Görev ve Sunucular": "Görevlerin veri, CPU, bağlantı ve sunucu yükü ayrıntıları incelenir.",
        "Çözüm Karşılaştırması": "Local, Edge, BOALBFS, Analytical ve küçük senaryoda Exact aynı senaryoda karşılaştırılır. F düşük olduğunda daha iyidir.",
        "Deney Kayıtları": "Çoklu-seed deneyleri manifest, CSV ve checksum ile kaydedilir; policy deneyinde baseline ve Mamdani cap karşılaştırılır.",
        "Mamdani Katkısı": "Güvenlik S ve belirsizlik U, görev bazlı offloading cap üretir; aktif kurallar ve cap'in plana etkisi gösterilir.",
        "Projeyi Anla": "Problemi, makaledeki yöntemi, bizim katkımızı ve ayarların neyi değiştirdiğini buradan öğren.",
    }
    with st.container(border=True):
        st.markdown(f"**{view} ekranı nasıl okunur?**")
        st.caption(guides[view])


def learning_view(data):
    """Explain inputs, policy decisions, and modeled latency."""

    st.subheader("Önce büyük resmi anlayalım")
    st.markdown(
        "Bir fabrika cihazının hesaplama işi var. İşin tamamını cihazda yapabilir "
        "veya bir bölümünü yakındaki sunucuya gönderebilir. Sunucu daha hızlı "
        "hesaplasa bile veriyi göndermek zaman alır. **Ne kadarını, hangi "
        "sunucuya göndermek uygun?** Programımız bu kararı bir model içinde arar."
    )
    st.markdown(
        "**Makaledeki yöntem (baseline):** uzmanların üçgensel değerlendirmelerinden "
        "güvenlik puanı S ve model riski hesaplanır. GA konumu, SA-PSO gönderim "
        "oranını arar. Süre, risk ve sunucu yük farkı F puanında birleştirilir.\n\n"
        "**Bizim ana katkımız:** S'nin yanında değerlendirme üçgenlerinin "
        "ortalama genişliği U da kullanılır. Dokuz Mamdani kuralı, gönderilebilecek "
        "en yüksek oranı belirler. Örneğin üst sınır %30 ise optimizer %0–30 "
        "arasında arar; %30 göndermek zorunda değildir.\n\n"
        "**Diğer çalışma:** Analytical, sabit sunucu seçimindeki oranı modelin "
        "doğrusal yapısından hesaplar. Bütün sunucu atamalarını en iyi şekilde "
        "bulduğu anlamına gelmez. GUI ise bu hesapları görüp denememizi sağlar."
    )
    st.info(
        "Düşük F, bu modelin tercihlerine göre daha iyi demektir. Başarı yüzdesi "
        "veya gerçek saldırı olasılığı değildir. Daha az göndermek model riskini "
        "azaltırken işi cihazda tutup gecikmeyi artırabilir."
    )
    st.markdown("#### Aynı güvenlik puanı, farklı değerlendirme genişliği")
    examples = []
    for triangle, width in (("(0.7, 0.7, 0.7)", 0.0), ("(0.4, 0.7, 1.0)", 0.6)):
        cap = evaluate_uncertainty_aware_offloading(0.7, width).allowed_offloading_ratio
        examples.append(
            {
                "Üç perspektifte aynı üçgen": triangle,
                "Güvenlik S": 0.7,
                "Genişlik U": width,
                "İzinli üst oran (%)": 100 * cap,
            }
        )
    table(examples)
    st.caption(
        "Bunlar açıklama örnekleridir. U, uzmanlar arası anlaşmazlığı ölçmez: "
        "iki uzman ayrı ama kesin puan verse bile her üçgenin genişliği sıfır olabilir. "
        "Kurallar ve üyelik şekilleri proje tercihidir; gerçek güvenlik garantisi değildir."
    )
    st.markdown("#### Ayarı değiştirince ne değişir?")
    table(
        [
            {
                "Ayar": "Veri seed / görev sayısı",
                "Etkisi": "Yeni sentetik girdi üretir; Senaryoyu oluştur ile uygulanır. Seed tek başına veri değildir.",
            },
            {
                "Ayar": "Sunucu sayısı",
                "Etkisi": "Seçenekleri ve toplam kapasiteyi değiştirir. Aynı seed ile link girdileri de değişebilir.",
            },
            {
                "Ayar": "Güvenlik eşiği",
                "Etkisi": "S eşikten düşükse risk doğar. Eşik artarsa sabit görevde risk azalmaz; otomatik olarak S değişmez.",
            },
            {
                "Ayar": "Süre / Risk / Yük ağırlıkları",
                "Etkisi": "Neye önem verildiğini değiştirir. Ayarları uygula ve çözümleri tekrar çalıştır.",
            },
            {
                "Ayar": "Cihaz CPU",
                "Etkisi": "Sabit görev için yerel hesaplama süresini değiştirir.",
            },
            {
                "Ayar": "Görev CPU tahsisi / sunucu kapasitesi",
                "Etkisi": "Tahsis edge hesaplama hızını, toplam kapasite kaç rezervasyonun sığacağını belirler.",
            },
            {
                "Ayar": "Güç / kanal / gürültü",
                "Etkisi": "Kablosuz hızı ve iletim süresini değiştirir. Envanter Mbps alanı bu hızı belirlemez.",
            },
            {
                "Ayar": "Arama seed / GA / SA-PSO bütçesi",
                "Etkisi": "Aramayı değiştirir; veri aynı kalır. Büyük bütçe daha çok hesap demektir, optimum garantisi değildir.",
            },
            {
                "Ayar": "Tek görev gönderim sürgüsü",
                "Etkisi": "Yalnız seçilen görevi inceler; ekrandaki tam planı değiştirmez.",
            },
            {
                "Ayar": "Mamdani S / U sürgüleri",
                "Etkisi": "Yalnız kural denemesidir; optimize edilen görev girdilerini değiştirmez.",
            },
            {
                "Ayar": "Deadline / envanter hızı",
                "Etkisi": "Mevcut modelde bilgi alanıdır; deadline kısıtı uygulanmaz.",
            },
        ]
    )
    st.markdown("#### Şimdi seçili veride tek bir görevin hesabını gör")
    task = data.scenario.tasks[0]
    server = data.scenario.servers[0]
    link = next(
        link
        for link in data.scenario.links
        if link.task_id == task.task.task_id
        and link.server_id == server.server.server_id
    )
    rows = []
    for ratio in (0.0, 0.5, 1.0):
        latency = calculate_task_latency(
            task.task,
            offloading_ratio=ratio,
            local_cpu_cycles_per_second=task.local_cpu_cycles_per_second,
            edge_cpu_cycles_per_second=server.allocated_cpu_cycles_per_second,
            transmission_rate_bits_per_second=link.rate_bits_per_second,
        )
        rows.append(
            {
                "Gönderim (%)": 100 * ratio,
                "Cihaz (s)": latency.local_seconds,
                "İletim (s)": latency.transmission_seconds,
                "Sunucu (s)": latency.edge_seconds,
                "Toplam (s)": latency.total_seconds,
            }
        )
    table(rows)
    st.caption(
        f"{task.task.task_id} / {server.server.server_id}: gerçek seçili girdilerin "
        "tek görev hesabıdır; çok görevli uygunluk veya optimum çözüm iddiası yoktur. "
        "Üç süre toplanır. Üstteki özet kartları ise gösterilen tam plana aittir."
    )
    st.markdown("#### Kodları hangi sırayla okumalıyım?")
    st.markdown(
        "1. `models.py` ve `config.py`: görev/sunucu verileri ve ayarlar.\n"
        "2. `fuzzy_security.py`: uzman üçgeni → S → risk.\n"
        "3. `latency.py`, `load_balance.py`, `objective.py`: süre, yük ve F.\n"
        "4. `evaluation.py`: verilen tam planın doğru ve uygun olup olmadığını hesaplar.\n"
        "5. `optimizers/genetic.py`, `sapso.py`: farklı planları deneyip en iyisini arar.\n"
        "6. `fuzzy_controller.py`: bizim S/U → üst oran katkımız.\n"
        "7. `gui/services.py`, `dashboard.py`: bu hesapları ekrana bağlar.\n\n"
        "İlk deneme: 3 görev, 2 sunucu, seed 42 ile başla; önce Görev ve Sunucular, "
        "sonra Bulanık Güvenlik, Çözüm Karşılaştırması ve Mamdani Katkısı ekranlarına geç."
    )


def experiments_view(data, settings):
    st.subheader("Kendini tekrar eden deneyler ve kay\u0131tl\u0131 kan\u0131t")
    with st.expander("Yeni \u00e7oklu-seed deneyi"):
        from experiments.baseline.mode_comparison import run_experiment as run_modes
        from experiments.proposed.ratio_comparison import run_experiment as run_ratios

        kind = st.selectbox(
            "Protokol",
            (
                "Tam GA kar\u015f\u0131la\u015ft\u0131rmas\u0131",
                "Sabit konum oranlar\u0131",
                "Mamdani oran politikas\u0131",
                "Mamdani GA sensitivity",
                "Local / Edge / Local-Edge",
            ),
        )
        seeds = st.multiselect(
            "Veri seed'leri", (7, 21, 42, 84, 2026), default=[7, 21, 42, 84, 2026]
        )
        search_seeds = st.multiselect("Arama seed'leri", (0, 1, 2), default=[0, 1, 2])
        st.caption(
            "Bu protokoller yeni sentetik veri \u00fcretir, tek g\u00f6revdeki elle d\u00fczenlemeleri ta\u015f\u0131maz. Ama\u00e7/kaynak a\u011f\u0131rl\u0131klar\u0131 protokolde e\u015fittir; mevcut arama b\u00fct\u00e7eleri kullan\u0131l\u0131r. \u00c7\u0131kt\u0131lar yerel results/ alt\u0131ndad\u0131r."
        )
        if st.button(
            "Deneyi \u00e7al\u0131\u015ft\u0131r ve kaydet",
            icon=":material/science:",
            disabled=not seeds or not search_seeds,
        ):
            try:
                _, _, genetic, swarm, _ = settings
                if (
                    genetic.evaluation_budget
                    * swarm.evaluation_budget
                    * len(seeds)
                    * len(search_seeds)
                    * (3 if kind == "Mamdani GA sensitivity" else 1)
                    > 250000
                ):
                    raise ValueError(
                        "GUI deney b\u00fct\u00e7esi a\u015f\u0131ld\u0131; CLI ile daha b\u00fcy\u00fck deney yap\u0131labilir."
                    )
                output = (
                    ROOT
                    / "results"
                    / (
                        "gui_experiment_"
                        + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
                    )
                )
                with st.spinner(
                    "\u00c7oklu-seed deneyi \u00e7al\u0131\u015f\u0131yor; tamamlanmas\u0131 birka\u00e7 dakika s\u00fcrebilir..."
                ):
                    kwargs = {
                        "data_seeds": tuple(seeds),
                        "optimizer_seeds": tuple(search_seeds),
                        "scenario_config": data.configuration,
                        "swarm_config": swarm,
                    }
                    if kind == "Local / Edge / Local-Edge":
                        run_modes(output, genetic_config=genetic, **kwargs)
                    elif kind == "Mamdani GA sensitivity":
                        from experiments.proposed.uncertainty_mamdani_comparison import (
                            run_experiment as run_mamdani_experiment,
                        )

                        run_mamdani_experiment(
                            output,
                            data_seeds=tuple(seeds),
                            optimizer_seeds=tuple(search_seeds),
                            scenario_config=data.configuration,
                            genetic_config=genetic,
                            swarm_config=swarm,
                            link_rate_factors=(0.5, 1.0, 2.0),
                        )
                    else:
                        run_ratios(
                            output,
                            genetic_config=genetic,
                            scope=(
                                "pipeline"
                                if kind.startswith("Tam")
                                else "policy"
                                if kind == "Mamdani oran politikas\u0131"
                                else "fixed"
                            ),
                            **kwargs,
                        )
                st.session_state.last_bundle = output.name
                st.rerun()
            except (ValueError, TypeError, OSError) as exc:
                st.error(f"Deney tamamlanamad\u0131: {exc}")
    folders = list_bundles(ROOT)
    if not folders:
        st.info("Yerelde kay\u0131tl\u0131 deney paketi yok.")
        return
    preferred = next(
        (
            i
            for i, p in enumerate(folders)
            if p.name
            == st.session_state.get("last_bundle", "proposed_pipelines_v1_checked")
        ),
        0,
    )
    folder = st.selectbox(
        "Deney paketi", folders, index=preferred, format_func=lambda p: p.name
    )
    try:
        manifest, rows = load_bundle(folder)
    except (ValueError, OSError, TypeError) as exc:
        st.error(f"Deney kan\u0131t\u0131 do\u011frulanamad\u0131: {exc}")
        return
    st.success(
        f"Tamamlanm\u0131\u015f paket: {len(rows)} kay\u0131t. \u00c7\u0131kt\u0131 checksum'lar\u0131 do\u011fruland\u0131."
    )
    method_field = "method" if "method" in rows[0] else "mode"
    valid = [r for r in rows if r.get("objective")]
    if not valid:
        st.warning("Bu pakette uygulanabilir karar yok.")
        return
    stats = pd.DataFrame(bundle_statistics(rows))
    if "link_rate_factor" in stats.columns:
        selected_factor = st.selectbox(
            "İncelenen bağlantı hızı koşulu",
            sorted(stats["link_rate_factor"].unique()),
            format_func=lambda value: f"{value:g}x temel bağlantı hızı",
        )
        stats = stats.loc[stats["link_rate_factor"] == selected_factor]
        valid = [r for r in valid if float(r["link_rate_factor"]) == selected_factor]
        st.caption(
            "Tablo ve aşağıdaki karşılaştırma yalnız seçilen hız koşulunu gösterir. "
            "Hız değiştiğinde normalizasyon da değişebilir; farklı koşulların F "
            "değerlerinden tek başına performans artışı yüzdesi çıkarma."
        )
    st.dataframe(stats, hide_index=True, width="stretch")
    if manifest.get("experiment") == "uncertainty-aware-mamdani-v1":
        sensitivity_plot = folder / "comparison.png"
        if sensitivity_plot.is_file():
            st.markdown("#### Mamdani sensitivity sonucu")
            st.image(
                sensitivity_plot,
                caption=(
                    "Kablosuz link hızı değişirken baseline ve Mamdani "
                    "BOALBFS sonuçlarının karşılaştırması."
                ),
                width="stretch",
            )
    pareto = folder / "risk_latency_pareto.png"
    if pareto.is_file() and manifest.get("experiment") == "mamdani-policy-ratios-v1":
        st.markdown("#### Risk-gecikme dengesi")
        st.image(
            pareto,
            caption=(
                "Mamdani cap uygulandığında risk azalırken gecikmenin nasıl "
                "değiştiği. Sol-alt bölge daha düşük risk ve gecikmeyi gösterir."
            ),
            width="stretch",
        )
        policy_columns = [
            column
            for column in (
                "uncertainty_weighted_exposure",
                "mean_offloading_ratio",
                "mean_allowed_cap",
                "offloaded_tasks",
            )
            if column in rows[0]
        ]
        if policy_columns:
            st.markdown("#### Mamdani politika metrikleri")
            st.dataframe(
                pd.DataFrame(rows)[["method", *policy_columns]],
                hide_index=True,
                width="stretch",
            )
    plot_records = stats.rename(
        columns={
            "F": "objective",
            "Arama_s": "search_seconds",
            "Gorev_s": "latency_seconds",
            "Risk": "model_risk",
            "Yuk": "load_variance",
        }
    ).to_dict("records")
    result_charts(plot_records, aggregate=True)
    st.caption(
        "\u00d6nce her veride arama tekrarlar\u0131 ortalan\u0131r, sonra ba\u011f\u0131ms\u0131z veri ortalamalar\u0131. SD g\u00fcven aral\u0131\u011f\u0131 veya anlaml\u0131l\u0131k testi de\u011fildir. F iyile\u015firken model riski artabilir."
    )
    row_index = st.selectbox(
        "Kay\u0131tl\u0131 karar",
        range(len(valid)),
        format_func=lambda i: (
            f"{valid[i][method_field]} | veri {valid[i]['data_seed']} | arama {valid[i]['optimizer_seed']}"
        ),
    )
    if st.button("Bu girdiyi ve karar\u0131 incele", icon=":material/open_in_new:"):
        try:
            loaded, run = restore_bundle_run(folder, valid[row_index], manifest)
            if run.link_rate_factor != 1.0:
                st.session_state.bundle_preview = (str(folder), row_index, loaded, run)
            else:
                open_bundle_in_workspace(
                    loaded, run, manifest, valid[row_index], settings
                )
        except (ValueError, TypeError, OSError, KeyError) as exc:
            st.error(f"Karar tekrar hesaplanamadı: {exc}")
    preview = st.session_state.get("bundle_preview")
    if preview and preview[:2] == (str(folder), row_index):
        loaded, saved_run = preview[2:]
        if saved_run.link_rate_factor == float(
            valid[row_index].get("link_rate_factor", 1)
        ):
            st.markdown("#### Kaydın doğrulanmış planı")
            st.info(
                f"Bu kayıt {saved_run.link_rate_factor:g}x bağlantı hızıyla yeniden "
                "hesaplandı. Ayrıntılar kayıt üzerinde gösteriliyor; çalışma "
                "senaryosundaki temel kablosuz girdiler değiştirilmedi."
            )
            st.write(
                f"Yöntem: {saved_run.method} | "
                f"F: {number(saved_run.evaluation.objective.value)} | "
                f"Toplam süre: {number(saved_run.evaluation.total_latency_seconds)} s | "
                f"Model riski: {number(saved_run.evaluation.total_security_risk)}"
            )
            display_plan(loaded, saved_run)
    with st.expander("Ham kayıtlar, ayarlar ve sınırlar"):
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.json(manifest)
        st.download_button(
            "Deney CSV indir",
            (folder / "runs.csv").read_bytes(),
            folder.name + "_runs.csv",
            "text/csv",
            icon=":material/download:",
        )


def open_bundle_in_workspace(loaded, run, manifest, row, settings):
    """Install only an unscaled snapshot as editable working inputs."""
    if run.link_rate_factor != 1.0:
        raise ValueError("scaled conditions must be inspected separately")
    objective, load = bundle_configuration(manifest)
    genetic = (
        GeneticSearchConfig(**manifest["genetic_config"])
        if "genetic_config" in manifest
        else settings[2]
    )
    swarm = SwarmSearchConfig(**manifest["swarm_config"])
    if (
        genetic.population_size > 30
        or genetic.generations > 30
        or swarm.particle_count > 24
        or swarm.iterations > 60
    ):
        raise ValueError(
            "Paketin arama ayarlar\u0131 GUI s\u0131n\u0131r\u0131n\u0131 a\u015f\u0131yor; mevcut CLI ile incelenebilir."
        )
    install_dataset(loaded, source="experiment")
    st.session_state.settings = (
        objective,
        load,
        genetic,
        swarm,
        int(row["optimizer_seed"]),
    )
    st.session_state.runs = [run]
    st.session_state.run_context = context_key(loaded, *st.session_state.settings)
    st.session_state.next_view = VIEWS[2]
    st.rerun()


def main():
    st.set_page_config(
        page_title="Fuzzy Security Lab", page_icon=":material/hub:", layout="wide"
    )
    st.html("""<style>
    h1 {font-size:2.1rem !important;letter-spacing:-0.02em !important;color:#173b38 !important;}
    h2 {font-size:1.4rem !important;letter-spacing:-0.01em !important;color:#176b5a !important;}
    h3 {font-size:1.12rem !important;letter-spacing:0 !important;color:#31534f !important;}
    .stApp {background:#eef5f3;}
    [data-testid='stAppViewContainer'] {background:linear-gradient(135deg,#eef5f3 0%,#f7faf9 52%,#e9f2f0 100%);}
    [data-testid='stHeader'] {background:rgba(238,245,243,0.9);}
    .stMainBlockContainer {max-width:1500px;padding-top:4rem;padding-bottom:3rem;container-type:inline-size;background:rgba(255,255,255,0.82);border-left:1px solid #dceae6;border-right:1px solid #dceae6;box-shadow:0 0 28px rgba(42,91,80,0.06);}
    [data-testid='stMetricValue'] {font-size:1.65rem;color:#176b5a;}
    [data-testid='stMetric'] {border:1px solid #d6e8e3;border-top:4px solid #2c9b7b;border-radius:10px;background:linear-gradient(135deg,#ffffff,#f2faf7);padding:0.75rem 0.9rem;}
    [data-testid='stMetricLabel'] {color:#41615c;}
    [data-testid='stExpander'] {border-color:#cfe2de;border-radius:10px;}
    [data-testid='stAlert'] {border-radius:10px;}
    button {border-radius:8px !important;letter-spacing:0 !important;}
    [data-testid='stSidebar'] {background:linear-gradient(180deg,#eef8f5 0%,#f8fbfa 48%,#ffffff 100%);}
    [data-testid='stSidebar'] h1,[data-testid='stSidebar'] h2,[data-testid='stSidebar'] h3 {color:#176b5a !important;}
    [data-testid='stMarkdownContainer'] code {color:#8a4d16;background:#fff4df;padding:0.1rem 0.3rem;border-radius:4px;}
    .st-key-summary_metrics [data-testid='stMetricLabel'] {min-height:2.6em;align-items:flex-start;}
    .st-key-summary_metrics [data-testid='stMetricLabel'] p {white-space:normal;overflow:visible;text-overflow:clip;}
    @container(max-width:760px){
      .st-key-summary_metrics [data-testid='stHorizontalBlock'] {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));}
      .st-key-summary_metrics [data-testid='stColumn'] {width:100% !important;min-width:0 !important;}
    }
    @container(max-width:320px){.st-key-summary_metrics [data-testid='stHorizontalBlock'] {grid-template-columns:minmax(0,1fr);}}
    @media(max-width:700px){.stMainBlockContainer{padding:4rem 1rem 3rem;}}
    </style>""")
    if "dataset" not in st.session_state:
        st.session_state.dataset = generate_synthetic_dataset(
            replace(SyntheticScenarioConfig(), experiment=ExperimentConfig(42, 3, 2))
        )
        st.session_state.settings = (
            ObjectiveConfig(),
            LoadBalanceConfig(),
            GeneticSearchConfig(population_size=12, generations=8),
            SwarmSearchConfig(iterations=15),
            0,
        )
        st.session_state.runs = []
        st.session_state.epoch = 0
        st.session_state.edited = False
        st.session_state.input_source = "generated"
        st.session_state.view = VIEWS[-1]
    if "input_source" not in st.session_state:
        st.session_state.input_source = "generated"
    if "next_view" in st.session_state:
        st.session_state.view = st.session_state.pop("next_view")
    view = sidebar()
    data = st.session_state.dataset
    settings = st.session_state.settings
    objective, load, genetic, swarm, seed = settings
    st.title("G\u00f6rev Y\u00f6nlendirme Laboratuvar\u0131")
    st.caption(
        f"{len(data.scenario.tasks)} g\u00f6rev  |  {len(data.scenario.servers)} sunucu  |  veri seed {data.configuration.experiment.random_seed}  |  sentetik"
        + (" / elle d\u00fczenlendi" if st.session_state.edited else "")
        + {
            "generated": "",
            "snapshot": " / y\u00fcklenen snapshot",
            "experiment": " / deney girdisi",
        }[st.session_state.input_source]
    )
    interface_guide(view)
    runs = current_runs(data, settings)
    if runs:
        run = st.selectbox(
            "G\u00f6sterilen plan",
            runs,
            format_func=lambda r: r.method,
            key=f"active_{st.session_state.epoch}_{st.session_state.get('run_context')}",
        )
    else:
        run = run_method(
            data,
            "Local",
            seed=seed,
            genetic=genetic,
            swarm=swarm,
            objective=objective,
            load=load,
        )
        st.caption(
            "G\u00f6sterilen plan: Local / optimize edilmemi\u015f yerel kontrol"
        )
    p = run.evaluation
    with st.container(key="summary_metrics"):
        a, b, c, d = st.columns(4)
    a.metric(
        "Ama\u00e7 puan\u0131 F",
        number(p.objective.value),
        help="S\u00fcre, model riski ve y\u00fck varyans\u0131n\u0131n a\u011f\u0131rl\u0131kl\u0131 toplam\u0131. D\u00fc\u015f\u00fck daha iyi; ba\u015far\u0131 y\u00fczdesi de\u011fildir.",
    )
    b.metric(
        "G\u00f6rev s\u00fcreleri toplam\u0131",
        number(p.total_latency_seconds, 3) + " s",
        help="T\u00fcm g\u00f6revlerin model s\u00fcreleri toplam\u0131. Arama s\u00fcresi veya fabrikan\u0131n paralel bitirme zaman\u0131 de\u011fildir.",
    )
    c.metric(
        "Toplam model riski",
        number(p.total_security_risk),
        help="G\u00f6nderim oran\u0131 ile a\u011f\u0131rl\u0131kl\u0131 g\u00f6rev risklerinin toplam\u0131. \u00d6l\u00e7\u00fclm\u00fc\u015f sald\u0131r\u0131 olas\u0131l\u0131\u011f\u0131 de\u011fildir.",
    )
    d.metric(
        "Sunucu y\u00fck varyans\u0131",
        number(p.objective.load_variance),
        help="Bo\u015f sunucular dahil a\u011f\u0131rl\u0131kl\u0131 y\u00fcklerin varyans\u0131. D\u00fc\u015f\u00fck de\u011fer daha dengeli rezervasyonu belirtir.",
    )
    st.caption(
        "Ge\u00e7erli ama\u00e7 a\u011f\u0131rl\u0131klar\u0131: "
        + " / ".join(
            f"{name} %{value * 100:.2f}"
            for name, value in zip(
                ("s\u00fcre", "risk", "y\u00fck"),
                asdict(objective).values(),
                strict=True,
            )
        )
    )
    if run.method == "Local":
        st.info(
            "G\u00f6sterilen plan **Local**: t\u00fcm g\u00f6revler cihazda \u00e7al\u0131\u015ft\u0131\u011f\u0131 "
            "i\u00e7in toplam model riski ve sunucu y\u00fck varyans\u0131n\u0131n 0 olmas\u0131 beklenir. "
            "Di\u011fer planlar\u0131 g\u00f6rmek i\u00e7in **\u00c7\u00f6z\u00fcm Kar\u015f\u0131la\u015ft\u0131rmas\u0131** ekran\u0131nda "
            "y\u00f6ntemleri \u00e7al\u0131\u015ft\u0131r\u0131n.",
            icon=":material/info:",
        )
    st.divider()
    if view == VIEWS[0]:
        overview(data)
    elif view == VIEWS[1]:
        fuzzy_view(data)
    elif view == VIEWS[2]:
        task_view(data, run, objective, load)
    elif view == VIEWS[3]:
        compare_view(data, settings)
    elif view == VIEWS[4]:
        experiments_view(data, settings)
    elif view == VIEWS[5]:
        mamdani_view(data, run, settings)
    else:
        learning_view(data)
    st.divider()
    st.download_button(
        "G\u00f6sterilen plan + girdiler JSON",
        export_run(
            data,
            run,
            objective=objective,
            load=load,
            genetic=genetic,
            swarm=swarm,
            seed=seed,
            edits=st.session_state.edited,
            source=st.session_state.input_source,
        ),
        "offloading_plan.json",
        "application/json",
        icon=":material/download:",
    )
    with st.expander("Model s\u0131n\u0131rlar\u0131 ve kaynak"):
        st.markdown(
            "[Jin ve ark. (2024)](https://www.nature.com/articles/s41598-024-79464-2): fuzzy Denklem 11\u201315, s\u00fcre 16, risk 18, ama\u00e7 19. Yazar kodu/verisi de\u011fil, belgeli varsay\u0131mlarla yeniden uygulama."
        )
        st.write(
            "Risk ger\u00e7ek sald\u0131r\u0131 tahmini de\u011fildir. Kuyruk ve paralel bitirme zaman\u0131 yok. Analitik oran, sabit kaynak ve normalizasyon varsay\u0131m\u0131na dayan\u0131r. Hocan\u0131n projeye \u00f6zel MRR'si hen\u00fcz netle\u015fmedi."
        )
