# GUI ve Canli Demo

## Ne Yapiyoruz?

Cihazdaki bir hesaplama isinin nerede ve ne oranda yapilacagini seciyoruz.
Kararin maliyeti sure, fuzzy guvenlik riski ve sunucu yuk dengesiyle hesaplanir.
GUI yeni bir hesaplama motoru degildir: `src/` altindaki ayni fonksiyonlari ve
deney programlarini kullanir. Gercek bir fabrikaya gorev gondermez.

## Kendi Bilgisayarinda Calistirma

PowerShell'i ac ve proje klasorune gir:

```powershell
cd "C:\Users\alike\OneDrive\Masaüstü\fuzzy-security-task-offloading"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Bu komut dogrudan projenin Python ortamini kullanir; `Activate.ps1` gerekmez.
Ortam zaten etkinse `python -m streamlit run app.py` da kullanilabilir.

Tarayicida [GUI'yi ac](http://127.0.0.1:8501). Otomatik tarayici acilmasa da
adresi elle acabilirsin. Terminali sunum boyunca acik tut. Durdurmak icin
terminalde `Ctrl+C` kullan. Sonraki acilislarda ayni iki komut yeterlidir;
kutuphaneleri her defasinda kurmak gerekmez.

## Baska Bilgisayarda Kurulum

Kayitli ortam Windows ve Python 3.14.5 ile dogrulandi; diger isletim sistemleri
icin uyumluluk dogrulamasi yapilmadi. Windows'ta Python 3.14 kurulu olmali.
`py -3.14 --version` ile surumu kontrol et.

Git kuruluysa projeyi indir:

```powershell
git clone https://github.com/al1code/fuzzy-security-task-offloading.git
cd fuzzy-security-task-offloading
```

Git kullanmadan GitHub'dan ZIP indirip acmak da mumkundur. PowerShell'de
`app.py`, `gui/` ve `requirements-gui.txt` bulunan depo kokune gir. Paylasilan
surum GUI dosyalarini icermelidir; henuz pushlanmamis yerel degisiklikler
GitHub'dan indirilen surumde bulunmaz.

Ilk kurulum ve baslatma:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-gui.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Sonra `http://127.0.0.1:8501` adresini ac. `.venv` klasorunu bilgisayarlar
arasinda tasima; her bilgisayarda yeniden olustur. `requirements-gui.txt`
cekirdek bagimliliklarini da kurar, ayrica `requirements-dev.txt` kurmak
gerekmez. Ilk kutuphane kurulumu internet gerektirir; temel demo kurulumdan
sonra internet olmadan calisir.

Uygulama yalnizca calistigi bilgisayardan erisilir. Baska bilgisayarda acmak,
projeyi o bilgisayarda kurup baslatmak demektir; `127.0.0.1` adresi uzaktaki
sunum bilgisayarina baglanmaz. Kullanim telemetrisi kapalidir.

### Sik Karsilasilan Durumlar

| Durum | Yapilacak islem |
| --- | --- |
| `py` bulunamiyor veya Python 3.14 yok | Python 3.14 kurulumunu tamamla ve terminali yeniden ac. |
| `.venv\Scripts\python.exe` bulunamiyor | Depo kokunde oldugunu kontrol et; sanal ortam olusturma komutunu uygula. |
| `No module named streamlit` | Depo kokunde `.\.venv\Scripts\python.exe -m pip install -r requirements-gui.txt` calistir. |
| `app.py` bulunamiyor | Terminalde `app.py` dosyasinin bulundugu klasore gir; eski depo surumunde eksikse GUI'yi iceren surumu al. |
| 8501 portu kullanimda | `.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502` kullan ve `http://127.0.0.1:8502` adresini ac. |
| Tarayici baglanamiyor | Baslatma terminalindeki hatayi kontrol et; terminalin acik ve adres/portun dogru oldugundan emin ol. |
| Deney Kayitlari bos | Yeni kurulumda normaldir; yerel deney paketini tasiyabilir veya yeni deney uretebilirsin. |

