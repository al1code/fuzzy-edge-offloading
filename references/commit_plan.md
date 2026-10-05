# Commit Tercihi

Ogrenci tamamlanan gelistirme adimini tek commit olarak gondermeyi tercih
eder. Onceki fuzzy hesaplari ve cok-gorevli degerlendirme birlikte
`e8aaaf1` commit'ine alindi; onceden onerilen ayri dosya listeleri artik
uygulanmaz. Asistan commit/push yapmaz ve adimlarin bolunmesini zorunlu tutmaz.

Sentetik veri, kesin kontrol cozucusu ve yol haritasi `bd0c6ff` commit'ine
alindi; ogrenci commit ve push isleminin tamamlandigini bildirdi.

Asama 7-9 uygulamasi ve ilk deney `0ecf237` commit'ine alindi.
`eff0d34` commit'i deney paketlerini yerelden silmeden Git takibinden cikardi.
`results/` ciktilari artik ignore edilir; yalnizca klasor yer tutuculari takiptedir.
Sonraki kontrollu katki [oran maliyeti karsilastirmasi](ratio_comparison.md)
olarak uygulandi: AYNI deney dosyasi once sabit konumlari, sonra tam GA
akislarini karsilastirir. 29 deney testi ve kisa sonuc aciklamasi mevcut.
Bu adimin kod/test/belgeleri commit'e uygundur; `results/proposed_ratios_v1*`
ve `results/proposed_pipelines_v1*` altindaki girdiler, CSV'ler, manifest ve
grafikler yerelde kalir. Cekirdek `src/` ve bagimliliklar bu adimda degismedi.
Guncel devam notu [proje baglaminda](project_context.md) tutulur.

Her commit oncesi asistan degisiklikleri ve test durumunu aciklar; ayrica hangi
dosyalarin gerekli oldugunu, hangilerinin yalnizca yerelde kalmasi gerektigini
belirtir. Ayrintili deney girdileri, JSON kayitlari, tablo ve grafikler varsayilan
olarak ignore edilen `results/` altinda kalir. Secilen teslim kanitlari daha
sonra ogrencinin onayiyla yayimlanabilir.

Ogrenci degisiklikleri inceleyip onayladiktan sonra commit/push yapar.
Hazirlik alanindaki dosya listesini gormek icin:

```powershell
git status
git diff --cached --name-status
git diff --cached --stat
```

Bu belge komutlari kendiliginden calistirmaz. `git add .` ignore edilmeyen diger
yerel degisiklikleri de hazirlik alanina alir; commit'ten once dosya listesini
kontrol et. Asistan commit/push veya gecmisi geri alma islemi yapmaz.
