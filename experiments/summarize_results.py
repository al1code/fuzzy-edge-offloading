"""Build the published tables and figures from the compact recorded metrics.

Run from the repository root: python -m experiments.summarize_results
Recorded optimizer timings are summarized, not measured again by this program.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from math import isfinite
from pathlib import Path
from statistics import mean, stdev

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
MEASUREMENTS = ROOT / "results/tables/recorded_runs.csv"
METRICS = (
    "objective",
    "total_latency_seconds",
    "total_security_risk",
    "load_variance",
    "search_seconds",
)
TEAL, COPPER, SLATE = "#117B78", "#BE7950", "#7D99A4"
METHOD_LABELS = {
    "Local": "Yerel",
    "Edge": "Tam kenar",
    "Local-Edge": "Birlikte / BOALBFS",
    "Baseline BOALBFS": "BOALBFS",
    "Uncertainty-aware Mamdani": "Mamdani",
    "Unconstrained": "Ek sınır yok",
    "Constant mean cap": "Sabit sınır",
    "Security only": "Yalnız güvenlik S",
    "Full Mamdani": "Tam Mamdani S/U",
    "Analytical": "Analitik",
    "GA+SA-PSO": "GA + SA-PSO",
    "GA+Analytical": "GA + analitik",
}
TABLE_NOTES = {
    "baseline_modes": (
        "A — İş nerede çalıştırılmalı?",
        "baseline_modes",
        "Aynı görevleri tamamen cihazda, tamamen sunucularda veya iki tarafta birlikte çalıştırmayı karşılaştırdım. 60 görev, 3 sunucu; 5 veri seti × 3 arama tekrarı × 3 mod = 45 kayıt.",
        "Birlikte kullanımın toplam maliyeti F en düşük çıktı; yerel çözüme göre eşleştirilmiş ortalama kazanç yaklaşık %0,47 ile küçük kaldı. Makaledeki %46 kazancı bu koşullarda tekrar elde etmedim.",
    ),
    "mamdani_pipeline": (
        "B — Mamdani gönderim sınırı neyi değiştirdi?",
        "mamdani_tradeoff",
        "Temel BOALBFS ile görev başına Mamdani üst sınırı eklenen sürümü aynı girdilerde karşılaştırdım. 5 veri seti × 2 arama tekrarı × 3 bağlantı hızı × 2 yöntem = 60 kayıt.",
        "2 kat bağlantı hızında model riski yaklaşık %13,05 azaldı; görev süreleri toplamı %0,104 ve F %0,110 arttı. 0,5 ve 1 kat hızda bu arama bütçesiyle yöntemler tamamen yerelde kaldı; seçilen plan, F, risk ve görev süresi aynı çıktı. Planı aramak için harcanan süreler farklıdır. Katkı, risk ile süre arasındaki tercihi değiştiriyor.",
    ),
    "policy_controls": (
        "C — Risk azalması yalnız Mamdani sayesinde mi?",
        "policy_controls",
        "Aynı round-robin sunucu konumlarında dört oran politikasını karşılaştırdım. Oranlar analitik çözüldü. 5 veri seti × 3 bağlantı hızı × 4 politika = 60 kayıt; tam GA deneyi değildir.",
        "Sabit sınır da model riskini belirgin azalttı. 2 kat hızda tam Mamdani, sabit sınırdan biraz daha kısa süre ve düşük F; biraz daha yüksek risk verdi. Sonuçlar, risk düşüşünün tamamını U girdisinin özel başarısına bağlamıyor.",
    ),
    "ratio_fixed_locations": (
        "D — Sunucu seçimi sabitken oranı nasıl hesaplamalı?",
        "analytical_fixed_locations",
        "Sunucuları değiştirmeden SA-PSO oran araması ile analitik oran hesabını karşılaştırdım. 5 veri seti × 3 arama tekrarı × 2 yöntem = 30 kayıt.",
        "Bu model ve bütçede analitik hesap daha düşük F ve daha kısa oran çözüm süresi verdi. Sunucu seçimi sabit olduğundan bu, bütün sistemin global optimumu veya tam GA hızlanması değildir; tam akışın sonucu E tablosundadır.",
    ),
    "ratio_pipeline": (
        "E — Analitik hesap tam GA akışında ne kazandırdı?",
        "analytical_pipeline",
        "GA konum aramasının altında SA-PSO veya analitik oran hesabı kullandım. Aynı üst GA bütçesiyle 5 veri seti × 3 arama tekrarı × 2 yöntem = 30 kayıt.",
        "Kaydedilen ortalama plan arama süresi 9,7044 saniyeden 0,1878 saniyeye indi: yaklaşık 51,68 kat daha kısa. F de azaldı; ancak ortalama model riski arttı. Arama süresi görevlerin çalışma süresi değildir ve makineye bağlıdır.",
    ),
}


def load_measurements() -> dict[str, list[dict[str, str]]]:
    """Validate the small shared CSV without requiring local input snapshots."""
    records = {name: [] for name in TABLE_NOTES}
    with MEASUREMENTS.open(encoding="utf-8", newline="") as stream:
        for original in csv.DictReader(stream):
            row = {key: val for key, val in original.items() if val != ""}
            name = row.pop("experiment")
            if name not in records:
                raise ValueError(f"unknown recorded experiment: {name}")
            int(row["data_seed"])
            if "optimizer_seed" in row:
                int(row["optimizer_seed"])
            for field in ("link_rate_factor", *METRICS):
                if field in row and not isfinite(float(row[field])):
                    raise ValueError(f"non-finite recorded metric: {field}")
            if float(row["link_rate_factor"]) <= 0:
                raise ValueError("link_rate_factor must be positive")
            records[name].append(row)
    expected = dict(zip(TABLE_NOTES, (45, 60, 60, 30, 30), strict=True))
    if any(len(rows) != expected[name] for name, rows in records.items()):
        raise ValueError("recorded CSV must contain the 225 reported experiment runs")
    return records


def summarize(name: str, rows: list[dict[str, str]]) -> list[dict]:
    """Average optimizer repeats within a dataset, then average datasets."""
    groups = defaultdict(list)
    for row in rows:
        groups[
            (row.get("method", row.get("mode")), float(row.get("link_rate_factor", 1)))
        ].append(row)
    summaries = []
    for (method, factor), group in groups.items():
        for metric in METRICS:
            if metric not in group[0]:
                continue
            by_seed = defaultdict(list)
            for row in group:
                if row.get("status", "ok") not in (
                    "ok",
                    "success",
                    "complete",
                    "feasible",
                ):
                    raise ValueError(f"unsuccessful run in {name}: {row['status']}")
                by_seed[int(row["data_seed"])].append(float(row[metric]))
            dataset_means = [mean(values) for values in by_seed.values()]
            summaries.append(
                {
                    "experiment": name,
                    "method": method,
                    "link_rate_factor": factor,
                    "metric": metric,
                    "mean": mean(dataset_means),
                    "sd_between_datasets": stdev(dataset_means)
                    if len(dataset_means) > 1
                    else "",
                    "datasets": len(by_seed),
                    "runs": len(group),
                }
            )
    return summaries


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def readable_rows(summaries):
    """Place each method/condition on one row with Turkish metric headings."""
    rows = []
    groups = dict.fromkeys((r["method"], r["link_rate_factor"]) for r in summaries)
    for method, factor in groups:
        group = {
            r["metric"]: r
            for r in summaries
            if r["method"] == method and r["link_rate_factor"] == factor
        }
        row = {
            "Yöntem": METHOD_LABELS.get(method, method),
            "Bağlantı hızı (kat)": factor,
            "Toplam maliyet F": group["objective"]["mean"],
            "Görev süreleri toplamı (s)": group["total_latency_seconds"]["mean"],
            "Model riski": group["total_security_risk"]["mean"],
            "Yük varyansı": group["load_variance"]["mean"],
        }
        if "search_seconds" in group:
            row["Plan arama süresi (s)"] = group["search_seconds"]["mean"]
        rows.append(row)
    return rows


def markdown_table(summaries, factor):
    selected = [
        r for r in readable_rows(summaries) if r["Bağlantı hızı (kat)"] == factor
    ]
    headers = [
        "Yöntem",
        "Toplam maliyet F",
        "Görev süreleri toplamı (s)",
        "Model riski",
    ]
    if "Plan arama süresi (s)" in selected[0]:
        headers.append("Plan arama süresi (s)")
    lines = [
        "| " + " | ".join(headers) + " |",
        "| --- | " + " | ".join("---:" for _ in headers[1:]) + " |",
    ]
    for row in selected:
        values = [str(row["Yöntem"])]
        for header in headers[1:]:
            digits = 4 if "(s)" in header else 6
            values.append(f"{row[header]:.{digits}f}".replace(".", ","))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_readable_tables(summaries):
    sections = [
        "# Sonuç tabloları",
        "Her bölüm, hangi soruyu denediğimi, karşılaştırılan yöntemleri ve elde edilen sonucu birlikte gösterir. Tablolar GitHub üzerinde doğrudan okunabilir; dosya indirmek gerekmez.",
        "**Nasıl okunur?** Aynı deney koşulunda daha küçük F, daha düşük toplam maliyettir. Model riski saldırı olasılığı değildir. Görev süreleri toplamı ile planı aramak için harcanan süre ayrı ölçülerdir.",
        "Bütün değerler beş veri setinin ortalamasıdır; her veri setinde önce arama tekrarları ortalanmıştır. Yuvarlama yalnız bu görünüm içindir. CSV dosyalarında tam sayısal hassasiyet korunur.",
        "B deneyindeki plan arama süresi, Mamdani sınırlarının ön hesabını kapsamaz; uygulamanın toplam çalışma zamanı olarak yorumlanmamalıdır.",
    ]
    for name, (title, figure, setup, finding) in TABLE_NOTES.items():
        write_csv(
            ROOT / "results/tables" / f"{name}.csv", readable_rows(summaries[name])
        )
        sections.extend([f"## {title}", setup])
        factors = sorted({r["link_rate_factor"] for r in summaries[name]})
        for factor in sorted(factors, key=lambda f: (f != 2, f)):
            if len(factors) > 1:
                sections.append(
                    f"### Bağlantı hızı: {factor:g} kat".replace("0.5", "0,5")
                )
            sections.append(markdown_table(summaries[name], factor))
        sections.extend(
            [
                f"**Sonuç:** {finding}",
                f"[Grafik](../figures/{figure}.png) · [CSV tablosunu indir]({name}.csv)",
            ]
        )
    sections.extend(
        [
            "## Deneyleri doğru yorumlamak",
            "Bağımsız veri sayısı beştir. Aynı verideki arama tekrarları yeni veri örnekleri değildir. Özetlerin dayandığı 225 koşuluk sayısal ölçümler [küçük CSV dosyasında](recorded_runs.csv) bulunur; istatistiksel anlamlılık iddia edilmez. Üretilen görev verileri ve tam plan kayıtları yerelde tutulur.",
            "F normalizasyonu bağlantı hızı koşuluyla değişebilir. Farklı hızların F değerlerinden tek başına iyileşme yüzdesi çıkarılmamalıdır. Arama zamanı yeniden çalıştırıldığında donanıma ve sistem yüküne göre değişir.",
            "[Sonuçların genel görünümü](../README.md) · [Grafik galerisi](../figures/README.md)",
        ]
    )
    (ROOT / "results/tables/README.md").write_text(
        "\n\n".join(sections) + "\n", encoding="utf-8"
    )


def write_result_pages():
    """Give each result directory a readable entry page on GitHub."""
    overview = [
        "# Proje ne yaptı, deneylerde ne bulundu?",
        "Bir cihazın hesaplama işinin ne kadarını hangi sunucuya göndermesinin uygun olduğunu araştırdım. Program; görev süresini, bulanık güvenlikten türetilen model riskini ve sunucu yük dengesini birlikte değerlendirerek bir görev aktarma planı oluşturuyor.",
        "## Sonuçları incele",
        "- **[Karşılaştırma tabloları](tables/README.md):** yöntemlerin değerleri, deney koşulları ve kısa yorumları doğrudan okunabilir.\n- **[Grafik galerisi](figures/README.md):** beş deneyin görselleri ve ne anlattıkları birlikte sunulur.",
        "## Bir bakışta bulgular",
        "| Denediğim soru | Bulduğum sonuç |\n| --- | --- |\n| İş cihazda mı, sunucuda mı, birlikte mi çalışmalı? | Birlikte kullanım yerel çözüme göre eşleştirilmiş ortalama yaklaşık %0,47 F kazancı verdi. |\n| Mamdani gönderim sınırı neyi değiştirdi? | 2 kat hızda model riski %13,05 azaldı; görev süresi %0,104 ve F %0,110 arttı. |\n| Basit bir sabit sınır da işe yarıyor mu? | Sabit sınır da belirgin risk azalması sağladı; tam Mamdani her ölçütte üstün değil. |\n| Sunucular sabitken oranı doğrudan hesaplayabilir miyim? | Analitik hesap daha düşük F ve daha kısa oran çözüm süresi verdi. |\n| Analitik hesap tam GA akışında hız kazandırır mı? | Ortalama arama süresi 9,7044 → 0,1878 s: yaklaşık 51,68 kat daha kısa; ortalama model riski arttı. |",
        "## Temel yöntemin karşılaştırması",
        "Yerel, tam kenar ve birlikte kullanım aynı görevlerle denendi. Birlikte kullanımın F değeri en düşük çıktı; yerel çözüme göre kazanç küçük kaldı. Makaledeki %46 kazanç bu koşullarda tekrar elde edilmedi.",
        "![Yerel, tam kenar ve birlikte kullanımın toplam maliyet, süre ve model riski](figures/baseline_modes.png)",
        "## Mamdani katkısının sonucu",
        "Güvenlik puanı ve değerlendirme genişliğinden görev başına gönderim üst sınırı üretildi. Aşağıda 2 kat bağlantı hızındaki karşılaştırma var. Risk düşerken görev süresi ve F biraz arttı; 0,5 ve 1 kat hızda bu arama bütçesiyle fark oluşmadı.",
        "![Mamdani risk, süre ve maliyet tercihi](figures/mamdani_tradeoff.png)",
        "**Diğer üç deney:** sabit sınır kontrolü, sabit sunucularda analitik oran hesabı ve tam GA akışındaki hızlanma [grafik galerisinde](figures/README.md) ve [sayısal tablolarda](tables/README.md) açıklanır.",
        "## Değerler nasıl okunmalı?",
        "- **F:** süre, risk ve yük dengesinin toplam maliyeti. Aynı koşulda daha düşük olması tercih edilir; başarı yüzdesi değildir.\n- **Görev süreleri toplamı:** modelin cihaz, iletim ve sunucu işleri için hesapladığı saniyeler.\n- **Plan arama süresi:** programın karar ararken harcadığı gerçek süre; görev süresinden farklıdır ve makineye bağlıdır.\n- **Model riski:** gönderime bağlı hesaplanan maliyet; ölçülmüş saldırı olasılığı değildir.",
        "Deneyler 60 görev, 3 sunucu ve beş sentetik veri seti kullanır. Aynı verideki arama tekrarları yeni veri örnekleri değildir; toplam 225 kayıt, 225 bağımsız veri seti anlamına gelmez. Genel performans üstünlüğü veya istatistiksel anlamlılık iddia edilmez.",
        "<details>\n<summary>Yeniden üretim ayrıntıları</summary>\n\nGrafiklerin ve tabloların dayandığı 225 koşuluk ölçümler [küçük CSV dosyasında](tables/recorded_runs.csv) paylaşılır. Üretilmiş görev verileri ve tam plan kayıtları Git dışında, yerelde tutulur. Deney komutları [ana README](../README.md) içindedir. Kaydedilmiş ölçümlerden tabloları ve grafikleri yeniden üretmek için:\n\n```powershell\n.\\.venv\\Scripts\\python.exe -m experiments.summarize_results\n```\n\nBu komut optimizasyonu yeniden çalıştırmaz; ölçümleri özetler. Tam deneyi çalıştırmak girdileri ve karar kayıtlarını yeniden üretir.\n\n</details>",
    ]
    (ROOT / "results/README.md").write_text(
        "\n\n".join(overview) + "\n", encoding="utf-8"
    )
    gallery = [
        "# Grafik galerisi",
        "Beş deneyin neyi karşılaştırdığını ve ne sonuç verdiğini bu sayfadan okuyabilirsin. [Sayısal tablolar](../tables/README.md) · [Sonuçların genel görünümü](../README.md)",
    ]
    for name, (title, figure, setup, finding) in TABLE_NOTES.items():
        gallery.extend(
            [
                f"## {title}",
                setup,
                f"![{title}]({figure}.png)",
                f"**Sonuç:** {finding}",
                f"[PNG]({figure}.png) · [Sayısal tablolar](../tables/README.md) · [CSV](../tables/{name}.csv)",
            ]
        )
    gallery.extend(
        [
            "## Ölçüm sınırları",
            "Model riski saldırı olasılığı değildir. Görev süresi model hesabıdır; plan arama süresi gerçek program süresidir. Bütün deneyler sentetik girdilerle yapılmıştır. Farklı hız koşullarının F değerleri tek başına iyileşme yüzdesi olarak yorumlanmamalıdır.",
        ]
    )
    (ROOT / "results/figures/README.md").write_text(
        "\n\n".join(gallery) + "\n", encoding="utf-8"
    )


def value(rows, method, metric, factor=1):
    return next(
        r["mean"]
        for r in rows
        if r["method"] == method
        and r["metric"] == metric
        and r["link_rate_factor"] == factor
    )


def bar(ax, labels, values, colors, title, ylabel, digits=3):
    bars = ax.bar(labels, values, color=colors, width=0.56)
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold", pad=13)
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, max(values) * 1.28 if max(values) else 1)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="y", color="#DBE4E5", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.bar_label(
        bars, labels=[f"{v:.{digits}f}" for v in values], padding=5, fontsize=10
    )


def save_figure(fig, name, note):
    fig.text(0.06, 0.015, note, fontsize=9, color="#526B74")
    fig.tight_layout(rect=(0.02, 0.06, 0.99, 0.93))
    fig.savefig(ROOT / "results/figures" / f"{name}.png", dpi=180, facecolor="white")
    plt.close(fig)


def main():
    table_dir = ROOT / "results/tables"
    figure_dir = ROOT / "results/figures"
    table_dir.mkdir(exist_ok=True)
    figure_dir.mkdir(exist_ok=True)
    summaries = {}
    records = load_measurements()
    for name, rows in records.items():
        summaries[name] = summarize(name, rows)
    write_readable_tables(summaries)
    write_result_pages()

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "text.color": "#102D3B",
            "axes.labelcolor": "#102D3B",
            "xtick.color": "#102D3B",
            "ytick.color": "#526B74",
            "axes.edgecolor": "#B7C8CB",
            "font.size": 10,
        }
    )
    s = summaries["baseline_modes"]
    methods = list(dict.fromkeys(r["method"] for r in s))
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.3))
    fig.suptitle(
        "Temel kullanım modları", x=0.06, ha="left", fontsize=17, fontweight="bold"
    )
    for ax, metric, title, unit, digits in zip(
        axes,
        METRICS[:3],
        ["Toplam maliyet F", "Model görev süresi", "Model riski"],
        ["F", "saniye", "risk maliyeti"],
        [3, 2, 4],
        strict=True,
    ):
        bar(
            ax,
            ["Yerel", "Tam kenar", "Birlikte"],
            [value(s, m, metric) for m in methods],
            [SLATE, COPPER, TEAL],
            title,
            unit,
            digits,
        )
    save_figure(
        fig,
        "baseline_modes",
        "60 görev / 3 sunucu; 5 veri × 3 arama tekrarı. Çubuklar veri ortalamalarının ortalamasıdır.",
    )

    s = summaries["mamdani_pipeline"]
    methods = ["Baseline BOALBFS", "Uncertainty-aware Mamdani"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.3))
    fig.suptitle(
        "Mamdani: 2 kat bağlantı hızındaki tercih",
        x=0.06,
        ha="left",
        fontsize=17,
        fontweight="bold",
    )
    for ax, metric, title, unit, digits in zip(
        axes,
        ["total_security_risk", "total_latency_seconds", "objective"],
        ["Ortalama model riski", "Model görev süresi", "Toplam maliyet F"],
        ["risk maliyeti", "saniye", "F"],
        [6, 4, 6],
        strict=True,
    ):
        bar(
            ax,
            ["BOALBFS", "Mamdani"],
            [value(s, m, metric, 2) for m in methods],
            [COPPER, TEAL],
            title,
            unit,
            digits,
        )
    save_figure(
        fig,
        "mamdani_tradeoff",
        "5 veri × 2 arama tekrarı. 0,5 ve 1 kat hızda fark yoktur; düşük model riski gerçek saldırı garantisi değildir.",
    )

    s = summaries["policy_controls"]
    methods = ["Unconstrained", "Constant mean cap", "Security only", "Full Mamdani"]
    labels = ["Ek sınır yok", "Sabit sınır", "Yalnız S", "Tam S/U"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    fig.suptitle(
        "Sabit sunucu konumlarında politika kontrolü",
        x=0.06,
        ha="left",
        fontsize=17,
        fontweight="bold",
    )
    for ax, metric, title, unit, digits in zip(
        axes,
        ["total_security_risk", "total_latency_seconds"],
        ["Ortalama model riski", "Model görev süresi"],
        ["risk maliyeti", "saniye"],
        [6, 2],
        strict=True,
    ):
        bar(
            ax,
            labels,
            [value(s, m, metric, 2) for m in methods],
            [SLATE, COPPER, "#BACACB", TEAL],
            title,
            unit,
            digits,
        )
    save_figure(
        fig,
        "policy_controls",
        "2 kat hız, 5 veri, aynı round-robin konumları ve analitik oran çözümü. Tam GA deneyi değildir.",
    )

    s = summaries["ratio_fixed_locations"]
    methods = ["SA-PSO", "Analytical"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
    fig.suptitle(
        "Sabit konumlarda analitik oran hesabı",
        x=0.06,
        ha="left",
        fontsize=17,
        fontweight="bold",
    )
    for ax, metric, title, unit, digits in zip(
        axes,
        ["objective", "search_seconds"],
        ["Toplam maliyet F", "Oran çözüm süresi"],
        ["F", "saniye"],
        [6, 4],
        strict=True,
    ):
        bar(
            ax,
            ["SA-PSO", "Analitik"],
            [value(s, m, metric) for m in methods],
            [COPPER, TEAL],
            title,
            unit,
            digits,
        )
    save_figure(
        fig,
        "analytical_fixed_locations",
        "5 veri × 3 tekrar; sunucu konumları sabittir. Bu, tam GA akışının arama süresi değildir.",
    )

    s = summaries["ratio_pipeline"]
    methods = ["GA+SA-PSO", "GA+Analytical"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
    fig.suptitle(
        "Analitik oran hesabının tam GA akışındaki etkisi",
        x=0.06,
        ha="left",
        fontsize=17,
        fontweight="bold",
    )
    for ax, metric, title, unit, digits in zip(
        axes,
        ["search_seconds", "objective"],
        ["Plan arama süresi", "Toplam maliyet F"],
        ["saniye", "F"],
        [4, 6],
        strict=True,
    ):
        bar(
            ax,
            ["GA + SA-PSO", "GA + analitik"],
            [value(s, m, metric) for m in methods],
            [COPPER, TEAL],
            title,
            unit,
            digits,
        )
    save_figure(
        fig,
        "analytical_pipeline",
        "5 veri × 3 tekrar; aynı üst GA bütçesi. Arama süresi makineye bağlıdır; ortalama model riski artmıştır.",
    )
    print(
        f"Published {sum(len(r) for r in records.values())} recorded measurements, readable tables and 5 PNG figures."
    )


if __name__ == "__main__":
    main()
