# FastAPI + WebSocket + Gemini Chatbot — Yol Haritası II: Döngü 7–12

## Üründen Pazara: AI Backend Developer Paketi

Bu doküman, ilk yol haritasının (Döngü 1–6) devamıdır ve aynı sözleşmeyle çalışır: **sen okuyacaksın, sen düşüneceksin, sen kodlayacaksın.** Ben rotayı çizdim; her döngü sonunda K bölümündeki çıktılarla döndüğünde reviewer moduna geçeceğim.

İlk altı döngü projenin *içine* bakıyordu: doğruluk, güvenlik, dayanıklılık, test. Bu altı döngü projenin *dışına* bakıyor: kalıcılık, taşınabilirlik, gerçek kullanıcılar, satılabilir yetenekler ve pazar. Hedef konumlanman net:

> **AI Backend Developer — FastAPI, PostgreSQL, Docker, RAG, LLM integrations, testing, deployment.**

İki ilke bu yarının tamamına hâkim:

1. **Yeni proje yok.** Her döngü, aynı chatbot'u büyütür. İlk haritanın "bilinçli ertelenenler" tablosundaki maddeler (persistence, Dockerfile, retry, multi-device) burada sırayla "vadesi geldi" olarak açılır. Ertelenen her iş, bir öğrenme aracına dönüşür.
2. **Service-to-product.** Döngü 12'ye kadar ürün satmıyorsun; *yetenek* inşa ediyorsun. 12'de o yetenekleri pakete çevirip pazara çıkıyorsun. SaaS, ödeme sistemi, multi-tenancy bu haritada **yok** — ilk gerçek müşteri tekrar eden bir problem gösterdiğinde, üçüncü haritanın konusu olurlar.

---

## Döngülerin genel haritası (önce büyük resim)

| # | Döngü | Tek cümleyle |
|---|---|---|
| 7 | PostgreSQL, SQLAlchemy ve kalıcılık | Bağlantı ölünce sohbet de ölmesin; ertelenen persistence borcunu öde. |
| 8 | Docker, Compose ve CI | "Benim makinemde çalışıyor"dan "her yerde aynı şekilde çalışıyor"a geç. |
| 9 | Gerçek kimlik: JWT, kullanıcılar, RBAC | Tek paylaşılan token'dan kullanıcı hesaplarına ve rollere evril. |
| 10 | RAG: embeddings, pgvector, doküman asistanı | Bot artık *senin* dokümanlarınla konuşsun — pazarın bir numaralı talebi. |
| 11 | Frontend: chat arayüzü ve mini admin paneli | Backend'in ne kadar iyi olursa olsun, müşteri demo görmek ister. |
| 12 | Pazara çıkış: portföy, konumlanma, ilk üç iş | Teknik döngü değil; satış döngüsü. Yorum biriktirme fazı. |

