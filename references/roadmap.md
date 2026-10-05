# Proje Yol Haritasi

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
| 10 | Ozgun katki | Onceden tanimli soru, degisiklik ve olcutler ayni girdilerle baseline'a karsi denenir | Oran maliyeti calismasi: 30 sabit-konum ve ayri 30 tam-GA kaydi; sinirlar raporlanir |
| 11 | GUI, rapor, sunum ve teslim | Son kod adimi olarak sonuc arayuzu; dogrulanmis literatur, 8-12 sayfalik rapor, AI bildirimi, sunum ve temiz ortam/canli demo kontrolu | GUI mevcut motorla uygulandi; rapor/sunum ve nihai teslim kontrolleri acik |

Literatur okuma, kaynak kaydi, aciklama ve rapor notlari tum surec boyunca
ilerler; 11. asamada ilk kez baslamaz. Son asama bunlarin tamamlanip teslim
paketinin denetlenmesidir. Her gelistirme adimindan sonra degisiklikler
ogrenciye aciklanir; commit ve push islemlerini ogrenci yapar.

## Ne Zaman Bitmis Sayilacak?

- 9. asamanin secilen ilk deneyi ve 10'un sabit-konum deneyi yapildi;
  katkinin iki arama katmanindaki etkisi de ayri tam-GA deneyiyle kontrol edildi.
  Aciklayici [GUI](gui.md) mevcut motorla uygulandi; rapor/sunum ve teslim
  kontrolleri ayridir. Yeni algoritma planlamiyoruz.
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

Fuzzy kapsam notu: sayisal ucgensel degerlendirme mevcut; Table 3 dilsel
etiket eslemesi ve verilen noktada uyelik derecesi hesaplama henuz yok.
Makalenin agirlikli fuzzy degerlendirmesini ayri bir Mamdani/Sugeno kural
motoruyla karistirmayacagiz. Hocanin genel kural/inference beklentisinin bu
makaleye nasil uygulanacagi, nihai MRR uygunlugu iddia edilmeden netlesmeli.

Sabit konumlarda mevcut amac oranlara gore dogrusaldir. Bu nedenle en az
bir uc-nokta optimumu vardir. [Kesin arama notlari](exact_search.md) bunu
aciklar. [SA-PSO](boalbfs.md) makale yonteminin belgeli yeniden uygulamasidir;
mevcut modelde ara oranlarin mutlaka daha iyi oldugunu varsaymayacagiz.
Bu analitik ozellik, secilen [hesaplama maliyeti katkisi](ratio_comparison.md)
icin kullanildi. Yeni bir algoritma ailesi eklenmedi; mevcut kontrol hesabi
once sabit konumlarda, sonra ayni GA ile karsilastirildi. Bu dar kapsamli
bir muhendislik/maliyet katkisi; bilimsel yenilik veya hoca onayi iddiasi degil.
