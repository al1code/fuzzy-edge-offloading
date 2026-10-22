# Proje Yol Haritasi

> **23 Ekim 2026 — kod kapanışı:** GUI dahil 778 test geçti. Seçili uygulama
> kapsamı dondurulabilir; gerekli hata düzeltmeleri dışında öncelik rapor,
> sunum ve savunma hazırlığıdır. [Dört doğrulanmış GUI örneği ve sunum sırası](sunum_demo_akisi.md).
> Bu teknik kapanış, rapor/sunumun veya projeye özel MRR onayının tamamlandığı
> anlamına gelmez.

> **22 Ekim 2026 denetim eki:** Gerçek yönerge okundu. Bütün belgeler,
> **sunum dosyası dahil 27 Ekim'de** Classroom'a teslim edilmeli; 3 Kasım
> sunumların başlangıcıdır. Kod ve katkı için güncel kanıt/sınırlılıklar
> [inceleme notunda](inceleme_2026_10_22.md). GUI'ye Projeyi Anla ekranı eklendi;
> Mamdani hız koşullarının özeti ve kayıt tekrar hesabı düzeltildi. Aşağıdaki
> 20 Ekim durum notu tarihlidir; teslimin tamamen kapandığı anlamına gelmez.

> **Guncel durum (2026-10-20):** Teknik uygulama, ozgun Mamdani katkisi ve
> GUI deney gosterimi buyuk olcude tamamlandi. GUI'nin yeni kullanici rehberi,
> renkli metrik kartlari ve sade baslangic akisi da tamamlandi. 750+ test, tekrarlanabilir
> deney paketleri, policy karsilastirmasi, risk-gecikme grafigi ve link-rate
> sensitivity akisi calisir durumdadir. Kalanlar agirlikli olarak ek analiz,
> makale duyarlilik deneyleri ve teslim hazirligidir.

## Aslinda Ne Yapiyoruz?

Bir fabrika cihazinin hesaplama isini kendi uzerinde mi, bir kenar sunucuda mi,
yoksa kismen ikisinde mi yapmasinin uygun oldugunu secen bir program yaziyoruz.
Karar verirken toplam sureyi, fuzzy guvenlik riskini ve sunucularin yuk
dengesini birlikte dikkate aliyoruz. Gercek bir fabrikaya baglanmiyoruz;
belgelenmis kosullarla hesaplama ve karar verme deneyleri yapiyoruz.

Bugune kadar hesaplama motorunu ve ayni girdileri yeniden kullanma altyapisini
kurduk. Artik kucuk orneklerde kesin cozum, buyuk orneklerde genetik konum
aramasi ve buna baglanan SA-PSO oran aramasi var. Analitik oran referansi
ayri bir kontrol modu olarak duruyor; BOALBFS baseline'inin SA-PSO katmaninda
kullanilmiyor. Katki akisinda ayni GA analitik oran hesabiyla da deneniyor.

Akis: girdiler -> fuzzy guvenlik -> karar adayi -> sure/risk/yuk -> amac
degeri -> uygun karar -> kayitli deney -> karsilastirma ve yorum.

## Neye Gore Ilerliyoruz?