## Bes Dakikalik Ornek Kullanim

Bu rehberde etiketler ASCII ile yazildi; arayuzde Turkce karakterlerle gorunur.

1. Solda **Senaryo** ekranini sec. **Gorev: 3**, **Sunucu: 2**, **Veri seed: 42**,
   **Guvenlik esigi: 0.60** gir ve **Senaryoyu olustur** dugmesine bas.
   Seed ayni girdileri yeniden uretir; henuz cozum aramasi yapilmamistir.
2. **Bulanik Guvenlik** ekraninda `task-0001` sec. Uzman ucgenlerini ve
   **Hesap izi** bolumunu goster. Varsayilan ayarlarda `S=0.565143`,
   `mu=0.034257`; guvenlik puani 0.60 esiginin altinda oldugu icin risk pozitiftir.
3. **Gorev ve Sunucular** ekraninda `task-0001` / `edge-001` sec.
   **Tek gorev gonderim orani (%)** surgusunu 0, 50, 100 yap.
   %50, modelde isin yarisinin cihazda ve yarisinin sunucuda yapilmasidir.
   Bu inceleme tam plani degistirmez; **Elle plan** ayri degerlendirilir.
4. **Cozum Karsilastirmasi** ekraninda bes yontemi sec ve **Secili cozumleri
   calistir** dugmesine bas. Ustteki **Gosterilen plan** seciminden bir yontem
   secip **Gorev ve Sunucular** ekraninda kararlarini inceleyebilirsin.
5. Tablo ve grafiklerde `F`, sure, risk ve yuk dengesini birlikte yorumla.
   **Arama maliyeti**, karari bulma suresidir; gorevlerin yapilma suresi degildir.

Varsayilan kaynak ve agirlik ayarlariyla tek gorev ornegi:

| Gonderim | Cihaz (s) | Iletim (s) | Sunucu (s) | Toplam (s) |
| --- | ---: | ---: | ---: | ---: |
| %0 | 4.9209 | 0 | 0 | 4.9209 |
| %50 | 2.4605 | 1.6055 | 0.7381 | 4.8041 |
| %100 | 0 | 3.2109 | 1.4763 | 4.6872 |

Sunucu hesaplamayi hizlandirir ama iletim zaman alir ve gonderim risk ekler.
Bu uc gorevli ornekte Local `F=0.2828`, tam Edge `F=0.6479` verir.
BOALBFS, analitik katki ve kucuk kesin kontrol cihazda kalmayi secer.
Bu bir hata veya evrensel sonuc degildir: esit amac agirliklariyla bu girdilerde
sure kazanci risk maliyetini karsilamaz. Bu sayilar makalenin yayimlanmis
sonuclari degil, projenin sentetik demo hesaplaridir. Ayarlar degisirse sonuclar
da degisebilir; arama suresinin ayni cikmasi beklenmez.

## Canli Sunumdan Once

- Kurulumu ve bes dakikalik demoyu sunum bilgisayarinda onceden dene;
  kutuphane kurulumunu sunuma birakma.
- Kucuk ornekte tum yontemleri gosterebilirsin. Buyuk senaryoda **Kesin kontrol**
  secenegini kullanma; aday siniri nedeniyle reddedilebilir.
- Uzun coklu-seed deneylerini sunumdan once tamamla. Canli demoda kayitli
  sonuclari ac; yeni bir uzun deneyi beklemek zorunda kalma.
- Tarayiciyi yenilemek oturumdaki ayar/sonuclari sifirlayabilir. Elle duzenlenen
  girdileri korumak icin **Senaryo** ekranindaki **Girdileri indir** dugmesini
  kullan; tekrar acmak icin senaryo JSON'unu yukle.
