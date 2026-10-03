# Iki Ayrik Gelistirme Adimi Icin Commit Rehberi

Bu sohbet commit veya push yapmadi. Ortamin Git indeksine yazma kisiti
nedeniyle stage islemi de yapilamadi. Commit secimi ve calistirma ogrenciye
aittir. Asagidaki komutlar depo kokunde calistirilir.

## 1. Tamamlanan Fuzzy ve Hesaplama Altyapisi

Bu adim: fuzzy guvenlik, yerel/sunucu/iletisim suresi, kaynak rezervasyonlari,
yuk varyansi, daha siki girdi dogrulama, ornekler, ders/makale notlari ve veri
stratejisi. Sonraki cok-gorevli degerlendirme bu ilk listeye dahil degildir.

```powershell
$firstStepFiles = @(
    "README.md",
    "src/config.py", "src/models.py", "src/random_utils.py",
    "src/validation.py", "src/fuzzy_security.py",
    "src/latency.py", "src/load_balance.py",
    "tests/test_config.py", "tests/test_models.py", "tests/test_random_utils.py",
    "tests/test_fuzzy_security.py", "tests/test_fuzzy_security_demo.py",
    "tests/test_latency.py", "tests/test_load_balance.py", "tests/test_offloading_demo.py",
    "experiments/baseline/fuzzy_security_demo.py",
    "experiments/baseline/offloading_demo.py",
    "references/README.md", "references/adim_adim_rehber.md",
    "references/fuzzy_security.md", "references/project_context.md",
    "references/reproduction_plan.md", "references/simulation.md",
    "references/dataset_strategy.md", "references/commit_plan.md"
)
git add -- $firstStepFiles
git diff --cached --stat
git diff --cached
```

Hazirlik alaninda onceden baska dosyalar varsa onlar da commit'e girer;
ciktilari incelemeden commit atma. Bu liste baska dosyalari unstage etmez.
Onayindan sonra:

```powershell
git commit -m "feat: implement fuzzy security and offloading model calculations"
git push
```

## 2. Ortak Cok-Gorevli Degerlendirme

Bu adim: senaryo semasi, tum gorev/sunuculari birlikte degerlendirme, ortak
normalizasyon, Eq. (19), iki gorevli demo, bagimsiz hesaplama ve kisit testleri.
Birinci commit tamamlandiktan sonra:

```powershell
$secondStepFiles = @(
    "src/scenario.py", "src/objective.py", "src/evaluation.py",
    "tests/scenario_helpers.py", "tests/test_scenario.py",
    "tests/test_objective.py", "tests/test_evaluation.py", "tests/test_evaluation_demo.py",
    "experiments/baseline/evaluation_demo.py", "references/evaluation.md"
)
git add -- $secondStepFiles
git diff --cached --stat
git diff --cached
```

[Bu adimin aciklamasi](evaluation.md) incelendikten ve ogrenci onayindan sonra:

```powershell
git commit -m "feat: add multi-task evaluation and normalized objective"
git push
```

Adimlari ayri tutmak icin bu arada `git add .` veya `git commit -a` kullanma.
Komutlar herhangi bir degisikligi silmez veya geri almaz. Birinci adima ait
README'nin kapsam aciklamasi o commit'in tamamlandigi noktayi anlatir;
ikinci adim icin guncel aciklama `references/evaluation.md` dosyasindadir.