- [Referans makale](https://www.nature.com/articles/s41598-024-79464-2):
  fuzzy guvenlik Denklem 11-15, sure Denklem 16-17, risk Denklem 18,
  kaynak/yuk Denklem 5-10, ortak amac Denklem 19. BOALBFS ust katmanda
  adaptif genetik algoritma, alt katmanda SA-PSO kullanir.
- Ogrencinin sagladigi `Bulanik_Mantik_Donem_Projesi_Yonergesi.pdf`:
  bolum 5 dogru modelleme, calisan uygulama, test ve temel makale deneyi;
  bolum 6 gerekceli ozgun katki ve kontrollu karsilastirma;
  bolum 11 tekrar uretilebilirlik; bolum 14 aciklama/canli demo;
  bolum 15-17 AI bildirimi, etik ve teslim ciktilari.
- Dogrulama sirasina gore: once denklemler, sonra ortak degerlendirme,
  ardindan kucuk kesin cozum, sonra buyuk senaryolar icin arama ve deneyler.
  Her asamanin bitis olcutu vardir; test sayisi tek basina bitis kaniti degildir.

Bu 11 asama bizim calisma planimizdir, dersin resmi checkpoint numaralari veya
11 commit zorunlulugu degildir. Hoca projeye ozel MRR aciklarsa kapsami
yeniden degerlendiririz. Su anki kapsam ogrencinin onayladigi calisma hedefidir.

## 11 Ana Asama

| Asama | Ne yapiyoruz? | Asamanin bitis olcutu | Durum |
| --- | --- | --- | --- |
| 1 | Depo, ortam, ayarlar ve rastgelelik | Dogrulanmis ayarlar, bagimsiz RNG ve kayitli bagimliliklar | Hazir |
| 2 | Sayisal fuzzy guvenlik | Uzman ucgenleri, agirliklandirma, donusum ve risk elle kontrol edilir | Sayisal alt sistem hazir; asagidaki fuzzy kapsam notuna bak |
| 3 | Sure, ag ve kaynak yuku | Yerel/iletim/sunucu sureleri ve kapasite kontrolleri testlidir | Hazir |
| 4 | Ortak senaryo ve amac degeri | Tum yontemler ayni degerlendiriciyi ve sabit normalizerleri kullanir | Hazir |
| 5 | Tekrarlanabilir sentetik girdiler | Ham girdiler, ayarlar, surumler ve checksum ile JSON yeniden okunur | Hazir |
| 6 | Kucuk orneklerde kesin cozum | Tum uygun uc-nokta planlari taranir; elle hesap ve ara-oran testleriyle kontrol edilir | Hazir |
| 7 | Adaptif genetik sunucu secimi | Konum kromozomu, uygunluk, elitizm ve adaptif operatorler kayitli butceyle testlidir | Hazir; ayri analitik kontrol modu korunur |
| 8 | SA-PSO ve BOALBFS butunlestirme | Oran aramasi genetik katmana baglanir; kucuk kesin cozumlerle kalite kontrolu ve buyuk senaryoda calisma testi yapilir | Hazir; yayin disi ayarlar belgeli varsayimdir |
| 9 | Referans deneyleri | Local/Edge/Local-Edge, coklu seed, sure/risk/yuk/amac, calisma suresi, tablo/grafik ve makaleyle sinirli karsilastirma | Secilen ilk deney hazir: 45 kayit; normalizasyon/yayin uyumu siniri acik |
| 10 | Ozgun katki | Onceden tanimli soru, degisiklik ve olcutler ayni girdilerle baseline'a karsi denenir | Buyuk olcude hazir: Type-1 Mamdani cap politikasi, evaluator/SA-PSO/analitik solver entegrasyonu, sabit-konum policy deneyi, GA sensitivity deneyi, risk-gecikme grafigi ve GUI gosterimi |
| 11 | GUI, rapor, sunum ve teslim | Son kod adimi olarak sonuc arayuzu; dogrulanmis literatur, 8-12 sayfalik rapor, AI bildirimi, sunum ve temiz ortam/canli demo kontrolu | Kod/GUI hazir: gorev bazli Mamdani aciklamasi, policy ve GA sensitivity deneyleri, grafikler, renkli metric kartlari, baslangic rehberi ve form ici ornekler. Rapor, sunum, AI bildirimi ve nihai teslim kontrolu acik |

Literatur okuma, kaynak kaydi, aciklama ve rapor notlari tum surec boyunca
ilerler; 11. asamada ilk kez baslamaz. Son asama bunlarin tamamlanip teslim
paketinin denetlenmesidir. Her gelistirme adimindan sonra degisiklikler
ogrenciye aciklanir; commit ve push islemlerini ogrenci yapar.

## Ne Zaman Bitmis Sayilacak?

- 9. asamanin secilen ilk deneyi ve 10'un sabit-konum deneyi yapildi;
  katkinin iki arama katmanindaki etkisi ayri tam-GA deneyiyle kontrol edildi.
  Sabit-konum policy deneyinde `SA-PSO`, `Analytical`, `Mamdani SA-PSO` ve
  `Mamdani Analytical` ayni girdilerle karsilastiriliyor.
- GUI, gorev bazli kural aciklamasinin yaninda coklu-seed policy ve link-rate
  sensitivity deneylerini de calistirip kayitli grafiklerini gosterebiliyor.
  Yeni kullanici akisinda temel ayarlar gorunur, ileri kaynak/kanal ayarlari
  kapali expander icinde ve sayfanin amacina gore aciklamali olarak sunulur.
- Makalenin iki katmanini birlestiren temel program belgeli varsayimlarla
  calisir. Bu, yayinlanan deneylerin veya butun ders projesinin bitmesi degildir.
- 9'un ilk baseline deneyleri ve karsilastirma sinirlari [kayitli](experiments.md).
  Orijinal deneyin sayisal yuzdelerini veya tam MRR uygunlugunu elde ettigimizi
  iddia etmiyoruz. Gerekirse hoca kapsam bildirince deney kapsami yeniden ele alinir.
- 10'un [protokolu ve yorumu](ratio_comparison.md) kayitli. Sabit-konum
  sonucunu tum sisteme genellemeyiz; tam-GA deneyi kendi olcumleriyle
  yorumlanir. Analitik oran optimumu, global sunucu optimumu demek degildir.
- 11 tamamlandiginda ve acik kapsam konulari kapatildiginda proje teslim
  edilebilir olacak. Bu hedef sayilar konusma veya commit sayisi tahmini degildir.

Hesaplama kapsami sabit: yeni algoritma, gercek veri altyapisi veya dagitik
simulator eklenmeyecek. Ogrenci 2026-10-03'te son kod adimi olarak bir GUI
istedi; bu arayuz mevcut hesaplari ve kayitli deneyleri gosterecek, yeni bir
hesaplama motoru olmayacak. Sira: temel deney -> tek ozgun katki -> GUI ->
rapor/sunum ve teslim. 11 ana asama korunur; GUI son teslim asamasinin parcasi.

GUI hedefi: gorev/sunucu kararlari, fuzzy ara degerler, sure/risk/yuk
ayrintilari, mod karsilastirmalari ve kayitli sonuclarin anlasilir gorunumleri.
Sentetik veri, varsayimlar ve model riskinin gercek saldiri olasiligi olmadigi
arayuzde de korunur. Uygulama ve canli demo akisi [GUI rehberinde](gui.md).

## Henuz Acik Olan Konular

Yazarin veri/ayrinti yanitini bekleyerek ilerlemiyoruz. Birincil girdilerimiz
sentetik ve varsayimlari [kayitli](synthetic_data.md). Gercek bir gorev izi
istege bagli ek dayaniklilik deneyi olabilir; uzman guvenlik gorusleri ve
kablosuz kanal girdilerini tek basina saglamaz. Yayinlanan yuzdeleri aynen
elde edecegimizi veya yazar verisini kullandigimizi iddia etmiyoruz.

Fuzzy kapsam notu: makalenin agirlikli ucgensel degerlendirmesi ile onerilen
Mamdani karar katmani birbirinden ayridir. Onerilen katman, makale denklemlerini
degistirmez; agregalan ucgenlerin ortalama genisligini belirsizlik girdisi
olarak kullanir ve ratio cap uretir. Type-1 Mamdani kural tabani, min-AND,
max-birlestirme ve centroid durusturmesiyle kodlanmistir. Bu, ders icin
gerekceli bir uzanti ve kontrollu deneydir; makalenin kendi yontemi veya
yayinin deney sonucu olarak sunulmaz.

Sabit konumlarda mevcut amac oranlara gore dogrusaldir. Bu nedenle en az
bir uc-nokta optimumu vardir. [Kesin arama notlari](exact_search.md) bunu
aciklar. [SA-PSO](boalbfs.md) makale yonteminin belgeli yeniden uygulamasidir;
mevcut modelde ara oranlarin mutlaka daha iyi oldugunu varsaymayacagiz.
Bu analitik ozellik, secilen [hesaplama maliyeti katkisi](ratio_comparison.md)
icin kullanildi. Yeni bir algoritma ailesi eklenmedi; mevcut kontrol hesabi
once sabit konumlarda, sonra ayni GA ile karsilastirildi. Bu dar kapsamli
bir muhendislik/maliyet katkisi; bilimsel yenilik veya hoca onayi iddiasi degil.

## Gelistirme sirasi ve tahmini kapanis

Bu takvim kesin teslim tarihi degil, kalan is paketlerinin goreli eforudur.

| Durum | Is paketi | Tahmini efor | Kapanis kaniti |
| --- | --- | --- | --- |
| Tamamlandi | Mamdani controller, cap validation ve optimizer entegrasyonu | Bitti | Unit/integration testleri; cap ihlali reddediliyor |
| Tamamlandi | Sabit-konum baseline vs Mamdani oran karsilastirmasi | Bitti | `ratio_comparison.py --scope policy`, CSV/manifest/grafik |
| Tamamlandi | GUI'de gorev bazli Mamdani inceleme ve baseline/proposed calistirma | Bitti | Streamlit Mamdani gorunumu ve GUI testleri |
| Tamamlandi | GUI'de policy deneyi, Pareto grafigi ve GA link-rate sensitivity | Bitti | `Mamdani oran politikasi` ve `Mamdani GA sensitivity` protokolleri |
| Acik | Kural tabani icin alternatif policy/sensitivity analizi | 1-2 oturum | Ayni seedlerle conservative/balanced secenekleri |
| Acik | Makale Fig. 4-10 sensitivity runner'i | 1-3 oturum | Server/task/rate/load/weight/iteration tek manifestte |
| Opsiyonel | Makaledeki bes rakip optimizer | Kapsama bagli | Her rakip ayni evaluator ve butceyle calisir |
| Teslim | Rapor, IEEE kaynakca, AI kullanim bildirimi, sunum ve canli demo | Kod disi | Ogrenci teslim kontrol listesini tamamlar |

### Her kod degisikliginden sonra kontrol

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_fuzzy_controller.py tests/test_ratio_comparison.py tests/test_gui_dashboard.py tests/test_gui_services.py -q
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests -q
git diff --check
```

Ilk komut hizli geri donus testidir; tam test paketi evaluator, optimizer,
deney ve GUI sozlesmelerini birlikte kontrol eder.

### Teknik sinirlilik

Mevcut 3x3 Type-1 Mamdani kurallari guvenlik ve belirsizlik eksenlerinde
beklenen genel yonu verir, ancak max aggregation ve clipped output membership
geometrisi nedeniyle her ara noktada kesin global monotoniclik garantisi
vermez. Kod bunu evrensel bir garanti olarak sunmaz; [0,1] cap siniri,
anchor davranis testleri, centroid resolution stability ve kontrollu deney
metrikleriyle sinirli bir politika olarak belgeler.
