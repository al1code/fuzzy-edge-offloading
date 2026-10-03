# Commit Tercihi

Ogrenci tamamlanan gelistirme adimini tek commit olarak gondermeyi tercih
eder. Onceki fuzzy hesaplari ve cok-gorevli degerlendirme birlikte
`e8aaaf1` commit'ine alindi; onceden onerilen ayri dosya listeleri artik
uygulanmaz. Asistan commit/push yapmaz ve adimlarin bolunmesini zorunlu tutmaz.

Bekleyen degisiklikler [sentetik veri uretimi ve yeniden okuma](synthetic_data.md),
ilk kayitli senaryo, [kucuk kesin kontrol cozucusu](exact_search.md),
testleri ve [11 asamali yol haritasidir](roadmap.md). Degisiklikler
ogrenci tarafindan incelenip onaylandiktan sonra depo kokunde:

```powershell
git status
git add .
git diff --cached --stat
git commit -m "feat: add reproducible scenarios and exact small-instance verification"
git push
```

Bu belge komutlari kendiliginden calistirmaz. `git add .` diger yerel
degisiklikleri de hazirlik alanina alir; commit'ten once dosya listesini
kontrol etmek yeterlidir. Herhangi bir degisikligi silme/geri alma islemi
onerilmemektedir.
