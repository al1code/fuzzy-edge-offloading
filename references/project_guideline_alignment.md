# Gerçek proje yönergesiyle uygunluk kontrolü

22 Ekim 2026'da kullanıcının verdiği `Bulanik_Mantik_Donem_Projesi_Yonergesi.pdf`
okundu: 12 PDF sayfası, 1–19 numaralı bölümler. Bu kontrol teknik kanıtları
listeler; öğretim üyesinin puanlama veya projeye özel MRR onayı değildir.

## Güncel karar

Uygulama ve karşılaştırma altyapısı önemli ölçüde mevcut. **Projenin bütün
teslimleri tamamlanmış değildir.** Rapor, sunum, doğrulanmış güncel literatür,
AI kullanım bildirimi ve öğrencinin sözlü açıklama yeterliği ayrıca kapatılmalı.
GUI'nin çalışması bunların yerine geçmez. Teknik kanıtlar ve gerçek sonuçlar
[inceleme notunda](inceleme_2026_10_22.md), öğrenme rehberi
[buradan_basla.md](buradan_basla.md) içindedir.

## Madde bazında kanıt ve açık işler

| Yönerge | Depoda karşılık | Durum / sınır |
| --- | --- | --- |
| 1–3: incele, anla, uygula, geliştir, deney yap | Çekirdek model, optimizer'lar, deneyler ve yöntem belgeleri | Altyapı mevcut; anlama/savunma ayrıca gerekli |
| 4: 15–20 dakika sunum, yaklaşık 5 dakika savunma | GUI ve açıklama rehberleri | Teslim edilebilir sunum dosyası ve prova açık |
| 5.1: projeye özel MRR | BOALBFS + sayısal güvenlik + seçilmiş mod deneyi kapsamı | Genel yönerge her proje için MRR belirlenmesini söylüyor; resmi proje kapsamı bu dosyadan çıkarılamaz |
| 5.2: girdi/çıktı, üyelik, kural/çıkarım, durulaştırma | Baseline'da ağırlıklı üçgen değerlendirmesi; ayrı katkıda Type-1 Mamdani | Mamdani makaleye atfedilmez |
| 5.2–5.3: temel deney ve makaleyle karşılaştırma | Local/Edge/Local-Edge; makale/kod uyum notları | Seçilmiş deney ailesi mevcut; ham yazar verisi/ayarları olmadan sayısal birebirlik ve tam MRR kapanışı iddia edilmez |
| 6.1: gerekçeli katkı | S'ye ek U ile görev bazlı gönderim sınırı; analitik oran çalışması | Teknik katkı mevcut; literatürde benzersizlik ve güvenlik üstünlüğü kanıtı yok |
| 6.2–6.3: adil kıyas, deney ve yorum | Eşleştirilmiş veri/seed/bütçe; sabit/yalnız-S/tam-SU ablation | Sonuçlar kayıtlı; iyileşmeyen koşullar ve ödünleşim açık |
| 7–8: kaynakça hariç 8–12 sayfa rapor | report/ | Rapor dosyası açık |
| 8, 12: kaynak ve IEEE atıfları | references/README.md | Güncel literatür karşılaştırması ve rapor içi IEEE atıfları açık |
| 9: GitHub düzeni ve aşamalı geçmiş | Gerçek Git geçmişi, kaynak/test/deney dizinleri | Mevcut; bu tur commit/push yapılmadı |
| 10: kapsamlı README | Proje/öğrenci/makale, yöntem, veri, kurulum, kullanım, deney ve sınırlar | Mevcut; Türkçe başlangıç ve denetim bağlantıları eklendi |
| 11: tekrar üretilebilirlik | Girdiler, seed, sürümler, checksum ve requirements | Mevcut; temiz başka ortam kurulumu bu tur yapılmadı |
| 13: checkpoint'ler | Yol haritası ve teknik kanıtlar | Resmi checkpoint/MRR değerlendirmesinin yerine geçmez |
| 14–15: demo, kodu açıklama, AI bildirimi | Öğrenme ekranı, canlı hesaplar ve testler | Öğrencinin öğrenmesi/provası ve raporda Generative AI Usage Disclosure açık |
| 16: etik | Sentetik/yazar verisi, baseline/katkı ve varsayım ayrımları | Korunmalı; üretilmemiş sayı veya doğrulanmamış kaynak eklenmemeli |
| 17–18: bütün teslimler ve eleştirel değerlendirme | Kod ve deneyler mevcut | Rapor, sunum, literatür ve son demo kontrolü açık |
| 19: Classroom teslimi | Takvim aşağıda | Bütün dosya ve bağlantılar 27 Ekim'e kadar yüklenmeli |

## Katkının değerlendirilmesi

Yönerge 6.2, geliştirilen yöntemin mutlaka daha yüksek performans göstermesini
istemiyor. Gerekçe, teknik uygulama, deney tasarımı, adil karşılaştırma ve
sonuç analizi gerekiyor. Risk azalırken F veya sürenin kötüleştiği koşullar
bu nedenle açıkça tartışılmalıdır. Çalışan kod veya üyelik grafiği tek başına
güçlü bilimsel katkı kanıtı değildir.

## Veri ve kabul durumu

İncelenen data/author_provided/ yalnız yer tutucu içeriyordu. Proje seeded
sentetik senaryolar kullanıyor; dağılımların önemli bir kısmı belgeli proje
varsayımıdır. Önceki README/devir notlarında hocanın sentetik veriyi uygun
gördüğü belirtiliyor; bu incelemede ayrı onay yazısı veya projeye özel MRR
belgesi görülmedi. Yeni bir onay verilmiş gibi yazılmamalıdır.

## Teslim kontrolü

- [ ] Doğrulanmış literatür ve IEEE atıflı 8–12 sayfalık rapor.
- [ ] Introduction, Related Work, Theoretical Background, Original Method,
  Reproduction Methodology, Proposed Extension, Experimental Setup, Results,
  Discussion, Limitations, Conclusion ve References bölümleri.
- [ ] Raporda Generative AI Usage Disclosure.
- [ ] Makale sonucu, proje sonucu, varsayım ve katkının açık ayrımı.
- [ ] Her tablo/grafik için gerçek deney paketi ve tekrar çalıştırma komutu.
- [ ] Sunum dosyası, farklı girişlerle demo ve sözlü savunma provası.
- [x] 23 Ekim: normal Windows izinleriyle GUI dahil 778 test geçti.
- [ ] Temiz başka ortam kurulumu ve öğrencinin canlı demo provası.
- [ ] Gerekli deney çıktılarının teslim paketinde bulunması. results/ Git'te
  ignored olduğundan GitHub klonu yerel grafikleri taşımaz.
- [ ] Gözden geçirilmiş commit/push ve dosya/bağlantıların açılabilirliği.
- [ ] **27 Ekim 2026:** rapor, sunum, GitHub bağlantısı ve bütün istenen
  belgelerin Classroom'a yüklenmesi.
- [ ] **3 Kasım 2026:** sunum/savunmaların başlangıcına hazır olma.

Puanlar: sunum/savunma 20; uygulama 30; katkı 30; rapor/GitHub 20.