- Hazir deneyleri gostereceksen ilgili `results/<paket_adi>/` klasorunu tum
  icerigiyle yeni bilgisayardaki `results/` altina tasiyip onceden acmayi dene.
  Tek CSV/grafik yeterli degildir: girdiler, ayarlar ve butunluk dosyalari gerekir.

Deney paketleri Git tarafindan ignore edilir. GitHub'dan temiz kurulumda
**Deney Kayitlari** bos olabilir; diger dort ekran mevcut modelleri kullanmaya
devam eder. **Yeni coklu-seed deneyi** bolumunden paket uretilebilir. Kisa bir
deneme icin az sayida veri/arama seed'i sec; bu kucuk denemeyi rapordaki asil
coklu-seed deneyinin yerine sunma. Yeni paketler de yerelde kalir.

## Bes Gorunum

| Gorunum | Girdi / eylem | Sonuc / aciklama |
| --- | --- | --- |
| Senaryo | Seed, gorev/sunucu sayisi, CPU/bellek/bant, veri/kanal araliklari; JSON yukle/indir | Ham girdiler, S dagilimi, ortak normalizerler ve girdi kimligi |
| Bulanik Guvenlik | Secili gorevin uzman ucgenleri, ortak uzman/perspektif agirliklari ve esik | Ucgenler, agirlikli birlestirme, q, S, mu ve risk egrisi |
| Gorev ve Sunucular | Secili gorev/sunucu, inceleme orani, elle tam plan | Cihaz/iletim/sunucu sureleri, kaynak rezervasyonlari, F bilesenleri ve kapasite kontrolu |
| Cozum Karsilastirmasi | Local, Edge, BOALBFS, analitik katki, kucuk kesin kontrol; arama/amac/yuk ayarlari | Ortak girdilerle kararlar, sure/risk/yuk/F, arama zamani, hesap sayisi ve GA gecmisi |
| Deney Kayitlari | Kayitli yerel paket veya yeni coklu-seed protokolu | Butunluk kontrolu, veri-ortalamasi/SD, grafikler, ham kayitlar ve karar replay |

SA-PSO parcacik/iterasyon, atalet, cekimler, hiz, sicaklik ve sogutma ayarlanir.
GA birey/nesil/elit sayisi ile adaptif operator sinirlari ayarlanir.
Agirlik girdileri toplamlarina bolunerek normalize edilir. Gecersiz ayarlar
uygulanmaz; onceki gecerli senaryo/ayar korunur.

## Degerler Ne Demek?

- `S`: agirlikli uzman degerlendirmesi. Uc perspektifin donusumu
  `(a + 4b + c) / 6`, sonra perspektif agirliklariyla toplam.
- `mu`: S esik altindaysa `1-exp(-(esik-S))`, degilse 0. Gercek saldiri
  olasiligi degil, modelin risk puanidir. Ucgen uyelikleri de olasilik degildir.
- Gorev suresi: cihaz + iletim + sunucu. Tum gorevlerin toplami fabrikadaki
  paralel bitirme zamani veya algoritmanin arama suresi degildir.
- Gonderim riski: gorev riski ile gonderim oraninin carpimi.
- Yuk: CPU/bant/bellek rezervasyonunun kapasiteye orani; varyans bos sunuculari
  da icerir. Secili sunucuda oran 0 bile olsa rezervasyon vardir; Local farklidir.
- `F`: normalize sure + normalize risk + yuk varyansinin agirlikli toplami.
  Daha dusuk tercih edilir; basari yuzdesi degildir. F azalirken risk artabilir.
- Arama suresi: algoritmanin karari bulmasi icin harcadigi zaman. Donanima ve
  butceye baglidir; gorevin model suresiyle karistirilmaz.
- Tam-plan ve ek uc-nokta hesaplari farkli islerdir; esit GA butcesi esit
  hesaplama maliyeti degildir. SD, bagimsiz veri ortalamalari arasindadir;
  guven araligi veya anlamlilik testi degildir. Eksik baseline gruplari dislanir.