Sıralamanın iç mantığı: 7 (veri) → 8 (paketleme) → 9 (kimlik, 7'nin üstüne oturur) → 10 (RAG, 7'nin Postgres'ini pgvector ile yeniden kullanır) → 11 (hepsini gösteren yüz) → 12 (hepsini satan paket). Hiçbir döngü bir sonrakinin ön koşulunu eksik bırakmaz.

---

## Döngü 7 — PostgreSQL, SQLAlchemy ve Kalıcılık

### A. Bu döngünün temel amacı
İlk haritadan beri taşınan en eski bilinçli borç: sohbet geçmişi bağlantının ömrü kadar yaşıyor; sayfa yenilenince bot her şeyi unutuyor (Döngü 1'de "ne gerekirdi?" diye not etmiştin: kimlik + veritabanı + geri yükleme). Bu döngü o cevabı koda çevirir: PostgreSQL'de `conversations` ve `messages` tabloları, SQLAlchemy (veya SQLModel) ile async ORM erişimi, Alembic ile şema migration'ları, ve WebSocket yeniden bağlandığında geçmişin `chats.create(history=...)` ile geri yüklenmesi. MySQL/PDO deneyimin var; buradaki sıçrama SQL öğrenmek değil, **ORM + migration + async driver** üçlüsünü ve "şema zamanla değişir, migration onun versiyon kontrolüdür" zihniyetini yerleştirmek.

### B. Hangi bilinen boşluklar bu döngüye giriyor?
- **[İlk harita, bilinçli erteleme]** Chat history persistence (Redis/SQLite/Postgres, reconnect'te restore) — "D5'teki katmanlama yapılmadan storage soyutlaması anlamsız" denmişti; D5 bitti, vade doldu.
- **[İlk harita, bilinçli erteleme]** Multi-device session — "persistence olmadan yapılamaz" denmişti; bu döngü ön koşulunu kurar (kendisi D9'da kimlikle tamamlanır).
- **[D5 mirası]** `ChatService` soyutlaması var ama arkasında bellek var; gerçek bir repository katmanı yok.
- **[Yeni]** Veri modeli tasarımı: mesajları tek tek mi, konuşma bloğu olarak mı saklamalı? Token-pencereleme (D4) ile DB'deki tam geçmiş ilişkisi ne?

### C. Bu döngü neden bu sırada ele alınmalı?
Çünkü 9, 10 ve 11'in hepsi veritabanına yaslanır: kullanıcı hesapları (D9) bir `users` tablosu ister; RAG (D10) pgvector'ü ister — ki o da bir Postgres eklentisidir, yani bu döngüde kurduğun veritabanı D10'da embedding deposu olarak yeniden kullanılır; dashboard (D11) istatistikleri DB'den okur. Docker'dan (D8) önce gelmesinin sebebi de pratik: compose dosyasında ayağa kaldıracağın ikinci servis tam olarak bu Postgres olacak — önce servisi tanı, sonra paketle.

Neden MySQL değil? Bildiğin araç olduğu için cazip; ama pgvector (D10'un kalbi), daha güçlü JSON desteği ve yurt dışı ilanlarındaki sinyal değeri Postgres'i net kazanan yapar. MySQL bilgin boşa gitmez — SQL aynı SQL; değişen ekosistem.

### D. Döngü sonunda projede beklenen kalite artışı
- **Kalıcılık:** Yenileme/yeniden bağlanma sohbeti öldürmüyor; "kaldığın yerden devam" çalışıyor.
- **Mimari:** `ChatService`'in altında gerçek bir repository katmanı; iş mantığı SQL'den habersiz.
- **Şema disiplini:** Her şema değişikliği bir Alembic migration'ı; `alembic upgrade head` ile her ortam aynı şemaya geliyor.
- **D4 entegrasyonu:** DB'de *tam* geçmiş duruyor; modele giden pencere (D4'teki windowing) ondan türetiliyor — "kayıt" ile "bağlam" ayrımı netleşmiş.

### E. Öğrenmem gereken teknik kavramlar
**PostgreSQL**
- Temel tipler, `TIMESTAMPTZ`, `UUID` kolonları, index mantığı (hangi sorguya hangi index). — Sorguların ölçeklenmesi için.
- Transaction ve isolation temelleri. — Mesaj + konuşma güncellemesinin atomik olması için.

**SQLAlchemy 2.x / SQLModel**
- Async engine + `asyncpg` driver, `AsyncSession`, session ömrü (request-scoped vs connection-scoped). — Event loop'u bloklamamak için (D1'deki tuzağın DB hali!).
- Declarative modeller, ilişkiler (`Conversation` 1—N `Message`), lazy/eager loading farkı. — N+1 sorgu tuzağı için.
- Repository deseni: ORM çağrılarını tek modülde toplamak. — D5 katmanlamasının devamı.

**Alembic**
- `alembic init`, autogenerate, upgrade/downgrade, migration'ın kod incelemesi. — Autogenerate'in her şeyi görmediğini bilmek için.

**Tasarım**
- Veri modeli: `users`(şimdilik iskelet) / `conversations` / `messages(role, content, token_count, created_at)`. — D9 ve D11'in üstüne oturacağı temel.
- "DB'deki tam geçmiş" vs "modele giden pencere" ayrımı. — D4 ile köprü.

### F. Okumam gereken resmi dokümantasyonlar
- **SQLAlchemy 2.0 docs** → "Asyncio Support" (tamamı), "ORM Quick Start", "Session Basics"
- **SQLModel docs** (tercih edersen) → tutorial'ın tamamı; FastAPI ile entegrasyon bölümü
- **Alembic docs** → "Tutorial", "Auto Generating Migrations" (sınırlamalar kutusu dahil)
- **PostgreSQL docs** → "Data Types" (özellikle uuid, timestamptz, jsonb), "Indexes" giriş
- **FastAPI docs** → "SQL (Relational) Databases" sayfası — dependency ile session geçirme deseni
- **Google GenAI SDK** → `chats.create(history=...)` parametresi ve history formatı (D4'te okuduğunu bu kez "geri yükleme" gözüyle)

### G. Dokümantasyon okurken cevaplamam gereken odak soruları
1. Async SQLAlchemy'de session'ı WebSocket bağlantısı boyunca açık mı tutmalıyım, her işlemde açıp kapatmalı mıyım? Trade-off ne?
2. Senkron bir DB çağrısı async handler'da neyi bozar? (D1'deki "bloklayan çağrı" dersinin DB karşılığı.)
3. `Conversation`—`Message` ilişkisinde lazy loading WebSocket bağlamında neden tehlikeli olabilir (session kapandıktan sonra erişim)?
4. Alembic autogenerate neleri *göremez*? Üretilen migration'ı neden her zaman elle incelemeliyim?
5. Mesajları tek tek satır olarak mı, konuşmayı JSONB blob olarak mı saklamalı? Hangisi sorgulanabilirlik, hangisi basitlik verir; bu projede hangisi?
6. **(Projeme özel)** Reconnect'te geçmişi `chats.create(history=...)`'e verirken D4 penceresini mi, tam geçmişi mi vermeliyim? `token_count` kolonu bu kararı nasıl kolaylaştırır?
7. **(Projeme özel)** `connection_id` (her bağlantıda yeni UUID) ile `conversation_id` (kalıcı) artık farklı kavramlar — loglama (D2) bu ayrımı nasıl yansıtmalı?
8. **(Karşılaştırma)** Persistence için Redis/SQLite/Postgres seçenekleri vardı; bu projede Postgres'i seçmenin somut gerekçeleri neler? Hangi senaryoda Redis daha doğru olurdu?

### H. Öğrenme notlarımı hangi formatta çıkarmalıyım?
İlk haritadaki standart tablo (Kavram / Kendi cümlemle / Bu projedeki karşılığı / Eski davranış / Yeni davranış / Riski / Açık sorum) + bu döngüye özel ek: **şema diyagramı** (Mermaid — zaten biliyorsun) ve her tablo için "neden bu kolonlar" gerekçe satırı.

### I. Kodda benim kendim uygulamam gereken iyileştirme görevleri
1. Docker olmadan lokal Postgres kur (şimdilik native), `DATABASE_URL`'i `Settings`'e ekle (validator'ıyla — D2 kası).
2. `users` (iskelet: id, created_at), `conversations`, `messages` modellerini yaz; Alembic'i başlat; ilk migration'ı üret ve **elle incele**.
3. Repository katmanı: `ConversationRepository` (create, append_message, get_history). `ChatService` yalnızca bunu çağırsın — SQL/ORM detayı service'e sızmasın.
4. WebSocket açılışında: query'den `conversation_id` gelirse geçmişi yükle ve `chats.create(history=...)` ile oturumu kur; gelmezse yeni konuşma yarat ve id'yi ilk envelope'la (D4) istemciye bildir.
5. Her mesajda (kullanıcı + asistan) DB'ye yaz; `token_count`'u D4'teki sayımdan doldur.
6. D4 penceresini DB'den türet: "son N token'lık dilimi getir" sorgusu.
7. **(Bilinçli erteleme)** Mesaj araması, arşivleme, soft-delete — ihtiyaç yokken şema şişirme.
8. **(Bilinçli erteleme)** Redis cache katmanı — ölçüm olmadan optimizasyon yok.

### J. Bu döngü tamamlandı mı, nasıl anlayacağım?
- Sayfayı yenileyip aynı `conversation_id` ile bağlanınca bot kaldığı yerden devam ediyor; yeni bağlantıda yeni konuşma açılıyor.
- `alembic downgrade -1 && alembic upgrade head` temiz çalışıyor.
- Testler (D6) gerçek bir test veritabanına karşı koşuyor; repository mock'lanarak service testleri DB'siz çalışabiliyor.
- Async handler içinde hiçbir senkron DB çağrısı yok (kanıt: kod taraması + yük altında event loop donmuyor).
- "DB'deki kayıt" ile "modele giden pencere"nin farkını iki cümlede anlatabiliyorum.

### K. Döngü sonunda bana neyle dönmelisin?
Not dosyan (şema diyagramı dahil), migration dosyaların, repository + güncellenmiş service kodu, ve şu üç sorunun yazılı cevabı: blob-vs-satır kararın ve gerekçesi; reconnect'te pencere-vs-tam-geçmiş kararın; session ömrü kararın. Reviewer modunda bunları değerlendireceğim.

---

## Döngü 8 — Docker, Compose ve CI

### A. Bu döngünün temel amacı
Proje şu an "Erdem'in makinesinde + Railway'de" çalışıyor; ikisi arasındaki fark görünmez ve tekrarlanamaz. Bu döngü uygulamayı bir **Dockerfile** ile imaja, uygulama+Postgres ikilisini bir **docker-compose** dosyasıyla tek komutla kalkan bir sisteme, ve D6'da yazdığın testleri her push'ta koşan bir **GitHub Actions** hattına bağlar. Hedef zihniyet: "ortam, kodun parçasıdır" — 12-factor'ün config/disposability ilkelerinin (D2 ve D6'da tohumlanan) somutlaşması.

### B. Hangi bilinen boşluklar bu döngüye giriyor?
- **[İlk harita, bilinçli erteleme]** "Dockerfile + reverse proxy + production deploy — projeyi gerçekten bir VPS'e koymaya hazır olduğunda." Vade: şimdi (reverse proxy hariç — o hâlâ erken).
- **[D6 mirası]** Testler var ama yalnızca lokalde elle koşuyor; "refactor güveni" otomasyona bağlanmadı.
- **[D7 mirası]** Postgres kurulumu elle yapıldı; yeni makinede tekrarı belgesiz.

### C. Bu döngü neden bu sırada ele alınmalı?
D7'den sonra: çünkü compose'un ayağa kaldıracağı ikinci servis Postgres — paketlenecek şey önce var olmalı. D9'dan önce: çünkü auth'u test ederken "temiz ortamda sıfırdan kur" yeteneği hata ayıklamayı yarıya indirir; ayrıca CI, D9'dan itibaren her güvenlik değişikliğinde regresyon ağı olur. Freelance hedefi için de eşik: müşteriye teslimin evrensel dili "şu repo'yu klonla, `docker compose up`."

### D. Döngü sonunda projede beklenen kalite artışı
- **Tekrarlanabilirlik:** Sıfır makinede `git clone` → `docker compose up` → çalışan sistem (uygulama + DB + migration'lar).
- **CI güveni:** Her push'ta lint + testler; kırmızı pipeline merge'ü durduruyor.
- **Imaj disiplini:** Küçük, katman-önbellekli, secret içermeyen imaj; `.env` imaja girmiyor (D2 ilkesinin Docker karşılığı).
- **Teslim edilebilirlik:** Proje artık "müşteri sunucusuna kurulabilir" sınıfında.

### E. Öğrenmem gereken teknik kavramlar
**Docker**
- Image vs container, layer ve cache mantığı, multi-stage build. — Hızlı ve küçük build için.
- `WORKDIR`, `COPY` sırası, `pip install`'ın cache'lenmesi; non-root user. — Standart iyi pratikler.
- Env var'ların container'a geçişi; `.dockerignore`. — Secret'ın imaja sızmaması için (D2/D3 refleksi).

**Docker Compose**
- Service tanımı, `depends_on` + healthcheck (Postgres "hazır" olmadan app başlamasın), named volume (veri kalıcılığı), network.
- Migration'ın nerede koşacağı: app açılışında mı, ayrı bir komutla mı? — Trade-off'u bilerek seçmek.

**GitHub Actions**
- Workflow/job/step yapısı, `services:` ile test Postgres'i, pip cache, secret'ların Actions'ta yönetimi.

**Uvicorn production**
- `--reload`'suz çalıştırma, `--workers` ve WebSocket'lerle ilişkisi (sticky olmayan bağlantı durumu — neden şimdilik tek worker mantıklı).

### F. Okumam gereken resmi dokümantasyonlar
- **Docker docs** → "Dockerfile best practices", "Multi-stage builds", "Compose" quickstart + `healthcheck`
- **FastAPI docs** → "FastAPI in Containers - Docker" (resmi sayfa; tek worker önerisinin gerekçesi)
- **GitHub Actions docs** → "Building and testing Python", "About service containers"
- **Uvicorn docs** → "Deployment" sayfası
- **12-factor.net** → "Config", "Build, release, run", "Disposability" (kısa; D2/D6'da başladığını bitir)

### G. Dokümantasyon okurken cevaplamam gereken odak soruları
1. `COPY requirements.txt` + `pip install`'ı `COPY . .`'dan önce yazmak cache'i nasıl kurtarır?
2. Multi-stage build bu projede gerçekten gerekli mi, yoksa premature mı? Karar gerekçen?
3. Compose'da `depends_on` tek başına neden yetmez; healthcheck ne ekler?
4. Migration'ı container açılışında otomatik koşturmanın riski ne (iki replica aynı anda kalkarsa)? Bu projede hangi yolu seçiyorum?
5. WebSocket'li bir uygulamada `--workers 4` ne bozar? Bağlantı içi durum (rate-limit listesi, chat objesi) worker'lar arasında paylaşılır mı?
6. **(Projeme özel)** `.env` dosyam imaja girmemeli; Railway'de, compose'da ve Actions'ta aynı `Settings` sınıfı üç farklı kaynaktan nasıl besleniyor? (D2'deki "env değişkeni > .env" önceliğinin meyvesi.)
7. **(Projeme özel)** D6 testlerinin bir kısmı gerçek DB istiyor; Actions'ta `services: postgres` ile test DB'sini nasıl veririm, `DATABASE_URL`'i nasıl yönlendiririm?
8. **(Karşılaştırma)** CI'da testleri host Python'da koşmak vs compose içinde koşmak — hız/aslına-uygunluk trade-off'u; bu projede hangisi?

### H. Öğrenme notlarımı hangi formatta çıkarmalıyım?
Standart tablo + bu döngüye özel: **"build günlüğü"** — imaj boyutunu ve build süresini her iyileştirmede ölçüp not et (başlangıç → multi-stage → cache düzeni). Sayılarla konuşan not, en kalıcı not.

### I. Kodda benim kendim uygulamam gereken iyileştirme görevleri
1. `Dockerfile` yaz (önce naif, sonra cache-düzenli; gerekçeliyse multi-stage), `.dockerignore` ekle.
2. `docker-compose.yml`: app + postgres (healthcheck'li) + named volume; tek komutla temiz kurulum.
3. Migration stratejine karar ver ve uygula (entrypoint mi, `docker compose run app alembic upgrade head` mi) — gerekçesini README'ye yaz.
4. GitHub Actions workflow: push/PR'da ruff (veya seçtiğin linter) + pytest, `services: postgres` ile.
5. README'yi yeniden yaz: "Quickstart: docker compose up" + mimari özeti + env değişken tablosu. (Bu README, D12'deki portföyün ilk sayfasıdır — İngilizce yaz.)
6. Railway deploy'unu imaj-tabanlı akışla hizala.
7. **(Bilinçli erteleme)** Nginx/reverse proxy, HTTPS sonlandırma, çoklu worker — gerçek VPS müşterisi gelince.
8. **(Bilinçli erteleme)** Imaj registry'si, sürüm etiketleme stratejisi — tek geliştiriciyken bürokrasi.

### J. Bu döngü tamamlandı mı, nasıl anlayacağım?
- Hiç kurulum yapılmamış bir makinede (veya `docker compose down -v` sonrası) tek komutla sistem ayağa kalkıyor ve sohbet + kalıcılık çalışıyor.
- Actions her push'ta yeşil; bilerek bozduğun bir test pipeline'ı kırmızıya çeviriyor.
- Imajda secret yok (kanıt: `docker history` / imaj içi dosya kontrolü).
- "Image ile container farkı ne, cache nasıl çalışıyor, neden tek worker?" sorularını akıcı cevaplayabiliyorum.

### K. Döngü sonunda bana neyle dönmelisin?
Dockerfile + compose + workflow dosyaların, build günlüğün (ölçümlerle), yeni README, ve iki yazılı karar: migration stratejin + tek-worker gerekçen.

---

## Döngü 9 — Gerçek Kimlik: JWT, Kullanıcılar ve RBAC

### A. Bu döngünün temel amacı
D3'teki `app_access_token` kapıyı kilitledi ama herkes aynı anahtarı taşıyor: kimlik yok, sadece giriş izni var. Bu döngü onu gerçek bir kimlik sistemine evriltir: kayıt/giriş uçları, parola hash'leme, **JWT** üretimi ve doğrulaması, WebSocket handshake'inde token'dan kullanıcıyı çözme, ve iki rollü basit **RBAC** (admin/user — PHP projendeki `kullanici_rutbe` sezgisinin profesyonel hali). D7'deki `users` iskeleti ete kemiğe bürünür; "kim bağlandı?" sorusu nihayet gerçek bir cevaba kavuşur ve loglar (D2) kullanıcıya bağlanır.

### B. Hangi bilinen boşluklar bu döngüye giriyor?
- **[D3 mirası]** Tek paylaşılan token: iptal edilemez, kişiselleştirilemez, sızarsa herkes etkilenir.
- **[D3 açık sorusu]** "Rate limit bağlantı başına mı kullanıcı başına mı?" — kimlik olmadan cevaplanamıyordu; şimdi cevaplanır ve kullanıcı-başına taşınır.
- **[D7 mirası]** `conversations.user_id` boşta — konuşmalar artık sahibine bağlanır; multi-device session ön koşulu tamamlanır.
- **[İlk harita yetkinlik listesi]** "Depends ile DI'yi hem HTTP hem WebSocket'te uygulamak" — auth dependency'si bunun gerçek sınavı (notlarındaki D3/Depends sayfaları nihayet sahaya iner).

### C. Bu döngü neden bu sırada ele alınmalı?
D7'siz olmazdı (kullanıcı nereye yazılacak?); D8'siz sancılı olurdu (auth hatası ayıklarken temiz ortam + CI regresyon ağı altın değerinde). D10'dan önce olmasının sebebi ürünsel: RAG'de kullanıcılar *kendi dokümanlarını* yükleyecek — "bu doküman kimin?" sorusu kimliksiz sorulamaz. Güvenlik açısından da doğal sıra: D3 "kapı", D9 "kimlik", ileride (üçüncü harita) "kiracı ayrımı".

### D. Döngü sonunda projede beklenen kalite artışı
- **Kimlik:** Her bağlantı bir kullanıcıya çözülüyor; loglarda `user_id` + `connection_id` birlikte.
- **Güvenlik:** Parolalar doğru hash'le (bcrypt/argon2) saklanıyor; JWT süreli; sızan tek token tek kullanıcıyı etkiliyor.
- **Yetki:** Admin uçları (örn. D11'in besleyeceği istatistikler) role kapısının arkasında.
- **D3 borcu kapanıyor:** Rate limit kullanıcı-başına; "aynı kullanıcı iki sekme açınca limiti ikiye katlıyor" açığı bitiyor.

### E. Öğrenmem gereken teknik kavramlar
**Kimlik temelleri**
- Hashing vs encryption; bcrypt/argon2; neden düz parola asla. — Temel hijyen.
- JWT anatomisi: header/payload/signature; claim'ler (`sub`, `exp`, `iat`); imza doğrulama; **JWT'nin şifreli değil imzalı** olduğu gerçeği (payload'a sır koyma!).
- Access token süresi trade-off'u; refresh token kavramı (uygulaması ertelenebilir, kavramı bilinmeli).

**FastAPI**
- `OAuth2PasswordBearer` akışı, `Depends(get_current_user)` deseni; aynı dependency'nin HTTP ve WebSocket'te kullanım farkı.
- WebSocket'te token taşıma: D3'teki query-string kararın geçerli kalıyor (tarayıcı header koyamıyor — MDN okuman); değişen şey token'ın *içeriği*: statik sır → imzalı JWT.

**RBAC**
- En basit hali: `users.role` kolonu + `require_role("admin")` dependency'si. Permission tabloları, scope'lar — erteleme listesinde.

### F. Okumam gereken resmi dokümantasyonlar
- **FastAPI docs** → "Security" bölümünün tamamı (Intro → OAuth2 with Password and JWT) — bu döngünün ana metni
- **PyJWT** (veya jose) docs → encode/decode, `exp` doğrulama, algoritma sabitleme (`alg` karmaşası uyarısı)
- **passlib / bcrypt docs** → hash + verify; work factor
- **OWASP** → "Password Storage Cheat Sheet", "JWT Cheat Sheet" (D3'teki OWASP refleksinin devamı)
- **MDN** → WebSocket constructor sayfana dön — bu kez "JWT'yi query'de taşımanın log'a sızma riski" gözüyle (sunucu access-log'larında URL maskeleme)

### G. Dokümantasyon okurken cevaplamam gereken odak soruları
1. JWT imzalı ama şifreli değil — payload'ı kim okuyabilir? Bu, içine ne koyup koymayacağımı nasıl belirler?
2. `exp` süresi: 15 dakika vs 7 gün — bu projede (uzun ömürlü WebSocket!) trade-off ne? Token, bağlantı *açıkken* expire olursa ne yapmalıyım: bağlantıyı kesmek mi, bağlantı kurulurkenki doğrulamayı yeterli saymak mı?
3. `Depends(get_current_user)` WebSocket endpoint'inde HTTP'dekiyle aynı mı çalışır? `WebSocketException` ile reddetme, benim D3'teki elle `close(1008)` yaklaşımımdan ne zaman daha iyi?
4. Parola hash'inde work factor neyi dengeler? Login ucu bu yüzden DoS hedefi olabilir mi — D3 rate limit'i login'e de uygulanmalı mı?
5. JWT'yi query string'de taşımak access log'larına sızma riski yaratır — bu projede riski nasıl küçültürüm (kısa exp, log maskeleme, wss)?
6. **(Projeme özel)** `get_current_user` dependency'si D7'deki repository'yi kullanacak — DI zinciri (settings → db session → user) FastAPI'de nasıl kurulur? D5 katmanlarına nereye oturur?
7. **(Projeme özel)** Rate limit state'i kullanıcı-başına olunca nerede yaşamalı: bellek (tek worker — D8 kararınla tutarlı) mı, DB mi? Gerekçen?
8. **(Karşılaştırma)** Session-cookie vs JWT — bu proje için JWT'yi seçtiren somut özellikler ne (WebSocket, API-first, stateless)? Hangi projede cookie'yi seçerdim?

### H. Öğrenme notlarımı hangi formatta çıkarmalıyım?
Standart tablo + bu döngüye özel: **tehdit tablosu** — "saldırı senaryosu → hangi önlem karşılıyor → hangi senaryo hâlâ açık" (D3'teki attack-surface checklist'inin büyümüş hali).

### I. Kodda benim kendim uygulamam gereken iyileştirme görevleri
1. `users` tablosunu tamamla (email, password_hash, role, created_at) — Alembic migration'la (D7 kası).
2. `/auth/register` ve `/auth/login` uçları; login JWT döndürsün. (Bunlar HTTP — Pydantic body doğrulaması, serinin 3. yazısındaki bilgin nihayet ana akışta.)
3. `get_current_user` dependency'si; HTTP'de header'dan, WebSocket'te query'den token çözsün.
4. WebSocket handshake'i: statik token kontrolünü JWT doğrulamasıyla değiştir; `user_id`'yi `ConnectionLoggerAdapter` bağlamına ekle (D2 kası).
5. Konuşmaları kullanıcıya bağla: kullanıcı yalnız kendi `conversation_id`'lerine bağlanabilsin (yetki kontrolü — IDOR'a karşı).
6. Rate limit'i kullanıcı-başına taşı; login ucuna da kaba bir limit koy.
7. `require_role("admin")` dependency'si + tek örnek admin ucu (örn. `/admin/stats` iskeleti — D11 besleyecek).
8. Testler (D6/D8): kayıt-giriş-yetki akışı, süresi geçmiş/bozuk token, başkasının konuşmasına erişim denemesi — hepsi CI'da.
9. **(Bilinçli erteleme)** Refresh token, e-posta doğrulama, parola sıfırlama, OAuth (Google login) — ürün ihtiyacı doğunca.
10. **(Bilinçli erteleme)** İnce taneli permission sistemi — iki rol yetiyorken tablo şişirme.

### J. Bu döngü tamamlandı mı, nasıl anlayacağım?
- Kayıt → giriş → WebSocket'e JWT ile bağlanma → kendi geçmişini görme akışı uçtan uca çalışıyor; iki farklı kullanıcı birbirinin konuşmasını **göremiyor** (testi var).
- Bozuk/expired token 1008 ile reddediliyor ve doğru seviyede loglanıyor (D2/D3 refleksi).
- DB'de düz parola yok; JWT payload'ında hassas veri yok.
- Tehdit tablon dolu ve "hâlâ açık" sütununda ne yazdığını savunabiliyorsun.

### K. Döngü sonunda bana neyle dönmelisin?
Tehdit tablon, auth akış diyagramın (Mermaid), kod + testler, ve üç yazılı karar: exp süresi + uzun-WebSocket politikası; rate-limit state'inin yeri; query-string'de JWT risk azaltman.

---

## Döngü 10 — RAG: Embeddings, pgvector ve Doküman Asistanı

### A. Bu döngünün temel amacı
Şu ana kadar bot yalnızca modelin ezberiyle konuşuyor. Bu döngü, freelance pazarının bir numaralı talebini ekler: **kullanıcının kendi dokümanlarıyla konuşan bot.** Akışın iki yarısı var — *ingestion*: PDF yükle → metni çıkar → parçalara böl (chunking) → her parçayı embedding'e çevir → pgvector'e yaz; ve *retrieval*: soru gelince soruyu embed et → en yakın parçaları bul → bunları bağlam olarak prompt'a koy → Gemini cevaplasın, kaynak göstersin. Kavramsal hedef: "vektör benzerliği"nin ne olduğunu, chunking kararlarının cevap kalitesini nasıl belirlediğini ve RAG'in halüsinasyonu neden azalttığını (ama bitirmediğini) içselleştirmek.

### B. Hangi bilinen boşluklar bu döngüye giriyor?
- **[Konumlanma raporu]** "RAG + embeddings + vector DB — AI ürünlerinde en satılabilir alan." Portföyün (D12) ana demosu burada doğar.
- **[D4 mirası]** Token bütçesi disiplini şimdi iki kat kritik: retrieval edilen bağlam da token harcar; pencere hesabına "context budget" ekleniyor.
- **[D3 mirası]** Input validation yeni bir yüzey kazanıyor: dosya yükleme (boyut, tip, içerik) — `\x00` kontrolünün büyük kardeşi.
- **[D9 mirası]** "Bu doküman kimin?" — her doküman ve her arama kullanıcıya bağlı.

### C. Bu döngü neden bu sırada ele alınmalı?
Teknik zincir tamamlandı da ondan: Postgres var (D7) → pgvector bir `CREATE EXTENSION` uzaklığında; kimlik var (D9) → doküman sahipliği kurulabilir; envelope var (D4) → "kaynaklar" cevabın yanında yapılandırılmış alan olarak gidebilir; Docker var (D8) → pgvector'lü Postgres imajı compose'a tek satır. Bu döngü, önceki dokuzun bileşik faizi — ve D11'den önce gelmeli, çünkü dashboard'un gösterişli kısmı ("dokümanını yükle, sorunu sor") burada üretiliyor.

### D. Döngü sonunda projede beklenen kalite artışı
- **Yetenek sıçraması:** Bot, modelin bilmediği (senin yüklediğin) bilgiyle, kaynak göstererek cevap veriyor.
- **Maliyet bilinci:** Retrieval'lı promptun token bütçesi ölçülüyor ve sınırlanıyor (D4 disiplini genişledi).
- **Dürüstlük:** "Dokümanlarda bulamadım" diyebilen bot — RAG'in en zor ve en değerli davranışı.
- **Satılabilirlik:** Demo artık "genel chatbot" değil, "şirketinizin dokümanlarıyla konuşan asistan".

### E. Öğrenmem gereken teknik kavramlar
**Embeddings**
- Embedding nedir: metni anlam uzayında vektöre çevirmek; benzerlik = vektör yakınlığı (cosine). — RAG'in fizik kanunu.
- Gemini embedding modeli (`text-embedding` ailesi), boyut, maliyet; sorgu-embed'i ile doküman-embed'i aynı modelden olmalı.

**Chunking**
- Parça boyutu / overlap trade-off'u: küçük parça → isabetli ama bağlamsız; büyük → bağlamlı ama bulanık. — Kalitenin asıl ayarı.
- Sayfa/başlık sınırlarına saygılı bölme; metadata (kaynak dosya, sayfa no) taşıma — kaynak gösterme bunun üstüne kurulur.

**pgvector**
- `vector` tipi, `<=>` (cosine distance) operatörü, `ivfflat`/`hnsw` index'leri ve ne zaman gerektikleri (az veride brute-force yeter — premature index'leme!).

**PDF parsing**
- Metin tabanlı vs taranmış PDF farkı; çıkarımın kirli gerçekleri (başlık/dipnot gürültüsü). — "Garbage in, garbage out."

**RAG prompt tasarımı**
- Bağlamı sınırlarla verme ("yalnızca şu pasajlara dayan"), kaynak isteme, bulunamadıysa "bilmiyorum" talimatı; system_instruction (D3) ile ilişkisi.

### F. Okumam gereken resmi dokümantasyonlar
- **Google GenAI SDK / Gemini docs** → Embeddings bölümü (model adları, `embed_content`, batch)
- **pgvector README (GitHub)** → kurulum, operatörler, index bölümleri — kısa ve yoğun, tamamı
- **pypdf (veya pdfplumber) docs** → metin çıkarma; sınırlamalar bölümü özellikle
- **SQLAlchemy** → custom type ile pgvector entegrasyonu (pgvector-python paketi README'si)
- **Eugene Yan — "Patterns for Building LLM-based Systems"** → şimdi vakti geldi: RAG ve Guardrails bölümleri (eugeneyan.com/writing/llm-patterns/)

### G. Dokümantasyon okurken cevaplamam gereken odak soruları
1. Cosine similarity ile Euclidean distance farkı ne; embedding'ler normalize ise neden çoğu zaman aynı kapıya çıkar? pgvector'de hangi operatör hangisi?
2. Chunk boyutunu token'la mı karakterle mi tanımlamalı? Overlap yüzde kaç mantıklı bir başlangıç; neyi ölçerek ayarlarım?
3. Top-k kaç olmalı? k'yı artırmak ne zaman cevabı iyileştirir, ne zaman gürültü + token maliyeti ekler? (D4 bütçesiyle bağla.)
4. ivfflat/hnsw index'i kaç satırdan sonra anlamlı? Benim demo ölçeğimde index kurmamak neden doğru karar olabilir?
5. Retrieval edilen bağlam chat history'sine mi eklenmeli, her soruda taze mi kurulmalı? Çok turlu sohbette RAG bağlam yönetimi nasıl değişir?
6. **(Projeme özel)** Ingestion (PDF işleme + embedding) WebSocket handler'da mı koşmalı? Event loop'u bloklama riski (D1 dersi!) — `to_thread` mı, FastAPI BackgroundTasks mı, ayrı uç mu?
7. **(Projeme özel)** "Dokümanlarda bulamadım" davranışını nasıl kurarım: similarity eşiği mi, prompt talimatı mı, ikisi mi? Eşiği neye göre seçerim?
8. **(Projeme özel)** Kaynak gösterimi envelope'a (D4) nasıl girer — `assistant_done` mesajına `sources: [{file, page}]` alanı mı? Frontend sözleşmesi nasıl değişir?
9. **(Karşılaştırma)** pgvector vs Chroma vs Pinecone — bu projede pgvector'ü seçtiren ne (zaten Postgres var, tek servis, taşınabilirlik)? Hangi ölçekte ayrı vektör DB'ye geçerdim?

### H. Öğrenme notlarımı hangi formatta çıkarmalıyım?
Standart tablo + bu döngüye özel: **kalite deney günlüğü** — aynı 5 test sorusunu farklı chunk-boyutu/k değerlerinde dene, cevap kalitesini ve token maliyetini tablola. (D6'daki "ölçmeden iyileştirme yok" refleksinin RAG hali — bu tablo aynı zamanda Medium Part 9'unun iskeleti.)

### I. Kodda benim kendim uygulamam gereken iyileştirme görevleri
1. pgvector'ü kur (compose imajını `pgvector/pgvector` ile değiştir — D8 kası); `documents` ve `chunks(embedding vector, file, page, user_id)` tabloları + migration.
2. `/documents/upload` ucu (auth'lu — D9; dosya boyutu/tipi validasyonlu — D3 refleksi): PDF → metin → chunk → embed → DB. Bloklamayan tasarım (G6 kararınla).
3. Retrieval fonksiyonu: soru → embed → top-k chunk (kullanıcının dokümanlarıyla sınırlı!) → eşik altıysa "bulunamadı" yolu.
4. RAG prompt kurulumu: bağlam + sınır talimatları; cevapta kaynak listesi; `assistant_done` envelope'una `sources` alanı.
5. Token bütçesi: history penceresi (D4) + retrieval bağlamı + cevap payı tek bütçede; loglara "bu cevabın bağlam maliyeti" satırı (D2 kası).
6. Kalite deneyini koş ve günlüğü doldur; seçtiğin chunk/k değerlerini config'e (D2) taşı.
7. Testler: ingestion birimi (örnek PDF fixture), retrieval doğruluğu (bilinen soru → beklenen chunk), yetki (başkasının dokümanı dönmüyor).
8. **(Bilinçli erteleme)** Reranking, hybrid search (BM25+vektör), summarization-pencere — ölçüm "yetmiyor" demeden ekleme.
9. **(Bilinçli erteleme)** DOCX/HTML ingestion, OCR — PDF'i sindirmeden format koleksiyonculuğu yok.

### J. Bu döngü tamamlandı mı, nasıl anlayacağım?
- Bir PDF yükleyip içeriğinden ancak o PDF'le cevaplanabilecek bir soru sorduğunda bot doğru cevabı **kaynak göstererek** veriyor; dokümanda olmayan soruda uydurmak yerine "bulamadım" diyor (ikisinin de testi var).
- Başka kullanıcının dokümanı asla retrieval'a girmiyor (testi var).
- Deney günlüğün dolu; chunk/k seçimini sayılarla savunabiliyorsun.
- "Embedding nedir, RAG halüsinasyonu neden azaltır ama bitirmez?" sorusuna iki paragraf akıcı cevabın var.

### K. Döngü sonunda bana neyle dönmelisin?
Deney günlüğün, ingestion→retrieval akış diyagramın, kod + testler, ve üç yazılı karar: chunk stratejin, eşik/"bulamadım" tasarımın, ingestion'ın koştuğu yer. Bu döngünün notları doğrudan Medium Part 9 olur — formatın hazır.

---

## Döngü 11 — Frontend: Chat Arayüzü ve Mini Admin Paneli

### A. Bu döngünün temel amacı
Backend ne kadar sağlam olursa olsun, müşteri (ve işveren) **gördüğüne** inanır. Bu döngü iki yüz üretir: (1) gerçek bir chat arayüzü — login, konuşma listesi, streaming'in canlı aktığı mesaj balonları, doküman yükleme, kaynak gösterimi; (2) mini admin paneli — kullanıcı sayısı, mesaj/token istatistikleri, son hatalar. Astro/HTML-CSS geçmişin var; buradaki sıçrama **React'in zihinsel modeli**: state → render, component, effect — ve WebSocket'in bu modele bağlanması. Hedef "frontend developer olmak" değil; **ürününü tek başına gösterebilen full-stack yeterlilik.**

### B. Hangi bilinen boşluklar bu döngüye giriyor?
- **[D4 sözleşme borcu]** Envelope protokolü backend'de tasarlandı ama gerçek tüketicisi yoktu; Jinja test sayfası `{type:"chunk"}/"done"/"error"` ayrımını kullanmıyor. Sözleşme nihayet iki taraflı çalışır.
- **[D9 mirası]** JWT akışının istemci tarafı: token'ı alma, saklama (ve saklama yerinin trade-off'u), WebSocket URL'ine ekleme.
- **[Konumlanma raporu]** "React/Next.js temel dashboard — müşteri demo görmek ister."

### C. Bu döngü neden bu sırada ele alınmalı?
Gösterilecek her şey artık var: kimlik (9), kalıcı geçmiş (7), doküman asistanı (10), yapılandırılmış mesajlar (4). Daha erken yapılsaydı her backend değişikliğinde arayüz kırılacaktı; şimdi sözleşme oturmuş durumda. D12'den hemen önce olması da kasıtlı: pazara çıkarken elinde tıklanabilir, kaydedilebilir, link verilebilir bir demo olacak.

### D. Döngü sonunda projede beklenen kalite artışı
- **Demo gücü:** Login → sohbet → PDF yükle → kaynaklı cevap akışı, 60 saniyelik bir ekran kaydına sığıyor.
- **Sözleşme kanıtı:** Envelope'un her tipi arayüzde ayrı davranış üretiyor (chunk birikiyor, done imleci kapatıyor, error zarif görünüyor, rate-limit uyarısı çıkıyor).
- **Full-stack iddiası:** CV'deki "FastAPI + React" satırının arkasında çalışan bir sistem var.

### E. Öğrenmem gereken teknik kavramlar
**React çekirdeği**
- Component, props, `useState`, `useEffect` (bağımlılık dizisi ve cleanup — WebSocket'i kapatmak için kritik), listeler ve `key`.
- "State değişir → arayüz yeniden çizilir" zihinsel modeli — DOM'u elle değiştirme alışkanlığından kopuş.

**WebSocket istemcisi**
- `new WebSocket(url)` (D3'te MDN'den okuduğun constructor — şimdi kullanıcısısın), `onmessage`'da `JSON.parse` + type'a göre dallanma, reconnect mantığının temeli.
- Streaming UX: chunk'ları son mesaja ekleme; otomatik kaydırma.

**İstemci auth**
- Login formu → JWT alma → saklama: localStorage vs memory trade-off'u (XSS yüzeyi) → WS URL'ine query ile ekleme (D9 kararınla tutarlı).

**Araç**
- Vite + React (Next.js'i erteleyebilirsin — SSR'a ihtiyacın yok; gerekçesini bilerek ertele), fetch ile REST çağrıları, temel CSS düzeni (Tailwind istersen — zorunlu değil).

### F. Okumam gereken resmi dokümantasyonlar
- **react.dev** → "Quick Start", "Thinking in React", "Synchronizing with Effects" (cleanup bölümü şart)
- **MDN** → "WebSocket API" istemci sayfası + `MessageEvent` (D4 okuma listendeki yarım kalan madde)
- **Vite docs** → "Getting Started" (kısa)
- **MDN** → "Using Fetch" (login/upload çağrıları için)

### G. Dokümantasyon okurken cevaplamam gereken odak soruları
1. `useEffect` cleanup fonksiyonu ne zaman çalışır; WebSocket'i orada kapatmazsam ne sızar (StrictMode'un çift-çalıştırması neyi açığa çıkarır)?
2. Chunk'lar saniyede onlarca gelirken her chunk'ta `setState` çağırmak render maliyeti yaratır mı? Naif yol ne zaman yeter, ne zaman buffer gerekir? (Ölç — varsayma.)
3. JWT'yi localStorage'da tutmanın XSS riski ne; memory'de tutmanın UX bedeli (yenilemede logout) ne? Bu demo için hangisi ve neden?
4. `onclose` event'inde close code (1008!) frontend'e ulaşır mı? "Token geçersiz" ile "sunucu hatası"nı kullanıcıya farklı göstermek için D1'deki kod tablon nasıl kullanılır?
5. **(Projeme özel)** Envelope'daki her `type` için arayüz davranış tablosu: chunk/done/error/system → ne görünür? (Bu tablo D4 notlarındaki "mesaj türleri tablosu"nun ikiz kardeşi — ikisi uyuşmak zorunda.)
6. **(Projeme özel)** Reconnect olunca `conversation_id` ile geçmişi REST'ten mi çekmeli, WS açılışında sunucu mu göndermeli? Sözleşmeye hangisi yazılacak?
7. **(Karşılaştırma)** Vite+React vs Next.js — bu projede SSR'sız SPA'nın yeterli olduğunu nasıl gerekçelendiriyorum? Hangi üründe Next'e geçerdim?

### H. Öğrenme notlarımı hangi formatta çıkarmalıyım?
Standart tablo + bu döngüye özel: **davranış tablosu** (envelope tipi → UI davranışı → test edildi mi) ve her ekranın bir cümlelik amacı. Ekran görüntüleri not dosyasına girsin — D12 portföyünün hammaddesi.

### I. Kodda benim kendim uygulamam gereken iyileştirme görevleri
1. Vite + React projesi kur (`frontend/` klasörü — monorepo basitliği yeter); compose'a (D8) servis olarak ekleme kararını bilinçli ver (dev'de ayrı `npm run dev` yeterli olabilir).
2. Login/register ekranı → JWT al, sakla (G3 kararınla), korumalı düzene geç.
3. Chat ekranı: konuşma listesi (REST: `GET /conversations` — D7), mesaj geçmişi, WebSocket bağlantısı, envelope-dallanmalı `onmessage`, streaming balonu + done işareti, error/system zarif gösterimi.
4. Doküman paneli: PDF upload (progress'li), kaynaklı cevapta `sources`'ı tıklanabilir rozet olarak göster (D10 sözleşmesi).
5. Admin sayfası (role=admin — D9): `/admin/stats`'tan kullanıcı/mesaj/token sayıları + son N hata logu basit tablolarda.
6. CORS'u backend'de bilinçli yapılandır (`allowed_origins` — D2 validator'ının yeni müşterisi).
7. Backend'deki Jinja test sayfasını emekliye ayır.
8. **(Bilinçli erteleme)** Tasarım sistemi, dark mode, mobil mükemmelliği — demo temiz olsun, şık olması D12'de bir günlük iş.
9. **(Bilinçli erteleme)** Next.js/SSR, state kütüphaneleri (Redux vb.) — ihtiyaç kanıtı yok.

### J. Bu döngü tamamlandı mı, nasıl anlayacağım?
- Tarayıcıdan uçtan uca akış: kayıt → login → sohbet (canlı streaming) → yenile → geçmiş duruyor → PDF yükle → kaynaklı cevap → admin'de sayılar.
- Envelope davranış tablosunun her satırı elle test edilmiş; "error" ve "rate-limited" arayüzde çirkin patlamıyor.
- `useEffect` cleanup'ı doğru: sekme/route değişiminde bağlantı sızmıyor.
- 60 saniyelik demo videosu çekilmiş (bu, D12'nin ilk teslimatı).

### K. Döngü sonunda bana neyle dönmelisin?
Davranış tablon, ekran görüntüleri + demo videosu, frontend kodu, ve iki yazılı karar: token saklama yerin + reconnect/geçmiş yükleme sözleşmen.

---

## Döngü 12 — Pazara Çıkış: Portföy, Konumlanma ve İlk Üç İş

### A. Bu döngünün temel amacı
Bu döngüde kod yazmak ikincil; **paketlemek ve satmak** birincil. Üç teslimat var: (1) **Portföy** — chatbot'un üç müşteri-diliyle paketlenmiş hali (doküman asistanı, web widget'ı, Telegram botu), her biri canlı + videolu + İngilizce README'li; (2) **Konumlanma** — "AI Backend Developer" kimliğiyle profil seti (GitHub, LinkedIn, Upwork, Bionluk, Medium bio); (3) **İlk üç iş** — düşük fiyatlı, dar kapsamlı, hızlı teslimli işlerle yorum biriktirme. Zihniyet değişimi net olmalı: müşteri "FastAPI bilen birini" aramaz, **"şu acımı çözecek birini"** arar — bütün metinler problem diliyle yazılır.

### B. Hangi bilinen boşluklar bu döngüye giriyor?
- **[Konumlanma raporu]** "Customer discovery + satış + pricing — teknikten sonra en büyük fark." Hiç dokunulmadı; bu döngünün ana öğrenmesi.
- **[Service-to-product stratejisi]** "Önce küçük hizmet → tekrar eden problemi gör → ürünleştir" — bu döngü zincirin ilk halkasını kurar.
- **[Pratik boşluk]** Teklif yazma, kapsam belgesi ("şunlar dahil, şunlar değil" — scope creep'i kendi haritandan tanıyorsun; müşteride aynı canavar), basit fiyatlama, haftalık ilerleme iletişimi.

### C. Bu döngü neden bu sırada ele alınmalı?
Çünkü artık satacak şey var ve daha fazla teknik döngü, getirisi azalan yatırım: pazardan gelecek ilk gerçek talep, hangi teknik konunun *gerçekten* sırada olduğunu (ödeme mi? WhatsApp mı? multi-tenancy mi?) senin yerine söyleyecek. Üçüncü haritayı pazar yazar. Ayrıca takvimle de uyumlu: MSc başvuru dosyana "yayınlanmış teknik seri + production proje + gerçek müşteri işi" üçlüsü girer.

### D. Döngü sonunda beklenen kalite artışı (bu kez projede değil, sende)
- **Görünürlük:** Aranabilir, linklenebilir, 60 saniyede anlaşılan bir portföy.
- **Dil:** Projeyi 30 saniyede (asansör), 2 dakikada (teklif) ve 15 dakikada (mülakat) anlatabilme — İngilizce.
- **Kanıt:** İlk 3 tamamlanmış iş + yorum; "hiç müşterisi olmamış" eşiği aşılmış.
- **Veri:** Hangi taleplerin tekrar ettiğine dair ilk gerçek gözlemler — üçüncü haritanın tohumu.

### E. Öğrenmem gereken kavramlar
**Paketleme**
- Aynı teknolojinin üç müşteri paketi: "Doküman asistanı" (PDF'lerinizle konuşun), "Site chatbot'u" (tek `<script>` ile gömülen widget), "Telegram botu" (webhook = bildiğin FastAPI POST ucu — yarım günlük iş, kanal değeri büyük).
- Demo hijyeni: seed veri, sıfırlanabilir demo hesabı, kötü girdilere zarif davranış (D3-D4 zaten hazırladı).

**Konumlanma ve profil**
- Niş cümlesi kalıbı: *kim için + hangi acı + nasıl kanıt*. Başlangıç önerin: "Küçük işletmeler ve teknik firmalar için doküman/destek/teklif süreçlerini otomatikleştiren AI asistanlar kurarım — canlı demo: [link]".
- Upwork profil anatomisi; Bionluk farkı (TR pazarı, ilk yorum daha kolay); LinkedIn başlık + öne çıkanlar; GitHub profil README.

**Satış temeli**
- Teklif yazımı: şablon değil, müşterinin ilanındaki probleme 2 cümlelik mini-çözüm + ilgili demo linki + tek soru.
- Kapsam belgesi: dahil/dahil-değil listesi, revizyon sayısı, teslim tanımı. Fiyatlama: ilk işlerde hedef kâr değil **yorum**; saatlik vs sabit fiyat trade-off'u.
- Müşteri iletişim ritmi: haftalık kısa ilerleme mesajı — freelancer'ı batıran kod değil, sessizliktir.

### F. Okumam/incelemem gerekenler
- **swyx — "Learn in Public"** (swyx.io) — yaptığın şeyin çerçevesi; Medium serinle bağla
- **Upwork resmi "how to get started / proposal tips" rehberleri** — pazarın kendi kuralları kendi ağzından
- **Eugene Yan — applied-llms.org** ("What We've Learned From a Year of Building with LLMs") — müşteri dilinde LLM değer anlatımı için
- **Miguel Grinberg'in Mega-Tutorial yapısı** — Part 8+ serini planlarken bölümleme şablonu
- 10-15 gerçek Upwork/Bionluk ilanı oku (başvurmadan): hangi kelimelerle yazıyorlar, neye para veriyorlar — bu senin "dokümantasyon okuman"

### G. Cevaplamam gereken odak soruları
1. Niş cümlem kim için fazla geniş, kim için fazla dar? Üç farklı versiyon yazıp hangisinin somut bir müşteri yüzü çağrıştırdığına bak.
2. İlk üç işte fiyat tabanım ne? "Ucuz ama sınırlı kapsam" ile "ucuz ve sınırsız sömürü" arasındaki çizgiyi kapsam belgesi nasıl çiziyor?
3. Bir ilana teklif yazarken ilk iki cümlem neden benden değil müşterinin probleminden bahsetmeli?
4. Demo videom 60 saniyede neyi göstermeli, neyi göstermemeli? (İpucu: kod değil, sonuç.)
5. **(Bana özel)** CoLearn ağım (Şeyma, Orhan) ve abinin mühendislik çevresi — ilk işin referansla gelme ihtimali soğuk başvurudan yüksek; bu kanala nasıl profesyonelce ("iş arıyorum" değil "şunu kurdum, tanıdığınız birine lazım olursa") girerim?
6. **(Bana özel)** Medium serim + GitHub'ım profilde nasıl konuşur: "yazı yazıyorum" olarak mı, "böyle düşünüyorum, kanıtı burada" olarak mı?
7. Hangi işi **reddetmeliyim**? (Kapsamı tanımsız, "önce yap sonra konuşuruz", sıfır bütçeli "ortaklık" teklifleri — kırmızı bayrak listeni yaz.)

### H. Notlarımı hangi formatta çıkarmalıyım?
Bu döngünün not defteri bir **CRM-günlüğü**: başvurulan ilan / tarih / teklif metni / sonuç / öğrenilen. 20 başvuru sonunda bu tablo, hangi teklif dilinin işe yaradığının verisi olur. Artı: niş cümlesi versiyonları ve kırmızı bayrak listesi.

### I. Kendim uygulamam gereken görevler
1. Üç paketi hazırla: doküman asistanı (D10-11 demo'su cilalı), gömülebilir widget (chat'i tek `<script>`'le veren küçük embed), Telegram botu (webhook ucu). Her birine: canlı link + 60 sn video + İngilizce README.
2. GitHub'ı vitrine çevir: profil README, sabitlenmiş repo'lar, chatbot repo'sunda mimari diyagram + "built with" bölümü; Medium serisine çapraz link.
3. Profilleri kur: Upwork (İngilizce — IELTS hazırlığınla bileşik), Bionluk (TR), LinkedIn başlık/özet güncelle, Medium bio'ya "available for freelance projects" satırı.
4. 30 saniyelik İngilizce proje anlatımını yaz ve **sesli prova et** (mülakat + müşteri görüşmesi kası; IELTS speaking'e de hizmet eder).
5. Kapsam belgesi şablonunu ve teklif şablon-iskeletini (kişiselleştirilecek boşluklarıyla) hazırla.
6. İlk 20 teklifi gönder (Upwork+Bionluk karışık), CRM-günlüğünü tut; ağına tek, zarif bir duyuru mesajı at (G5 kararınla).
7. İlk işi alınca: kapsamı yazılı onaylat → haftalık ilerleme ritmi → teslim → **yorum iste** (istemezsen gelmez).
8. **(Bilinçli erteleme)** Şirketleşme/fatura mekaniği ilk gelir görünene kadar; ödeme entegrasyonu, abonelik, multi-tenancy → üçüncü harita, ilk tekrar eden talep geldiğinde.

### J. Bu döngü tamamlandı mı, nasıl anlayacağım?
- Üç paket canlı, videolu, İngilizce README'li; profiller yayında; 20+ teklif gönderilmiş ve CRM-günlüğü dolu.
- **En az bir iş tamamlanmış ve bir yorum alınmış** (üç, hedef; bir, eşik).
- 30 saniyelik İngilizce anlatım ezber değil, akıcı.
- Tekrar eden taleplere dair en az üç gözlem yazılmış — üçüncü haritanın ilk satırları.

### K. Döngü sonunda bana neyle dönmelisin?
Portföy linkleri, CRM-günlüğün, ilk iş(ler)in hikâyesi (ne istendi, ne teslim ettin, ne öğrendin), ve pazar gözlemlerin. Bunlarla birlikte üçüncü haritanın (service-to-product: ürünleştirme, ödeme, multi-tenancy) kapsamına **pazar verisiyle** karar vereceğiz.

---

## Bilinçli Ertelenenler (Harita II Genelinde)

| Konu | Neden ertelendi | Ne zaman vadesi gelir | Şu anki bedeli |
|---|---|---|---|
| **Ödeme / abonelik** | Satacak müşteri yokken ödeme altyapısı ölü yatırım. | İlk "bunu aylık kullanmak istiyorum" diyen müşteri. | Yok — ilk işler proje-bazlı faturalanır. |
| **Multi-tenancy** | Tek müşterili işlerde gereksiz karmaşıklık. | Aynı kurulumu ikinci müşteriye kopyalarken acı hissedilince. | Her müşteriye ayrı deploy — D8 bunu zaten ucuzlattı. |
| **Reverse proxy / nginx / VPS** | Railway + compose mevcut ihtiyacı karşılıyor. | İlk "kendi sunucuma kur" diyen müşteri. | Yok. |
| **Refresh token, OAuth login** | Demo ve ilk işler için access token yeter. | Gerçek son-kullanıcılı ilk ürün işi. | Kullanıcı 7 günde bir yeniden girer. |
| **Reranking / hybrid search** | Ölçüm "retrieval yetmiyor" demeden optimizasyon yok. | D10 deney günlüğü kalite tavanını gösterince. | Bazı sorularda ikinci-en-iyi chunk gelir. |
| **Next.js / SSR** | SPA demo ihtiyacını karşılıyor; SEO gereksinimi yok. | Pazarlama sayfalı gerçek ürün. | Yok. |
| **Kubernetes, mikroservis, mesaj kuyruğu** | Bu ölçekte mimari kostümü. | Bu haritada gelmez; belki üçüncüde de gelmez. | Yok — ve bu iyi bir şey. |

---

## İlk Çalışma Oturumunun Net Görevi (Döngü 7)

**Ön koşul:** Döngü 4'ün kalanı (envelope + windowing), 5 ve 6 tamamlanmış olmalı. Değilse oraya dön — bu harita beklemeyi bilir.

**İlk oturumda okunacak 4 başlık:**
1. **SQLAlchemy 2.0 →** "Asyncio Support" sayfasının tamamı.
2. **Alembic →** "Tutorial" + "Auto Generating Migrations" (sınırlamalar kutusu dahil).
3. **FastAPI →** "SQL (Relational) Databases" sayfası.
4. **PostgreSQL →** "Data Types" içinden uuid / timestamptz / jsonb bölümleri.

**İlk oturumda çıkarılacak notlar:** async session ömrü seçenekleri; autogenerate'in görmedikleri; satır-vs-JSONB karşılaştırması; `connection_id` ≠ `conversation_id` ayrımının log düzenine etkisi.

**İlk oturum sonunda üretilmesi gereken:** Şema taslağı (Mermaid) + üç yazılı ön-karar (blob mu satır mı; session ömrü; reconnect'te pencere mi tam geçmiş mi). **Henüz kod yok** — ilk oturum anlama, ikinci oturum değiştirme oturumudur.

**Dokunulmayacaklar:** Docker (D8), auth (D9), RAG (D10). Scope creep'in panzehiri hâlâ aynı: tek soru, net cevap.

---

## Bu Sürecin Sonunda Elde Edeceğin Yetkinlikler

**Backend derinliği** — Async ORM ile veri katmanı kurmak; migration disiplini; repository deseniyle iş mantığını SQL'den ayırmak; "kayıt vs bağlam" ayrımını LLM uygulamasına uygulamak.

**Teslim edilebilirlik** — Bir sistemi imaj+compose+CI üçlüsüyle her ortamda aynı şekilde ayağa kaldırmak; secret'ları üç ortamda (lokal/compose/cloud) tek Settings'ten yönetmek; "neden tek worker" gibi kararları gerekçeleriyle savunmak.

**Kimlik ve güvenlik** — JWT tabanlı auth'u HTTP ve WebSocket'te kurmak; parola hijyeni; rol tabanlı yetki; tehdit tablosuyla düşünmek; IDOR gibi sınıf hataları teste bağlamak.

**Applied AI mühendisliği** — RAG hattını uçtan uca kurmak (ingestion → retrieval → kaynaklı cevap); chunk/k/eşik kararlarını deneyle vermek; token bütçesini history+retrieval+cevap üçgeninde yönetmek; "bilmiyorum" diyebilen sistem tasarlamak.

**Full-stack yeterlilik** — React'le streaming chat arayüzü ve admin paneli kurmak; WebSocket istemci yaşam döngüsünü (effect cleanup, reconnect, close code'lar) yönetmek; backend sözleşmesini (envelope) iki taraflı yaşatmak.

**Pazar kasları** — Teknolojiyi müşteri problemine çevirip paketlemek; niş cümlesi kurmak; teklif/kapsam/fiyat üçgenini yönetmek; yorum biriktirme stratejisi; tekrar eden talebi ürün sinyali olarak okumak.

---

## Son Söz

İlk harita seni "çalışan koddan doğru koda" taşıdı. Bu harita "doğru koddan satılabilir yeteneğe" taşıyor. Üçüncü harita — ürünleştirme — şimdi yazılmıyor, çünkü onu ben değil, Döngü 12'de toplayacağın pazar verisi yazacak.

Kural değişmedi: her döngüde sen okuyacaksın, sen düşüneceksin, sen kodlayacaksın. Ben K bölümü çıktılarınla geldiğinde reviewer moduna geçeceğim. Ve bir bonus disiplin: 7'den 11'e her döngünün not defteri, Medium serinin bir sonraki İngilizce part'ının iskeletidir — Part 8 (persistence), Part 9 (RAG) en güçlü adaylar. Learn in public; zaten yapıyorsun.

İlk hareket: Döngü 4'ün kalanını bitir. Sonra Bölüm "İlk Çalışma Oturumu"ndaki dört okumayla dön.

Hazır olduğunda haber ver.

---

## EK NOT — Prompt Güvenliği & Çıktı Disiplini (Döngü 9'a iliştirilir)

*Kaynak: DeepLearning.AI "ChatGPT Prompt Engineering for Developers" dersi (13 Haz 2026 izlendi).*

Bu maddeler **şimdi değil**, güvenlik döngüsünde (D9) açılır — orada auth/RBAC ile birlikte "guardrail" başlığı altında doğal yeri var. Erken yapılırsa scope creep olur.

- **Prompt injection savunması:** Kullanıcı mesajı `system_instruction`'ı eziyor mu? ("önceki talimatları unut..."). Savunma: kullanıcı içeriğini delimiter/yapı içine almak, system_instruction'ı ayrı tutmak. D3'teki input validation'ın LLM'e özgü devamı — checklist'in 14. maddesi (guardrail ihlalleri) buraya bağlanır.
  - Okuma: Simon Willison prompt injection serisi (https://simonwillison.net/series/prompt-injection/)
- **"Bilmiyorum" diyebilme + kaynak-temelli cevap:** Halüsinasyon azaltma — model cevabı önce kaynağa dayandırsın, bulamazsa uydurmasın. Bu D10'da (RAG) zaten ana konu; D10 deney günlüğüne taşınır.
- **Çıktı yapısı disiplini:** Structured output (JSON) = parse edilebilirlik. Bu prensip D4 envelope işinde zaten uygulanıyor; prompt çıktısı tarafında da geçerli (ileride tool/function calling'de kritik olacak — D10.5).
