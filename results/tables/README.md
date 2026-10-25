# Sonuç tabloları

Her bölüm, hangi soruyu denediğimi, karşılaştırılan yöntemleri ve elde edilen sonucu birlikte gösterir. Tablolar GitHub üzerinde doğrudan okunabilir; dosya indirmek gerekmez.

**Nasıl okunur?** Aynı deney koşulunda daha küçük F, daha düşük toplam maliyettir. Model riski saldırı olasılığı değildir. Görev süreleri toplamı ile planı aramak için harcanan süre ayrı ölçülerdir.

Bütün değerler beş veri setinin ortalamasıdır; her veri setinde önce arama tekrarları ortalanmıştır. Yuvarlama yalnız bu görünüm içindir. CSV dosyalarında tam sayısal hassasiyet korunur.

B deneyindeki plan arama süresi, Mamdani sınırlarının ön hesabını kapsamaz; uygulamanın toplam çalışma zamanı olarak yorumlanmamalıdır.

## A — İş nerede çalıştırılmalı?

Aynı görevleri tamamen cihazda, tamamen sunucularda veya iki tarafta birlikte çalıştırmayı karşılaştırdım. 60 görev, 3 sunucu; 5 veri seti × 3 arama tekrarı × 3 mod = 45 kayıt.

| Yöntem | Toplam maliyet F | Görev süreleri toplamı (s) | Model riski | Plan arama süresi (s) |
| --- | ---: | ---: | ---: | ---: |
| Yerel | 0,239262 | 219,9130 | 0,000000 | 0,0008 |
| Tam kenar | 0,621733 | 265,2710 | 5,550637 | 0,0901 |
| Birlikte / BOALBFS | 0,238117 | 218,4440 | 0,004116 | 9,8212 |

**Sonuç:** Birlikte kullanımın toplam maliyeti F en düşük çıktı; yerel çözüme göre eşleştirilmiş ortalama kazanç yaklaşık %0,47 ile küçük kaldı. Makaledeki %46 kazancı bu koşullarda tekrar elde etmedim.

[Grafik](../figures/baseline_modes.png) · [CSV tablosunu indir](baseline_modes.csv)

## B — Mamdani gönderim sınırı neyi değiştirdi?

Temel BOALBFS ile görev başına Mamdani üst sınırı eklenen sürümü aynı girdilerde karşılaştırdım. 5 veri seti × 2 arama tekrarı × 3 bağlantı hızı × 2 yöntem = 60 kayıt.

### Bağlantı hızı: 2 kat

| Yöntem | Toplam maliyet F | Görev süreleri toplamı (s) | Model riski | Plan arama süresi (s) |
| --- | ---: | ---: | ---: | ---: |
| BOALBFS | 0,317580 | 219,3001 | 0,006949 | 0,3824 |
| Mamdani | 0,317929 | 219,5273 | 0,006042 | 0,4244 |

### Bağlantı hızı: 0,5 kat

| Yöntem | Toplam maliyet F | Görev süreleri toplamı (s) | Model riski | Plan arama süresi (s) |
| --- | ---: | ---: | ---: | ---: |
| BOALBFS | 0,139520 | 219,9130 | 0,000000 | 0,4039 |
| Mamdani | 0,139520 | 219,9130 | 0,000000 | 0,4434 |

### Bağlantı hızı: 1 kat

| Yöntem | Toplam maliyet F | Görev süreleri toplamı (s) | Model riski | Plan arama süresi (s) |
| --- | ---: | ---: | ---: | ---: |
| BOALBFS | 0,239262 | 219,9130 | 0,000000 | 0,3853 |
| Mamdani | 0,239262 | 219,9130 | 0,000000 | 0,4336 |

**Sonuç:** 2 kat bağlantı hızında model riski yaklaşık %13,05 azaldı; görev süreleri toplamı %0,104 ve F %0,110 arttı. 0,5 ve 1 kat hızda bu arama bütçesiyle yöntemler tamamen yerelde kaldı; seçilen plan, F, risk ve görev süresi aynı çıktı. Planı aramak için harcanan süreler farklıdır. Katkı, risk ile süre arasındaki tercihi değiştiriyor.

[Grafik](../figures/mamdani_tradeoff.png) · [CSV tablosunu indir](mamdani_pipeline.csv)

## C — Risk azalması yalnız Mamdani sayesinde mi?

Aynı round-robin sunucu konumlarında dört oran politikasını karşılaştırdım. Oranlar analitik çözüldü. 5 veri seti × 3 bağlantı hızı × 4 politika = 60 kayıt; tam GA deneyi değildir.

### Bağlantı hızı: 2 kat

