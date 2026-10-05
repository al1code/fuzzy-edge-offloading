# Bu Projede Ne Yapıyoruz?

Bu rehber, mevcut kodu ve çalıştırılabilir örnekleri anlamak için hazırlanmıştır.
Örnek sayılar bize aittir; makalenin deney sonuçları olarak sunulmaz.

## 1. Çözmeye Çalıştığımız Problem

Bir fabrika cihazının bir hesaplama görevi olduğunu düşün. Örneğin üretimdeki
bir ölçümün analiz edilmesi gerekiyor. Cihaz bu hesabı kendisi yapabilir veya
verinin bir kısmını yakındaki güçlü bir edge sunucusuna gönderebilir.

Kararımız iki parçadan oluşuyor:

1. Hangi sunucuya gönderelim?
2. Görevin ne kadarını gönderelim?

Görevin %40'ını sunucuya gönderirsek kalan %60 cihazda hesaplanır. Bu oranı
kodda `offloading_ratio`, makalede `x` ile gösteriyoruz. `x=0` tamamen yerel,
`x=1` tamamen sunucuda hesaplama anlamına gelir.

Hızlı sunucu her zaman en iyi seçenek değildir: veriyi iletmek zaman alır,
güvenlik riski ortaya çıkar ve aynı sunucuya çok görev yığılması kaynakları
tüketir. Makale süre, risk ve sunucular arasındaki yük dengesini birlikte
değerlendiren bir yöntem öneriyor.

Biz bu matematiksel yöntemi Python'da yeniden gerçekleştiriyoruz. Kararı
hesaplayan parçalar ve bu parçaları tekrar tekrar çağırarak uygun kararlar
arayan iki katmanlı algoritma artık çalışıyor. Deneylerimizi belgeli sentetik
girdilerle yaptık; makalenin yazarlarından alınmış veri veya aynı sayısal
sonuçlar gibi sunmuyoruz. Elle kontrol örnekleri ile deney sonuçları ayrıdır.

## 2. Mevcut Dosyalar Ne İşe Yarıyor?

| Dosya | Cevapladığı soru |
| --- | --- |
| `src/models.py` | Görevin verisi, gereken hesaplama miktarı ve sunucunun kaynakları hangi bilgilerle temsil edilir? |
| `src/config.py` | Hangi parametreleri ve hangi ağırlıkları kullanıyoruz? |
| `src/validation.py` | Gelen bilgi geçerli mi? Örneğin oran %140 olabilir mi, CPU hızı negatif olabilir mi? |
| `src/random_utils.py` | Aynı deney verilerini tekrar üretmek için rastgele sayıları nasıl kontrol ediyoruz? |
| `src/fuzzy_security.py` | Uzmanların belirsiz görüşlerinden görev güvenliği ve risk nasıl hesaplanır? |
| `src/latency.py` | Verdiğimiz offloading kararında hesaplama ve veri gönderme ne kadar sürer? |
| `src/load_balance.py` | Sunucunun CPU, bant genişliği ve belleğinin ne kadarı ayrılmıştır; sunucular ne kadar dengesiz yüklenmiştir? |
| `src/optimizers/genetic.py` | Hangi görev hangi sunucuya gönderilsin veya yerelde kalsın? |
| `src/optimizers/sapso.py` | Seçilen sunuculara görevin ne kadarı gönderilsin; iki karar katmanı nasıl birleşsin? |
| `tests/` | Küçük, sonucu önceden hesaplanmış örneklerde kod doğru sonuç veriyor mu? |
| `experiments/baseline/` | Bu parçaları birlikte nasıl çalıştırıyoruz? |

`validation.py` içindeki "experiment inputs and domain models" ifadesi,
"deney girdileri ve problemdeki görev/sunucu gibi nesneleri temsil eden
modeller" anlamına gelir. Bu dosya bir güvenlik puanı üretmez; diğer hesaplara
hatalı değerlerin girmesini önler. Örneğin negatif veri büyüklüğü reddedilir.

`random_utils.py` aynı seed ve yazılım sürümleriyle aynı rastgele diziyi üretir.
Sentetik verilerde ve arama algoritmalarında kullanılıyor. Veri üretiminin seed'i
ile karar aramasının seed'i ayrıdır: girdileri sabit tutup aramayı tekrarlayabiliriz.

