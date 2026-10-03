# Commit Tercihi

Ogrenci tamamlanan gelistirme adimini tek commit olarak gondermeyi tercih
eder. Onceki fuzzy hesaplari ve cok-gorevli degerlendirme birlikte
`e8aaaf1` commit'ine alindi; onceden onerilen ayri dosya listeleri artik
uygulanmaz. Asistan commit/push yapmaz ve adimlarin bolunmesini zorunlu tutmaz.

Sentetik veri, kesin kontrol cozucusu ve yol haritasi `bd0c6ff` commit'ine
alindi; ogrenci commit ve push isleminin tamamlandigini bildirdi.

Yeni bekleyen adim [adaptif genetik sunucu secimi](genetic_search.md),
analitik kontrol referansi, [SA-PSO ve iki katmanin baglantisi](boalbfs.md),
testler ve guncellenen belgelerdir. Asama 7 ve 8 tek committe toplanabilir.
Asama 9 da eklendi: Edge'in yerel konumlari yasaklayan GA karsilastirmasi,
eslestirilmis coklu-seed deney surucusu, ham kayitlar/tablo/grafik, testler,
normalizasyon sinirinin aciklamasi ve ertelenmis GUI plani. Mevcut bekleyen
degisiklikler ogrencinin tercihiyle tek committe toplanabilir.
Degisiklikler
ogrenci tarafindan incelenip onaylandiktan sonra depo kokunde:

```powershell
git status
git add .
git diff --cached --stat
git commit -m "feat: add paired offloading experiments and reproducible results"
git push
```

Bu belge komutlari kendiliginden calistirmaz. `git add .` diger yerel
degisiklikleri de hazirlik alanina alir; commit'ten once dosya listesini
kontrol etmek yeterlidir. Herhangi bir degisikligi silme/geri alma islemi
onerilmemektedir.