| Yöntem | Toplam maliyet F | Görev süreleri toplamı (s) | Model riski |
| --- | ---: | ---: | ---: |
| Ek sınır yok | 0,306694 | 204,7802 | 0,175890 |
| Sabit sınır | 0,314321 | 214,9523 | 0,057621 |
| Yalnız güvenlik S | 0,310962 | 210,7620 | 0,102734 |
| Tam Mamdani S/U | 0,313693 | 214,4765 | 0,058617 |

### Bağlantı hızı: 0,5 kat

| Yöntem | Toplam maliyet F | Görev süreleri toplamı (s) | Model riski |
| --- | ---: | ---: | ---: |
| Ek sınır yok | 0,139437 | 219,7683 | 0,000000 |
| Sabit sınır | 0,139503 | 219,8654 | 0,000000 |
| Yalnız güvenlik S | 0,139468 | 219,8143 | 0,000000 |
| Tam Mamdani S/U | 0,139498 | 219,8585 | 0,000000 |

### Bağlantı hızı: 1 kat

| Yöntem | Toplam maliyet F | Görev süreleri toplamı (s) | Model riski |
| --- | ---: | ---: | ---: |
| Ek sınır yok | 0,237908 | 218,5105 | 0,003346 |
| Sabit sınır | 0,238826 | 219,4521 | 0,001093 |
| Yalnız güvenlik S | 0,238372 | 218,9936 | 0,002075 |
| Tam Mamdani S/U | 0,238745 | 219,3718 | 0,001216 |

**Sonuç:** Sabit sınır da model riskini belirgin azalttı. 2 kat hızda tam Mamdani, sabit sınırdan biraz daha kısa süre ve düşük F; biraz daha yüksek risk verdi. Sonuçlar, risk düşüşünün tamamını U girdisinin özel başarısına bağlamıyor.

[Grafik](../figures/policy_controls.png) · [CSV tablosunu indir](policy_controls.csv)

## D — Sunucu seçimi sabitken oranı nasıl hesaplamalı?

Sunucuları değiştirmeden SA-PSO oran araması ile analitik oran hesabını karşılaştırdım. 5 veri seti × 3 arama tekrarı × 2 yöntem = 30 kayıt.

| Yöntem | Toplam maliyet F | Görev süreleri toplamı (s) | Model riski | Plan arama süresi (s) |
| --- | ---: | ---: | ---: | ---: |
| SA-PSO | 0,325002 | 229,9271 | 1,247517 | 0,1034 |
| Analitik | 0,237908 | 218,5105 | 0,003346 | 0,0021 |

**Sonuç:** Bu model ve bütçede analitik hesap daha düşük F ve daha kısa oran çözüm süresi verdi. Sunucu seçimi sabit olduğundan bu, bütün sistemin global optimumu veya tam GA hızlanması değildir; tam akışın sonucu E tablosundadır.

[Grafik](../figures/analytical_fixed_locations.png) · [CSV tablosunu indir](ratio_fixed_locations.csv)

## E — Analitik hesap tam GA akışında ne kazandırdı?

GA konum aramasının altında SA-PSO veya analitik oran hesabı kullandım. Aynı üst GA bütçesiyle 5 veri seti × 3 arama tekrarı × 2 yöntem = 30 kayıt.

| Yöntem | Toplam maliyet F | Görev süreleri toplamı (s) | Model riski | Plan arama süresi (s) |
| --- | ---: | ---: | ---: | ---: |
| GA + SA-PSO | 0,238117 | 218,4440 | 0,004116 | 9,7044 |
| GA + analitik | 0,236411 | 216,7583 | 0,009375 | 0,1878 |

**Sonuç:** Kaydedilen ortalama plan arama süresi 9,7044 saniyeden 0,1878 saniyeye indi: yaklaşık 51,68 kat daha kısa. F de azaldı; ancak ortalama model riski arttı. Arama süresi görevlerin çalışma süresi değildir ve makineye bağlıdır.

[Grafik](../figures/analytical_pipeline.png) · [CSV tablosunu indir](ratio_pipeline.csv)

## Deneyleri doğru yorumlamak

Bağımsız veri sayısı beştir. Aynı verideki arama tekrarları yeni veri örnekleri değildir. Özetlerin dayandığı 225 koşuluk sayısal ölçümler [küçük CSV dosyasında](recorded_runs.csv) bulunur; istatistiksel anlamlılık iddia edilmez. Üretilen görev verileri ve tam plan kayıtları yerelde tutulur.

F normalizasyonu bağlantı hızı koşuluyla değişebilir. Farklı hızların F değerlerinden tek başına iyileşme yüzdesi çıkarılmamalıdır. Arama zamanı yeniden çalıştırıldığında donanıma ve sistem yüküne göre değişir.

[Sonuçların genel görünümü](../README.md) · [Grafik galerisi](../figures/README.md)
