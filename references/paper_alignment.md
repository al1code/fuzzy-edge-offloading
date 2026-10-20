# Makale Uyumu ve Onerilen Gelistirme

Bu not, Jin ve arkadaslarinin 2024 tarihli BOALBFS makalesi ile bu depodaki
uygulamayi ayni kavramlarla karsilastirir. Makalenin Nature sayfasi bazi
ortamlarda 406 dondugu icin dogrulama icin acik erisimli PMC kopyasi da
kullanilmistir:

- [Nature makalesi](https://www.nature.com/articles/s41598-024-79464-2)
- [PMC tam metin kopyasi](https://pmc.ncbi.nlm.nih.gov/articles/PMC11561288/)

## Makalenin temel yontemi

Makale, endustriyel IoT gorevlerinin cihazda, kenar sunucuda veya kismen
offload edilmesini; gecikme, fuzzy-guvenlik riski ve sunucu yuk varyansini
birlikte minimize eden iki katmanli BOALBFS ile ariyor:

1. Fuzzy guvenlik: uzmanlarin ucgensel degerlendirmeleri agirliklandiriliyor,
   her perspektif crisp skora donusturuluyor ve guvenlik riski hesaplaniyor.
2. Ortak amac: toplam gecikme, offloading riski ve kaynak yuk varyansi
   agirlikli bir `F` puaninda birlestiriliyor.
3. Ust katman: adaptif genetik algoritma her gorevin local veya hangi edge
   server konumunu seciyor.
4. Alt katman: SA-PSO secilen konumlar icin offloading oranlarini ariyor.
5. Degerlendirme: Local, Edge ve Local-Edge modlari; server sayisi, gorev
   sayisi, kablosuz hiz, load balancing, agirliklar ve iterasyon duyarliligi;
   ayrica BOALBFS, GAPSO, SAPSO, HCPSO, GWOPSO ve IWOPSO karsilastiriliyor.

Makalede Table 4 icin temel araliklar `N=[60,140]`, `M=[3,9]`, es zamanli
agirliklar `1/3`, `theta=[0.2,0.8]`, `f_i^l=3 GHz`, `f_j^e=10 GHz`,
`Lambda=20 MHz`, `Omega_j=1024 MB` ve GA olasiliklari
`Pc1=0.9`, `Pc2=0.6`, `Pm1=0.1`, `Pm2=0.001` olarak veriliyor.

## Uyum matrisi

| Makale parcasi | Depodaki karsiligi | Durum ve sinir |
| --- | --- | --- |
| Eq. (11)-(15) fuzzy guvenlik ve risk | `src/fuzzy_security.py` | Uygulandi; uzman agirliklari ve bazi parametreler makalede sayisal verilmedigi icin acik proje girdisi |
| Eq. (1)-(4), (16)-(19) sure, iletim, risk ve amac | `src/latency.py`, `src/evaluation.py`, `src/objective.py` | Uygulandi; CPU/birim ve wireless noise yorumlari belgeli varsayim |
| Eq. (5)-(10) kaynak rezervasyonu ve yuk varyansi | `src/load_balance.py` | Uygulandi; secili sunucu `y` rezervasyonu oran `x`'ten bagimsiz tutuluyor |
| GA konum katmani | `src/optimizers/genetic.py` | Uygulandi; makaledeki belirsiz mutation ifadesi literal yorumla belgeli |
| SA-PSO oran katmani | `src/optimizers/sapso.py` | Uygulandi; makalenin eksik optimizer ayrintilari proje secimi olarak kayitli |
| BOALBFS entegrasyonu | `solve_boalbfs` | Uygulandi; ortak evaluator ve sabit normalizasyon kullaniliyor |
| Local / Edge / Local-Edge | `experiments/baseline/mode_comparison.py` | Uygulandi; makale yuzdelerinin birebir tekrari degil |
| Makalenin server/gorev/hiz/agirlik duyarliligi | Kismen mevcut sensitivity inputlari | Tam makale Fig. 4-10 protokolu henuz tek komutlu deney paketi degil |
| GAPSO, SAPSO, HCPSO, GWOPSO, IWOPSO | Yok | BOALBFS icin rakip algoritma ailesi henuz implemente edilmedi |
| Yazar verisi ve Java ayarlari | Yok | Makale sentetik rastgele veri kullaniyor; kaynak kod/seed/ham veri paylasilmadigi icin birebir yeniden oynatma mumkun degil |

Bu nedenle proje su anda **cekirdek yontemin belgeli Python yeniden
uygulamasi + kontrollu uzanti** seviyesindedir; makalenin her figuru ve rakip
algoritmasi tamamlanmis tam replikasyon olarak etiketlenmemelidir.

## Makaledeki deneylerle karsilastirma

Makale Fig. 2'de Local-Edge'in objective degerini Edge'e gore %27, Local'e
gore %46 azalttigini; Fig. 3'te gecikmeyi 820 ms'den 667 ms'ye indirdigini
raporlar. Fig. 4-5 server sayisi arttikca iyilesme ve diminishing returns,
Fig. 6 load balancing ile `0.628`'den `0.537`'ye objective azalmasi, Fig. 7-8
gorev sayisi arttikca objective ve yuk varyansinin artmasi, Fig. 9 wireless
hiz 6M/s'den 15M/s'ye cikinca objective'in %15.19 azalmasi, Fig. 10 ise
agirlik degisiminin sonucu degistirdigini inceler.

Bizde kayitli ilk baseline deneyinde 5 veri seed'i ve 3 optimizer seed'i ile
45 kayit alindi:

| Mod | Ortalama F | Sure (s) | Model riski | Yuk varyansi |
| --- | ---: | ---: | ---: | ---: |
| Local | 0.239262 | 219.9130 | 0 | 0 |
| Edge | 0.621733 | 265.2710 | 5.550637 | 0.000130 |
| Local-Edge / BOALBFS | 0.238117 | 218.4440 | 0.004116 | 0.000701 |

Bu kosullarda Local-Edge, Local'e gore ortalama `%0.469991` daha dusuk F
vermistir. Makaledeki `%46` sonucu ile ayni sayi beklenmemelidir: makalenin
ham verisi, normalizasyon sabitleri, random seed'leri ve tum Java ayarlari
paylasilmamistir. Ayrica mevcut projede risk referansi `sum(mu_i)` ve sure
referansi gorev bazli endpoint ust siniri olarak acikca tanimlanmistir.

## Bizim guncellemenin getirdigi iyilestirme

Yeni katman makalenin fuzzy guvenlik denklemlerini degistirmiyor. Onlarin
uzerine, guvenlik puaninin yanina uzman goruslerinin yayilma miktarini ekleyen
bir karar korumasi koyuyor:

1. Uzman ucgenleri agregalanir.
2. Uc perspektifin ortalama ucgen genisligi `U` olarak olculur.
3. Guvenlik `S` ve belirsizlik `U`, belgeli 3x3 Type-1 Mamdani kural tabanina
   girer.
4. Centroid sonucu her gorev icin izin verilen offloading oraninin ust siniri
   olur.
5. Bu cap, ortak evaluator tarafindan zorlanir; SA-PSO ve GA+SA-PSO cap'i
   ihlal edemez.

Boylece ayni `S` degerinde daha genis/uzlasmasiz uzman gorusu daha temkinli
offloading uretir. Bu, makaledeki risk formuluyle ifade edilmeyen yeni bir
belirsizlik-duyarliligi katmanidir; `uncertainty_weighted_exposure` ise
tanisal bir metrik olup saldiri olasiligi degildir.

Kucuk kontrollu bir kosuda (3 gorev, 2 sunucu, seed 42, ayni GA/SA-PSO
butcesi, link hizi 2x) su gozlenmistir:

| Yontem | F | Sure (s) | Model riski | Belirsizlik maruziyeti | Ortalama cap |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline BOALBFS | 0.326422 | 13.5494 | 0.034257 | 0.019275 | 0.333333 |
| Uncertainty-aware Mamdani | 0.331065 | 14.7839 | 0.011263 | 0.006337 | 0.109591 |

Bu ornek, yeni katmanin amacinin her zaman `F`'yi dusurmek olmadigini gosterir:
guvenlik ve belirsizlik maruziyeti azalirken daha fazla latency pahasina
temkinli karar verebilir. Link hizi 1x kosulunda her iki yontem de tamamen
local plana dondu ve `F=0.282758` oldu; politika gereksiz offloading'i
zorlamiyor. Bu sayilar makale sonucu degil, yeni kodun davranisini gosteren
tekrarlanabilir smoke-test olcumleridir.

## Sonraki kapanis kosullari

Makale uyumunu daha ileri tasimak icin kalan teknik isler:

- Fig. 4-10 icin server/gorev/hiz/load-balance/agirlik sensitivity runner'i,
- makaledeki bes rakip optimizer icin ayni evaluator ve ayni butceyle adapterler,
- Table 4 parametre araliklarinin tek manifestte kaydi,
- her yeni deneyde baseline, Mamdani ve rakiplerin ayni dataset/normalizasyon
  ile paired calistirilmasi,
- raporda makale yuzdeleri ile proje yuzdelerinin ayri sunulmasi.

