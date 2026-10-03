# Kucuk Senaryolarda Kesin Kontrol Cozucusu

## Bu Adim Neden Gerekli?

Onceki program verdigimiz bir planin sure/risk/yuk/amac degerlerini
hesapliyordu. `src/optimizers/exact.py` artik kucuk senaryoda en dusuk amac
degerine sahip plani kendisi bulur. Boylece ilerideki genetik/SA-PSO aramasinin
sonucunu bilinen bir optimumla karsilastirabiliriz. Bu bir dogrulama aracidir;
makalenin BOALBFS algoritmasi veya buyuk makale deneyi degildir.

## Neden Yalnizca 0 ve 1 Oranlarini Arayabiliyoruz?

Bu ozellik [makalenin](https://www.nature.com/articles/s41598-024-79464-2)
denklemlerini mevcut sabit-girdili modelimize uygulamaktan cikan bir
matematiksel gozlemdir; yazarlarin acikladigi yeni bir algoritma degildir.

Bir gorev icin yerel sure `a_i`, secilen sunucuda tam iletim+hesaplama suresi
`b_ij`, fuzzy risk `mu_i` ve oran `x_i` olsun. Sabit sunucu seciminde:

```text
T_i = (1 - x_i) * a_i + x_i * b_ij
R_i = mu_i * x_i
```

Kaynak rezervasyonlari ve yuk varyansi sunucu secimine (`y`) baglidir;
`x` ile carpilmaz. Sabit, pozitif normalizerler ve normalize edilmis amac
agirliklari kullanildiginda:

```text
F(y, x) = sabit(y) + sum(k_i * x_i)
k_i = delta_latency * (b_ij - a_i) / T_ref
      + delta_risk * mu_i / R_ref
```

Her `x_i` icin ifade dogrusaldir. `k_i > 0` ise 0, `k_i < 0` ise 1 en
iyidir; `k_i = 0` ise tum oranlar esit degerlidir. Dolayisiyla uygun bir
konum atamasinda en az bir optimumun butun oranlari 0 veya 1 olur.
Tum konum secimleriyle bu uc noktalar tarandiginda mevcut modelin kuresel
optimumuna ulasilir. Ara oranlar yasaklanmis degildir; optimumun varligi
nedeniyle onlari ayri ayri taramak gerekmemektedir.

Bu sonuc sabit CPU/bant/bellek tahsisleri, sabit baglanti hizlari, sabit fuzzy
degerler ve sabit normalizerler icindir. Ileride oranla kaynak tahsisi,
kuyruk, paralel `max(local, edge)` suresi veya yeni oran kisitlari eklenirse
kanit yeniden incelenmeli; bu cozucu otomatik olarak yeni modele kesin olmaz.
"Kesin" tam tarama ve model optimumu anlamindadir; hesaplamalar yine Python
kayan-nokta duyarliligindadir, rasyonel/sembolik aritmetik degildir.

## Secilen Sunucuda Oran 0 Neden Ayri Secenek?

Bir gorevin yerel calismasi iki farkli planda gorulebilir:

- `(server=None, ratio=0)`: hic sunucu rezervasyonu yok.
- `(server=s1, ratio=0)`: gorev yerel calisir ama s1'de kaynak ayrilidir.

Mevcut y-bagli rezervasyon denklemlerinde ikinci secenek yuk dengesini
degistirebilir. Bu nedenle silinmez veya sessizce yerel karara donusturulmez.
Iki sunuculu bagimsiz kontrol ornegimizde t1'in s1'de tam calismasi ve t2'nin
s2 secili ama yerel calismasi yuklari esitler ve `F=0.4` optimumunu verir.
Bu, is yapilmadan rezervasyonla yuk varyansinin azalabildigi bir model
sinirliligidir; gercek sistemde kaynak verimliligi iyilesmesi diye yorumlanmaz.

## Arama Butcesi ve Hata Davranisi

Her gorevin `1 + 2*M` secenegi vardir: yerel, sonra her sunucuda 0 ve 1.
N gorev icin `(2*M + 1)**N` aday vardir. Varsayilan ust sinir 100000 adaydir.
Ornegin 3 gorev ve 2 sunucu 125 adaydir; 60 gorev ve 3 sunucu `7**60`
adaydir ve varsayilan butcede reddedilir. Cozucu adim adim tarar, tum
kombinasyonlari buyuk bir liste olarak bellekte toplamaz.

Butce asiliyorsa hic plan degerlendirilmeden hata verilir. Yari kalmis
arama "kesin cozum" diye sunulmaz. Bu aday siniri bir calisma-suresi garantisi
degildir; her adayin degerlendirme maliyeti senaryo boyutuna baglidir.

Yalnizca `CapacityExceededError` aday elenmesine neden olur. Bu sinif onceki
`ValueError` davranisiyla uyumludur ama kapasite ihlalini diger girdi/hesap
hatalarindan ayirir. Diger hatalar gizlenmez. Sunucu adi hata mesajinda kalir.

Esit hesaplanmis amac degerlerinde ilk aday korunur. Sira senaryodaki gorev
ve sunucu sirasidir; yerel once gelir, her sunucuda 0 sonra 1 denenir.
Esitlik icin yapay bir toleransla gercek iyilesmeler silinmez. Sonuc, secilen
planin butun ara hesaplarini, normalizerlerini, kontrol edilen/uygun/
uygunsuz aday sayilarini icerir. Rastgele sayi kullanilmaz.

## Nasil Calistiririm?

Depo kokunde, aktif sanal ortamla:

```powershell
python -B -m experiments.baseline.exact_demo
```

Demo 3 gorev, 2 sunucu ve seed 42 kullanir; dosya yazmaz. JSON'da
`best_objective_value`, `local_objective_value`, aday sayilari ve `best`
icindeki gorev kararlari, sure parcalari, riskler ve sunucu yuklari gorulur.
En iyi degerin yerel degerden kucuk veya esit olmasi beklenir; esitlik
basarisizlik degildir. Varsayilan agirliklarda yerel calisma en iyi olabilir.

Onceki adimla kaydedilmis kucuk bir senaryoyu aynen kullanmak icin:

```powershell
python -B -m experiments.baseline.synthetic_demo --tasks 3 --servers 2 --seed 7 --output data/generated/small_seed7.json
python -B -m experiments.baseline.exact_demo --input data/generated/small_seed7.json
```

Uretim komutu mevcut dosyayi ezmez. Yeniden okumada checksum, ham girdiler ve
kayitli normalizerler korunur; tekrar veri cekilmez. `--input` uretim
secenekleriyle birlikte kullanilamaz. `--max-candidates` siniri acikca degistirir;
buyuk makale senaryosunu tam taramak icin bu siniri arttirmak pratik degildir.

## Neyi Test Ediyoruz?

- Elle hesap: standart iki gorevli ornekte yerel `F=1/3`; sadece sure agirligi
  ve `T_ref=10` ile tam offloading `F=0.15`.
- Yerel olmayan optimum ve secili-sunucu/sifir-oran rezervasyonu.
- Ara oranlari iceren bagimsiz aritmetik ve farkli seed/agirlikli oran-grid
  kontrolleri: daha iyi ara nokta atlanmamasi.
- CPU, bant ve bellek kapasite ihlallerinin sayilmasi; secili sifir oranlar
  icin de kapasite denetimi; hic rezervasyon sigmazsa yerel plan.
- Tek sunucu, esitlik, tekrar calistirmada ayni sonuc, girdi tipleri,
  butcenin once kontrolu, baska hesap hatalarinin gizlenmemesi.
- Komut satiri, JSON yeniden okuma, buyuk aramanin sonuc uretmeden reddi.

Bu kontroller optimizasyon icin referans olusturur; bir makale deneyinin
yerine gecmez. [Sonraki asamalar ve bitis olcutleri](roadmap.md).