## 3. Fuzzy Mantık Bu Projede Nerede?

Bir uzmanın "bu görev güvenli" demesi kesin bir ölçüm değildir. Makaledeki
yöntem bu belirsizliği üç sayıyla temsil ediyor:

```text
(alt değer, en olası değer, üst değer)
```

Örneğin `(0.1, 0.2, 0.5)` değerlendirmesinde 0.2 en olası değerlendirmedir;
0.1 ve 0.5 belirsizliğin sınırlarını belirtir. Bu üçlü bir
`TriangularFuzzyNumber` nesnesidir. 0.5 burada "%50 saldırı ihtimali" demek
değildir; modelin güvenlik değerlendirme ölçeğindeki bir değerdir.

Üç ayrı bakış açısı kullanıyoruz:

1. Görev verisi: `task_data`.
2. Görev türü: `task_type`.
3. Terminal yaşam döngüsü: `terminal_lifecycle`.

Bu sayısal alt sistem uzman görüşlerini ağırlıklandırıp fuzzy sayıları tek
puana dönüştürür. Makaledeki bu hesap, ayrı bir Mamdani/Sugeno kural motoru
kurmamızı gerektirmez. Genel ders yönergesindeki kural tabanı beklentisinin bu
makalenin MRR kapsamına nasıl uygulanacağı öğretim üyesiyle netleştirilmelidir.

## 4. Mevcut Fuzzy Örneği Adım Adım

İki sentetik uzmanımız var. İlk uzmanın ağırlığı 0.25, ikincinin 0.75.
Bu ağırlıkları biz örnek için seçtik; yazarların uzman ağırlıkları değiller.

### Adım A: Aynı Perspektifte Uzmanları Birleştir

Görev verisi için görüşler `(0.1, 0.2, 0.5)` ve `(0.4, 0.6, 0.9)`:

```text
alt      = 0.25 × 0.1 + 0.75 × 0.4 = 0.325
en olası = 0.25 × 0.2 + 0.75 × 0.6 = 0.500
üst      = 0.25 × 0.5 + 0.75 × 0.9 = 0.800
```

Birleşmiş üçlü `(0.325, 0.5, 0.8)` olur. Kod karşılığı
`aggregate_expert_assessments`; makaledeki karşılığı Denklem 11'dir.

### Adım B: Üçlüyü Tek Puana Dönüştür

Makale en olası değere daha fazla ağırlık veren dönüşümü kullanıyor:

```text
puan = (alt + 4 × en olası + üst) / 6
     = (0.325 + 4 × 0.5 + 0.8) / 6
     = 0.5208333333
```

Kod karşılığı `paper_transformation_value`; makaledeki karşılığı Denklem
12'dir. Standart centroid hesabı ayrı bir yöntemdir ve bu baseline hesapta
kullanılmaz.

### Adım C: Üç Perspektifi Birleştir

Aynı hesap diğer iki perspektif için de yapılınca:

| Perspektif | Birleşmiş üçlü | Tek puan | Örnek perspektif ağırlığı |
| --- | --- | --- | --- |
| Görev verisi | `(0.325, 0.5, 0.8)` | `0.5208333333` | `0.5` |
| Görev türü | `(0.275, 0.475, 0.725)` | `0.4833333333` | `0.3` |
| Terminal yaşam döngüsü | `(0.225, 0.325, 0.45)` | `0.3291666667` | `0.2` |

```text
güvenlik puanı = 0.5 × 0.5208333333
               + 0.3 × 0.4833333333
               + 0.2 × 0.3291666667
               = 0.47125
```

Kod karşılığı `assess_security`; makaledeki karşılığı Denklem 13'tür.
Burada uzman ağırlıkları ile perspektif ağırlıkları farklı iş yapar.
İlki kimin görüşüne, ikincisi hangi bakış açısına ne kadar önem verdiğimizi
belirler. API'nin varsayılan perspektif ağırlıkları eşit üçte birdir; örnekte
etkiyi göstermek için farklı ağırlıklar kullanılıyor.

### Adım D: Puanı Risk Değerine Dönüştür

Örnek güvenlik eşiğini 0.6 seçtik. `0.47125 < 0.6` olduğu için:

