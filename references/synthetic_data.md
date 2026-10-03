# Tekrar Uretilebilir Sentetik Senaryolar

## Bu Adimda Ne Yapiyoruz?

Artik her gorevi tek tek elle tanimlamak yerine gorev, uzman ve kanal
girdilerini bir tohumdan uretiyoruz. Ayni ayarlar, uretici surumu ve kayitli
ortamda ayni veriler olusur. Farkli algoritmalarin farkli gorevlerle
karsilastirilmasini onlemek icin uretilen gercek girdileri JSON'da sakliyoruz.

Bu, bir **sayisal yontem uygulama senaryosudur**. Gercek fabrika verisi,
yazarin ozgun veri seti veya makale sonucunun birebir tekrari degildir.
Dagilimlar gercek is yuklerinden kalibre edilmemistir. Baseline algoritmasi
ve yayinlanmis deney karsilastirmasi henuz tamamlanmamistir.

## Dosyalar ve Akis

- `src/config.py`: `PositiveRange` ve `SyntheticScenarioConfig` ile tum
  uretim ayarlari; eski `ExperimentConfig` varsayilanlari korunur.
- `src/synthetic.py`: Yerel NumPy ureticisi, ham uzman degerlendirmeleri,
  hesaplanan senaryo, ortak normalizasyon ve ortam bilgisi.
- `src/dataset_io.py`: Surumlu JSON kaydi, butunluk kontrolu ve yeniden okuma.
- `experiments/baseline/synthetic_demo.py`: Uretme/okuma ve verilen basit
  dagitimlarin uygulanabilirlik kontrolu. Optimizasyon yapmaz.

```text
tohum + ayarlar
  -> veri boyutu / CPU isi / bant / bellek / uzman ucgenleri / kanal kazanci
  -> mevcut fuzzy fonksiyonundan guvenlik seviyesi
  -> mevcut Shannon fonksiyonundan baglanti hizi
  -> ortak senaryo ve normalizasyon
  -> ayni senaryoda verilen kararlarin degerlendirilmesi
```

## Varsayilan Parametrelerin Kaynagi

