# Veri Stratejisi: Yazarin Yanitina Bagimli Olmadan Ilerlemek

## Ana Deney Verimiz

[Makalenin deney bolumu](https://www.nature.com/articles/s41598-024-79464-2)
rastgele uretilmis deney parametrelerini tarif eder. Veri erisimi bolumu,
verilerin makul bir istek uzerine yazardan alinabilecegini belirtir. Bu depoda
ozgun deney verisi veya yazar kodu yoktur. Yazarin yaniti artik bir gelistirme
kosulu degildir; gelirse ayri bir karsilastirma firsati olarak ele alinacaktir.

Ana yolumuz, kaynagi belirtilen parametrelerle kendi sentetik senaryolarimizi
uretmek ve ayni senaryolari butun yontemlere vermektir. Yayinlanmis sinirlar ile
bizim varsayimlarimiz ayrica kaydedilecektir. Bu, yontemin yeniden uygulamasidir;
ozgun verilerle birebir deney tekrari veya ayni yuzdelere ulasma iddiasi degildir.

## Gercek Veri Isimize Yarar mi?

Evet, ozellikle CPU ve bellek talepleri gercek is yuklerinden alinabilir.
Ancak bu izler, endustriyel gorevin veri gizliligini, uzmanin ucgensel guvenlik
degerlendirmesini veya terminalin yasam dongusunu vermez. Ag trafiginin
normalize edilmis olmasi da kablosuz bant genisligi ve bit/s baglanti hizi
elde ettigimiz anlamina gelmez. Eklenen degerler acikca sentetik/varsayim
olarak etiketlenmelidir.

## Adaylar ve Sinirlari

1. **Alibaba Cluster Trace v2018:** Ilk ek deney adayi. Resmi
   [sema](https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2018/schema.txt)
   icindeki `batch_task` kayitlarinda `plan_cpu` ve `plan_mem` bulunur.
   CPU icin 100 bir cekirdektir; bellek normalize edilmistir, MB degildir.
   Gorev adi yalnizca is icinde benzersizdir: anahtar `(job_name, task_name)`
   olmalidir. CPU talebi de toplam islem dongusu sayisi degildir.
2. **Google ClusterData 2019:** Ikinci aday. Resmi
   [aciklama](https://github.com/google/cluster-data/blob/master/ClusterData2019.md)
   kaynak talebi/kullanimina odaklanir; kullanici verisi veya erisim oruntusu
   sunmaz. Belgeye gore sikistirilmis veri yaklasik 2.4 TiB'dir ve BigQuery
   uzerinden sunulur. Su an tumunu indirmek veya ucretli sorgu calistirmak
   gerekli degildir.

Alibaba'nin resmi [v2018 belgesi](https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2018/trace_2018.md)
`batch_task` arsivini yaklasik 125 MB olarak listeler; tam iz cok daha buyuktur.
Yalnizca gerekli dosyanin kucuk bir alt kumesi tercih edilmelidir. Indirme
baglantilarinin fiilen calistigi bu asamada denenmedi; herhangi bir veri
indirilmedi veya deneyde kullanilmadi. Lisans/kullanim kosullari indirme
asamasinda tekrar kontrol edilecektir.

## Uygulama Sirasi

1. Ortak cok-gorevli degerlendiriciyi ve amac fonksiyonunu dogrula.
2. Sabit tohumla sentetik senaryo ureticisini ekle. Gorev sayisi, sunucu sayisi,
   dagilimlar, uzman sayisi/agirliklari, CPU/bellek/ag birimleri ve belirsiz
   yayin parametreleri icin secilen varsayimlari kaydet.
3. Yerel, tam sunucu ve parcali calisma yontemlerini ayni girdiler, amac
   agirliklari ve normalizasyon sabitleriyle karsilastir.
4. Baseline tamamlandiktan sonra Alibaba'dan sinirli bir ornek icin adaptoru
   ekle: kaynagin surumu ve dosya karmasi, filtreler, ornekleme tohumu,
   birim donusumleri ve yapay ek alanlar kaydedilsin.
5. Bu sonucu ayri bir **iz tabanli hibrit senaryo deneyi** olarak raporla.
   Onu ozgun makale veri seti veya gercek uzman guvenlik verisi olarak sunma.

Veriyi aramak, su anki model dogrulamasini engellemez. Bir veri seti tek basina
optimizasyon yonteminin dogru uygulanmasini veya dersin tum teslimlerini
tamamlamis sayilmamizi da saglamaz.