```text
eksik kalan miktar = 0.6 - 0.47125 = 0.12875
risk = 1 - exp(-0.12875) ≈ 0.1208062635
```

Puan eşikte veya daha yüksekse risk sıfır olur. Kod karşılığı
`calculate_security_risk`; makaledeki karşılığı Denklem 14'tür. Makalenin
bu denklemin altındaki cümlesi eşitsizliği ters anlatıyor; uygulama açıkça
denklemi esas alıyor.

Bu risk sayısını ölçülmüş bir saldırı olasılığı olarak yorumlamıyoruz.
Kararları karşılaştırmak için kullandığımız matematiksel risk ölçüsüdür.

### Adım E: Gönderilen Oranı Hesaba Kat

Görevin %40'ı seçilmiş sunucuya gidiyorsa:

```text
offloading riski = 0.4 × 1 × 0.1208062635 ≈ 0.0483225054
```

Ortadaki 1 sunucunun seçildiğini gösterir. Hiç veri göndermiyorsak bu
offloading risk terimi sıfırdır. Bu, cihazın gerçek dünyada her türlü
güvenlik riskinden arınmış olduğu anlamına gelmez.

## 5. Bugün Eklediğimiz Süre Hesabı

Aynı görevin veri boyutunu 1 MB, toplam hesaplama ihtiyacını 1.2 milyar
CPU çevrimi seçelim. Cihaz saniyede 1 milyar çevrim yapabiliyor; görev için
sunucuda saniyede 4 milyar çevrim ayrılıyor. Veri iletim hızı 40 Mbps.

Bu sayılar birim kontrolü ve öğrenme için seçilmiş örnek değerlerdir.
Makalenin yayınlanmış deneylerini temsil etmezler.

%40 offloading için üç ayrı süre hesaplanır:

```text
cihazda hesaplama = 0.6 × 1.2 milyar / 1 milyar = 0.72 saniye
veri gönderme    = 0.4 × 8 milyon bit / 40 milyon bit/s = 0.08 saniye
sunucuda hesap   = 0.4 × 1.2 milyar / 4 milyar = 0.12 saniye
toplam           = 0.72 + 0.08 + 0.12 = 0.92 saniye
```

1 MB'ı 8 milyon bite çevirdik. Toplam CPU ihtiyacı zaten görev modelinde
bulunduğundan onu veri boyutuyla tekrar çarpmıyoruz. Toplam süreyi makalenin
Denklem 16'sındaki gibi topluyoruz; paralel çalışma varsayımıyla maksimum
almak farklı bir model olurdu.

| Karar | Süre, saniye | Offloading riski |
| --- | --- | --- |
| Tamamen cihazda | `1.20` | `0.000000` |
| %40 sunucuda | `0.92` | `0.048323` |
| Tamamen sunucuda | `0.50` | `0.120806` |

Bu örnekte daha fazla offloading süreyi azaltırken riski artırıyor.
Hızlı olan kararı tek başına "en iyi karar" ilan edemeyiz. Bağlantıyı 4 Mbps
yaparsak tam offloading 2.30 saniye sürer; bu kez yerel hesaplama daha hızlıdır.

## 6. Sunucu Yükü Ne Demek?

Örnek sunucunun kapasitesi 8 milyar çevrim/s, 20 MHz bant genişliği ve
1024 MB bellek. Bir görev için 4 milyar çevrim/s, 5 MHz ve 256 MB ayırıyoruz:

```text
CPU kullanımı   = 4 / 8       = 0.50
bant kullanımı  = 5 / 20      = 0.25
bellek kullanımı= 256 / 1024  = 0.25
eşit ağırlıklarla yük = (0.50 + 0.25 + 0.25) / 3 = 0.333333
```

Bir kaynak kapasitesini aşan atamalar reddedilir. Boş sunucunun yükü sıfırdır.
İki sunucunun yükleri `0.333333` ve `0` olduğunda yük varyansı `1/36`, yani
yaklaşık `0.027778` olur. Bütün sunucuların yükü aynıysa varyans sıfırdır.

Kaynak rezervasyonları makaledeki gibi sunucu seçimine bağlıdır. Bu örnekte
aynı sunucu seçildiğinde %40 ve %100 offloading aynı kaynak rezervasyonunu
kullanır; yükü oranla tekrar çarpmıyoruz.

