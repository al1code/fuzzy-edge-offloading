# Kod kapanışı ve sunumda gösterilecek dört örnek

## Kod aşaması ne zaman bitti sayılır?

**23 Ekim 2026: seçilen uygulama kapsamını dondurabiliriz.** Bu karar bütün
ders projesinin veya öğretim üyesinin projeye özel MRR onayının tamamlandığı
anlamına gelmez. Rapor, sunum, literatür, teslim ve savunma ayrıca hazırlanır.

Kapanış ölçütleri ve kanıtları:

- Baseline hesabı, GA/SA-PSO, Mamdani kısıtı ve kayıt/tekrar oynatma çalışıyor.
- **GUI dahil 778 test geçti, 54.60 s.** Önceki yerel soket engeli normal
  Windows izinleriyle aşıldı. Günlük: `results/audit_20261023/all-tests.txt`.
- Ruff kod ve biçim denetimleri temiz; 69 Python dosyası biçime uygun.
- Çoklu koşu ve ablation sonuçları kayıtlı; katkının etkisi/sınırları açık.
- Aşağıdaki örnekler gerçek çekirdek/GUI servisleriyle hesaplandı.

**Dondurulan kapsam:** makaledeki çekirdek yöntem, ayrı Mamdani oran politikası,
yardımcı analitik kontrol, kayıtlı karşılaştırmalar ve mevcut GUI. Bundan sonra
kod tarafındaki değişiklikler gerekli hata düzeltmeleriyle sınırlı tutulmalı.
Yeni optimizer veya özellik eklemek raporun ön koşulu değildir.

## Hazırlık: bütün örnekler aynı başlangıçtan

Depo kökünde:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Temiz bir oturumda aşağıdaki ayarlarla başla; önceki denemelerde kaynak/kanal
ayarlarını değiştirdiysen uygulama sunucusunu durdurup yeniden açarak varsayılan
oturuma dön. Bu örnekler sentetik açıklama örnekleridir, makalenin deney sonucu değildir.

| Ayar | Değer |
| --- | --- |
| Veri seed | 42 |
| Görev / sunucu | 3 / 2 |
| Güvenlik eşiği | 0.60 |
| Cihaz CPU | 3 milyar çevrim/s; yalnız son örnekte 1 yapılacak |
| Görev CPU tahsisi | 10 milyar çevrim/s |
| Amaç ağırlıkları | Süre/risk/yük eşit: her biri yaklaşık %33.33 |
| Kaynak yük ağırlıkları | CPU/bant/bellek eşit |
| Arama seed | 0 |
| GA birey / nesil / elit | 12 / 8 / 1 |
| SA-PSO parçacık / iterasyon | 8 / 15 |
| Diğer kaynak/kanal/operatör ayarları | Varsayılan |

Senaryo girdilerinden **Senaryoyu oluştur**; arama ayarlarını değiştirdiysen
**Ayarları uygula** düğmesine bas. Yeni senaryo eski arama sonuçlarını temizler.

## 1. İşin hangi kısmı nerede hesaplanıyor?

**Ekran:** Görev ve Sunucular. `task-0001` ve `edge-001` seç.
**Tek görev gönderim oranı (%)** sürgüsünü sırayla 0, 50, 100 yap.

| Gönderim | Cihaz (s) | İletim (s) | Sunucu (s) | Toplam (s) |
| --- | ---: | ---: | ---: | ---: |
| %0 | 4.9209 | 0 | 0 | 4.9209 |
| %50 | 2.4605 | 1.6055 | 0.7381 | 4.8041 |
| %100 | 0 | 3.2109 | 1.4763 | 4.6872 |

**Söyleyeceğin:** “Daha fazla gönderince cihazın işi azalıyor, fakat iletim
ve sunucu süresi ekleniyor. Model bu üç süreyi topluyor. Bu görevde tam
gönderim biraz daha hızlı; optimizer ayrıca risk ve yükü değerlendirecek.”

Üstteki özet kartları tam plana aittir; tek görev sürgüsü bunları değiştirmez.
Bu tablonun görevi kapasiteye uygun bütün planı optimize etmek değildir.

## 2. Güvenlik eşiği neyi değiştiriyor?

**Ekran:** Bulanık Güvenlik. İlk görevi seç. Üçgenleri ve ağırlıkları
değiştirme. Bu ekranın içindeki **Güvenlik eşiği** sürgüsünü değiştirip her
seferinde **Bulanık girdileri uygula** düğmesine bas.

| Eşik | Güvenlik puanı S | Görev riski mu |
| --- | ---: | ---: |
| 0.40 | 0.565143 | 0 |
| 0.60 | 0.565143 | 0.034257 |
| 0.80 | 0.565143 | 0.209316 |

**Söyleyeceğin:** “Görev aynı; güvenlik değerlendirmesi değişmedi. Kabul
eşiğini yükselttim. S, eşiğin altında kaldıkça modelin atadığı risk büyüyor.”

