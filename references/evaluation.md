# Cok Gorevli Degerlendirme: Su Anda Ne Yapiyoruz?

## Bu Adimin Amaci

Onceki kod tek bir gorevin suresini, fuzzy guvenlik riskini ve sunucu yukunu
hesapliyordu. Bu adim bunlari **birden fazla gorev ve sunucu icin tek bir
degerlendiricide** birlestirir. Girdimiz bir dagitim karari, ciktimiz onun
uygulanabilirligi ve puanidir. En iyi karari arayan algoritma henuz yoktur.

Ornek soru: "Birinci gorevin %40'ini birinci sunucuya, ikinci gorevin %60'ini
ikinci sunucuya verirsek ne olur?" Artik bu soruyu tum sistem icin sorabiliriz.

## Yeni Dosyalar

- `src/scenario.py`: Gorevleri, yerel CPU'lari, fuzzy'den gelen guvenlik
  seviyelerini, sunuculari, baglanti hizlarini ve rezervasyonlari bir araya getirir.
- `src/evaluation.py`: Her gorevin kararini, butun sunucularin kaynak
  kullanimini, toplam sure/risk ve yuk varyansini degerlendirir.
- `src/objective.py`: Normalizasyon sabitlerini ve amac agirliklarini dogrular;
  uc olcutun ayri katkilarini ve toplam amac puanini verir.
- `experiments/baseline/evaluation_demo.py`: Iki gorevli aciklanabilir bir
  ornek; mevcut fuzzy hesaplamasinin sonucunu yeni modele baglar.
- `tests/test_scenario.py`, `tests/test_evaluation.py`, `tests/test_objective.py`
  ve `tests/test_evaluation_demo.py`: Giris, birim, kapasite, denklem ve birlikte
  calisma kontrolleri. `tests/scenario_helpers.py` bagimsiz test girdileridir.

## Girdi ve Karar Kurallari

`TaskProfile`, mevcut `Task` modelini korur. Toplam CPU isi dongu sayisidir;
veri boyutu ile ikinci kez carpilmaz. `ServerProfile`, mevcut `EdgeServer`
modeline gorev basina CPU tahsisini ekler: toplam kapasite ile tahsis ayni
sey degildir. Hz ve bit/s birbirinin yerine kullanilmaz.

Her gorev/sunucu cifti icin bir pozitif hiz verilir. Hizi mevcut Shannon
hesaplayicisindan alabiliriz veya acikca kaydedilmis bir deney girdisi olarak
verebiliriz. Mevcut sunucu envanterindeki Mbps alanlari, bu cifte ozel hizlarin
yerine gecmez. Hz rezervasyonu ile hizi tutarli saglamak senaryo ureticisinin
gorevi olacaktir. Kopuk/sifir hizli baglantilar bu semada henuz temsil edilmez.

Her goreve tam bir karar gerekir. `server_id=None` yerel calisma demektir ve
oran sifir olmalidir. Pozitif oran mutlaka bilinen bir sunucuya baglanir.
Bir gorev ayni anda birden fazla sunucuya atanamaz; bu yorum makalenin
M+1 konumlu cozum uzayina dayanir.

Sunucu secilip oran sifir verilirse rezervasyon korunur. Boylece makalenin
`y`'ye bagli yuk hesaplari gizlice `x` ile carpilmaz. Tamamen yerel karar
icin hem oran sifir hem sunucu secimi bos olmalidir.

CPU, bant genisligi veya bellek kapasitesi asilirsa karar reddedilir; degerler
kirilmaz ve uygulanamaz planlara basarili sonuc verilmez. Butun sunucular,
bosta olanlar dahil, yuk varyansina katilir. Gorev son tarihi ek model
bilgisidir; makaleye yeni bir son tarih/kuyruk kisiti eklenmez.

## Denklem Baglantisi ve Normalizasyon