MHz bant genişliği, Mbps ise veri hızıdır. İkisi aynı şey değildir. Mevcut
örnek veri hızını açık girdi alır. `calculate_wireless_rate` ayrıca makalenin
Shannon ifadesinden hız hesaplayabilir; gürültü birimine ilişkin varsayımı
[simülasyon notlarında](simulation.md) açıklanmıştır.

## 7. Nasıl Çalıştırırım?

Proje kökünde ve aktif sanal ortamda yalnızca fuzzy hesabı:

```powershell
python -B -m experiments.baseline.fuzzy_security_demo
```

Fuzzy, süre ve yük hesaplarını birlikte görmek için:

```powershell
python -B -m experiments.baseline.offloading_demo
```

İkinci komut girdileri ve her kararın sonucunu JSON olarak gösterir. JSON'daki
`scenarios` bölümünde oranı, süre parçalarını, toplam süreyi, riski ve yükü
bulabilirsin. `security_assessment` bölümünde fuzzy ara hesaplar vardır.

Yavaş bağlantıyla yerel ve tam offloading'i karşılaştırmak için:

```powershell
python -B -m experiments.baseline.offloading_demo --link-rate-mbps 4 --ratios 0 1
```

## 8. Henüz Ne Kaldı?

Şimdiki program verdiğimiz seçenekleri değerlendiriyor; ayrıca küçük bir
senaryoda bütün seçenekleri tarayıp en uygun kararı kendisi bulabiliyor.
Büyük görev kümelerinde genetik sunucu seçimi ve SA-PSO oran araması birlikte
çalışıyor. Ortak değerlendirme fonksiyonu ve tekrarlanabilir veri üretimi mevcut.
Üretilen görevleri, yapay uzman görüşlerini ve ağ koşullarını dosyada saklayıp
aynı girdilerle yeniden çalıştırabiliyoruz. Küçük kesin kontrol çözücüsü de
eklendi; iki katmanlı arama da hazır. Temel deney ve oran maliyeti çalışması
yapıldı; aşağıdaki 9 ve 10. bölümler bunları açıklıyor.

```powershell
python -B -m experiments.baseline.exact_demo
```

Bu komut 3 görev ve 2 sunucuda 125 ihtimali kontrol eder. Sonuçtaki
`best_objective_value` en düşük amaç değeri, `best.tasks` görev kararlarıdır.
Mevcut modelde oran sabit sunucu seçiminde doğrusal etki yaptığından en az bir
optimum 0/1 oranlarında bulunur; bu, ara oranların yasaklandığı anlamına gelmez.
Ayrıntılar [kesin arama notlarında](exact_search.md).

**11 aşamalı planda 10. aşamanın seçilen deneyleri doğrulandı.** Temel program,
ilk deney ve katkı karşılaştırması var; GUI, rapor/sunum ve teslim sırada.
[Bütün aşamalar, bitiş ölçütleri ve açık konular](roadmap.md).

Genetik arama sunucu seçimlerini adaylar olarak üretir, iyi sonuç veren
adaylardan yeni seçenekler oluşturur ve en iyi bulduğu kararı korur.
Eski kontrol modunda oranlar doğrusal modelin 0/1 referansıyla hesaplanır.
Yeni `boalbfs` modunda ise SA-PSO gerçekten farklı oranlar deneyerek arama yapar;
kesin çözümü içeriden kullanmaz.

```powershell
python -B -m experiments.baseline.genetic_demo --tasks 3 --servers 2 --verify-exact
```

`best.decisions` seçilen kararlar, `history` nesiller boyunca sonuçlar,
`exact_comparison.absolute_gap` küçük örnekte kesin çözüme farktır.
[Bu adımın ayrıntılı açıklaması](genetic_search.md).

İki katmanı birlikte çalıştırmak için:

```powershell
python -B -m experiments.baseline.genetic_demo --method boalbfs --tasks 3 --servers 2 --verify-exact
```

Genetik katmanın önerisi örneğin "ilk görev yerelde, ikinci görev sunucu 2'de"
olabilir. SA-PSO bu öneri için ikinci görevin gönderilecek oranını arar.
Her denemede süre, risk ve yük tekrar hesaplanır; küçük amaç değeri tercih edilir.
Bazı geçici kötü adımları kabul etse de bulduğu en iyi sonucu kaybetmez.
`evaluations` sunucu seçimi denemelerini, `plan_evaluations` içlerindeki toplam
plan hesaplarını gösterir. Kısa arama kesin optimumu bulmak zorunda değildir.
Makalenin açıklamadığı arama ayarları [ayrı varsayım notunda](boalbfs.md) kayıtlıdır.

