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

Biz bu matematiksel yöntemi Python'da yeniden gerçekleştiriyoruz. Şu aşamada
verdiğimiz kararı hesaplayan parçalar çalışıyor. İleride bir optimizasyon
algoritması bu parçaları tekrar tekrar çağırarak uygun kararları arayacak.

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
| `tests/` | Küçük, sonucu önceden hesaplanmış örneklerde kod doğru sonuç veriyor mu? |
| `experiments/baseline/` | Bu parçaları birlikte nasıl çalıştırıyoruz? |

`validation.py` içindeki "experiment inputs and domain models" ifadesi,
"deney girdileri ve problemdeki görev/sunucu gibi nesneleri temsil eden
modeller" anlamına gelir. Bu dosya bir güvenlik puanı üretmez; diğer hesaplara
hatalı değerlerin girmesini önler. Örneğin negatif veri büyüklüğü reddedilir.

`random_utils.py` aynı seed ile aynı rastgele diziyi üretir. Bugünkü küçük
örneklerde sabit sayılar kullanıldığı için bu yardımcı henüz veri üretmiyor.
Çok görevli deney verilerini oluştururken kullanılacak.

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

Şimdiki program verdiğimiz seçenekleri değerlendiriyor. Büyük bir görev
kümesinde uygun sunucuları ve oranları otomatik seçme kısmı henüz yazılmadı.
Sıradaki işler ortak değerlendirme fonksiyonu, tekrarlanabilir veri üretimi,
optimizasyon, makale deneyi ve özgün katkının karşılaştırılmasıdır.

Hocanın belirlediği özel MRR henüz yok. Senin çalışma kapsamını seçme
yetkilendirmenle önerdiğimiz hedef, bu hesapları karar arayan bir baseline
sistemine bağlamak ve en az bir temel deneyi gerçekleştirmektir. Ayrıntılı
plan [reproduction_plan.md](reproduction_plan.md) dosyasında kayıtlıdır.

Testlerin geçmesi formüllerin seçilmiş girdilerde doğru hesaplandığını
gösterir. Makalenin deney sonuçlarını yeniden ürettiğimizi veya dersin bütün
teslim koşullarını tamamladığımızı göstermez.