[Referans makalenin](https://www.nature.com/articles/s41598-024-79464-2)
Eq. (17)'si gorev surelerini toplar; bu toplam, sistemin duvar saati bitis
suresi veya en uzun gorev suresi degildir. Eq. (18) offloading risklerini
toplar. Eq. (19) ise su puani en aza indirmeyi hedefler:

```text
F = delta_1 * (toplam_sure / T_ref)
  + delta_2 * (toplam_risk / risk_ref)
  + delta_3 * yuk_varyansi
```

Varsayilan delta agirliklari Table 4 gibi esittir. Yuk varyansi zaten
normalize kaynak kullanimindan gelir; yeniden bolunmez. **Kucuk F daha iyidir.**
Bu deger, genetik algoritmadaki `1/F` fitness donusumu degildir.

Yazarlar maksimum sure ve riske bolmeyi tanimlar, ancak uygulanan sabitleri
hesaplama ayrintisini vermez. Bizim acik varsayimimiz:

1. Her gorev icin yerel sure ile tum sunuculardaki tam-offloading surelerinin
   en buyugunu al, sonra bunlari topla. Sabit sunucuda sure orana gore
   dogrusal oldugu icin bu, parcali kararlari da sinirlar. Ortak kapasite
   kisitlari goz ardi edildiginden her zaman erisilebilir bir maksimum degil,
   koruyucu bir ust sinirdir.
2. Risk referansi tum gorevlerin `mu_i` toplami olur. Hepsi sifirsa bolme
   hatasini onlemek icin referans 1 kullanilir; risk katkisi yine sifirdir.
3. Referanslari senaryo icin bir kez hesapla, kaydet ve tum yontemlere ayni
   sabitleri ver. Her yontemin kendi sonucuna gore yeniden olcekleme yapma.

`evaluate_plan` normalizasyonu zorunlu girdi olarak alir; gizlice yeniden
hesaplamaz. Farkli arastirma olcekleri acikca verilebilir. Bu olcekler sonucu
1'in ustune tasirsa deger kesilmez; bu durum raporlanabilir.

## Calistir ve Sonucu Anla

Depo kokunde, sanal ortam acikken:

```powershell
python -B -m experiments.baseline.evaluation_demo
python -B -m experiments.baseline.evaluation_demo --security-threshold 0.4
python -B -m pytest -p no:cacheprovider
```

Varsayilan ornekte iki gorevin CPU isi ve veri boyutu ikinci gorevde iki
katidir; guvenlik degerlendirmeleri aynidir. Ortak sure referansi 3.6 saniye,
risk referansi yaklasik 0.241613'tur.

| Verilen plan | Toplam sure (s) | Normalize risk | Yuk varyansi | F |
| --- | ---: | ---: | ---: | ---: |
| Iki gorev de yerelde | 3.60 | 0 | 0 | 0.333333 |
| Tam offloading, farkli sunucular | 1.50 | 1 | 0 | 0.472222 |
| %40 / %60 offloading, farkli sunucular | 2.48 | 0.5 | 0 | 0.396296 |
| Ayni oranlar, tek sunucu | 2.48 | 0.5 | 0.111111 | 0.433333 |

Bu girdilerde hiz kazanimi guvenlik maliyetini karsilamiyor: verilen dort
plan arasinda yerel planin F'si en dusuk. Esik 0.4 yapildiginda risk sifir
olur ve tam-offloading planinin puani daha dusuk olur. Bunlar yayin sonucu
degil, denklemleri gosteren yapay orneklerdir. Daha dusuk F'nin mutlaka daha
kisa sure veya gercek saldiri olasiligi anlamina geldigi soylenemez.

## Optimizasyondan Once Onemli Kontrol

Sabit sunucu secimi, sabit kaynak tahsisi ve ortak normalizasyonla Eq. (19),
offloading oranlarina gore afin bir fonksiyondur. Yuk kisitlari yalnizca
sunucu secimine baglidir. Dolayisiyla bu modelde her oranin en iyi degeri
uc noktalardan birinde bulunabilir; katsayi sifirsa ara degerler de esit
derecede iyidir. Ara oranlarin mutlaka daha iyi oldugunu varsaymiyoruz.

Testler bu afinlik ozelligini dogrular. Sonraki optimizasyonu kucuk orneklerde
dogrulamak icin uc nokta/analitik kontrol kullanilabilir. Makalenin baseline
algoritmasini yeniden uygulama hedefi korunur; daha iyi ara oranlar elde
etmek icin gizlice paralel `max`, kuyruk veya yeni ceza denklemleri eklenmez.
Ek bir model ancak ayri ve acik bir katkida denenebilir.

## Sonraki Adim

Sabit tohumlu sentetik senaryo uretimi, parametre varsayimlarinin kaydi ve
kucuk-ornek optimizasyon dogrulamasi. Yazarin yaniti bu adimlari engellemez;
gercek izlerden yararlanma plani [veri stratejisinde](dataset_strategy.md)
anlatilir. Buyuk deneyler, BOALBFS, makale karsilastirmasi ve ozgun katkimiz
henuz tamamlanmis degildir.
