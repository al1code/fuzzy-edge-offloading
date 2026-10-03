# Deney 1: Ayni Isleri Nerede Calistirmaliyiz?

## Soruyu Anla

Kodun calismasi ile yontemin iyi sonuc vermesi farkli seylerdir. Bu deneyde
ayni isleri uc farkli kosulla calistirip sonucu olcecegiz. Temel soru,
[makalenin Fig. 2 karsilastirmasina](https://www.nature.com/articles/s41598-024-79464-2)
dayanir; yazar verisinin veya yuzdelerinin birebir tekrari degildir.

| Mod | Neye izin veriyoruz? | Karari kim seciyor? |
| --- | --- | --- |
| Local | Tum gorevler cihazda, x=0; sunucu rezervasyonu yok | Tek sabit plan |
| Edge | Tum gorevler sunucularda, x=1; yerel konum yasak | Mevcut adaptif genetik arama |
| Local-Edge | Yerel veya sunucu; x=0..1 | Mevcut GA + SA-PSO |

Edge ilk adayi gorevleri sunuculara sirayla dagitir; sonraki adaylar GA ile
aranir. Oranlari azaltarak veya bazi gorevleri yerelde birakarak Edge
kapasite problemini gizlemeyiz. Ilk dagitim kapasiteyi asarsa
`no_feasible_initial_plan` kaydedilir: bu, baska uygun dagitim olmadiginin
kaniti degildir. Basarisiz sonuclara F=0 veya uydurma ceza puani verilmez.

## Sonuclara Bakmadan Secilen Protokol

- 60 gorev, 3 sunucu; mevcut sentetik veri uretici ve varsayimlari korunur.
- Veri seed'leri: 7, 21, 42, 84, 2026 (bes farkli gorev/ag/uzman senaryosu).
- Arama seed'leri: 0, 1, 2 (her senaryoda uc bagimsiz arama baslangici).
- Toplam 5 x 3 x 3 = 45 mod kaydi; hicbir sonuc secilip elenmez.
- GA: 12 birey, 8 nesil, 1 elit; her aramada 100 GA degerlendirmesi.
- SA-PSO: 8 parcacik, 15 iterasyon; Local-Edge icin en fazla 12900 plan
  degerlendirmesi. Local bir, Edge 100 plan degerlendirir (ilk aday uygunsa).
- Amac ve kaynak agirliklari esit ucte bir; guvenlik esigi 0.6.
- Bir senaryodaki uc mod ayni gorevleri, uzman goruslerini, baglantilari,
  kapasiteleri ve sabit normalizasyonu kullanir. Modlar icin veri yeniden cekilmez.

Bu, hesaplama butcesi esit bir algoritma yarisi degildir: Local-Edge alt
katmanda daha fazla arama yapar. Kullanim modu ve kayitli karar politikasi
birlikte karsilastirilir; ne kuresel optimum ne de tek basina "parcali
offloading her zaman ustundur" sonucuna varilir. Ayarlar yazarin kurtarilmis
deney butceleri degil, onceden kaydedilen proje secimleridir.

## Hangi Sayilar Ne Demek?

1. `total_latency_seconds`: gorevlerin hesaplanan surelerinin toplami. Gercek
   duvar saati bitis suresi veya programin arama suresi degildir.
2. `total_security_risk`: gonderilen oranlara bagli model risklerinin toplami.
   Olculmus saldiri olasiligi degildir; buyuk gorev kumelerinde 1'i asabilir.
3. `load_variance`: sunucularin kaynak yukleri ne kadar farkli? Sifira yakin
   deger daha dengeli rezervasyon demektir, kaynaklarin bos oldugu degil.
4. `objective`: normalize sure, normalize risk ve yuk varyansinin agirlikli
   toplami F. En dusuk sureyi degil, bu uc olcut arasindaki dengeyi ariyoruz.
5. `search_seconds`: programin karar ararken harcadigi gercek sure. Ayni seed
   kararlari tekrarlar; bu sure isletim sistemi ve makine yukune gore degisir.

Kazanc yuzdesi = 100 x (referans F - yontem F) / referans F. Her kazanc
ayni veri ve arama seed'indeki referansla hesaplanir, sonra ortalanir.
Negatif deger kotulesme demektir. Referans F=0 veya referans yoksa tanimsizdir.

## Ortalamayi Dogru Oku

Her veri senaryosunda uc aramanin ortalamasini aliriz. Sonra bu bes senaryo
ortalamasini ortalariz. Ayni verinin tekrarlarini 15 bagimsiz veri gozlemi
saymayiz. `sd_between_datasets` bu senaryo ortalamalarinin ornek standart
sapmasidir; grafikteki hata cubuklari budur, guven araligi veya anlamlilik
testi degildir. `mean_sd_within_dataset` arama tekrarlarinin degiskenligini
ayri gosterir. Eksik/basarisiz gruplar acik sayimlarla raporlanir; tek
senaryoda senaryolar arasi standart sapma tanimsizdir, sifir diye kaydedilmez.
Hata cubugu araliklari standart sapma nedeniyle sifirin altina uzanabilir;
bu negatif risk/yuk olculdugu anlamina gelmez. Grafik eksik sonuclari ve
tanimsiz sapmayi sifir deger diye gostermemelidir.

## Onemli Normalizasyon Siniri

Bizim risk referansimiz `sum(mu_i)`. Bu pozitifse tam Edge'in normalize riski
1, Local'in riski 0 olur. Esit amac agirliklariyla Edge F > 1/3; Local F <= 1/3,
cunku sure referansi yerel toplam sureyi ustten sinirlar. Dolayisiyla mevcut
yorumda tam Edge'in Local'den daha iyi F vermesi mumkun degildir. Makalenin
Fig. 2'deki Edge < Local siralamasini bu secimlerle elde edemeyiz.
Bu sinir acikca raporlanir; sonucu makaleye benzetmek icin agirlik/normalizer
sessizce degistirilmez. Birim, veri, normalizasyon ve arama ayrintilarinin
belirsizligi nedeniyle makalenin %27/%46 degerlerini yeniden elde ettigimizi
iddia etmiyoruz. Bizim modelimizin ic tutarliligi ve yayinin birebir yeniden
uretilmesi ayri konulardir. Bes veri senaryosu kesifsel bir ilk deneydir.

## Calistir ve Kaniti Incele

```powershell
python -B -m experiments.baseline.mode_comparison --output results/baseline_modes_v1
```

Yeni klasor olmalidir; mevcut klasor asla uzerine yazilmaz. Hizli kontrol:

```powershell
python -B -m experiments.baseline.mode_comparison --output results/modes_small --tasks 3 --servers 2 --data-seeds 42 --optimizer-seeds 0 --population 4 --generations 2 --particles 3 --pso-iterations 3
```

`manifest.json` protokol, surumler, kod/sonuc checksum'lari ve tamamlanma
durumudur. `datasets/` gercek sayisal girdileri, `runs.json` tam kararlar ve
nesil gecmislerini, `runs.csv` tekil olcumleri, `summary.csv` istatistikleri,
`comparison.png` dort temel olcutu saklar. `status=complete` butun dosyalar
yazildiginda konur; yarim kalmis deneyi tamamlanmis saymayiz.

Dersin 5. bolumu icin bu secilmis temel deneyin sorusu, uygulamasi ve sinirli
makale karsilastirmasi; 11. bolumu icin yeniden denetlenebilir girdiler ve
ayarlar; 14. bolumu icin okunabilir sonuc aciklamalari hazirlanir. Ozel MRR,
linguistik fuzzy kapsam, ozgun katki ve final teslim halen ayri konulardir.

## Ilk Kayitli Sonuclar

2026-10-03, yukaridaki protokolle `results/baseline_modes_v1` calistirildi;
45 kaydin tamami uygundu. Bunlar proje varsayimlarindaki sonuclardir.

| Mod | Ortalama F | Gorev sureleri toplami (s) | Toplam model riski | Yuk varyansi |
| --- | ---: | ---: | ---: | ---: |
| Local | 0.239262 | 219.9130 | 0 | 0 |
| Edge | 0.621733 | 265.2710 | 5.550637 | 0.000130 |
| Local-Edge | 0.238117 | 218.4440 | 0.004116 | 0.000701 |

Local-Edge'in eslestirilmis ortalama F kazanci Local'e gore `%0.469991`,
Edge'e gore `%61.692433`. Bunlar makaledeki yuzdelerle esit deney kosullari
degildir. Yerel referansa gore fark kucuktur; bir anlamlilik testi yapilmadi.
Local-Edge ortalama gonderim orani `%1.4444`: bu kosullarda kararlar cogunlukla
yerelde kalir. Risk ve yuk varyansi Local'den daha yuksektir; uc olcutun
her birinde iyilesme oldugunu soylemeyiz. Iletim maliyeti nedeniyle Edge'in
sure toplami da Local'den yuksek cikmistir.

Grafik etiketleri/eksik-sapma gosterimi duzeltildikten sonra ayni protokol
2026-10-04'te `results/baseline_modes_v1_replay` klasorunde tekrar calistirildi. Bu ikinci
calistirma yeni bes bagimsiz veri senaryosu degildir; yeniden uretilebilirlik
kontroludur. Ilk kayitlar uzerine yazilmaz. Esas degerler ilk deneyden secilip
iyilestirilmez. 45 kaydin tam karar, puan, nesil gecmisi ve degerlendirme
sayilari ilk calistirmayla birebir eslesti; gercek arama sureleri bilerek
esitlik kontrolune dahil edilmedi. Replay paketindeki 9 kanit dosyasinin
checksum'i ve mevcut 25 kaynak dosyasinin kimligi dogrulandi. Grafik de
gorsel olarak kontrol edildi. 649 test, Ruff ve fark/bosluk kontrolleri gecti.
