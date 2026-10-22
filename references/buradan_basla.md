# Projeyi anlamaya buradan başla

## 1. Bir cümlede ne yapıyoruz?

Bir fabrika cihazındaki hesaplama işinin **ne kadarını cihazda tutup ne
kadarını hangi uç sunucuya göndereceğimize** karar veren bir simülasyon
geliştiriyoruz. Gerçek cihazlara iş göndermiyoruz. Veriler sentetik.

Sunucu hızlı olabilir, fakat veriyi göndermek zaman alır. İşin dışarıya
gönderilen kısmı modelde güvenlik riski taşır. Herkes aynı sunucuyu seçerse
kaynak kapasitesi veya yük dengesi sorun olur. Program bu etkileri birlikte
değerlendirir.

## 2. Makaledeki yöntem ne yapıyordu?

Üç karar örneği:

| Karar | Anlamı |
| --- | --- |
| Local; x=0 | İşin tamamı cihazda |
| edge-001; x=0.4 | İşin %40'ı bu sunucuda, %60'ı cihazda |
| edge-002; x=1 | İşin tamamı ikinci sunucuda |

Makaledeki üç güvenlik perspektifi **Task Data, Task Type, Terminal
Lifecycle**. Uzmanlar her perspektife `(alt, olası, üst)` üçgeni verir.
Kod uzman ağırlıklarıyla bu üçgenleri birleştirir, her birini
`(alt + 4*olası + üst)/6` ile puana dönüştürür ve perspektif puanlarını
ağırlıklandırarak **S** güvenlik seviyesini bulur.

`S < eşik` olduğunda model riski pozitiftir; eşik veya üstünde sıfırdır.
Gönderim riski bu riskin gönderilen oranla çarpımıdır. Bu, gerçek saldırı
olasılığı ölçümü değildir. Makale yönteminde ayrı Mamdani kural tabanı yoktur.

**BOALBFS:** Üstte GA (genetik algoritma) sunucu/yerel konumu arar; altta
SA-PSO seçilen sunuculara ne kadar gönderileceğini arar. Birçok aday plan
denenir; en düşük **F** değerine sahip uygun plan saklanır. F; normalize
toplam süre, normalize model riski ve sunucu yük varyansının ağırlıklı
toplamıdır. F bir başarı yüzdesi değildir. Kaynak denklemleri ve belirsiz
birim yorumları `simulation.md` / `paper_alignment.md` içindedir.

## 3. Bizim katkımız ne?

**Ana katkı: genişlik-duyarlı Mamdani oran sınırı.** Özgün güvenlik skoru S
korunur. Buna, birleştirilen üçgenlerin ortalama genişliği **U** eklenir.
`S` ve `U` düşük/orta/yüksek üyeliklerine ayrılır. Dokuz kural min-AND,
max birleştirme ve centroid ile bir **izinli en yüksek gönderim oranı** üretir.
Ardından aynı GA/SA-PSO motoru bu sınıra uyar.

Somut örnek: her üç perspektif için aynı üçgeni kullanalım.

| Üçgen | S | U | Mamdani üst sınırı, yaklaşık |
| --- | ---: | ---: | ---: |
| (0.7, 0.7, 0.7) | 0.7 | 0 | %73.88 |
| (0.4, 0.7, 1.0) | 0.7 | 0.6 | %41.61 |

Bunlar gerçek hesaplanan açıklama örnekleridir; makalenin deney sonucu değildir.
Makale dönüşümü iki üçgene aynı S'yi verirken bizim politika genişlik farkını
da kullanır. Üst sınır %41.61 ise optimizer %0–41.61 arasında arar; tam
%41.61 göndermesi gerekmez.

U, **uzmanlar arası anlaşmazlık** değildir. Biri kesin 0, diğeri kesin 1 veren
iki uzmanın da kendi üçgeni sıfır genişliklidir; birleşik U yine sıfır olur.
Kural tabanı ve üyelik şekilleri tasarım tercihleridir. Her ara noktada
“U artarsa oran mutlaka azalır” garantisi yoktur. Düşük güvenlikte kırpılan
çıktının centroid'i küçük dalgalanmalar gösterebilir.

**İkinci çalışma: analitik oran hesabı.** Bu modelde sunucu sabitken F,
oran bakımından doğrusaldır. En iyi oran uç noktadadır: 0 veya izinli üst
sınır. Analytical bu özelliği kullanıp SA-PSO yerine oranı doğrudan seçer.
Bu, bütün sunucular için global optimumu bulduğu anlamına gelmez. Tamamlayıcı
bir hesaplama maliyeti/karşılaştırma çalışmasıdır.

