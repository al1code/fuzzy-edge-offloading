# Proje ne yaptı, deneylerde ne bulundu?

Bir cihazın hesaplama işinin ne kadarını hangi sunucuya göndermesinin uygun olduğunu araştırdım. Program; görev süresini, bulanık güvenlikten türetilen model riskini ve sunucu yük dengesini birlikte değerlendirerek bir görev aktarma planı oluşturuyor.

## Sonuçları incele

- **[Karşılaştırma tabloları](tables/README.md):** yöntemlerin değerleri, deney koşulları ve kısa yorumları doğrudan okunabilir.
- **[Grafik galerisi](figures/README.md):** beş deneyin görselleri ve ne anlattıkları birlikte sunulur.

## Bir bakışta bulgular

| Denediğim soru | Bulduğum sonuç |
| --- | --- |
| İş cihazda mı, sunucuda mı, birlikte mi çalışmalı? | Birlikte kullanım yerel çözüme göre eşleştirilmiş ortalama yaklaşık %0,47 F kazancı verdi. |
| Mamdani gönderim sınırı neyi değiştirdi? | 2 kat hızda model riski %13,05 azaldı; görev süresi %0,104 ve F %0,110 arttı. |
| Basit bir sabit sınır da işe yarıyor mu? | Sabit sınır da belirgin risk azalması sağladı; tam Mamdani her ölçütte üstün değil. |
| Sunucular sabitken oranı doğrudan hesaplayabilir miyim? | Analitik hesap daha düşük F ve daha kısa oran çözüm süresi verdi. |
| Analitik hesap tam GA akışında hız kazandırır mı? | Ortalama arama süresi 9,7044 → 0,1878 s: yaklaşık 51,68 kat daha kısa; ortalama model riski arttı. |

## Temel yöntemin karşılaştırması

Yerel, tam kenar ve birlikte kullanım aynı görevlerle denendi. Birlikte kullanımın F değeri en düşük çıktı; yerel çözüme göre kazanç küçük kaldı. Makaledeki %46 kazanç bu koşullarda tekrar elde edilmedi.

![Yerel, tam kenar ve birlikte kullanımın toplam maliyet, süre ve model riski](figures/baseline_modes.png)

## Mamdani katkısının sonucu

Güvenlik puanı ve değerlendirme genişliğinden görev başına gönderim üst sınırı üretildi. Aşağıda 2 kat bağlantı hızındaki karşılaştırma var. Risk düşerken görev süresi ve F biraz arttı; 0,5 ve 1 kat hızda bu arama bütçesiyle fark oluşmadı.

![Mamdani risk, süre ve maliyet tercihi](figures/mamdani_tradeoff.png)

**Diğer üç deney:** sabit sınır kontrolü, sabit sunucularda analitik oran hesabı ve tam GA akışındaki hızlanma [grafik galerisinde](figures/README.md) ve [sayısal tablolarda](tables/README.md) açıklanır.

## Değerler nasıl okunmalı?

- **F:** süre, risk ve yük dengesinin toplam maliyeti. Aynı koşulda daha düşük olması tercih edilir; başarı yüzdesi değildir.
- **Görev süreleri toplamı:** modelin cihaz, iletim ve sunucu işleri için hesapladığı saniyeler.
- **Plan arama süresi:** programın karar ararken harcadığı gerçek süre; görev süresinden farklıdır ve makineye bağlıdır.
- **Model riski:** gönderime bağlı hesaplanan maliyet; ölçülmüş saldırı olasılığı değildir.

Deneyler 60 görev, 3 sunucu ve beş sentetik veri seti kullanır. Aynı verideki arama tekrarları yeni veri örnekleri değildir; toplam 225 kayıt, 225 bağımsız veri seti anlamına gelmez. Genel performans üstünlüğü veya istatistiksel anlamlılık iddia edilmez.

<details>
<summary>Yeniden üretim ayrıntıları</summary>

Grafiklerin ve tabloların dayandığı 225 koşuluk ölçümler [küçük CSV dosyasında](tables/recorded_runs.csv) paylaşılır. Üretilmiş görev verileri ve tam plan kayıtları Git dışında, yerelde tutulur. Deney komutları [ana README](../README.md) içindedir. Kaydedilmiş ölçümlerden tabloları ve grafikleri yeniden üretmek için:

```powershell
.\.venv\Scripts\python.exe -m experiments.summarize_results
```

Bu komut optimizasyonu yeniden çalıştırmaz; ölçümleri özetler. Tam deneyi çalıştırmak girdileri ve karar kayıtlarını yeniden üretir.

</details>