[Makale Table 4](https://www.nature.com/articles/s41598-024-79464-2/tables/4)
ile ayni bildirilen degerleri kullandigimiz alanlar: yerel CPU 3 GHz,
gorev basina edge CPU 10 GHz, guc 100 mW, bellek 1024 MB, bant kapasitesi
20 MHz ve esit perspektif/amac/yuk agirliklari. CPU frekanslari bu modelde
dongu/s girdisi olarak yorumlanir. Gorev/sunucu sayilari yayin araliklarinin
alt sinirindan secilir; bunlar yazarin sabit deney ayarlari degildir.

| Ayar | Varsayilan | Durum |
| --- | --- | --- |
| Tohum | 42 | Proje secimi |
| Gorev / sunucu | 60 / 3 | Yayin araliklarindan secim; kucuk testler de desteklenir |
| Guvenlik esigi | 0.6 | Yayin araligindan proje secimi |
| Toplam sunucu CPU butcesi | 200e9 dongu/s | Proje varsayimi, 2048 MIPS'in donusumu degil |
| Uzmanlar | 3, esit agirlikli | Proje varsayimi |
| Veri boyutu | U(0.5, 5) MB | Proje varsayimi |
| CPU katsayisi C_i | U(200, 800) dongu/bit | Proje varsayimi |
| Gorev bant rezervasyonu | U(0.25e6, 1e6) Hz | Proje varsayimi |
| Gorev bellek rezervasyonu | U(8, 32) MB | Proje varsayimi |
| Kanal genlik kazanci | U(0.0001, 0.001) | Proje varsayimi; formulde karesi kullanilir |
| Gurultu spektral yogunlugu | 1e-17 W/Hz | Proje varsayimi, -100 dBm'in W/Hz karsiligi degil |
| Envanter link alanlari | 100 Mbps | Metadata; gorev link hizi bununla uretilmez |
| Son tarih | 30 s | Metadata; amac/kisitlara eklenmez |

U(a,b), surekli uniform cekimdir; esit sinirlar sabit deger verir. 1 MB
8 milyon bittir. CPU isi `data_size_mb * 8_000_000 * C_i` olarak hesaplanir.
Kayit, toplam dongu sayisini ve ayrica ham C_i'yi korur.

Makalede toplam CPU kapasitesinin MIPS, gorev CPU'sunun GHz verilmesi
nedeniyle ikisi otomatik olarak esdeger kabul edilmez. 200e9 toplam butce,
20 adet 10e9 tahsisi destekleyen acik bir sayisal secimdir; fiziksel bir
200 GHz cekirdek iddiasi degildir. Varsayilan 60/3 round-robin dagitiminda
sunucu basina 20 gorev duser. Gorev sayisi artarken kapasite kendiliginden
artirilmaz. 140/3 icin tam round-robin offloading bu butceyi asar.

Gurultu icin de yayindaki -100 dBm degerini Hz basina oldugunu varsayip
kopyalamiyoruz. Bu iki belirsizligin etkisi ileride duyarlilik deneyleriyle
incelenmelidir. JSON'daki ayarlar degistirildiginde gercek secilen degerler
kaydedilir; bu tablonun kaynak aciklamasi yalnizca varsayilanlar icindir.

## Yapay Uzmanlar Nasil Uretiliyor?

Her gorev, her uzman ve uc perspektif icin uc bagimsiz U[0,1) sayisi cekilip
siralanir: en kucuk `low`, ortadaki `modal`, en buyuk `high` olur. Bu,
ucgen parametreleri icin bir sayisal test dagilimidir; bilesenlerin her biri
ayri ayri uniform dagiliyor demek degildir. Table 3'un High/Medium/Low
etiketleri olarak sunulmaz. Uzman sayisi agirlik dizisinin uzunlugudur.

Guvenlik seviyesini dogrudan rastgele cekmiyoruz. Ham ucgenler mevcut
`assess_security` fonksiyonundan gecerek degerlendiriliyor. Boylece fuzzy
modul gercek akis icinde kullaniliyor ve hesap geriye dogru izlenebiliyor.
Farkli uzman/perspektif agirliklari API'den verilebilir. Esik degisimi,
ayni tohumdaki gorevleri veya kanal girdilerini yeniden degistirmez.
Uzman sayisini degistirmek ise cekim sayisini degistirir; ayni tohum tek
basina diger girdileri sabit tutmaz. Boyle bir duyarlilik deneyinde kayitli
fiziksel senaryo korunmali ve yalnizca arastirilan guvenlik degerlendirmesi
degistirilmelidir.

## Tekrarlanabilirlik ve Dosya Butunlugu

Uretici `create_random_state` ile bagimsiz bir NumPy ureticisi kullanir;
global Python/NumPy rastgele durumlarini degistirmez. Surum adi
`uniform-numeric-v1`dir. Cekim sirasi: her gorev icin D, C, bant, bellek,
ardindan uzman/perspektif ucgenleri; tum gorevlerden sonra gorev-oncelikli,
sunucu-ikincil sirada kanal kazancidir. Bu sirayi degistirmek bir uretici
surumu degisikligi gerektirir.

JSON su bilgileri saklar: butun ayarlar ve tohum, gercek gorev/sunucu/link
degerleri, ham uzman ucgenleri, C_i degerleri, kanal kazanclari, ortak
normalizasyon sabitleri, Python/NumPy/rastgele uretici bilgisi ve sema surumu.
Eksik alanlar bugunun varsayilanlariyla doldurulmaz. NaN/Infinity, yinelenen
alanlar, bilinmeyen surumler ve tutarsiz hesaplar reddedilir.

SHA-256, sirali anahtarlara sahip standartlastirilmis JSON girdilerini ve
metadata'yi kapsar. Dosya yolunu veya zamani kapsamaz; bu nedenle ayni veri
yeni bir dosya adiyla ayni kimligi alir. Bu bir kazara degisiklik kontroludur,
verinin yazardan geldigine veya dogruluguna dair dijital imza degildir.

Yeniden okumada yeni rastgele cekim yapilmaz. Kaydedilen gercek link hizlari,
guvenlik seviyeleri ve normalizasyonlar kullanilir; girdilerle tutarliligi
kontrol edilir. Hesap kontrolunde 1e-12 goreli tolerans vardir; guvenlik
seviyesi icin ayrica 1e-15 mutlak tolerans kullanilir. Ortam bilgisi, okuyan
bilgisayarin surumuyle degistirilmez. Tohum tek basina farkli kutuphane
surumleri arasinda ayni sonucu garanti etmez; kilitli ortam ve kayitli girdiler
birlikte kullanilmalidir. Yeni kayit mevcut dosyanin ustune yazmaz.

## Nasil Calistirilir?

Depo kokunde, aktif sanal ortamda ozet ve karar kontrolleri:

```powershell
python -B -m experiments.baseline.synthetic_demo
python -B -m experiments.baseline.synthetic_demo --seed 7 --tasks 6 --servers 2
```

Depoda uretilmis ilk ornegi yeniden okumak:

```powershell
python -B -m experiments.baseline.synthetic_demo --input data/generated/synthetic_v1_seed42_n60_m3.json
```

Yeni bir tohumla girdileri kaydetmek:

```powershell
python -B -m experiments.baseline.synthetic_demo --seed 7 --output data/generated/synthetic_v1_seed7_n60_m3.json
```

`--input` ile uretim parametrelerini ayni anda vermek hata olur; bir dosyayi
okurken tohumu degistirmek o dosyayi degistirmis sayilmaz. Varsayilan komut
dosya yazmaz. Kayit icin `--output` gerekir; mevcut ad varsa yeni ad secilir.

Kontrol dagitimlari: tamamen yerel, gorevleri sirayla sunuculara veren tam
round-robin ve ayni secimlerle %50 offloading. Bunlar optimize edilmis
kararlar veya BOALBFS sonuclari degildir. Uygulanamaz planda `feasible=false`
ve nedeni doner; basarili amac puani verilmez. Daha fazla gorev/sunucu
kullanmak, tek basina referans deneyini tamamlamak anlamina gelmez.
Ozet, bu kontrolun amac/yuk agirliklarini da acikca yazar. Bu agirliklar
degerlendirme ayarlaridir, veri uretim ayarlari degildir; ileriki deneylerde
veri kimligiyle birlikte deney sonucunda kaydedilmelidir.

## Sonraki Adim

Kucuk senaryolarda en iyi karar icin bagimsiz kontrol/cozum ve bununla
dogrulanan baseline optimizasyonu. Once ayni girdide algoritmanin dogru
cozum aradigini gosterecegiz; sonra buyuk ve cok-tohumlu deneylere gececegiz.
Gercek iz adaptoru [veri stratejisindeki](dataset_strategy.md) ayri ek deney
hedefi olarak kalir.
