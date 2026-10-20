# Sonraki Yapay Zeka Aracina Devir Notu

## Projenin amaci

Bu repository, Jin ve arkadaslarinin Scientific Reports 2024 makalesindeki
“Task offloading for multi-server edge computing in industrial Internet with
joint load balance and fuzzy security” yontemini belgelenmis varsayimlarla
Python'da yeniden gerceklestirir ve uzerine belirsizlik-duyarli Type-1 Mamdani
offloading karari ekler.

Referanslar:

- Nature: https://www.nature.com/articles/s41598-024-79464-2
- Acik erisimli metin: https://pmc.ncbi.nlm.nih.gov/articles/PMC11561288/
- Ders yonergesi: repository disindaki `Bulanik_Mantik_Donem_Projesi_Yonergesi.pdf`

## Mevcut teknik akış

1. Seeded sentetik senaryo uretilir.
2. Uzman ucgensel fuzzy guvenlik degerlendirmeleri birlestirilir.
3. Gecikme, iletim, guvenlik riski ve kaynak yuk varyansi hesaplanir.
4. Ortak normalize `F` objective degeri hesaplanir.
5. GA local/server konumlarini secer.
6. SA-PSO oranlari arar; bu ikisi `solve_boalbfs` ile birlesir.
7. Baseline ve proposed yontemler ayni veri, normalizasyon, seed ve butceyle
   paired karsilastirilir.

## Onerilen katkı

`src/fuzzy_controller.py`:

- Makaledeki security level `S` korunur.
- Agregalan triangular expert assessments'in ortalama genisligi `U`
  belirsizlik girdisi olur.
- 3x3 rule base, min-AND, max output aggregation ve centroid defuzzification
  ile task-specific allowed offloading ratio cap'i uretilir.
- Cap `evaluate_plan`, analytical location solver, SA-PSO ve BOALBFS boyunca
  zorunlu uygulanir.

Katki her zaman `F`'yi azaltmak zorunda degildir. Beklenen davranis, belirsizlik
ve offloading risk maruziyetini azaltirken latency pahasina daha temkinli karar
verebilmesidir. Bu nedenle hem `F`, hem total latency, total risk, cap,
uncertainty-weighted exposure ve search cost birlikte raporlanmalidir.

## Önemli dosyalar

- `src/fuzzy_security.py`: makalenin fuzzy güvenlik hesabı
- `src/evaluation.py`: ortak plan evaluator ve oran cap denetimi
- `src/optimizers/genetic.py`: GA konum araması
- `src/optimizers/sapso.py`: SA-PSO oran araması ve BOALBFS
- `src/fuzzy_controller.py`: yeni Mamdani denetleyicisi
- `experiments/baseline/mode_comparison.py`: Local/Edge/Local-Edge baseline
- `experiments/proposed/uncertainty_mamdani_comparison.py`: paired katkı deneyi
- `gui/dashboard.py`: Streamlit arayüzü ve Mamdani görünümü
- `references/paper_alignment.md`: makale uyumu ve sonuç farklarının açıklaması
- `references/project_guideline_alignment.md`: ders yönergesi uygunluk matrisi

## Veri kararı

Makalenin ana veri setine erişim yok. Ders hocası, makalede bildirilen
parametre aralıklarından seeded sentetik veri üretilmesini uygun gördü. Bu
durum proje ve raporda açıkça yazılmalı. Sentetik sonuçlar makalenin
yayınlanmış yüzdelerinin birebir tekrarı değildir; yazar verisi, seed'leri ve
tam Java ayarları mevcut değildir.

## Doğrulanmış durum

- Python 3.14.5 sanal ortamı.
- Son tam test: `749 passed`.
- Yeni Mamdani, ratio-cap ve kontrollü deney testleri geçiyor.
- Pylance yeni katkıyla ilişkili hata bildirmiyor; yalnızca mevcut unused
  parameter uyarıları var.
- `results/` altındaki deney paketleri local/ignored tutulur.
- Commit/push otomatik yapılmamalı; öğrenci inceleyip kendisi yapar.

## Çalıştırma komutları

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests -q
.\.venv\Scripts\python.exe -m experiments.baseline.mode_comparison --output results/baseline_modes_new
.\.venv\Scripts\python.exe -m experiments.proposed.uncertainty_mamdani_comparison --output results/mamdani_v1
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Yeni output klasörü kullan; deneyler mevcut klasörün üzerine yazmaz.

## Buradan devam edilecek işler

1. Önce `git status` ve mevcut diff'i incele; öğrencinin yerel değişikliklerini
   geri alma.
2. Bu devir notu, `paper_alignment.md` ve `project_guideline_alignment.md`
   ile çelişen bir iddia ekleme.
3. Yeni deney eklenirse baseline/proposed aynı dataset ve normalization ile
   paired çalışmalı, manifest ve checksum yazılmalı.
4. Öncelikli teknik genişletme gerekirse Fig. 4-10 sensitivity runner'ı ekle.
5. Altı rakip optimizer'ı eklemek ancak öğrenci kapsamı genişletirse yapılmalı;
   mevcut MRR için zorunlu kabul edilmemeli.
6. Rapor ve sunum kullanıcı tarafından ayrıca hazırlanacak; kod tarafında
   yalnızca tekrar üretilebilirlik ve açıklanabilirlik eksikleri düzeltilmeli.