Kodun tüm satırları dersin zorunlu isteği değildir; test ve açıklama dosyaları
da miktarı artırır. Hesaplama kapsamını sabitledik. Son isteğinle GUI'yi de
plana aldık: deney ve katkı kodu bittikten sonra mevcut sistemi gösteren bir
arayüz hazırlayacağız; yeni bir hesaplama motoru yazmayacağız.

Hocanın belirlediği özel MRR henüz yok. Senin çalışma kapsamını seçme
yetkilendirmenle önerdiğimiz hedef, bu hesapları karar arayan bir baseline
sistemine bağlamak ve en az bir temel deneyi gerçekleştirmektir. Ayrıntılı
plan [reproduction_plan.md](reproduction_plan.md) dosyasında kayıtlıdır.

Testlerin geçmesi formüllerin seçilmiş girdilerde doğru hesaplandığını
gösterir. Makalenin deney sonuçlarını yeniden ürettiğimizi veya dersin bütün
teslim koşullarını tamamladığımızı göstermez.

## 9. Deneyler: Artık Neyi Ölçüyoruz?

Soru şu: aynı 60 görevi cihazlarda mı, sunucularda mı, yoksa seçerek iki
tarafta mı çalıştırmak daha uygun? Üç yönteme aynı görevleri, ağ koşullarını,
uzman değerlendirmelerini, kapasiteyi ve puanlama ölçüsünü veriyoruz.

Local bütün görevleri cihazda tutar. Edge bütün görevleri sunuculara gönderir;
hangi sunucunun seçileceğini genetik algoritma arar. Local-Edge ise hem
sunucuyu hem gönderilen oranı arar. Edge'in görevleri gizlice yerelde
bırakmasına izin vermiyoruz; o artık başka bir mod olurdu.

Beş farklı veri senaryosu ve her birinde üç arama tekrarı seçtik. Toplam 45
mod kaydı var. Tek bir şanslı sonucu seçmiyoruz. Önce bir senaryonun tekrarlarını,
sonra farklı senaryoları ortalıyoruz. Grafikteki çubuklar ortalamaları;
hata çizgileri senaryoların değişkenliğini gösterir, başarı garantisi değildir.

En küçük F, en hızlı işlem demek değildir. Süre, risk ve yük dengesini birlikte
değerlendiriyoruz. Programın arama süresi de görevlerin hesaplanan sürelerinin
toplamından farklı bir ölçüdür. Risk puanı gerçek saldırı olasılığı değildir.

İlk deneyde ortalama F: Local `0.239262`, Edge `0.621733`, Local-Edge `0.238117`.
Local-Edge'in yerel çalışmaya göre eşleştirilmiş ortalama kazancı yaklaşık
`%0.47`; büyük bir üstünlük iddia etmiyoruz. Bizim risk normalizasyonumuz ve
eşit ağırlıklarımız, tamamen Edge'in Local'den daha iyi F vermesini engelliyor.
Bu yüzden makalenin sıralamasını veya yüzdelerini aynen elde ettiğimizi
söyleyemeyiz. Kodu hedeflenen sonuca uydurmak yerine bu sınırı raporluyoruz.

[Protokol, dosyalar, istatistikler ve sonuçların sınırları](experiments.md).
Kaydedilen görev kararları tek tek tekrar hesaplanabilir. Deney dosyaları
yerelde kalır; GitHub'a otomatik eklenmez.

## 10. Kontrollü Katkı: Oranı Aramak mı, Hesaplamak mı?

Bu sefer sunucuları değiştirmiyoruz. Aynı görev-sunucu dağılımında yalnızca
gönderilecek oranı bulma yöntemini karşılaştırıyoruz: SA-PSO farklı oranlar
deniyor; doğrudan yöntem her görev için 0 ve 1'in maliyetini hesaplıyor.
Mevcut sabit kaynak modelinde maliyet orana göre doğrusal olduğu için bu yeterli.

