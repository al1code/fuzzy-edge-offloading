# Kaynaklar ve yöntemin teknik karşılığı

## Temel kaynak

[1] X. Jin, S. Zhang, Y. Ding ve Z. Wang, “Task offloading for multi-server edge
computing in industrial Internet with joint load balance and fuzzy security,”
*Scientific Reports*, c. 14, makale 27813, 2024,
doi: [10.1038/s41598-024-79464-2](https://doi.org/10.1038/s41598-024-79464-2).

[Yayıncı tam metni](https://www.nature.com/articles/s41598-024-79464-2).
Diğer bilimsel kaynakların IEEE künyeleri ve literatür karşılaştırması
[teknik raporun](../report/Bulanik_Mantik_Proje_Raporu.pdf) Related Work ve
References bölümlerindedir. Yazarın özgün kaynak kodu bu projede kullanılmamıştır.

## Bulanık güvenlik

`src/fuzzy_security.py`, makalenin (11)–(15) numaralı denklemlerini uygular.
Task Data, Task Type ve Terminal Lifecycle perspektifleri için her uzman
`(a, b, c)` üçgeni verir. Üçgenler uzman ağırlıklarıyla birleştirilir;
`(a + 4b + c) / 6` dönüşümüyle sayısal puan elde edilir. Perspektif puanlarının
ağırlıklı birleşimi `S` güvenlik seviyesidir. Sayısal puan dönüşümü, ayrı
`centroid()` hesabıyla karıştırılmamalıdır.

Model, `S` güvenlik eşiğinin altındaysa pozitif risk üretir; eşikte ve üstünde
riski sıfır alır. Denklem (14) ile ardından gelen metnin eşitsizlikleri
çeliştiğinden uygulamada denklem izlenir. Gönderim riski görev riskiyle
gönderilen oranın çarpımıdır. Bu değer gerçek saldırı olasılığı değildir.

## BOALBFS

`src/optimizers/genetic.py` adaptif GA ile görevlerin yerel/sunucu konumlarını
arar. Rulet seçimi, adaptif çaprazlama/mutasyon ve elitizm kullanılır.
`src/optimizers/sapso.py`, verilen konumlarda SA-PSO ile oranları arar.
PSO adayları kendi ve grubun iyi çözümlerinden yararlanır; benzetimli tavlama
bazen kötü adımları kabul ederek aramanın dar bir bölgede sıkışmasını azaltır.
`solve_boalbfs` iki katmanı ortak amaç fonksiyonunda birleştirir.

Arama bütçeleri, başlangıç dağılımları, tavlama sıcaklığı ve makalede tam
belirtilmeyen diğer ayarlar proje seçimleridir; deney manifestlerine yazılır.
Makaledeki mutasyon ifadesi (35) için `f_l = F` yorumu kullanılır. GA ve
SA-PSO yalnız en iyi gözlenen uygun planı döndürür; global optimum garantisi yoktur.

## Ortak model ve normalizasyon

`src/latency.py`: cihaz, iletim ve sunucu süreleri toplanır; toplam model süresi
görev sürelerinin toplamıdır. Paralel bitiş zamanı veya kuyruk modeli yoktur.
`src/load_balance.py`: CPU, bant genişliği ve bellek rezervasyonları kontrol
edilir. Rezervasyon sunucu seçimine bağlıdır; seçili sunucuda gönderim oranı
sıfır olsa bile rezervasyon kalır. Yerel kararda sunucu seçilmez.

`src/evaluation.py` ve `src/objective.py`: normalize süre, normalize risk ve
yük varyansı ağırlıklı `F` puanında birleştirilir. Karşılaştırılan planlar aynı
normalizasyonu kullanır. Pozitif toplam riskte tam kenarın normalize riski 1'dir.
Eşit ağırlıklarla tam kenar `F > 1/3`, yerel `F <= 1/3` olur. Bu yüzden bu
normalizasyon makaledeki tam kenar/yerel sıralamasını aynı şekilde üretemez;
özgün verinin bulunmaması tek fark nedeni değildir.

## Mamdani katkısı

`src/fuzzy_controller.py`, özgün puan hesabından ayrı bir Type-1 Mamdani katmanıdır.
Girdiler `S` ve birleşik üçgenlerin ortalama genişliği `U`'dur. Düşük/orta/yüksek
üçgen üyelikler, dokuz kural, min-AND, max birleştirme ve 1001 noktalı centroid
ile izinli en yüksek gönderim oranı hesaplanır. GA/SA-PSO bu üst sınıra uyar.

`U` uzman anlaşmazlığının doğrudan ölçüsü değildir. Kurallar gerçek saldırı
verisiyle kalibre edilmemiştir. Bütün ara noktalarda monotonluk veya her koşulda
performans üstünlüğü iddiası yoktur. Kural tablosu ve üyelik koordinatları
kaynak kodunda açıkça tanımlıdır; görev bazlı hesap izi arayüzde görülebilir.

## Kesin ve analitik kontrol

Sabit konum, kaynak ve normalizasyonda `F` gönderim oranlarına göre afindir.
Her görev için sıfır veya izinli üst oran değerlendirilerek oran alt problemi
çözülebilir. `src/optimizers/locations.py` bu özelliği kullanır.
`src/optimizers/exact.py`, küçük senaryolarda bütün konum/uç nokta seçeneklerini
aday bütçesi içinde tarar. Bu doğrulama aracıdır; büyük ölçekteki GA araması
yerine geçen bir global çözüm iddiası değildir.

## Veri, deneyler ve çıktılar

- [Sentetik girdiler ve parametre kaynakları](synthetic_data.md)
- [Kaydedilmiş deneyler, ham kayıtlar, tablolar ve grafikler](../results/README.md)
- [Kurulum ve yeniden çalıştırma komutları](../README.md)

Özgün yazar girdileri ve bütün uygulama ayrıntıları elde edilmemiştir.
Bu çalışma çekirdek yöntemi yeniden uygular ve kontrollü katkılar ekler;
makalenin bütün rakip algoritmalarını, şekillerini ve yüzdelerini tekrar etmez.

## Yapay zekâ ve görseller

ChatGPT ve Codex kod, açıklama, inceleme ve dokümantasyon desteğinde kullanılmıştır.
Sunumun endüstriyel kapak çizimi, cihaz/sunucu illüstrasyonu ve arka planları
OpenAI görsel üretim aracıyla oluşturulmuş kavramsal görsellerdir. Gerçek fabrika
fotoğrafı veya deney kanıtı değildir. Sayısal grafikler kayıtlı proje sonuçlarını
gösterir. Raporun Generative AI Usage Disclosure bölümü kullanımı açıklar.
