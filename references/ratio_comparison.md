# Kontrollu Katki: Oran Aramasinin Hesaplama Maliyeti

Bu dosyadaki ilk deney yalnizca alt katmani inceler. Tek basina projenin
katkisinin veya tum sistemdeki faydanin tamamlandigini gostermez. Asagidaki
uctan uca deney ayni degisikligin butun karar surecindeki etkisini olcer.

## Hangi Soruyu Soruyoruz?

Sunucu secimi sabitken, gorevin ne kadarini sunucuya gonderecegimizi
SA-PSO ile aramak yerine mevcut modelin dogrusal yapisindan hesaplamak
sonuc kalitesini ve hesaplama maliyetini nasil degistiriyor?

Yeniden kontrol edilen ders yonergesinin bolum 6.1'i hesaplama maliyeti /
performans optimizasyonu ve ablation karsilastirmalarina izin verir;
tamamen yeni bir algoritma zorunlu degildir. Bu, teknik gerekcesi olan
tek bir alt-katman karsilastirmasidir, bilimsel yenilik veya hoca onayi iddiasi degil.

## Neden Dogrudan Hesaplayabiliyoruz?

[Makalenin](https://www.nature.com/articles/s41598-024-79464-2) Denklem 16,
18 ve 19'unu mevcut sabit-girdili uygulamada birlestirince, sabit sunucu
seciminde amac degeri her gorevin oranina gore dogrusaldir:

```text
F = sabit_yuk + sum(sabit_yerel_maliyet + k_i * x_i)
k_i = w_sure * (tam_sunucu_suresi - yerel_sure) / T_ref
      + w_risk * fuzzy_risk / R_ref
```

`k_i < 0` ise oran 1, `k_i > 0` ise 0 en iyidir; esitlikte 0 secilir.
Oranlar surekli kabul edilir, ancak en az bir optimum uc noktalardadir.
[Daha once dogrulanan hesap](exact_search.md) ve `evaluate_locations_exact`
yeniden kullanilir. Yeni bir hesaplama motoru veya algoritma ailesi eklenmez.
SA-PSO koduna dokunulmaz ve ona bu optimum verilmez.

## Sonuclari Gormeden Belirlenen Protokol (2026-10-05)

- 60 gorev, 3 sunucu; veri seed'leri 7, 21, 42, 84, 2026.
- SA-PSO seed'leri 0, 1, 2; 8 parcacik, 15 iterasyon.
- Gorevler sunuculara sirayla dagitilir: 1, 2, 3, 1, 2, 3, ... .
  Bu konumlar optimize edilmez veya sonuclara bakilarak secilmez.
- Her eslestirmede girdiler, fuzzy riskler, kaynak rezervasyonlari, agirliklar,
  normalizerler ve sunucu secimleri aynidir. Yalnizca oran bulma yontemi degisir.
- 15 eslesme, iki yontem icin toplam 30 kayit; bagimsiz veri sayisi 5'tir.
- Her iki yontem ayni konumlarda oran 0 olsa bile sunucu rezervasyonunu korur.
- Kalite: amac F ve sabit-konum optimumuna fark; ayrica sure, risk ve yuk kaydi.
- Maliyet: tam-plan degerlendirme sayisi ve yalnizca cozucunun calisma suresi.
  Dogrudan yontemin bir tam-plan kontrolune EK OLARAK gorev basina iki
  uc-nokta hesabinin oldugu ayri `endpoint_tests` alaninda kaydedilir.
  Degerlendirme sayilari tek basina esit is miktari anlamina gelmez.
- Once her veri icinde tekrarlarin ortalamasi, sonra 5 veri ortalamasinin
  ortalamasi/ornek standart sapmasi alinir. Bu bir anlamlilik testi degildir.
- Olcum sirasi seed paritesine gore degisir; veri uretimi, RNG kurulumu,
  dosya yazma ve grafik cizimi sure olcumunun disindadir. Sureler tekrar
  calistirmada ayni olmak zorunda degildir; kisa olcumler gurultulu olabilir.

## Nasil Calistiriyoruz?

Depo kokunde, aktif sanal ortamla:

```powershell
python -B -m experiments.proposed.ratio_comparison --output results/proposed_ratios_v1
```

Klasor zaten varsa baska bir cikti adi kullan; eski veriler ezilmez.
Kaydedilen girdiler, karar dizileri ve metrikler, ozet CSV, grafik ve checksum
manifesti `results/` altinda YEREL kalir; `git add .` bunlari eklemez.
Tamamlanmayan bir calistirmada manifest `running` kalir; tamamlanmis deney
gibi yorumlanmaz. Uygunsuz sabit dagitim kapasite hatasi verir; bu, diger
sunucu dagitimlarinin da uygunsuz oldugu anlamina gelmez.

## Sonucun Sinirlari

Bu deney ust GA katmanini calistirmaz. Sonuc yalnizca sabit sunucu
secimindeki oran alt-problemi icindir; tum BOALBFS'in hizlandigi veya
kuresel optimumun bulundugu soylenemez. Kaynak/kanal/normalizer sabitligi
degisir, kuyruk veya paralel sure modeli eklenirse dogrusallik yeniden
incelenmelidir. Sentetik girdiler ve model riskleri gercek fabrika verisi
veya gercek saldiri olasiligi degildir. Sonuc ne olursa olsun raporlanir.

Ilk calistirmadan sonra eklenen kontrol: ayni sunucu rezervasyonlariyla
tum oranlarin 0 oldugu planin F degeri de `zero_ratio_objective` alaninda
gosterilir. Bu, karsilastirmanin yontemlerini veya girdilerini degistirmez.
Mevcut SA-PSO kapasiteyi 0 oranlariyla kontrol eder, fakat aramanin en iyi
baslangic adayi rastgele parcaciklardan secilir; kontrol plani incumbent
olarak kullanilmaz. Analitik yontemin SA-PSO'ya karsi farkini yorumlarken
bu baslangic secimi aciklanmalidir. Ek kontrolun bir tam-plan hesabi iki
yontem icin ortaktir, sure olcumunun ve cozucu cagri sayilarinin disindadir.

## Dogrulanan Sonuc

Ilk deneme `results/proposed_ratios_v1` klasorunde, ek sifir-oran kontrolunu
iceren son calistirma `results/proposed_ratios_v1_checked` klasorundedir.
Son calistirmada testler ayni anda calistirilmadi. Onceki paket ezilmedi;
ikisi de yerelde ve Git disinda kalir. Bunlar iki bagimsiz deney orneklemi
degil, ayni girdilerle tekrar calistirmadir.

| Yontem | Ortalama F | Veri ortalamalari arasinda F SD | Ortalama cozucu suresi (ms) | Tam-plan hesabi | Ek uc-nokta hesabi |
| --- | ---: | ---: | ---: | ---: | ---: |
| SA-PSO | 0.325002 | 0.010014 | 103.38 | 129 | 0 |
| Dogrudan analitik | 0.237908 | 0.004375 | 2.13 | 1 | 120 |

15 eslesmenin hepsinde dogrudan yontem daha dusuk F verdi. Bu sayilar
yalnizca secilen 60-gorevli, sabit konumlu deneyin sonuclaridir; kisa sureler
donanim/yuke baglidir. Tam-plan ve tek-gorev hesaplari esit maliyetli degildir.

Onemli kontrol: ayni rezervasyonlarla tum oranlari 0 yapmak ortalama
`F=0.239277` verir. Analitik yontemin buna gore ortalama F dususu yaklasik
`%0.572`'dir (iki ortalamanin yuzde farki, eslestirilmis kazanc ortalamasi degil).
SA-PSO'ya gore buyuk farki tum sisteme genellemek yanlis olur: 60 boyutlu
oran aramasi kisa butce ve rastgele parcaciklarla baslar; sifir-oran kontrolu
incumbent olarak korunmaz. Daha uzun butce veya farkli baslangic bu farki
degistirebilir. Bu deneyde bunlari degistirmedik veya iyi seed secmedik.

Alt-katman deneyi ilk dogrulandiginda 667 test ve Ruff kontrolleri gecti.
O surumde son paketteki 8 cikti checksum'u ve
20 program/bagimlilik dosyasi checksum'u dogrulandi. Kaydedilen 5 veri seti
onceki baseline girdileriyle ayni fingerprint'e sahip. 30 karar/metrik kaydi
yeniden hesaplandi ve birebir eslesti; calisma sureleri bu esitlige dahil degil.
Grafik gorsel olarak kontrol edildi. Temiz ortam teslim kontrolu halen ayridir.

## Uctan Uca Protokol: Sonuclardan Once (2026-10-05)

Soru: ayni GA butcesinde SA-PSO yerine analitik oran degerlendiricisi
kullanmak, bulunan gorev/sunucu kararlarinin kalitesini ve toplam arama
maliyetini nasil degistirir? Yeni algoritma degil, mevcut `solve_genetic`
bilesiminin kontrollu maliyet/performance degerlendirmesidir.

- Onceki deneylerle ayni 5 veri seed'i, 60 gorev, 3 sunucu, 3 arama seed'i.
- Iki tam akis: `GA+SA-PSO` ve `GA+Analytical`. Ayni GA ayarlari:
  12 birey, 8 nesil, 1 elit; toplam 100 aday degerlendirmesi.
- SA-PSO ayarlari degismez: 8 parcacik, 15 iterasyon. Fuzzy degerler,
  agirliklar, normalizerler, kapasite ve baslangic kurallari da degismez.
- Konumlar artik sabit DEGILDIR. Fitness farki sonraki GA adaylarini
  degistirebilir; ayni seed ayni arama yolu garantisi degildir.
- Esit ust-katman butcesi, esit hesaplama butcesi degildir. Gercek tam-plan
  cagrilari ve tum adaylardaki analitik uc-nokta hesaplari ayri sayilir;
  kapasiteye uymayan adaylarin hesabi da sayaca dahildir.
- Zaman olcumu tum GA+oran aramasini kapsar; veri uretimi, RNG kurulumu,
  sonradan yapilan kontroller ve dosya/grafik yazma harictir. Sira degisir.
- F, sure, risk, yuk, karar dizileri, nesil-en-iyi gecmisi ve maliyet kayitli.
  `objective_delta_vs_sapso` eslestirilmis F farkidir; negatif daha iyidir.
  `gap_to_exact` her yontemin KENDI konumlarindaki oran optimumuna farktir;
  butun atama probleminin global optimumuna fark DEGILDIR.
- Ortak tum-yerel kontrol ve her kazananin kendi konumlarinda sifir-oran
  kontrolu kaydedilir. Son kontrol iki yontemde ayni konum demek degildir.
  Bunlar zaman/sayac disinda; ayrica SA-PSO kazananinin oranlari sonradan
  analitik hesapla kontrol edilir, aramaya bu bilgi verilmez.
- Veri icindeki 3 tekrar once ortalanir, sonra 5 veri ortalamasi ve SD
  raporlanir. Iyi seed secilmez; ustunluk veya anlamlilik varsayilmaz.
- Kucuk ornekler mevcut kesin cozucuyle ve `solve_genetic` ile test edilir;
  sonuclar replay edilir ve kaynak/cikti hash'leri kontrol edilir.

```powershell
python -B -m experiments.proposed.ratio_comparison --scope pipeline --output results/proposed_pipelines_v1
```

Bu protokol sonraki kalite sonucunu gormeden kaydedildi. Onceki sabit-konum
deneyleri silinmez veya tam sistem sonucu diye yeniden adlandirilmaz.
SA-PSO baslangicini/butcesini degistirmedik; bu secimlerin etkisi sinirdir.
Yeni paket de `results/` altinda yerel kalir.

## Uctan Uca Dogrulanan Sonuc

Ilk kayit `results/proposed_pipelines_v1`, son gorsel kontrol ve tekrar
`results/proposed_pipelines_v1_checked` altindadir. Ilk grafikte log ekseninin
alt siniri yanlis gorundugu icin grafik duzeltildi ve gorunum testi eklendi;
algoritmalar, girdiler, butce ve agirliklar degistirilmedi. Eski paket ezilmedi.
Son paket grafik duzeltmesini iceren program hash'iyle olusturuldu.
Ikisi ayni 15 eslesmenin tekraridir, 10 bagimsiz veri seti DEGILDIR.

Asagidaki degerler son pakette 5 veri ortalamasinin ortalamasidir. Her veri
icin 3 arama tekrari var; 30 kayit, iki yontem icin 15'er calistirma.

| Olcut | GA+SA-PSO | GA+Analytical |
| --- | ---: | ---: |
| Ortalama F (dusuk daha iyi) | 0.238117 | 0.236411 |
| F icin veri ortalamalari arasinda ornek SD | 0.004618 | 0.003349 |
| Tum karar aramasi, saniye | 9.7044 | 0.1878 |
| Arama suresi icin veri ortalamalari arasinda SD, saniye | 0.1867 | 0.0035 |
| Tam-plan hesaplari, ortalama adet | 12225.87 | 100 |
| EK tek-gorev uc-nokta hesaplari, ortalama adet | 0 | 8200.27 |
| Ust GA adaylari, adet | 100 | 100 |
| Gorev sureleri toplami, saniye | 218.4440 | 216.7583 |
| Toplam model riski | 0.004116 | 0.009375 |
| Sunucu yuk varyansi | 0.000701 | 0.000291 |

- 12 eslesmede daha iyi, 3 eslesmede esit, hicbirinde daha kotu F.
  Seed 7'deki uc eslesme esittir; tum tekrarlar raporlanir.
- Eslesme basina `100*(F_baseline-F_analitik)/F_baseline` hesaplanip
  veri bazinda ortalandiginda ortalama dusus `%0.706169`'dur.
  Iki ortalamanin yuzde farki `%0.716446`'dir; farkli ozetleri karistirmayiz.
- Ortalama arama surelerinin orani yaklasik `51.7`'dir. Bu, bu bilgisayarda
  secilen ayarlarla iki arama katmaninin olcumudur; veri/fuzzy uretimi,
  dosya yazma, GUI veya gercek gorev calistirma hizi dahil degildir.
  Ilk tekrar 9.874 / 0.194 saniyeydi; surelerin degismesi beklenir.
- Ortalama F, sure ve yuk varyansi azalirken ortalama risk artar. Sure
  kazanci ve yuk terimi toplam puani iyilestirir; daha guvenli oldugunu
  veya her bileseni iyilestirdigini soyleyemeyiz.
- Alt-katman deneyindeki `%0.57`, baska bir kontrolle baska bir soruydu.
  Buradaki katkimiz agirliklari degistirmek veya yeni fuzzy model kurmak
  degil: ayni modelde oran arama maliyetini azaltmak ve etkisini olcmek.
- Gercek tam-plan hesaplari ile tek-gorev endpoint hesaplari farkli islerdir;
  100 ile 12225'i bolerek hesaplama hizini iddia etmeyiz. GA global optimum
  garanti etmez; risk normalizasyonu ve kisa SA-PSO baslangici sinirlardir.
  Yalnizca 5 sentetik veri setiyle genelleme/anlamlilik iddiasi yapilmaz.

678 test ve Ruff/format kontrolleri gecti. Son paketin 20 kaynak/bagimlilik
hash'i ve 8 cikti hash'i dogrulandi; ilk paketin 8 cikti hash'i de dogrulandi.
30 karar, tum puan bilesenleri, sifir-oran/tum-yerel kontrolleri ve kendi
konumlarindaki analitik oran farki yeniden hesaplandi. Ilk tekrar ile kararlar,
metrikler, gecmis ve sayaclar birebir eslesti; zamanlar haric.
15 analitik arama `solve_genetic` ile bastan tekrarlandi. 15 SA-PSO sonucu
onceki baseline paketinin karar, metrik, sayac ve en-iyi gecmisiyle de ayni.
5 veri fingerprint'i baseline ile ayni; 20 ozet istatistigi yeniden hesaplandi.
Son grafik gorsel olarak kontrol edildi. Temiz ortam ve nihai teslim ayri.