## Kisa Sunum Sirasi

1. Senaryo: girdiler sentetik; cihaz ve sunucu kaynaklari neyi temsil ediyor?
2. Bulanik Guvenlik: tek gorevin uzman goruslerinden S ve mu'ya hesap izini ac.
3. Gorev ve Sunucular: inceleme oranini 0/100 yap; sure bilesenlerini karsilastir.
   Bu surgu tam plani degistirmez. Elle plan ayri degerlendirilir.
4. Cozum Karsilastirmasi: 3 gorev / 2 sunucuda tum yontemleri calistir.
   Exact yalnizca kucuk orneklerde kalite kontroludur, genel buyuk-cozum yolu degil.
5. Deney Kayitlari: `proposed_pipelines_v1_checked` paketini ac; F/sure/risk/yuk
   ile arama maliyetini ayri yorumla. Bir karari acip girdilerle tekrar hesapla.

Bu akisin amaci yonerge bolum 14'teki canli demo ve teknik aciklamayi
desteklemektir. Bolum 5/11 icin ortak hesaplar, kayitli girdiler ve testler;
bolum 6 icin baseline/katki karsilastirmasi korunur. GUI tek basina MRR onayi,
yayin sonuclarinin aynen geri kazanilmasi veya bitmis rapor anlamina gelmez.
Table 3 dilsel esleme ve hocanin fuzzy kapsam beklentisi hala aciktir.
Ucgen grafigi sayisal degerlendirmeyi cizer; yeni bir Mamdani/Sugeno motoru
veya herhangi bir noktada uyelik hesaplayan yeni bir cekirdek API eklenmedi.

## Kayitlar ve Sinirlar

Bir senaryo/fuzzy/arama ayari degisince eski sonuclar yeni girdilere tasinmaz.
Elle fuzzy degisiklik ham JSON snapshot'inda saklanir; seed tek basina bu
degisikligi geri getirmez. Senaryo yukleyici dataset JSON icindir; plan+girdi
JSON'u ayar/karar/ara degerleri denetlemek icin tam bir cikti snapshot'idir.

Yeni coklu-seed deneyleri mevcut deney programlarini cagirir. Yeni sentetik
veri uretir; tek gorevde elle degistirilen ucgenleri kullanmaz. Ortak protokolde
amac/kaynak agirliklari esittir; anlik GUI'deki farkli amac agirliklari alinmaz.
Tam GA ve sabit-konum deneyleri farkli sorulari yanitlar; birlestirilmez.

GUI sinirlari: 140 gorev / 9 sunucu, Exact icin 5.000 aday, tek BOALBFS aramasi
icin 100.000 ve coklu-seed icin 250.000 ust plan butcesi. Daha buyuk deneyler
mevcut CLI ile yapilabilir; kapasite asimi sessizce duzeltilmez.

Deneyleri acarken cikti SHA-256'lari dogrulanir; bu kriptografik bir yazar
imzasi veya eski kaynak kodunun halen ayni olduguna dair kanit degildir.
Secili plan ayni girdilerle tekrar hesaplanip kayitli metriklerle karsilastirilir.

`results/gui_experiment_*`, `results/gui_qa`, `results/gui_session`, test
gecici klasorleri ve `results/mpl_cache` yereldir, Git tarafindan ignore edilir.
Kayitli deney paketleri zaten ayni kurala tabidir; bunlari pushlamak gerekmez.
Teslim icin secilecek az sayida tablo/grafik daha sonra ayrica incelenir.

## Dogrulama

```powershell
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

`test_gui_services.py` tum yontemlerin ortak cekirdekle eslesmesini, replay,
agirlik/fuzzy degisikliklerini, butce/kapasite sinirlarini ve bozuk paketleri
sinir. `test_gui_dashboard.py` gercek Streamlit etkilesimlerini sinar; GUI
kurulu degilse bu dosya atlanir, cekirdek testleri calismaya devam eder.