Örneğin sunucuya gönderim hem zaman kazandırabilir hem risk ekleyebilir.
İkisinin ağırlıklı toplamı gönderimle artıyorsa oran 0, azalıyorsa 1 seçilir.
Bu, tüm sunucu seçimleri arasındaki en iyi kararı bulduğumuz anlamına gelmez.

30 kayıtta ortalama F, SA-PSO için `0.325002`, doğrudan hesap için `0.237908`.
Ama tüm oranları sıfır seçmek bile `0.239277` veriyor: doğrudan hesabın buna
göre kazancı yalnızca yaklaşık `%0.57`. Rastgele başlangıç ve kısa arama
bütçesinin etkisini gizlemiyoruz. [Protokol ve sonuç sınırları](ratio_comparison.md).

Bu küçük yüzde tek başına katkının tamamını anlatmıyor: önceki deney yalnızca
sunucular sabitken oran hesabını ölçüyordu. Bu yüzden aynı deney dosyasına
bir de iki katmanı birlikte çalıştıran karşılaştırma ekledik. Yeni bir motor
veya algoritma ailesi yazmadık.

İki çözüm de 100 sunucu-dağıtımı adayı değerlendiriyor. İlki her adayın
gönderim oranlarını SA-PSO ile arıyor; ikincisi doğrusal modelden hesaplıyor.
İkinci yöntemin puanları farklı olduğundan GA'nın ileride seçtiği sunucular
da farklı olabilir. Aynı seed, bütün adayların aynı olmasını garanti etmez.

15 eşleşmede 12 daha iyi, 3 eşit sonuç var. Ortalama F `0.238117`'den
`0.236411`'e indi; eşleştirilmiş ortalama düşüş yaklaşık `%0.71`.
Ortalama görev süreleri toplamı `218.44` saniyeden `216.76` saniyeye indi;
bu, bilgisayarda programın çalışma süresi değil, görev sürelerinin modeldeki
toplamıdır. Yük daha dengeli; fakat model riskinin ortalaması biraz daha
yüksek. "Her şeyi iyileştirdik" demiyoruz.

Asıl kazanç karar aramasında: son ölçümde iki katmanın birlikte araması
ortalama `9.70` saniye yerine `0.19` saniye sürdü, yaklaşık `52` kat fark.
Bu, görevlerin 52 kat hızlı çalıştığı veya programın her bölümünün hızlandığı
anlamına gelmez. Aynı girdilerde uygun bir karar aramak için daha az hesap
yapıyoruz. Veri/fuzzy üretimi ve dosya yazma bu zaman ölçümüne dahil değil.
Bu yüzden katkıyı yalnızca küçük kalite yüzdesiyle tarif etmiyoruz; hesaplama
maliyetini düşüren, sonuçları kontrol edilmiş bir mühendislik değişikliği.

## 11. Dinleyiciye Nasıl Anlatacağım?

1. Problem: cihazın işi sunucuya göndermesi her zaman kazançlı değildir;
   iletim zaman alır, güvenlik riski ve sunucu yükü oluşur.
2. Bulanık bölüm: uzmanların belirsiz görüşlerini üçgensel sayılarla temsil
   edip görev için güvenlik/risk puanı hesaplarız. Bu, saldırı tahmini değildir.
3. Makale yöntemi: GA sunucuyu, SA-PSO gönderilecek oranı arar;
   süre, risk ve yük birlikte puanlanır.
4. Bizim değişikliğimiz: sabit kaynak modelinde oran maliyeti doğrusal olduğu
   için oranı aramak yerine iki uç noktadan hesaplarız. Sunucu araması kalır.
5. Kanıt: aynı görevler ve aynı GA bütçesiyle iki çözümü karşılaştırırız;
   karar kalitesi, arama süresi ve artan risk dahil sonuçları gösteririz.
6. Sınır: veriler sentetik, model varsayımları belgeli; bütün fabrikalarda
   üstünlük veya küresel optimum iddiası yok. Yeni bir fuzzy yöntem icat etmedik.

Son kod adımı olan GUI bu sırayı izleyecek: tek görev/fuzzy hesabı, görev ve
sunucu kararları, ardından karşılaştırma. Mevcut motoru gösterecek; rapor,
literatür, AI bildirimi ve temiz ortam kontrolü ayrıca tamamlanacak.
