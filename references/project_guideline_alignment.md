# Proje Yönergesi Uygunluk Kontrolü

Bu kontrol, `Bulanik_Mantik_Donem_Projesi_Yonergesi.pdf` içindeki teknik,
deneysel, GitHub ve tekrar üretilebilirlik maddeleriyle mevcut repository'nin
karşılaştırılmasıdır. Rapor ve sunum bu kontrolün dışında tutulmuştur.

## Genel karar

Proje, yönergenin beklediği **incele -> yeniden gerçekleştir -> geliştir ->
kontrollü deney yap -> karşılaştır -> analiz et -> GitHub'da paylaş** akışını
kod, test, deney ve dokümantasyon düzeyinde karşılıyor.

Yapay veri kullanımı bu proje için kabul edilmiş bir kapsam kararıdır. Referans
makalenin ham veri seti, random seed'leri ve tam üretim kodu erişilebilir
olmadığı için deneyler kaydedilmiş parametre aralıklarından üretilen seeded
sentetik senaryolarla yürütülüyor. Ders hocasının bu durumu uygun gördüğü
bilgisi proje kapsamına dahil edilmiştir. Bu sonuçlar yazarların verileriyle
birebir yeniden üretim veya makalenin yüzdelerinin doğrulanması olarak
sunulmayacaktır.

## Madde bazlı kontrol

| Yönerge beklentisi | Repository'deki kanıt | Durum |
| --- | --- | --- |
| Güncel bilimsel çalışma ve problem analizi | [paper_alignment.md](paper_alignment.md), [fuzzy_security.md](fuzzy_security.md), referans makale bağlantıları | Karşılanıyor |
| Referans yöntemin belirlenen bölümünü yeniden gerçekleştirme | Fuzzy güvenlik, gecikme, iletişim, kaynak yükü, ortak `F`, GA, SA-PSO ve BOALBFS | Karşılanıyor |
| Sistem girdileri ve çıktılarının tanımlanması | `src/scenario.py`, `src/evaluation.py`, sentetik veri manifestleri | Karşılanıyor |
| Membership function yapıları | Güvenlik için triangular assessment modeli; önerilen controller için low/medium/high üçgenleri | Karşılanıyor |
| Fuzzy rule base ve inference | [fuzzy_controller.py](../src/fuzzy_controller.py): 3x3 Type-1 Mamdani, min-AND, max aggregation | Karşılanıyor |
| Defuzzification | Centroid ile görev bazlı offloading cap'i | Karşılanıyor |
| Farklı girişlerle test | Unit, integration, GUI ve kontrollü deney testleri | Karşılanıyor |
| En az bir temel makale deneyinin yeniden gerçekleştirilmesi | Local / Edge / Local-Edge paired deney paketi ve 45 kayıt | Karşılanıyor; sayısal birebirlik iddiası yok |
| Referans ve geliştirilmiş yöntemin kontrollü karşılaştırması | [uncertainty_mamdani_comparison.py](../experiments/proposed/uncertainty_mamdani_comparison.py) | Karşılanıyor |
| Teknik gerekçeli özgün katkı | Uzman görüşü genişliğini belirsizlik girdisi yapıp oran cap'i üretme | Karşılanıyor |
| Tekrar üretilebilirlik | Seed, manifest, kaynak/artifact checksum, sabit normalizasyon, requirements dosyaları | Karşılanıyor |
| README'de amaç, yöntem, veri, kurulum, çalıştırma, sonuç ve sınırlılık | [README.md](../README.md) | Karşılanıyor |
| GitHub geliştirme geçmişi | Birden fazla anlamlı commit ve mevcut değişikliklerin ayrı dosya kapsamı | Sürdürülmeli |
| Generative AI kullanım bildirimi | Yönerge raporda açık bölüm istiyor | Rapor aşamasında eklenmeli |
| IEEE kaynakça ve literatür araştırması | Teknik kod dokümantasyonu mevcut; rapor/sunum kapsamı | Rapor aşamasında tamamlanmalı |
| Canlı demo ve sözlü savunma | Streamlit GUI ve deney kayıtlarını inceleme akışı mevcut | Sunum aşamasında gösterilmeli |

## MRR yorumu

Bu proje için makalenin tamamını, altı optimizer'ı ve yazarların tüm
duyarlılık figürlerini yeniden üretmek gerekli MRR olarak seçilmemiştir.
Makalenin ana fuzzy güvenlik bileşeni ve BOALBFS iki katmanlı akışı
gerçekleştirilmiş; en az bir temel mod karşılaştırması çalıştırılmıştır.
Makaledeki GAPSO, SAPSO, HCPSO, GWOPSO ve IWOPSO rakipleri ile Fig. 4-10'un
tam deney protokolü ek kapsam olarak açıkça listelenmiş, fakat mevcut teslim
kapsamında tamamlanmış gibi gösterilmemiştir.

## Veri seti açıklaması

README ve raporda aşağıdaki ayrım korunmalıdır:

- Referans makalenin ham ana veri setine erişim yoktur.
- Yönerge ve ders hocasının onayı doğrultusunda proje, makalede bildirilen
  aralıkları ve varsayımları kullanarak seeded sentetik veri üretir.
- Her sentetik veri paketi; ham görev, sunucu, link, uzman değerlendirmesi,
  ayarlar, seed, yazılım sürümü ve checksum bilgilerini saklar.
- Sentetik sonuçlar yöntemin ve yazılımın kontrollü davranışını gösterir;
  makalenin yayımlanmış sayısal sonuçlarının birebir doğrulaması değildir.

## Sonuç

Kod ve deney altyapısı yönergeye uygundur. Teslim öncesi kod dışı kalan işler:

1. Raporun 11 bölümlü yapıda yazılması ve IEEE kaynakçanın tamamlanması.
2. Rapora `Generative AI Usage Disclosure` bölümünün eklenmesi.
3. Sunumda fuzzy kurallar, üyelikler, Mamdani çıktısı, deney ve sınırlılıkların
   canlı olarak açıklanması.
4. Öğrencinin tüm kodu, deney tasarımını ve sonuçları sözlü olarak savunabilecek
   şekilde doğrulaması.
