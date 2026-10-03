# Adaptif Genetik Sunucu Secimi: Asama 7

## Artik Program Ne Yapiyor?

Once hesaplama motorunu, sonra kucuk kesin cozum aracini kurduk. Simdi
buyuk bir gorev kumesi icin her ihtimali tek tek denemeden uygun sunucu
secimleri ariyoruz. Her adayin degeri yine ayni sure, fuzzy risk, kapasite
ve yuk denklemleriyle hesaplanir. Daha kucuk amac degeri daha iyidir.

Bu asama makalenin ust genetik katmanini, acikca kayitli uygulama secimleriyle
kurar. Bu kontrol modunun oran degerlendirmesinde SA-PSO degil, dogrusal modelin
sabit-konum uc-nokta referansi kullanilir. Cikti etiketinde bu ayrim vardir.
[Asama 8](boalbfs.md) ayrica SA-PSO baglantisini ekler; bu belgedeki komutlar
analitik kontrol modudur. Yayindaki deney karsilastirmasi henuz tamamlanmadi.

## Makaleyle Baglanti

Kaynak: [Jin ve digerleri, Scientific Reports 2024](https://www.nature.com/articles/s41598-024-79464-2),
ust adaptif genetik ve alt SA-PSO bolumleri, Denklem 32-36 ve Table 4.

| Bilesen | Makaledeki dayanak | Koddaki karsiligi |
| --- | --- | --- |
| Gorev basina M+1 konum | Konum uzayi ve ust katman y secimi | 0 yerel, 1..M senaryodaki sunucular |
| Genetik uygunluk | Denklem 32: f_u=1/F | Tasma yapmayan ortak carpana gore olcekli ters amac |
| Rulet secimi | Denklem 33 | Uygunlukla orantili ebeveyn secimi |
| Bitisik segment caprazlama | Caprazlama aciklamasi | Ayni konumlardaki dolu bir segmentin iki ebeveyn arasinda takasi |
| Adaptif caprazlama | Denklem 34 | Yuksek ebeveyn f_u, populasyon ortalamasi ve maksimumu |
| Adaptif mutasyon | Basili Denklem 35 ve f_l tanimi Denklem 36 | Ebeveyn amac degeri F ile parca parca olasilik |
| Olasilik sinirlari | Table 4 | Pc: 0.9/0.6, Pm: 0.1/0.001 |

**Denklem 35 yorum notu:** Ust katman baglaminda mutasyon ifadesi `f_l`
yaziyor; Denklem 36 ise `f_l=F` ve kucuk degerin daha iyi oldugunu belirtiyor.
Biz basili ifadeyi harfiyen izliyoruz. Bu, buyuk F degerlerine daha dusuk
mutasyon olasiligi verebilir; caprazlamadaki iyi bireyi koruma davranisiyla
ayni degildir. Olasiliklarin ikisinde de sessizce `1/F` kullanarak makalenin
bu belirsizligini gizlemiyoruz. Yazar uygulamasi elde edilirse veya hoca
farkli yorum isterse bu karar testleriyle birlikte yeniden ele alinmali.

Secim ve caprazlama icin `min(F)/F`, pozitif F'lerde `1/F` ile ayni goreli
uygunluktur. Ortak carpani hem ebeveyne hem ortalama/maksimuma uygulamak
Denklem 33-34'u degistirmez. F tam sifirsa sifir-amacli bireyler esit
agirlikla secilir; digerleri secilmez. Tam esit bir populasyonda adaptif
formulun paydasi sifirdir; bu belirtilmemis durum icin yuksek olasiligi
kullaniriz. Amac fonksiyonuna ceza veya epsilon eklenmez.

## Basit Bir Kromozom Ornegi

3 gorev ve 2 sunucu icin `(0, 2, 1)` su anlama gelir:

- Gorev 1 yerel calisir, sunucu rezervasyonu yoktur.
- Gorev 2 senaryodaki ikinci sunucuyu secer.
- Gorev 3 senaryodaki birinci sunucuyu secer.

Kromozom oran tasimaz. Her secim icin ayri bir oran degerlendiricisi tam
plani hesaplar. Mevcut `evaluate_locations_exact` her secili gorevin 0/1
oranlarini karsilastirir. Sabit konumlarda sure ve risk dogrusal, yuk ise
oranlardan bagimsiz oldugu icin en az bir uc-nokta optimumu vardir.
[Kaniti ve kapsami](exact_search.md) onceki asamada kaydedildi.

Oran 0 ciksa bile secili sunucu korunur; kaynak rezervasyonu y'ye baglidir.
Bu, gercekte is gonderilmeden rezervasyonla yuk dengesinin iyilesebildigi
model sinirliligini korur. Kaynak verimliligi artisi diye sunulmaz.
Esit uc-nokta katkilarinda oran 0 secilir. Kesin oran referansi konumlari
aramaz; genetik arama tum konumlarin kuresel optimumunu garanti etmez.

## Aramanin Adimlari

1. Bir yerel birey ve kalan rastgele bireylerle populasyon olusturulur.
2. Her konum, oran degerlendiricisi ve ortak plan degerlendiricisiyle puanlanir.
3. Kapasite asan bireyin sonucu yoktur ve rulet secim agirligi sifirdir.
4. En iyi `elite_count` birey bir sonraki nesle degismeden aktarilir.
5. Ruletle ebeveynler secilir; adaptif olasilikla bitisik segment takas edilir.
6. Her gen adaptif olasilikla farkli bir gecerli konuma degistirilir.
7. Yeni bireyler degerlendirilir; nesil butcesi bitene kadar islem surer.

Elitizm nedeniyle en iyi bulunan F kotulesmez. Ama her calistirmada kuresel
optimum bulunacagi garanti edilmez. Kucuk bilinen orneklerdeki esitlikler
dogrulama kanitidir, butun girdiler icin matematiksel garanti degildir.

## Acik Uygulama Secimleri

- Populasyon 30, nesil 25, elit sayisi 1: proje varsayimlari, yazar kodundan
  kurtarilmis degerler degildir. Operator sinirlari Table 4'e dayanir.
- Rastgele baslatmaya ek olarak bir yerel birey koyariz. Ortak modelde bu
  daima kapasiteye uygundur ve yerel referanstan daha kotu sonuc dondurmemeyi
  saglar. Diger genler 0..M'den bagimsiz uniform cekilir.
- Dolu segmentin baslangici, sonra sag ucu uniform cekilir. Tum segmentlerin
  birlikte esit olasilikli oldugu iddia edilmez; tum kromozom takasi da mumkundur.
- Mutasyon, mevcut konumdan farkli M secenekten uniform secer. Ebeveyn
  uygunlugu caprazlama oncesinden kullanilir; gen basina deneme yapilir.
- Bir neslin populasyon boyutu degismez. Son eslestirmede tek bos yer kalirsa
  ikinci cocuk kullanilmaz. Tek gorev/tek sunucu da gecerlidir.
- Kapasiteye uygunsuz adaylar onarilmaz; yalniz `CapacityExceededError` elenir.
  Diger hatalar, degisen gorev/konum sirasi ve degisen normalizerler gizlenmez.
- Caprazlama f_u ortalamasi uygunsuz bireylerin sifir uygunlugunu da icerir.
  Mutasyonun ham F istatistikleri ise yalniz uygun bireylerdendir; uygunsuz
  bir adayin gercek, sonlu F degeri raporlanmaz.
- Nesil ortalamasinda sadece uygun bireyler kullanilir. Cesitlilik sayisi
  tum populasyondaki farkli konumlari sayar. Nesil 0 baslatmadir.
- Ust katman degerlendiriciden gelen plani korur. SA-PSO `search_locations`
  arayuzune asama 8'de baglandi. Tekrarlanan konumlar icin gizli cache yoktur;
  stokastik alt katmanin yeni denemesi engellenmez.
- Elitlerin kayitli plani yeniden hesaplanmadan korunur. Nesil disinda gizli
  arama, erken durdurma veya rastgele coklu baslatma yapilmaz.

## Butce ve Tekrar Uretilebilirlik

`P` populasyon, `G` nesil ve `E` elit ise oran degerlendiricisi cagri sayisi:

```text
P + G * (P - E)
30 + 25 * (30 - 1) = 755
```

Bu, uc-nokta degerlendiricisinin cagri butcesidir. SA-PSO her cagrida birden
fazla tam plan degerlendirir; iki katmanli mod toplam plan cagrilarini ayrica
kaydeder. 755 bir sure garantisi veya tum BOALBFS islem sayisi degildir.

Veri seed'i ve optimizasyon seed'i ayridir. JSON veri girdilerini dondurur;
GA, taze `create_random_state(optimizer_seed)` ile baslar. Ayni girdiler,
ayarlar, surumler ve taze RNG ile ayni sonuc beklenir. Kullanilmis RNG'yi
tekrar vermek ayni seed'den yeniden baslatmaz. Python/NumPy global RNG'leri
degistirilmez. Demo ayarlari, checksum, surumler, normalizerler, agirliklar,
nesil gecmisi ve uygulanan butceyi JSON'a koyar; dosya yazmaz.

## Nasil Calistiririm?

Kayitli 60 gorev / 3 sunucu girdileriyle:

```powershell
python -B -m experiments.baseline.genetic_demo --input data/generated/synthetic_v1_seed42_n60_m3.json
```

Kucuk ornekte kesin cozumle karsilastirma:

```powershell
python -B -m experiments.baseline.genetic_demo --tasks 3 --servers 2 --verify-exact
```

Ornegin farkli arama seed'i ve butce:

```powershell
python -B -m experiments.baseline.genetic_demo --optimizer-seed 7 --population 20 --generations 15
```

`--seed` veri uretimini, `--optimizer-seed` aramayi degistirir. `--input`
ile veri-uretim secenekleri birlikte kullanilamaz. `--verify-exact` kucuk
ornekler icindir; buyuk veriyle kesin arama butcesi asilirsa program hata
verir, yarim bir sonucu kesin diye raporlamaz. `absolute_gap`, bulunan
F eksi kesin F'dir; sifira yakin deger ayni kaliteyi gosterir. Kesin F
sifirsa goreli fark tanimsizdir ve JSON'da null olur.

`best.decisions` gorev kararlari, `best.objective` amac bilesenleri,
`history` nesillerdeki durumdur. Varsayilan sentetik girdilerde yerel karar
en iyi bulunabilir. Bu sonuc makalenin yuzdelerinin yeniden elde edildigi
anlamina gelmez.

[Yol haritasinin](roadmap.md) 8. asamasi tamamlandi: [SA-PSO baglantisi](boalbfs.md).
Dogrusallik referansi oran aramasini dogrulamada kalir; yeni bir model
eklenirse bu referansin varsayimlari yeniden incelenmeli.

## Kayitli Calistirma Kontrolu

2026-10-03, Python 3.14.5 / NumPy 2.5.3 ortaminda, yukaridaki kayitli veri
komutu calistirildi. Veri checksum'i
`eb4a8813f71e7fc3523fdd0613187094ecc0da24d2a3a90549b15c4261915fc5`;
GA seed 42, populasyon 30, nesil 25, elit 1 ve esit amac/yuk agirliklari:

| Kontrol | Deger |
| --- | --- |
| Gorev / sunucu | 60 / 3 |
| Oran degerlendiricisi cagri sayisi | 755 |
| Kapasiteye uygunsuz degerlendirme | 52 |
| Yerel referans F | 0.23913868314392583 |
| Ilk populasyonun en iyi F degeri | 0.23636061582789142 |
| Son en iyi F degeri | 0.23586001610303212 |

3 gorev / 2 sunucu / seed 42 kucuk kontrolunde genetik ve kesin referans
F degerleri `0.2827579965221595`, mutlak fark `0.0` bulundu. Bunlar tekil
calistirma kontrolleridir; coklu-seed deneyi, kuresel optimum kaniti veya
BOALBFS makale sonucunun yeniden uretimi degildir. Nesil gecmisi ve tum
ayarlar yeniden calistirilan komutun JSON ciktisinda gorulebilir.
