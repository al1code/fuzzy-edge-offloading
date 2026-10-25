# Sentetik veri ve parametreler

Veriler özgün yazar girdileri değildir. Makalede belirtilen aralıklar ile açık
proje varsayımları kullanılarak `src/synthetic.py` tarafından üretilir.
Üretilmiş girdiler GitHub paketine dahil edilmez. Aşağıdaki komutlar örnek
veriyi yerelde oluşturur; aynı tohum ve ayarlar yeniden kullanılabilir.

| Parametre | Projede kullanılan değer | Kaynak / yorum |
| --- | --- | --- |
| Ana deney boyutu | 60 görev, 3 sunucu | Makale Tablo 4'teki 60–140 / 3–9 aralıklarının alt uçları |
| Perspektif ağırlıkları | Her biri 1/3 | Tablo 4 |
| Uzman sayısı ve ağırlıkları | 3 uzman, eşit ağırlık | Proje varsayımı |
| Güvenlik eşiği | 0,60 | Makaledeki 0,2–0,8 aralığından seçildi |
| Görev verisi | 0,5–5 MB | Proje varsayımı; 1 MB = 8.000.000 bit |
| İş yükü | 200–800 çevrim/bit | Proje varsayımı; toplam CPU işi ayrıca saklanır |
| Yerel CPU | 3 × 10^9 çevrim/s | 3 GHz frekans yorumu; MIPS ile özdeş kabul edilmez |
| Göreve ayrılan sunucu CPU'su | 10 × 10^9 çevrim/s | Tablo 4'teki 10 GHz frekans yorumu |
| Sunucu toplam CPU kapasitesi | 200 × 10^9 çevrim/s | Rezervasyonlar için açık proje seçimi |
| Görev bant genişliği | 0,25–1 MHz | Proje varsayımı |
| Sunucu bant genişliği | 20 MHz | Tablo 4 |
| Görev belleği | 8–32 MB | Proje varsayımı |
| Sunucu belleği | 1024 MB | Tablo 4 |
| Gönderim gücü | 0,1 W | Proje seçimi |
| Kanal kazancı | 0,0001–0,001 | Proje varsayımı |
| Gürültü spektral yoğunluğu | 10^-17 W/Hz | Proje seçimi; dBm doğrudan W/Hz kabul edilmez |
| Envanter bağlantı hızı | 100 Mbps | Bilgi alanı; gerçek görev/sunucu hızı yerine kullanılmaz |
| Görev deadline | 30 s | Bilgi alanı; modelde deadline kısıtı yoktur |

Aralıklar düzgün dağılımla örneklenir; uzman üçgenleri [0,1] aralığındaki
çekilişlerin sıralanmasıyla oluşturulur. Bunlar gerçek fabrika ölçümüyle
kalibre edilmiş dağılımlar değildir. Bağlantı hızları görev/sunucu çifti için
Shannon modeliyle hesaplanır. Kesik veya sıfır hızlı bağlantılar temsil edilmez.
Uygun olmayan sunucu atamaları sessizce düzeltilmez; kapasite hatası olarak kaydedilir.

## Tohumlar ve dosya kimliği

Ana deneyler 7, 21, 42, 84 ve 2026 veri tohumlarını kullanır. Arama tohumları
temel mod ve analitik deneylerinde 0, 1, 2; Mamdani hız deneyinde 0, 1'dir.
Saklanan JSON yalnız tohumu değil gerçek görevleri, ham uzman üçgenlerini,
kanal girdilerini, yapılandırmayı, sabit normalizasyonu ve çalışma ortamını içerir.
Dosya biçiminin sürümü uyumluluk denetimi içindir.

`src/dataset_io.py` içerik kimliğini doğrular. Deney manifestleri dosyaların
SHA-256 karmalarını ayrıca tutar. Aynı girdiler aynı değerlendirmeyi vermelidir;
plan arama süresi donanıma ve sistem yüküne bağlıdır. Yeni rastgele aramaların
özdeşliği için bağımlılık sürümleri de korunmalıdır.

## Örnek komutlar

```powershell
.\.venv\Scripts\python.exe -m experiments.baseline.synthetic_demo --seed 42 --output data/generated/synthetic_seed42.json
.\.venv\Scripts\python.exe -m experiments.baseline.synthetic_demo --input data/generated/synthetic_seed42.json
.\.venv\Scripts\python.exe -m experiments.baseline.synthetic_demo --seed 7 --output data/generated/synthetic_seed7.json
```

Mevcut dosyanın üzerine yazılmaz. Yeni üretilen veriler karşılaştırılan bütün
yöntemlerle paylaşılmalıdır. Makale sonucu ile proje sonucu aynı şey değildir.
