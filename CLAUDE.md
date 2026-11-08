# Orijinal Minecraft – Proje Şartnamesi

Tarayıcıda çalışan, three.js (yerel `three.min.js`, r128) tabanlı Minecraft benzeri sonsuz blok dünyası. Tek dosya: [index.html](index.html). Yayın betiği: [yayinla.sh](yayinla.sh).

## Kural 0 – Her güncelleme GitHub'a yüklenir

- Yapılan her değişiklik, bir sonraki yanıtta `./yayinla.sh "ne değişti"` ile commit edilip GitHub'a gönderilir.
- Betik sürüm numarasını (`version.json` ve `APP_VERSION`) artırır, ardından `git add -A`, `git commit` ve `git push origin main` çalıştırır.
- Yükleme başarısız olursa bu kullanıcıya açıkça bildirilir; sessizce geçilmez.
- Sürüm numarası elle değiştirilmez; betik yönetir.

## Kural 1 – Oyun akıcı olmalı (kasma yasak)

Hedef: orta seviye bir telefonda ve dizüstünde **40 FPS altına düşmeden** oynanması. Bundan sonra eklenen her özellik aşağıdaki ilkelere uyar. Bir değişiklik bu kuralları bozuyorsa eklenmez veya sadeleştirilir.

### 1.1 Dünya çizimi
- **Blok başına nesne yok.** Blok için `Mesh`, `InstancedMesh` veya `Sprite` üretilmez. Dünya, chunk başına **malzeme başına tek birleşik `BufferGeometry`** olarak çizilir (`rebuildChunkMesh`).
- **Yalnızca görünen yüz çizilir.** Opak bir komşusu olan yüz üretilmez; aynı cins şeffaf bloklar (su-su, cam-cam) arasında yüz üretilmez. Yeni blok türü eklenirse `TRANSP` tablosu ve `BLOCKS` tanımı güncellenir.
- Dünya mesh'leri `matrixAutoUpdate = false` olur; kare başı matris hesabı yapılmaz.
- Çizim bütçesi (`?perf=1` ile ölçülür): normal bir sahnede **≤ 200 çizim çağrısı** ve **≤ 300 bin üçgen**.
- **Şeffaf malzeme yalnızca cam ve su** içindir. Yeni bir blok şeffaf yapılmaz (yaprak gibi bloklar opak kalır).

### 1.2 Malzeme, ışık, görüntü
- Yalnızca `MeshLambertMaterial` ve `MeshBasicMaterial`. `MeshStandard`/`Physical`, gölge, yansıma, post-processing **kullanılmaz**.
- Malzemeler ve kutu geometrileri **paylaşılır**: `LM(tex)`, `ML(renk)`, `MB(renk)`, `BG(w,h,d)` önbellekli yardımcıları kullanılır. Nesne başına `new THREE.Mesh...Material(...)` / `new THREE.BoxGeometry(...)` yazılmaz.
- Işık sayısı sabit: **1 ortam + 1 yönlü**. Yeni ışık eklenmez.
- Dokular 16×16, `NearestFilter`, `generateMipmaps = false`. Büyük görsel/dosya eklenmez.
- Kenar yumuşatma kapalı kalır. `pixelRatio` en fazla `DPR_MAX` (1.5).
- **Uyarlanabilir çözünürlük açık kalır:** FPS 40'ın altına düşünce çözünürlük %50'ye kadar iner, rahatlayınca yükselir (`adaptResolution`). Bu mekanizma bozulmaz.
- Kamera `far` değeri sis mesafesinden uzun tutulmaz (şu an 110).

### 1.3 Chunk yükleme ve dünya üretimi
- **Tek karede ağır iş yasak.** Bir kare içinde 8 ms'den uzun sürebilecek iş parçalara bölünür. Chunk üretimi ve mesh kurma **ayrı işler** olarak `pumpChunks` ile kare başına küçük bütçeyle (≈4 ms, en az bir iş), **en yakından başlayarak** yapılır.
- Senkron (`updateChunks(true)`) yükleme **yalnızca** oyun açılışında, kayıttan yüklemede ve yeniden doğmada (ışınlanma) kullanılır.
- Blok kırma/koyma `setBlock` ile chunk'ı **kirli** işaretler; mesh kare başında bir kez toplu yenilenir (`flushDirtyChunks`). `setBlock` içinde doğrudan mesh yenilenmez.
- Uzak chunk'lar bellekten silinir (`RENDER_DIST + 3` ötesi), geometrileri `dispose` edilir. Oyuncunun yaptığı değişiklikler `modsByChunk` içinde saklı kalır ve chunk yeniden üretilince uygulanır.
- `RENDER_DIST` artırılacaksa önce `?perf=1` ile ölçülür; FPS hedefi bozuluyorsa artırılmaz.
- Dünya üretimi yoğun gürültü hesabı yapıyorsa (`Math.sin` tabanlı `hash2D`) sonuçlar chunk içinde önbelleğe alınır (bkz. `makeCaveSampler`). **Aynı tohum aynı araziyi vermelidir**; üretim formülü değişirse kayıtlı dünyalar bozulacağı için bu bilerek ve bildirilerek yapılır.
- Doğal canlılar bir chunk için **yalnızca bir kez** doğar (`spawnedChunks`).

### 1.4 Sıcak yollar (kare başı ve blok başı çalışan kod)
- Sıcak yolda **metin anahtarı üretilmez** (`` `${x},${y},${z}` `` gibi). Blok sorgusu `getBlock`, chunk araması `ckey` (sayısal) ile yapılır.
- Kare başına **yeni nesne üretilmez** (`new THREE.Vector3`, geçici dizi/nesne). Gerekirse yeniden kullanılan değişkenler kullanılır.
- Blok hedefleme (`updateRaycast`) voxel taraması (DDA) ile yapılır; küçük adımlı döngüye geri dönülmez.
- DOM'a **yalnızca değer değişince veya seyrek** (≥ 0.25 sn) yazılır. Gökyüzü/sis rengi yalnızca evre değişince güncellenir.
- Kayıt (`writeSave`) kare içinde ağır iş yapmaz: değişiklik listesi önbellekli tutulur (`modsArrCache`), yalnızca değişince yeniden hesaplanır.

### 1.5 Canlılar ve efektler
- Toplam canlı sınırı **24** (`spawnMob`). Uzaktaki (>60 blok) canlılar silinir.
- Bir canlı **en çok ~10 parçadan** oluşur; geometri ve malzemeler paylaşılır (`BG`, `ML`, `MB`). Yeni canlı/efekt için büyük geometri veya yeni malzeme üretilmez.
- Küre/silindir gibi yuvarlak geometriler en çok ~12 segment kullanır.

### 1.6 Doğrulama (her değişiklikten sonra)
1. Oyunu `index.html?perf=1` ile aç; göstergede **FPS | çizim çağrısı | üçgen | chunk** görünür. Bütçeler (1.1) aşılıyorsa değişiklik sadeleştirilir.
2. Yürürken/uçarken chunk geçişlerinde **donma (takılma)** olup olmadığına bakılır; varsa iş parçalanır (1.3).
3. Blok kırıp koyarken, suya blok koyarken (su yayılması) gecikme olmamalıdır.
4. Telefon yatay boyutunda (en az 740×360) açılıp akıcılığı kontrol edilir.
5. Yeni bir özellik FPS'i gözle görülür düşürüyorsa **eklenmez**, önce optimize edilir.