Bu **görev riskidir**. Local planın üst kartındaki toplam gönderim riski
hâlâ sıfır olabilir: cihazda kalan işin dışarıya gönderim maruziyeti yoktur.
Sonraki örnekler için eşiği **0.60** yapıp tekrar uygula.

## 3. Bizim eklediğimiz Mamdani katmanı ne yapıyor?

**Ekran:** Mamdani Katkısı → Canlı 'ne olurdu?' denetimi.

| Güvenlik puanı S sürgüsü | Belirsizlik U sürgüsü | Canlı izinli en yüksek oran |
| --- | --- | ---: |
| 0.70 | 0.00 | yaklaşık %73.88 |
| 0.70 | 0.60 | yaklaşık %41.61 |

**Söyleyeceğin:** “Güvenlik puanını sabit tuttum. Değerlendirmenin genişliği
artınca bu örnekte Mamdani daha düşük bir gönderim sınırı verdi. Altındaki
tablo, hangi kuralların ne güçle çalıştığını gösteriyor.”

Örnek kural: **güvenlik yüksek ve belirsizlik orta ise izin orta**.
AND için min, çıktı birleştirme için max, son sayıyı üretmek için centroid
kullanılıyor. Yüzde, gönderilmesi zorunlu oran değildir; izinli üst sınırdır.

Bu iki sürgü **yalnız önizlemedir**; gerçek görev girdisini ve tam planı
değiştirmez. Sonraki örnek özgün görev üçgenlerini kullanır. U, üçgen genişliği
göstergesidir; uzmanlar arası anlaşmazlık veya saldırı olasılığı değildir.

## 4. Katkı gerçek kararı nasıl değiştiriyor?

Soldaki **Kaynaklar ve kablosuz bağlantı** bölümünde yalnız
**Cihaz CPU (milyar çevrim/s)** değerini **3 → 1** yap.
Seed=42, görev=3, sunucu=2, eşik=0.60 kalmalı. **Senaryoyu oluştur** düğmesine bas.

**Ekran:** Çözüm Karşılaştırması.
Local, BOALBFS ve Önerilen / belirsizlik-duyarlı Mamdani seçili olsun.
**Seçili çözümleri çalıştır** düğmesine bas.

Yukarıdaki arama ayarlarıyla doğrulanan sonuçlar:

| Yöntem | F | Görev süreleri toplamı (s) | Toplam model riski |
| --- | ---: | ---: | ---: |
| Local | 0.333333 | 46.1656 | 0 |
| BOALBFS | 0.293508 | 36.0901 | 0.034257 |
| Mamdani | 0.320241 | 42.8530 | 0.011263 |

Üstteki **Gösterilen plan** listesinden BOALBFS ve Mamdani'yi sırayla seç.
Görev ve Sunucular veya Mamdani Katkısı ekranındaki plan ayrıntısında
`task-0001` gönderimini göster:

- BOALBFS: **%100**, edge-001.
- Mamdani: **yaklaşık %32.88**, edge-001.
- Görevin gerçek S≈0.565143, U≈0.562663 girdileri bu %32.88 sınırını üretir;
  üçüncü örnekteki S=0.70 önizlemesi burada kullanılmaz.

**Söyleyeceğin:** “Cihaz yavaşlayınca sunucuya gönderim anlamlı oldu.
Normal yöntem ilk görevi tamamen gönderdi. Eklediğimiz politika oranı
sınırladı. Model riski azalırken cihazda daha çok iş kaldı ve süre arttı.
Bu örnekte en düşük F baseline'da; katkı daha temkinli bir karar üretiyor.”

Toplam görev süreleri Python'ın arama süresi veya paralel fabrika bitiş
zamanı değildir. Tek bir örnek genel üstünlük kanıtı değildir. Bilimsel
değerlendirmede kayıtlı çoklu-seed karşılaştırmaları da gösterilir.

## Sunumda neleri gösterelim?

GUI için **bu dört ekran yeterli**. Diğer ayrıntılar soru-cevap için kalabilir.

| Sunum parçası | Süre | Gösterilecek |
| --- | --- | --- |
| Problem ve motivasyon | 2 dk | Cihaz / ağ / sunucu çizimi |
| Literatür ve özgün yöntem | 3 dk | Doğrulanmış çalışmalar, S hesabı, GA/SA-PSO akışı |
| Bizim katkımız | 3 dk | S/U, dokuz kural ve gönderim üst sınırı |
| Deney tasarımı ve sonuç | 3 dk | Aynı veri/bütçe, çoklu-seed sonuç ve ablation tablosu |
| Canlı demo | 4 dk | Yukarıdaki dört örneğin kısa gösterimi |
| Sınırlılıklar ve sonuç | 2 dk | Sentetik veri, varsayımlar, ödünleşim ve kanıtın sınırı |

Toplam yaklaşık **17 dakika**. 27 Ekim'e kadar rapor, sunum dosyası ve GitHub
bağlantısı hazırlanıp teslim edilmeli. Kod dondurma, bundan sonra bu belgeleri
ve anlatımı önceliklendirmek içindir. 3 Kasım sunumların başlangıcıdır.
