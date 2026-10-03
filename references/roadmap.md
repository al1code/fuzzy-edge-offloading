# Proje Yol Haritasi

## Aslinda Ne Yapiyoruz?

Bir fabrika cihazinin hesaplama isini kendi uzerinde mi, bir kenar sunucuda mi,
yoksa kismen ikisinde mi yapmasinin uygun oldugunu secen bir program yaziyoruz.
Karar verirken toplam sureyi, fuzzy guvenlik riskini ve sunucularin yuk
dengesini birlikte dikkate aliyoruz. Gercek bir fabrikaya baglanmiyoruz;
belgelenmis kosullarla hesaplama ve karar verme deneyleri yapiyoruz.

Bugune kadar hesaplama motorunu ve ayni girdileri yeniden kullanma altyapisini
kurduk. Artik kucuk orneklerde karari programin kendisi seciyor. Sonraki
asamalarda bunu daha buyuk senaryolarda makalenin arama yontemiyle yapacagiz.

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
| 7 | Adaptif genetik sunucu secimi | Konum kromozomu, uygunluk, elitizm ve adaptif operatorler kayitli butceyle testlidir | Siradaki is |
| 8 | SA-PSO ve BOALBFS butunlestirme | Oran aramasi genetik katmana baglanir; kucuk kesin cozumlerle kalite kontrolu ve buyuk senaryoda calisma testi yapilir | Planlandi |
| 9 | Referans deneyleri | Local/Edge/Local-Edge, coklu seed, sure/risk/yuk/amac, calisma suresi, tablo/grafik ve makaleyle sinirli karsilastirma | Planlandi |
| 10 | Ozgun katki | Onceden tanimli soru, degisiklik ve olcutler ayni girdilerle baseline'a karsi denenir | Baseline degerlendirmesinden sonra secilecek |
| 11 | Rapor, sunum ve teslim | Dogrulanmis literatur, 8-12 sayfalik rapor, AI bildirimi, sunum, README, temiz ortamda calistirma ve canli demo kontrolu | Planlandi |

Literatur okuma, kaynak kaydi, aciklama ve rapor notlari tum surec boyunca
ilerler; 11. asamada ilk kez baslamaz. Son asama bunlarin tamamlanip teslim
paketinin denetlenmesidir. Her gelistirme adimindan sonra degisiklikler
ogrenciye aciklanir; commit ve push islemlerini ogrenci yapar.

## Ne Zaman Bitmis Sayilacak?

- Su anda 6. asama tamamlandi; bu planda 5 ana asama kaldi.
- 7 ve 8 tamamlandiginda, buyuk senaryoda otomatik karar arayan temel program
  calisir olacak. Bu, temel uygulama hedefidir; butun ders projesinin bitmesi degildir.
- 9 tamamlandiginda baseline deneyleri ve karsilastirma sinirlari kayitli olacak.
- 10 tamamlandiginda ozgun katkinin kontrollu deneyleri ve yorumu bulunacak.
- 11 tamamlandiginda ve acik kapsam konulari kapatildiginda proje teslim
  edilebilir olacak. Bu hedef sayilar konusma veya commit sayisi tahmini degildir.

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
aciklar. SA-PSO makale yontemini yeniden gerceklestirme hedefi olarak kalir;
mevcut modelde ara oranlarin mutlaka daha iyi oldugunu varsaymayacagiz.
Bu analitik ozellik gelecekte oran aramasinin kalitesini kontrol etmekte ve
gerekceli bir katkida kullanilabilir; katkimiz henuz secilmis degildir.