**GUI**, bu yöntemleri görüp deneyebilmemizi sağlar. Arayüz tek başına
bilimsel katkının veya üstünlüğün kanıtı değildir.

## 4. Katkı önemli mi?

Ders düzeyinde teknik olarak savunulabilir: ek bir girdi, yorumlanabilir
kurallar, gerçek optimizer kısıtı ve karşılaştırmalı deney var. Genişlik
bilgisinin skora indirgenirken kaybolması üzerinden gerekçelendirilebilir.

Bilimsel etki için mevcut kanıt sınırlı. Daha az göndermek zaten riski
azaltabilir; sabit bir oran sınırı da benzer sonuç üretiyor. 22 Ekim
deneylerinde bazı koşullarda hiç fark çıkmadı, bazılarında risk azalırken
süre/F kötüleşti. Gerçek saldırı verisi, endüstriyel doğrulama ve literatürde
benzersizlik kanıtı yok. Savunulabilecek iddia şudur:

> Güvenlik değerlendirmesinin genişliğini ayrıca kullanan bir gönderim
> politikası geliştirdik; hangi koşullarda ne kadar aktarım, süre ve model
> riski değişimi ürettiğini kontrollü deneylerle inceledik.

“Her zaman daha güvenli/hızlı”, “makaleyi geçtik” veya “yeni güvenlik garantisi”
iddiaları kullanılmamalı. Gerçek sayılar [inceleme notunda](inceleme_2026_10_22.md).

## 5. GUI'de ayarlar neyi değiştirir?

Yeni açılış: **Projeyi Anla**, seed 42, 3 görev, 2 sunucu. Küçük başlangıç
yalnız GUI tercihidir; CLI deney varsayılanı hâlâ 60/3.

| Kontrol | Gerçek etkisi | Ne zaman uygulanır? |
| --- | --- | --- |
| Veri seed | Sentetik çekimleri değiştirir; diğer ayarlar/sürümler de aynıysa tekrar edilir | Senaryoyu oluştur |
| Görev sayısı | İş yükü ve veri boyutu değişir | Senaryoyu oluştur |
| Sunucu sayısı | Seçenekler/toplam kapasite değişir; aynı seed ile bazı link çekimleri de değişebilir | Senaryoyu oluştur |
| Güvenlik eşiği | Sabit S için eşiğin yükselmesi görev riskini azaltmaz | Senaryo formu veya Bulanık Güvenlik formu |
| Uzman üçgenleri/ağırlıkları | S ve U; ardından risk ve Mamdani sınırı değişebilir | Bulanık girdileri uygula |
| Süre/risk/yük ağırlıkları | Hangi planın tercih edildiği değişir; veriler değişmez | Ayarları uygula, sonra çözümleri tekrar çalıştır |
| Kaynak yük ağırlıkları | CPU/bant/belleğin yük hesabına etkisi değişir | Ayarları uygula |
| Cihaz CPU | Sabit iş için yerel hesap süresi değişir | Senaryoyu oluştur |
| Görev CPU tahsisi | Edge hesap süresini ve sunucudaki rezervasyonu değiştirir | Senaryoyu oluştur |
| Toplam sunucu CPU/bellek/bant | Hangi atamaların kapasiteye sığdığını değiştirir | Senaryoyu oluştur |
| Güç, kanal kazancı, gürültü | Kablosuz link hızı ve iletim süresi değişir | Senaryoyu oluştur |
| Envanter Mbps / deadline | Mevcut modelde bilgi alanı; link hızı veya deadline kısıtı değildir | Hesap sonucunu değiştirmemesi normal |
| Arama seed | Aynı veride aramanın rastgele adımlarını değiştirir | Ayarları uygula, çözümleri tekrar çalıştır |
| GA birey/nesil, SA-PSO parçacık/iterasyon | Arama bütçesi ve süresi değişir; optimum garantisi vermez | Aynı |
| Tek görev gönderim sürgüsü | Bir görevin süre bileşenlerini inceler | Tam planı değiştirmez |
| Mamdani S/U sürgüleri | Bağımsız kural motoru denemesi | Veri veya optimizer girdisini değiştirmez |
| Deney hız koşulu 0.5x/1x/2x | Kaydedilmiş koşulu seçer; farklı hızları tek ortalamada karıştırmaz | Deney Kayıtları |

Ağırlık alanları toplamlarına bölünür: `1/1/1` ve `30/30/30` aynı tercihtir.
Gerçek yüzdeler özetin altında gösterilir. Yeni senaryo veya ayar uygulanınca
eski sonuçlar geçersizleşir; tekrar hesaplamak gerekir.

## 6. Sık kafa karıştıran sonuçlar

- **Risk ve yük hep sıfır:** gösterilen plan Local olabilir. Sunucuya iş
  gitmeyince bunların sıfır olması beklenir. Karşılaştırmayı çalıştırıp planı seç.
- **Bir görev sürgüsünü değiştirdim, üst kartlar aynı:** üst kartlar tam planı,
  aşağıdaki hesap tek görevi gösterir.
- **Mamdani sürgüsünü oynattım, karşılaştırma aynı:** sürgüler önizlemedir.
  Gerçek üçgenleri Bulanık Güvenlik formundan değiştirip uygula.
- **Hız artınca F yükseldi:** yeni senaryoda normalizasyon referansları da
  değişebilir. Hız koşulları arasında ham süre/risk ve normalizerleri incele;
  tek başına F farkından iyileşme yüzdesi çıkarma.
- **Oran sıfır ama sunucu yükü var:** model rezervasyonu seçili sunucuya (`y`)
  bağlar. Sunucu seçili olup oran sıfırsa rezervasyon kalır. Local seçiminde
  sunucu seçilmez. Bu, belgelenmiş model varsayımıdır.
- **Daha güçlü bilgisayarda farklı süre:** modeldeki görev süresi ile Python'ın
  çözümü ararken harcadığı gerçek süre farklı ölçütlerdir.
- **Mamdani F'yi yükseltti:** daha kısıtlı arama iyi bir aktarımı engellemiş
  olabilir. Bu sonuç gizlenmez; risk/gecikme tercihiyle birlikte açıklanır.

## 7. Kodu okuma sırası ve görevleri

| Dosya | Cevapladığı soru |
| --- | --- |
| `src/models.py`, `src/config.py` | Girdi nedir, birimi ve geçerlilik koşulu ne? |
| `src/fuzzy_security.py` | Uzman üçgeninden S ve risk nasıl çıkar? |
| `src/latency.py` | Cihaz, iletim ve sunucu süreleri nasıl hesaplanır? |
| `src/load_balance.py`, `src/objective.py` | Yük ve F nasıl hesaplanır? |
| `src/evaluation.py` | Verilen tam plan uygun mu, toplam sonucu ne? |
| `src/optimizers/genetic.py`, `sapso.py` | Daha iyi planı nasıl ararız? |
| `src/optimizers/locations.py`, `exact.py` | Küçük/doğrusal problemi nasıl bağımsız kontrol ederiz? |
| `src/fuzzy_controller.py` | Bizim S/U → üst oran politikamız ne? |
| `src/synthetic.py`, `dataset_io.py`, `random_utils.py` | Aynı gerçek girdileri nasıl üretip saklarız? |
| `gui/services.py`, `dashboard.py` | Hesapları ekrana nasıl bağlarız? |
| `experiments/` | Adil karşılaştırmayı nasıl kaydederiz? |

Önce hesaplayıcıları anla; optimizer'ın her iç satırını bir anda öğrenmeye
çalışma. `evaluation.py` bir planı **hesaplar**, optimizer farklı planları
**arar**. Bu ayrım kodu okumayı kolaylaştırır.

## 8. On dakikalık demo provası

Depo kökünde PowerShell:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

1. Projeyi Anla ekranındaki örneği oku.
2. Görev ve Sunucular'da bir görev için oranı %0, %50, %100 yap; üç süreyi açıkla.
3. Bulanık Güvenlik'te S ile eşiği karşılaştır; bir gerçek üçgeni değiştirip uygula.
4. Çözüm Karşılaştırması'nda Local, BOALBFS ve önerilen Mamdani'yi çalıştır.
   F, ham süre ve riski birlikte karşılaştır; aynı çıkarsa bunu açıkla.
5. Mamdani Katkısı'nda S=0.7 için U=0 ve U=0.6 kural önizlemelerini karşılaştır.
6. Deney Kayıtları'nda 0.5x/1x/2x koşullarını ayrı incele.

Başarı ölçütü yalnız programın açılması değildir: sonucu ve sınırlarını
açıklayabilmelisin. 27 Ekim'e kadar rapor, kaynakça, AI bildirimi ve sunum
dosyası da teslim edilmeli; 3 Kasım sunumların başlangıcıdır.
