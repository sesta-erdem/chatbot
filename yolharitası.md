# FastAPI + WebSocket + Gemini Chatbot — Öğrenme ve Geliştirme Yol Haritası

Bu yol haritası, paylaştığın review raporundaki tüm bulguları kapsar. Sen okuyacaksın, sen kodlayacaksın; ben sadece rotayı çizip her döngü sonunda reviewer modunda dönüp değerlendireceğim.

Yol haritasını **6 döngüye** böldüm. Sebep: 5 döngü bazı konuları yapay biçimde birleştirip "WebSocket lifecycle"ı "config"le aynı blokta toplamaya zorluyordu; 7 döngü ise "logging" gibi tek başına döngü olamayacak konuları gereksiz biçimde şişiriyordu. 6 döngü, her bloğun kendi içinde tek bir kavramsal eksen etrafında dönmesini sağlıyor.

---

## Döngülerin genel haritası (önce büyük resim)

| # | Döngü | Tek cümleyle |
|---|---|---|
| 1 | WebSocket lifecycle ve hata yönetimi temelleri | Bağlantının doğumu, ölümü ve patlamasını doğru anla. |
| 2 | Konfigürasyon, secret yönetimi ve structured logging | Görmediğin hatayı çözemezsin; okuyamadığın config'le ürün açamazsın. |
| 3 | Güvenlik ve maliyet kontrolü: auth, rate limit, generation config | Üç bulgu birlikte olunca "ücretsiz Gemini proxy" sorunu kapanır. |
| 4 | Mesaj protokolü ve LLM context/maliyet yönetimi | Frontend "bitti mi?" desin, backend kümülatif token şişmesini durdursun. |
| 5 | Kod organizasyonu, LLM soyutlama, lifespan | Tek dosya spagettisini katmanlara ayır, kaynakları lifecycle'a bağla. |
| 6 | Test, gözlemlenebilirlik ve production-readiness | Refactor güveni, metrics, graceful shutdown, health endpoint. |

Şimdi her döngüyü tam detayda.

---

## Döngü 1 — WebSocket Lifecycle ve Hata Yönetimi Temelleri

### A. Bu döngünün temel amacı
WebSocket bağlantısının üç ana fazını (kabul → mesaj döngüsü → kapanış) ve aralarındaki normal/anormal geçişleri doğru ayırt edebilmek. Şu an `WebSocketDisconnect` normal bir olay olduğu halde generic exception olarak işleniyor; bunun sonucunda kapalı sokete `send_text` denenip ikinci bir exception fırlatılıyor. Bu döngü, WebSocket lifecycle'ını "anlamış" olmanın somut göstergesi olan dört davranışı yerleştirir: disconnect'i sessizce karşılama, beklenmedik hatayı kullanıcıya sızdırmadan loglama, hata sonrası close code ile graceful kapanış, ve `finally` bloğunda kaynak temizliği.

### B. Review raporundaki hangi bulgular bu döngüye giriyor?

- **[HIGH — Bölüm 6.2, 8.1, Risk Tablosu]** `WebSocketDisconnect` yakalanmıyor; generic `except Exception` bloğuna düşüyor.
- **[HIGH — Bölüm 5.6, 8.2, 8.5, Risk Tablosu]** Ham exception mesajı kullanıcıya sızdırılıyor (`send_text(f"Hatamız: {e}")`).
- **[MEDIUM — Bölüm 6.7, Risk Tablosu]** Graceful close ve close code yok.
- **[MEDIUM — Bölüm 7.4, Risk Tablosu]** `chunk.text` `None` olabilir → `send_text` `TypeError` riski.
- **[MEDIUM — Bölüm 6.3]** İstemci stream sırasında ayrılırsa async generator temizliği belirsiz.
- **[LOW — Bölüm 6.1]** `accept` başarısızlığı gözlemlenebilir değil — bu döngüde dolaylı olarak çözülür (logging temeli atılınca).
- **[LOW — Bölüm 9.3]** `e`, `e1` isimlendirmesi — bu döngüde refactor sırasında düzeltilir.

### C. Bu döngü neden bu sırada ele alınmalı?
Çünkü sonraki her döngünün altyapısı budur. Auth ekleyeceksin → auth fail durumunda hangi close code'la kapatırsın? Rate limit ekleyeceksin → limit aşılınca disconnect mi, error envelope mı? LLM timeout ekleyeceksin → timeout sonrası bağlantıya ne olur? Bu soruların hepsi WebSocket lifecycle'ını doğru anlamadan cevaplanamaz. Ayrıca lifecycle, raporun tabiriyle "bu projenin tam göbeği" — projenin asıl protokolü WebSocket olduğu için önce orayı sağlamlaştırmak öğrenme açısından motivasyon yüksek tutar.

Neden ilk sırada **güvenlik** değil? Çünkü auth eklediğin anda auth fail senaryolarını close code ile kapatman gerekecek — yani lifecycle bilgisi auth'un ön koşulu. Neden ilk sırada **config** değil? Config'i bu döngüde de kullanacaksın ama çok dar kapsamla (sadece API key fail-fast); structured config katmanını Döngü 2'de oturtmak daha mantıklı.

### D. Döngü sonunda projede beklenen kalite artışı
- **Hata dayanıklılığı:** Normal disconnect log'u kirletmiyor; beklenmedik exception zincirleme patlamıyor.
- **WebSocket yaşam döngüsü doğruluğu:** Üç faz net ayrılmış; her fazın kendi exception handler'ı var.
- **Güvenlik (kısmi):** Internal hata detayı kullanıcıya gitmiyor — bilgi sızıntısı kapanıyor.
- **Gözlemlenebilirlik (tohum):** En azından "neden kapandı" sorusu cevaplanabilir hale geliyor (yine de tam structured logging Döngü 2'de).
- **Kod organizasyonu (mikro):** Try/except katmanları anlamlı isimlerle ve gerçek exception türleriyle yapılandırılmış.

### E. Öğrenmem gereken teknik kavramlar

**Starlette / WebSocket**
- `WebSocketDisconnect` exception'ı: ne zaman fırlar, ne ifade eder. — Senin kodunda yanlış kategoriye düştüğü için.
- WebSocket close codes (1000, 1001, 1008, 1011, 4000-4999 aralığı): hangi sayı ne anlama gelir. — Frontend'in "neden kapandı" sorusuna cevap verebilmesi için.
- `WebSocket.close(code, reason)` API'sı: ne zaman çağrılır, ne zaman çağrılmamalı. — Hatadan sonra graceful kapanış için.

**FastAPI**
- WebSocket endpoint'inde exception handling patterns. — Resmi dokümantasyondaki "Handling disconnections" örneğini doğrudan görmek için.

**Python async / asyncio**
- `try / except / finally` async fonksiyonlarda davranışı. — `finally`'nin async context'te de garantili çalıştığını içselleştirmek için.
- `asyncio.CancelledError`: neden yakalanırsa re-raise edilmeli. — İleride timeout/cancel kullandığında lifecycle'ı bozmamak için.
- Exception chaining (`raise X from Y`). — Hata kaynağını saklamadan üst katmana taşımak için.

**RFC 6455 (sadece ilgili bölümler)**
- Close handshake mantığı. — Close code'un ne işe yaradığını protokol seviyesinden anlamak için.

### F. Okumam gereken resmi dokümantasyonlar

- **FastAPI dokümantasyonu (fastapi.tiangolo.com)**
  - "WebSockets" → tüm sayfa
  - "Handling disconnections and multiple clients" (WebSockets sayfası içindeki alt bölüm)
  - "WebSockets" sayfasındaki `WebSocketDisconnect` örnekleri

- **Starlette dokümantasyonu**
  - "WebSockets" → `WebSocket` sınıfının tüm metotları, özellikle `close()`, `receive_text()`, `send_text()`
  - `WebSocketDisconnect` exception sınıfının dokümantasyonu

- **Python `asyncio` dokümantasyonu**
  - "Coroutines and Tasks" → "Task Cancellation" alt başlığı
  - "Developing with asyncio" → "Handling Cancellation" bölümü

- **Python dil dokümantasyonu**
  - "Errors and Exceptions" → "Defining Clean-up Actions" (`try/finally`)
  - "Exception chaining" (`raise ... from ...`)

- **MDN — WebSocket API**
  - "CloseEvent" sayfası → `code` özelliği ve standart close kodları tablosu

- **RFC 6455**
  - Section 7.4 ("Status Codes") — sadece bu bölüm yeterli; tüm RFC'yi okumana gerek yok

### G. Dokümantasyon okurken cevaplamam gereken odak soruları

1. `WebSocketDisconnect` ne zaman fırlar? Sadece istemci tarafından kapanışta mı, yoksa sunucu da bu exception'ı tetikleyebilir mi?
2. `WebSocketDisconnect` fırlatıldıktan sonra aynı `websocket` nesnesi üzerinde `send_text` veya `close` çağırmak ne sonuç doğurur?
3. WebSocket close code 1000, 1011 ve 1008 arasındaki anlam farkı nedir? Bu projede hangi senaryoda hangisini kullanmalıyım?
4. 4000-4999 aralığındaki "application-specific" close kodları hangi durumlarda iş görür? Projemde bir tanesini hangi davranışa atamayı düşünebilirim?
5. `finally` bloğu içinde `await` çağırmak güvenli midir? `CancelledError` durumunda davranışı nasıl değişir?
6. Generic `except Exception` yakalaması neden bir antipattern olarak görülür? Hangi senaryolarda yine de meşrudur?
7. `raise X from Y` ile `raise X` arasındaki fark nedir? Loglara nasıl yansır?
8. **(Projeme özel)** Şu an `except Exception as e` bloğunun içinde `await websocket.send_text(f"Hatamız: {e}")` çağrısı var. Eğer bu exception zaten `WebSocketDisconnect` ise bu satır ne fırlatır? Bu fırlatılan exception'ı dış `except Exception as e1` yakaladığında loglarda ne görünür?
9. **(Projeme özel)** `chunk.text` `None` döndüğünde `send_text(None)` ne yapar? Bu hatayı önlemenin iki farklı yolu nedir; bu projede hangisi daha okunabilir?
10. Beklenmedik bir exception olduğunda kullanıcıya hangi bilgiyi göstermek meşrudur, hangisi bilgi sızıntısıdır? "Sunucu hatası" demek yeterli mi, yoksa kullanıcının yapacağı bir aksiyon var mı?
11. **(Karşılaştırma)** Hata olduğunda WebSocket'i `close(code=1011)` ile kapatmak mı, yoksa bir error envelope gönderip bağlantıyı açık tutmak mı bu projede daha uygundur? Hangi senaryoda hangisi seçilir?
12. Async generator'ı `async for` döngüsünden erken çıkışla terk ettiğinde `aclose` ne yapar? Bu projede `chat.send_message_stream` iteratoru ortada bırakılırsa Gemini SDK tarafında ne temizlenir, ne temizlenmez?

### H. Öğrenme notlarımı hangi formatta çıkarmalıyım?

| Alan | İçerik |
|---|---|
| Kavram | Örn: `WebSocketDisconnect` |
| Kendi cümlemle açıklama | Tek paragrafta, dokümana bakmadan |
| Bu projedeki karşılığı | Hangi satır(lar)ı etkiliyor |
| Tetikleyici senaryo | Hangi kullanıcı davranışı bu kavramı tetikler |
| Yanlış handle edilirse ne olur | Concrete bir failure mode |
| Doğru handle nasıl görünür (pseudocode değil, davranış cümleleriyle) | Örn: "Bu fazda silently log, send_text deneme, finally bloğunda close" |
| Açık kalan sorum | Cevaplayamadığım nokta |

### I. Kodda benim kendim uygulamam gereken iyileştirme görevleri

Aşağıdaki sıra bilinçli: önce hatanın yanlış sınıflandırılması (en kafa karıştırıcısı), sonra sızıntı, sonra graceful close, sonra defensive programming.

1. **`WebSocketDisconnect`'i ayrı bir exception olarak yakala.** Yakalandığında `send_text` denenmesin, sadece kısa bir info log düşsün. Bu görev şu bulguyu kapatır: *[HIGH] WebSocketDisconnect yakalanmıyor.*

2. **Beklenmedik exception bloğunda kullanıcıya ham exception detayı GÖNDERME.** Kullanıcıya kısa, jenerik bir mesaj git; gerçek exception sunucu tarafına (şimdilik `print`, Döngü 2'de logger) gitsin. Görev: *[HIGH] Ham exception kullanıcıya gönderiliyor.*

3. **Beklenmedik exception sonrasında `await websocket.close(code=1011)` çağrısı ekle** — ve bu çağrının `WebSocketDisconnect` durumunda yapılmaması gerektiğini ayrı kontrolle sağla. Görev: *[MEDIUM] Graceful close ve close code yok.*

4. **`finally` bloğu ekle:** Bağlantı nasıl biterse bitsin (normal disconnect, hata, sunucu kapanışı) çalışan tek bir kapanış noktası olsun. Şu an cleanup bir yere yazılı değil; ileride buraya "chat history persist" gibi işler bağlanacak. Görev: *[HIGH/MEDIUM hybrid] Lifecycle cleanup yok.*

5. **Stream döngüsünde `chunk.text` `None` veya boş string olabileceğini varsay.** None ise gönderme, boşsa gönderip göndermeme kararını ver. Görev: *[MEDIUM] chunk.text None olabilir.*

6. **`e`, `e1` değişken adlarını ve `read_item`, `item.html` isimlerini bu döngüde değil — Döngü 5'te dosya bölünmesi sırasında düzelt.** Burada sadece bu isimleri *not et*; refactor scope creep'i önlemek için. (Bilinçli erteleme.)

7. **Manuel deney görevi:** Sadece anlayış için, projenin bir kopyasında dış `except Exception` bloğunu geçici olarak kaldır ve istemciyi disconnect ettirip stack trace'i oku. Sonra geri ekle. Bu kod commit'i değil, sadece sezgi egzersizi.

### J. Bu döngü tamamlandı mı, nasıl anlayacağım?

**Tamamlanma kriterleri:**
- [ ] `WebSocketDisconnect` için ayrı `except` bloğu var.
- [ ] Bu blok kullanıcıya `send_text` denemiyor.
- [ ] Bu blok info seviyesinde "bağlantı kapandı" log düşürüyor.
- [ ] Beklenmedik exception bloğu kullanıcıya generic mesaj gönderiyor, exception detayını sızdırmıyor.
- [ ] Beklenmedik exception sonrası bağlantı 1011 (veya seçtiğin başka uygun kod) ile kapatılıyor.
- [ ] Stream döngüsünde `chunk.text` None kontrolü var.
- [ ] `finally` bloğu var ve içinde en az bir log satırı / cleanup yer tutucu var.

**Manuel test senaryoları:**

1. **Normal disconnect:** Tarayıcıyı kapat veya WS sekmesini kapat. Sunucu loglarında yalnızca "bağlantı kapandı" tarzı bir info satırı görmelisin; stack trace OLMAMALI.
2. **Mesaj sırasında disconnect:** `chat.send_message_stream` chunk üretirken tarayıcıyı kapat. Loglarda generic exception veya stack trace OLMAMALI; "stream sırasında istemci ayrıldı" gibi temiz bir satır olmalı (ya da en azından temiz bir disconnect).
3. **Sentetik exception:** Kodda geçici olarak `raise RuntimeError("test")` yerleştir, mesaj gönder. Tarayıcıdaki kullanıcı SADECE generic bir mesaj görmeli; "RuntimeError: test" görmemeli. Sunucu loglarında ise tam traceback olmalı. Test sonrası raise'i kaldır.
4. **`chunk.text` None senaryosu:** Bu doğal olarak tetiklenmesi zor; ya safety filter tetiklenecek bir prompt dene, ya da kodda geçici olarak `chunk.text = None` benzeri bir mock kur. Hatasız geçmeli.

**Beklenen gözlemler:**
- Disconnect log'u: tek satır, info seviyesi, panic yok.
- Hata log'u: tek tam traceback, kullanıcı tarafında ise nötr metin.
- Frontend (eğer kullanıyorsan): close code'u bir şekilde görebiliyor olmalısın (browser dev tools → Network → WS → Close frame).

**Olmaması gereken durumlar (regression):**
- Normal disconnect'te traceback.
- "Hatamız: WebSocketDisconnect(...)" gibi içerik kullanıcıya akması.
- Stream başarıyla tamamlanan happy path'in çalışmayı bırakması.
- Hata sonrası bağlantının asılı kalması (kapatılmıyor).

### K. Döngü sonunda bana neyle dönmelisin?

1. Tablo formatında öğrenme notların — en az şu kavramlar için: `WebSocketDisconnect`, close codes (en az 3'ü), `try/finally` async davranışı, ham exception sızıntısı, `chunk.text` defensive handling.
2. 1-2 paragraflık özet: "WebSocket lifecycle'ı bu hafta önce nasıl anlıyordum, şimdi nasıl anlıyorum."
3. Değiştirdiğin kod parçaları (sadece değişen satırlar; tam dosya değil).
4. Manuel test senaryolarının her birinin sonucu — gözlemlediğin log satırları dahil.
5. Şu sorulara cevabın: "Hangi close code'u seçtim, neden?", "Beklenmedik exception'da bağlantıyı kapatmayı mı, açık tutmayı mı seçtim, neden?"
6. Hâlâ emin olmadığın 1-3 nokta.
7. "Acaba bunu doğru mu yorumladım?" dediğin kararlar — özellikle close code seçimi ve `finally` içeriği.



---

## Ekleyeceğin notlar

**Döngü 4'e ekle (timeout konusunun yanına):**
```
NOT: Python asyncio → "Task Cancellation" ve "Handling Cancellation" 
okumalarını Döngü 1'de atladık, Döngü 4'te okunacak.
```

**Döngü 5'e ekle (LLM soyutlaması konusunun yanına):**
```
NOT: Python → "Exception chaining" (raise X from Y) okumасını 
Döngü 1'de atladık, Döngü 5'te okunacak.
```

**Döngü 1'e ekle (tamamlananlar notuna):**
```
NOT: RFC 6455 Section 7.4 atlandı — close code'lar MDN'den öğrenildi, 
yeterli. İleride "neden böyle tasarlanmış?" sorusu gelirse bakılacak.
```

---

Bunları ekledikten sonra Döngü 2'ye geçelim. Hazır mısın?

## Döngü 2 — Konfigürasyon, Secret Yönetimi ve Structured Logging

### A. Bu döngünün temel amacı
Üretim seviyesinde bir backend'in iki temel altyapısını yerleştirmek: (1) tüm ayarların validate edilmiş, tek kaynaktan okunan, fail-fast davranan bir config katmanından gelmesi; (2) `print` yerine seviyeli, yapılandırılmış, korelasyon ID'sine sahip bir logging sistemi. Bu altyapı olmadan sonraki tüm döngülerin (auth, rate limit, metrics) sonucu görünmez olur — Döngü 1'de eklediğin disconnect ve close logları da `print` olarak kalırsa hiçbir aggregator'da aranamaz.

### B. Review raporundaki hangi bulgular bu döngüye giriyor?

- **[HIGH — Bölüm 3.3, 8.3, Risk Tablosu]** `print` ile logging, structured logging yok.
- **[HIGH — Bölüm 5.5, Risk Tablosu]** API key fail-fast yok; `os.environ.get` `None` dönerse sessizce kabul.
- **[HIGH — Bölüm 3.2]** Pydantic Settings kullanılmamış, config dağınık.
- **[Bölüm 8.2, 8.4]** Kullanıcı log'u ile developer log'u ayrımı yok; correlation ID yok.
- **[Bölüm 3.1]** Magic string'ler (model adı, template adı hardcoded).
- **[Bölüm 5.5]** `.env`'in `.gitignore`'da olduğunun doğrulanması (varsayım).

### C. Bu döngü neden bu sırada ele alınmalı?
Çünkü Döngü 3'te güvenlik ekleyeceksin: rate limit threshold'u, token tavanı, izinli origin'ler — bunlar ya hardcoded yapılır (kötü) ya da config'den okunur (doğru). Aynı şekilde her güvenlik olayı (rate limit aşıldı, auth fail) loglanmalı; bunu doğru yapmak için önce logger altyapısı gerek. Döngü 1'de bilinçli olarak "şimdilik `print` kalabilir" dedik; o `print`leri Döngü 2'de ortadan kaldırıyoruz. Config + logging önce yapılmazsa, sonraki her döngüde "ah bunu hardcode ediyorum, ileride düzeltirim" tuzağına düşersin.

Neden Döngü 1 öncesi değil? Çünkü logging altyapısını oturtmak için önce *neyi* loglamak istediğini bilmen gerek — Döngü 1'deki disconnect ve hata olayları doğal log noktalarını ortaya çıkardı.

### D. Döngü sonunda projede beklenen kalite artışı
- **Gözlemlenebilirlik:** `print` yerine `logging`; seviyeler (DEBUG/INFO/WARNING/ERROR); her bağlantı için correlation ID; production'da log aggregator'da aranabilir alanlar.
- **Sürdürülebilirlik:** Tüm ayarlar tek noktadan okunuyor; magic string yok.
- **Güvenlik:** Yanlış / eksik konfigürasyon production'a sızamıyor (fail-fast).
- **Hata dayanıklılığı:** API key yoksa uygulama açılışta düşüyor; runtime'da sessizce yanlış davranmıyor.

### E. Öğrenmem gereken teknik kavramlar

**Pydantic / config**
- `pydantic-settings` `BaseSettings` sınıfı. — Type-safe env okuma için.
- `Field(...)` ile required vs `Field(default=...)` ile optional ayrımı. — Fail-fast'ın çalışma mekanizması.
- Validator (`@field_validator`). — Custom validation (ör. API key boş olamaz) için.

**Python `logging`**
- Logger hiyerarşisi, handler, formatter, level. — Modüler logging için temel.
- `logging.getLogger(__name__)` patterni. — Modül-bazlı logger için.
- `LoggerAdapter` veya `extra` parametresi ile correlation ID ekleme. — Her bağlantıya kimlik vermek için.
- JSON formatter (manuel veya `python-json-logger`). — Aggregator dostu çıktı için.

**FastAPI**
- Uygulama başlangıcında config validation (lifespan / startup'ta erken kontrol). — Döngü 5'in lifespan'ı için zemin.
- `Depends` ile config injection. — Endpoint'lerde global değişken yerine DI.

**Production backend**
- 12-factor "Config" prensibi. — Neden env'den okumalı, neden kodda olmamalı.
- Correlation ID kavramı. — Distributed tracing'in giriş kapısı.

**Güvenlik**
- Secret leak vektörleri: log'a basma, error response'a koyma, git'e commit etme. — Hangi tuzakların farkında olunmalı.

### F. Okumam gereken resmi dokümantasyonlar

- **Pydantic v2 dokümantasyonu (docs.pydantic.dev)**
  - "Models" → "Fields" temel sözleşmesi
  - "Validators" → `@field_validator`, `@model_validator`
  - **pydantic-settings** ayrı paketi (docs.pydantic.dev/latest/concepts/pydantic_settings/) → "Settings Management", "Environment variable names", "Dotenv (.env) support"

- **Python `logging` dokümantasyonu (docs.python.org)**
  - "Logging HOWTO" → tüm sayfa, en az iki kez
  - "Logging Cookbook" → "Using LoggerAdapter to impart contextual information", "Implementing structured logging"
  - "logging.config" → `dictConfig` referansı

- **FastAPI dokümantasyonu**
  - "Settings and Environment Variables" → tüm sayfa, özellikle Pydantic Settings entegrasyonu

- **12-factor app (12factor.net)**
  - "III. Config"
  - "XI. Logs"

### G. Dokümantasyon okurken cevaplamam gereken odak soruları

1. `pydantic-settings`'te bir alanı zorunlu yapmak için ne yapılır? Default vermezsem davranış ne olur?
2. `BaseSettings` instance'ı modül seviyesinde mi, lifespan içinde mi oluşturulmalı? Trade-off'ları nedir?
3. `.env` dosyası bulunamazsa `pydantic-settings` ne yapar? Bu projem için bu davranış doğru mu?
4. Python `logging`'de root logger'a log basmak neden tavsiye edilmez? `getLogger(__name__)` neden tercih edilir?
5. Bir exception'ı `logger.exception(...)` ile mi yoksa `logger.error(..., exc_info=True)` ile mi loglamak doğru? Aralarındaki fark?
6. JSON formatter kullanmak için stdlib içinde hazır bir formatter var mı, yoksa custom mı yazılmalı? Üçüncü parti paket kullanmak ne kazandırır?
7. Bir bağlantı boyunca aynı `connection_id`'yi her log satırına eklemenin iki yolu nedir (LoggerAdapter vs `extra`)? Bu projede hangisi pratiktir?
8. **(Projeme özel)** Şu anda `client = genai.Client(api_key=...)` modül seviyesinde. Config'i Pydantic Settings'e taşıdığımda bu client init'i nereye taşımalıyım? Modül seviyesi mi, lifespan mı, dependency mi?
9. **(Projeme özel)** Şu an `gemini-2.5-flash` model adı hardcoded. Bunu config'e taşıdığımda yanlış model adı durumunda ne olur? Fail-fast nasıl uygulanır?
10. **(Karşılaştırma)** `logging` stdlib + manual JSON formatter ile `structlog` veya `loguru` arasında bu boyuttaki proje için hangisi doğru tercih? Hangi durumda hangi tarafa kayılır?
11. Kullanıcıya gönderilen hata mesajındaki "request ID / connection ID" nasıl üretilir, ne uzunlukta olur, hangi formatla? Bu ID'nin tahmin edilemez olması gerekir mi?
12. Log seviyelerinin (DEBUG/INFO/WARNING/ERROR/CRITICAL) bu projede her biri hangi olaya karşılık gelir? Bir kullanıcı disconnect'i hangi seviye? Gemini rate limit hatası hangi seviye?

### H. Öğrenme notlarımı hangi formatta çıkarmalıyım?

| Alan | İçerik |
|---|---|
| Kavram | … |
| Kendi cümlemle açıklama | … |
| Bu projedeki karşılığı | … |
| Yanlış yaparsam ne olur | … |
| Doğru yaparsam projede hangi davranış değişir | … |
| Açık kalan sorum | … |

Ek olarak bu döngüye özel: **"Log seviyesi atama kararları"** tablosu — projedeki her belirli olay için (disconnect, hata, mesaj alındı, stream başladı, stream bitti) hangi seviyenin seçildiği ve gerekçesi.

### I. Kodda benim kendim uygulamam gereken iyileştirme görevleri

1. **Pydantic Settings ile config sınıfı oluştur.** En az şu alanlar olsun: `gemini_api_key` (zorunlu), `gemini_model` (default değerli ama override'lanabilir), `log_level` (default `INFO`). Görev: *[HIGH] Pydantic Settings kullanılmamış + API key fail-fast yok.*

2. **Uygulama açılışında config validate olduğunu doğrula.** API key olmadan uygulama açılışta patlasın. Görev: *[HIGH] Fail-fast yok.*

3. **`.gitignore`'da `.env`'in olduğunu doğrula.** Yoksa ekle. Bu yalın bir kontrol görevi. Görev: *[HIGH] Secret leak riski.*

4. **`logging` stdlib ile bir logger setup'ı yap.** Tek bir yerde (örn. `logging_config.py` veya `main.py` üstü) `dictConfig` veya benzeri ile setup. Görev: *[HIGH] Structured logging yok.*

5. **Tüm `print` çağrılarını uygun seviyedeki `logger` çağrılarına çevir.** Bu sırada Döngü 1'de eklediğin disconnect/hata loglarını da geçir. Görev: *[HIGH] print kullanılıyor.*

6. **Her WebSocket bağlantısına bir `connection_id` üret (uuid4 yeterli).** Bu ID'yi o bağlantının tüm log satırlarında göster. `LoggerAdapter` veya `extra` ile. Görev: *[Bölüm 8.4] Correlation ID yok.*

7. **Kullanıcıya hata mesajı giderken connection_id'yi içersin** ("Bir hata oluştu (ID: abc-123). Lütfen yeniden deneyin.") — sen log'una bu ID'yi yazarsın, kullanıcı destek istediğinde bu ID'yi getirir. Görev: *[Bölüm 8.2] User ↔ developer log ayrımı.*

8. **Magic string'leri çıkar:** `gemini-2.5-flash` artık config'den geliyor; template adı (`item.html`) Döngü 5'e ertelendi (dosya yapısıyla beraber).

9. **(Bilinçli erteleme)** JSON formatter'a geçmek bu döngünün şart maddesi değil; düz text formatter da yeterli — ama eğer JSON denemek istersen bir bonus görev olarak yapabilirsin. Production'a giderken yine de gerekecek.

### J. Bu döngü tamamlandı mı, nasıl anlayacağım?

**Tamamlanma kriterleri:**
- [ ] Proje köküde `Settings` benzeri bir sınıf var.
- [ ] API key olmadan uygulama açılışta düşüyor (manuel test ettin).
- [ ] `print` kalmadı (`grep "print(" .`).
- [ ] Logger seviyeli, formatter'lı bir setup'tan geliyor.
- [ ] Her bağlantının tüm log satırlarında o bağlantının ID'si görünüyor.
- [ ] `.env` `.gitignore`'da.
- [ ] Model adı hardcoded değil.

**Manuel test senaryoları:**

1. **Fail-fast testi:** `.env`'i geçici olarak yeniden adlandır veya `GEMINI_API_KEY` satırını yorum satırı yap. Uygulama açılışta net bir hata mesajıyla düşmeli; "import sırasında patlamış" karmaşası değil, "config validation hatası" gibi okunabilir bir mesaj.
2. **Correlation ID testi:** Aynı anda iki browser sekmesi aç, ikisinden de mesaj gönder. Loglarda iki farklı ID akmalı; bir bağlantının log'u diğeriyle karışmamalı.
3. **Seviye testi:** `LOG_LEVEL=DEBUG` ile çalıştır, sonra `LOG_LEVEL=WARNING` ile çalıştır. Farkı gözlemle.
4. **Kullanıcı mesajı testi:** Sentetik hata üret (Döngü 1'den hatırla); kullanıcının gördüğü mesajda connection_id olmalı, exception detay OLMAMALI.
5. **Model adı testi:** Config'de geçersiz bir model adı dene (`gemini-imkansız-model`). Davranışı not et — bu açılışta fail-fast olabilir mi, yoksa ilk istekte mi patlar? Hangisi olmalı bu projede?

**Beklenen gözlemler:**
- Loglar artık "2025-... INFO [conn_id=...] mesaj alındı" gibi yapılı.
- API key eksikliği debug edilebilir bir hata mesajıyla çıkıyor.
- İki paralel bağlantının logları birbirinden ayrılabilir.

**Olmaması gereken durumlar:**
- Hâlâ kalmış `print`.
- Log'larda exception stack trace varken kullanıcı mesajında da exception detay.
- API key boşken uygulamanın açılıp ilk WS bağlantısında patlaması (fail-fast bunu engellemiş olmalı).
- `.env` git status'te commit edilebilir görünmesi.

### K. Döngü sonunda bana neyle dönmelisin?

1. `Settings` sınıfının skeleton'ı (tam kod değil; alan isimleri ve tipleri).
2. Logger setup yaklaşımın hakkında 1-2 paragraf: hangi handler, hangi formatter, neden.
3. "Log seviyesi atama kararları" tablosu (yukarıdaki şablondan).
4. Correlation ID'yi nasıl propagate ettiğin — LoggerAdapter mı, `extra` mı, kararını anlat.
5. Manuel test senaryolarının sonuçları (özellikle fail-fast testi).
6. JSON formatter denedinse not et; denemedinse "neden şimdilik gerek görmedim" notu.
7. Açık kalan sorular — özellikle "client'i nerede oluşturuyorum" sorusunu nasıl çözdüğün, çünkü bu Döngü 5'in lifespan'ına bağlanıyor.

---

## Döngü 3 — Güvenlik ve Maliyet Kontrolü: Auth, Rate Limit, Generation Config

### A. Bu döngünün temel amacı
Raporun yönetici özetinde "hemen ele alınması gereken" en kritik üç madde de bu döngüde: `/ws`'nin anonim olmaması, mesaj akışının rate limit'le sınırlandırılması, ve Gemini cevap boyutunun bütçeli olması. Bu üçü birlikte yapılınca "ücretsiz Gemini proxy" senaryosu kapanır — yani projeyi internete açtığında fatura kazası riski makul seviyeye iner. Bu döngünün asıl öğrenme zenginliği, üç farklı güvenlik düzleminin (kimlik, kullanım hacmi, kaynak harcaması) bir arada nasıl ele alınacağıdır.

### B. Review raporundaki hangi bulgular bu döngüye giriyor?

- **[CRITICAL — Bölüm 5.1, 5.8, Risk Tablosu]** `/ws` anonim erişime açık.
- **[CRITICAL — Bölüm 5.2, Risk Tablosu]** Rate limit yok.
- **[CRITICAL — Bölüm 5.4, 7.5, 7.7, Risk Tablosu]** `max_output_tokens` ve generation config yok.
- **[HIGH — Bölüm 5.3]** Input validation (max length, boş kontrol, kontrol karakterleri).
- **[MEDIUM — Bölüm 5.7]** CORS / Origin kontrolü — auth ile birlikte konuşulması gereken bir konu.
- **[MEDIUM — Bölüm 7.7]** System instruction yok.

### C. Bu döngü neden bu sırada ele alınmalı?
Çünkü Döngü 1 ve 2 bu döngünün ön koşullarıydı: auth fail durumunda doğru close code ile kapatabilmek için lifecycle bilgisi (D1) ve audit log için correlation ID + structured logging (D2) gerekiyordu. Şimdi her ikisi de elinde. Ayrıca, bu döngü öğrenme açısından "yüksek aciliyet ama orta zorluk" alanı — auth ekleme zihinsel olarak zor değil; trade-off'ları (query token vs header vs cookie) tanımak gerekiyor.

Neden ilk sırada değil? Çünkü auth eklerken auth fail close handling gerekiyor (D1), rate limit aşıldığında structured log gerekiyor (D2). Sondan önce neden değil? Çünkü bunlar olmadan projeyi hiçbir gerçek kullanıcıya açamazsın; kod organizasyonu (D5) lüks, bu üçü zorunluluk.

### D. Döngü sonunda projede beklenen kalite artışı
- **Güvenlik:** Anonim erişim kapandı; CSWSH ihtimali origin kontrolüyle azaltıldı; input validation devrede.
- **Maliyet kontrolü:** Mesaj/sn limiti + `max_output_tokens` + (opsiyonel) per-connection mesaj sayısı tavanı. "Tek kullanıcı saniyede 100 mesaj atıp API kotamı bitiremez."
- **Hata dayanıklılığı:** Mega prompt / boş prompt artık modele kadar gitmiyor.
- **Gözlemlenebilirlik:** Auth fail, rate limit aşıldı gibi güvenlik olayları loglanıyor.

### E. Öğrenmem gereken teknik kavramlar

**Güvenlik**
- WebSocket'te auth'un HTTP'den farkı (handshake öncesi mi, sonrası mı?). — Token'ı header'a mı query'ye mi koyman gerektiğine karar vermek için.
- Token-based auth (basit static token, sonra JWT/API key). — Auth şemalarının spektrumu.
- CSWSH (Cross-Site WebSocket Hijacking). — Origin doğrulamasının neden gerekli olduğunu kavramak için.
- Origin doğrulaması: `websocket.headers.get("origin")` kontrolü, whitelist mantığı. — Manuel yapman gerek; middleware otomatik halletmiyor.
- Rate limit algoritmaları: token bucket, leaky bucket, sliding window, fixed window. — Hangisinin ne zaman tercih edileceği.
- Input validation prensipleri: whitelist > blacklist, length cap, encoding kontrolü. — DoS ve injection'ı engellemek için.

**FastAPI**
- WebSocket'te `Depends` ile auth dependency. — Auth'u handler'dan çekip dependency'ye taşımak.
- WebSocket exception handling for auth fail (close before accept vs after accept). — Doğru close kodu seçimi.

**Python async**
- `asyncio` ile basit token bucket veya sliding window implementasyonu. — Üçüncü parti `slowapi` HTTP odaklı; WS için manuel kurman gerekecek.
- `asyncio.Lock`, `asyncio.Semaphore`. — Concurrent erişim kontrolünün araçları.

**LLM / Gemini entegrasyonu**
- `GenerateContentConfig` parametreleri: `max_output_tokens`, `temperature`, `top_p`, `top_k`, `safety_settings`, `system_instruction`. — Cevap davranışının kontrol kadranları.
- Token vs karakter farkı. — Bütçeleme yaparken hangi birimle düşüneceğin.

### F. Okumam gereken resmi dokümantasyonlar

- **FastAPI dokümantasyonu**
  - "Dependencies" → "Dependencies with yield" ve "Sub-dependencies"
  - "Advanced > WebSockets" — Depends kullanımı örneği
  - "Security" → "Get Current User" patterni (HTTP odaklı ama mantık aynı)

- **Starlette dokümantasyonu**
  - WebSocket Headers/Query erişimi (`websocket.headers`, `websocket.query_params`)
  - WebSocket close öncesi vs sonrası davranış (`close()` accept'ten önce çağrılırsa ne olur)

- **Google GenAI Python SDK (ai.google.dev / googleapis.github.io/python-genai)**
  - "Configure generation" → `GenerateContentConfig` referansı
  - "System instructions" başlığı
  - "Safety settings" başlığı
  - "Token counting" (varsa) — bütçeleme için

- **OWASP**
  - "WebSocket Security Cheat Sheet" → tüm bölümler
  - "Authentication Cheat Sheet" → "API Keys" ve "Session Management" başlıkları
  - "Cross-Site WebSocket Hijacking" — ayrı bir makale olarak aratılabilir
  - "Denial of Service Cheat Sheet" → Rate limiting bölümü

- **RFC 6455**
  - Section 10 ("Security Considerations") — özellikle 10.2 (Origin Considerations)

- **Wikipedia / blog (kavramsal)**
  - "Token bucket" algoritması — Wikipedia maddesi yeterli
  - "Sliding window rate limit" — kısa bir teknik blog

### G. Dokümantasyon okurken cevaplamam gereken odak soruları

1. WebSocket handshake'inde token'ı header'da mı query string'de mi göndermek daha güvenli? Tarayıcı tabanlı istemci için hangisi kullanılabilir, hangisi kullanılamaz, neden?
2. Auth fail durumunda `accept()` çağırmadan `close()` çağırmak mı, accept edip sonra close etmek mi doğru? Hangi close code uygun?
3. CSWSH saldırısı somut olarak nasıl gerçekleşir? Aynı tarayıcıdaki cookie'lerin saldırgan site üzerinden WS handshake'ine taşınması nasıl mümkün olur?
4. Origin header'ı istemci tarafından spoof edilebilir mi? Browser'dan gelen istek için bu güven seviyesi nedir? Non-browser istemciler için ne değişir?
5. Token bucket ve sliding window algoritmalarının trade-off'u nedir? Burst trafiğe nasıl davranırlar?
6. Rate limit aşıldığında bağlantı kapatmalı mı, sadece o mesajı reddedip ardından gelen mesajları kabul etmeli mi? Bu projede hangisi UX açısından doğru?
7. Gemini'de `max_output_tokens` cevabın **karakter** sayısını mı, **token** sayısını mı sınırlar? Türkçe için bir token kaç karaktere denk gelir (yaklaşık)?
8. `system_instruction` ne işe yarar? Olmadığında modelin "varsayılan kişiliği" davranışı nasıl olur?
9. **(Projeme özel)** Şu an `chat = await client.aio.chats.create(model='gemini-2.5-flash')`. `GenerateContentConfig`'i hangi noktada vermeliyim — `create` çağrısında mı, her `send_message_stream` çağrısında mı? SDK'nın hangisini desteklediğini doğrulamam gerek.
10. **(Projeme özel)** Rate limit'i bağlantı başına mı, kullanıcı (token) başına mı uygulamalıyım? Şu an "kullanıcı kimliği" tek bir paylaşılan token ise iki yaklaşımın farkı pratik olarak ne olur?
11. Input length cap için makul üst sınır kaç karakter / kaç token? Bu sınırı aşan input için kullanıcıya nasıl davranılır (reddedildi mesajı? otomatik kırpma? bağlantı kapatma?)?
12. **(Karşılaştırma)** Auth için (a) statik tek paylaşılan token, (b) sunucuda doğrulanan kısa-ömürlü token, (c) JWT — bu üçü arasından öğrenme + portfolyo + risk açısından bu proje için hangisi şu an doğru? Sonraki adım hangisine geçişe yatar?

### H. Öğrenme notlarımı hangi formatta çıkarmalıyım?

| Alan | İçerik |
|---|---|
| Kavram | … |
| Kendi cümlemle açıklama | … |
| Bu projedeki karşılığı | … |
| **Saldırı senaryosu** | Bu konu yokken hangi somut saldırı/abuse mümkün |
| **Savunma mekanizması** | Eklediğim kontrol bunu nasıl kapatıyor |
| Trade-off | Eklediğim kontrolün maliyeti / UX etkisi |
| Açık kalan sorum | … |

### I. Kodda benim kendim uygulamam gereken iyileştirme görevleri

Bu döngü en çok görevi olan döngü; bilinçli olarak parçaladım. Sıralama önemli: önce kapı (auth), sonra giriş süzme (input), sonra hız sınırı (rate limit), sonra dış kaynak bütçesi (generation config).

1. **Statik bir auth token mekanizması ekle.** Config'de `app_access_token` alanı; WebSocket handshake'inde query string veya header'dan oku, eşleşmezse `accept()` çağırma → `close()` ile uygun code (1008 policy violation veya custom 4001) ile düşür. Görev: *[CRITICAL] /ws anonim erişim.*

2. **Origin doğrulaması ekle.** Config'de `allowed_origins` listesi; handshake'te `websocket.headers.get("origin")` whitelist kontrolü. Görev: *[MEDIUM → auth eklenince HIGH] CORS/Origin yok.*

3. **Input validation katmanı.** Boş string, üst karakter sınırı (sen seç ve gerekçesini yaz), kontrol karakterleri (`\x00` gibi) reddedilsin. Reddedilen input için kullanıcıya nedenini söyleyen kısa bir mesaj git (henüz envelope yok, Döngü 4'te gelecek; şimdilik düz text yeterli). Görev: *[HIGH] Input validation yok.*

4. **Per-connection sliding window veya token bucket rate limit.** Önerim: ilk implementasyon basit olsun — son N saniyedeki mesaj sayısı bir threshold'u aşıyorsa o mesajı reddet. Limit aşıldığında bağlantıyı kapatmamayı seçebilirsin (UX iyi); ama tekrar tekrar limit aşılırsa kapatmayı düşün. Görev: *[CRITICAL] Rate limit yok.*

5. **`GenerateContentConfig` ekle:** En az `max_output_tokens`, `temperature`, `system_instruction`. `safety_settings` ileri seviyeyse şimdilik defaultta bırak — ama bilinçli karar olsun. Görev: *[CRITICAL] Generation config yok + [MEDIUM] system instruction yok.*

6. **Güvenlik olaylarını logla:**
   - Auth fail (WARNING) → hangi origin, hangi IP (mümkünse).
   - Rate limit aşıldı (WARNING) → conn_id, kaç mesaj saydı.
   - Geçersiz input reddedildi (INFO) → conn_id, hangi sebep.
   Görev: Döngü 2'nin loglama altyapısının ilk gerçek kullanımı.

7. **(Bilinçli erteleme)** Per-user (token başına) rate limit ve persistent storage'lı limit Döngü 5/6'ya bırakılır — şimdilik in-memory per-connection yeterli.

8. **(Bilinçli erteleme)** Token sayma ile gerçek "kullanıcı bütçesi" Döngü 4'te chat history yönetimiyle birlikte gelecek; bu döngüde sadece `max_output_tokens` ile dış sınır var.

### J. Bu döngü tamamlandı mı, nasıl anlayacağım?

**Tamamlanma kriterleri:**
- [ ] Token olmadan `/ws`'ye bağlanma denemesi `accept` olmadan kapanıyor.
- [ ] Yanlış origin'den gelen handshake reddediliyor.
- [ ] Boş mesaj, mega mesaj, kontrol karakterli mesaj reddediliyor.
- [ ] Saniyede çok mesaj atan istemci ya limitleniyor ya da bağlantısı kapatılıyor.
- [ ] Gemini'ye giden istek `max_output_tokens`'la sınırlı.
- [ ] `system_instruction` set edilmiş; bot artık "kimliğini" biliyor.
- [ ] Auth fail, rate limit, validation fail logda görünür.

**Manuel test senaryoları:**

1. **Auth bypass denemesi:** Token'sız bağlan. Beklenen: `accept` olmamış, bağlantı reddedilmiş; logda WARNING; browser dev tools'ta close frame görünüyor.
2. **Yanlış token denemesi:** Yanlış token ile bağlan. Aynı sonuç beklenir.
3. **Doğru token + yanlış origin:** Token doğru ama origin whitelist dışı. Reddedilmeli.
4. **Boş mesaj:** Doğru bağlanmış istemciden boş string gönder. Mesaj modele gitmemeli; kullanıcı kısa bir hata almalı.
5. **Mega mesaj:** Senin belirlediğin tavanı aşan bir input gönder. Aynı şekilde reddedilmeli.
6. **Spam testi:** Bir döngü ile saniyede 20 mesaj at. Bir kısmı reddedilmeli; logda rate limit warning'leri görünmeli.
7. **`max_output_tokens` testi:** "Bana 10000 kelimelik bir hikâye yaz." Cevap tavandan kesilmeli; ne kadarda kesildiğini gözlemle.
8. **`system_instruction` testi:** Bota "Sen kimsin?" diye sor. Cevap sistem talimatınla uyumlu olmalı.

**Beklenen gözlemler:**
- Reddedilen handshake'ler `accept` olmadan kapanıyor (gereksiz kaynak tutmuyorsun).
- Rate limit hit'leri loglarda görülebiliyor.
- Modelin cevap uzunluğu tavandan dönüyor — bu özellikle önemli, çünkü maliyet kontrolü bunun üstüne kurulu.

**Olmaması gereken durumlar:**
- Token doğruysa kullanıcının normal bir mesajının reddedilmesi (false positive).
- Rate limit'in tüm kullanıcılar için global olması (her bağlantı kendi limitiyle olmalı).
- `max_output_tokens` set edildiği halde 5000 kelimelik cevabın gelmesi (config çağrıya iletilmiyor demektir).
- Auth fail sonrası bağlantının asılı kalması.

### K. Döngü sonunda bana neyle dönmelisin?

1. Auth mekanizmasının tasarım kararı: token nereden okunuyor, neden orası, hangi close code seçtin, neden.
2. Rate limit algoritması seçimin ve gerekçesi (sliding window mu, token bucket mı, threshold ne).
3. Origin whitelist'inin nasıl yapılandırıldığı.
4. `GenerateContentConfig`'in tam set'i (alan adları + değerler) + system instruction'ın metni.
5. Sentetik saldırı testlerinin sonuçları (auth bypass, spam, mega mesaj).
6. "Saldırı senaryosu / savunma mekanizması" tablosunun en az 3 satırı.
7. Açık kalan sorular — özellikle "kullanıcı başına mı bağlantı başına mı limit" konusundaki tereddütlerin.

---

## Döngü 4 — Mesaj Protokolü ve LLM Context/Maliyet Yönetimi

### A. Bu döngünün temel amacı
Şu an WebSocket üzerinden iki yön de düz text akıyor: kullanıcı text gönderiyor, sunucu chunk text gönderiyor. Frontend "bu chunk mu, hata mı, stream bitti mi?" diye ayırt edemiyor. Bu döngünün ilk yarısı: yapılandırılmış mesaj envelope'u tasarlamak (`{type, content, ...}`). İkinci yarısı: chat history'nin sınırsız büyümesini durdurmak — şu an her mesajda tüm geçmiş modele gidiyor, token maliyeti kümülatif. Bu iki konu birlikte çünkü envelope tasarladığında stream sonu sinyalini frontend'e gönderebilir, ve bu sinyal stream başına kaç token harcandığını da raporlamak için doğal bir yerdir.

### B. Review raporundaki hangi bulgular bu döngüye giriyor?

- **[Bölüm 3.5, 3.7, MEDIUM/HIGH — Risk Tablosu]** Mesaj protokolü unstructured; stream sonu sinyali yok.
- **[HIGH — Bölüm 7.2, Risk Tablosu]** Chat history sınırsız büyüme.
- **[MEDIUM — Bölüm 6.6, 7.1]** Session/chat history persistence (bilinçli olarak yarısı ertelenecek).
- **[MEDIUM — Bölüm 7.3, Risk Tablosu]** Gemini çağrısına timeout yok.
- **[MEDIUM — Bölüm 7.7]** Generation config'in geri kalan parçaları (D3'te başlatıldı, D4'te perçinlenebilir).

### C. Bu döngü neden bu sırada ele alınmalı?
Üç sebep:
1. D3'te `max_output_tokens` ile çıktı kontrolü ekledin, ama girdi kontrolü (chat history büyümesi) hâlâ yok — D4'ün bunu kapatması doğal devam.
2. Envelope protokolü, D3'te eklediğin "geçersiz input reddedildi" gibi mesajların doğru yere oturması için gerekli — şimdiye kadar düz text yetiyordu, daha fazla state ekleyince yetmez.
3. Timeout, lifecycle ile (D1) ve logging ile (D2) bağlantılı — bu altyapılar olmadan timeout'un anlamı eksik.

Neden D5 öncesi? Çünkü envelope protokolü ve history yönetimi business logic'in tam ortasında — Döngü 5'te bu logic'i `ChatService`'e ayıracaksın; önce davranışı doğru kur, sonra ayır.

### D. Döngü sonunda projede beklenen kalite artışı
- **Maliyet kontrolü:** Chat history makul bir pencerede tutuluyor; kümülatif token şişmesi durdu.
- **Hata dayanıklılığı:** Gemini takıldığında timeout devreye giriyor; sonsuz asılı kalmıyor.
- **WebSocket protokol netliği:** Frontend "chunk", "stream başladı", "stream bitti", "hata", "rate-limited" gibi olayları kanal üzerinden net ayırt edebiliyor.
- **Sürdürülebilirlik:** Mesaj şeması Pydantic ile tipli — frontend ile sözleşme yazılı.

### E. Öğrenmem gereken teknik kavramlar

**FastAPI / Pydantic**
- WebSocket'te JSON envelope: `receive_json`, `send_json`. — `receive_text` / `send_text`'ten geçiş.
- Pydantic mesaj modelleri (`MessageIn`, `MessageOut`, type-discriminated unions). — Type-safe protokol.
- Discriminated union (literal `type` alanı). — `chunk`/`done`/`error`'ı tek modelde toplamanın yolu.

**Python async / asyncio**
- `asyncio.wait_for(...)` ile timeout. — Tek bir çağrıyı zamanla sınırlamak.
- `asyncio.TimeoutError` handling. — Timeout sonrası lifecycle.
- Async generator'ı timeout ile sarmak. — Stream'in bütünü yerine her chunk için timeout mu, toplam mı?

**LLM / Gemini entegrasyonu**
- Chat history pencereleme stratejileri:
  - Sliding window (son N mesaj).
  - Token-bütçeli pencere (en yeniden geriye doğru, token bütçesine kadar).
  - Summarization (özet + son N mesaj).
- Gemini SDK'da chat objesi history'sine manuel müdahale (`chat.get_history`, `chat.send_message` history ile mi otomatik mi).
- Token counting: `client.models.count_tokens` veya benzeri API.

**Protokol tasarımı**
- Message envelope: `{type, id, content, timestamp, ...}`. — Versiyonlanabilir bir sözleşme nasıl olur.
- "End-of-stream" sentinel (`[DONE]` veya `{type:"done"}`). — Frontend stream akışını nasıl sonlandırır.

### F. Okumam gereken resmi dokümantasyonlar

- **FastAPI dokümantasyonu**
  - "WebSockets" → `receive_json`, `send_json` örnekleri
  - "Body - Nested Models", "Discriminated Unions" (Pydantic ile)

- **Pydantic v2 dokümantasyonu**
  - "Models" → discriminated unions
  - "Field types" → `Literal`
  - "Validators" → mesaj input'unu doğrulamak için

- **Python `asyncio` dokümantasyonu**
  - "Coroutines and Tasks" → `asyncio.wait_for`, `asyncio.timeout` (Python 3.11+)
  - "Synchronization Primitives" — daha sonra gerekirse

- **Google GenAI Python SDK**
  - Chat history yönetimi başlığı (`chats` modülü, history mutation)
  - Token counting API
  - Streaming + `GenerateContentConfig` etkileşimi

- **MDN — WebSocket API**
  - `MessageEvent.data` üzerinde JSON parsing — frontend tarafı

### G. Dokümantasyon okurken cevaplamam gereken odak soruları

1. WebSocket üzerinden JSON envelope göndermenin trade-off'u nedir (parse overhead vs netlik)? Bu projem için makul mü?
2. Discriminated union ile mesaj türlerini ayırırken `Literal` alanı nereye konmalı? Pydantic v2'de bu nasıl yazılır?
3. Stream sırasında frontend "stream başladı" sinyalini ne zaman beklemeli — ilk chunk'tan önce mi, ilk chunk'la birlikte mi? Hangisi UX olarak daha iyi?
4. `asyncio.wait_for(coro, timeout=X)` timeout'a uğradığında coroutine ne olur? Cancellation nasıl propagate edilir?
5. Async generator'ı `wait_for` ile sarmak mümkün mü? Generator için timeout uygulamanın doğru yolu nedir?
6. Sliding window history'sinde sınır olarak mesaj sayısı mı, token sayısı mı kullanmalı? Hangisi daha öngörülebilir maliyet verir?
7. Gemini chat objesinin history'sine doğrudan müdahale etmek "supported" bir kullanım mı, yoksa her seferinde yeni chat objesi mi yaratılmalı?
8. **(Projeme özel)** Şu anda `chat` WebSocket bağlantısının ömrü kadar yaşıyor. Pencereleme uygularken (a) aynı chat objesinde history'yi kırpmak, (b) belirli aralıklarla yeni chat objesi yaratıp geçmişin özetini system instruction'a koymak — bu projede hangisi mantıklı? Hangisi SDK'da kolay?
9. **(Projeme özel)** Mesaj envelope'unu eklediğimde, kullanıcı tarafı hâlâ düz text gönderebilir mi yoksa frontend de envelope göndermeye geçmeli mi? Geriye uyumluluk düşüncem var mı?
10. Gemini SDK'da bir streaming çağrısı kullanıcı tarafından iptal edildiğinde (timeout veya disconnect) faturalama nerede durur? Yanıt üretildiği kadar mı faturalanır, baştan başa mı?
11. **(Karşılaştırma)** "Stream sonu" sinyali olarak (a) ayrı bir mesaj (`{type:"done"}`), (b) son chunk'a `is_final: true` flag eklemek, (c) iki kanal arasında ayrı bir WS subprotocol kullanmak — bu üç yaklaşımdan hangisi bu projede en uygun?
12. Timeout'u (a) tüm stream için tek bir tavan, (b) her chunk arasında "ne kadar bekleyebilirim" tavanı olarak iki şekilde uygulayabilirsin. Hangisi LLM streaming için daha doğru?

### H. Öğrenme notlarımı hangi formatta çıkarmalıyım?

| Alan | İçerik |
|---|---|
| Kavram | … |
| Kendi cümlemle açıklama | … |
| Bu projedeki karşılığı | … |
| Eski davranış | Önceden ne oluyordu |
| Yeni davranış | Şimdi ne oluyor |
| Riski / sınırı | Yine de neye dikkat |
| Açık kalan sorum | … |

Ek alan bu döngüye özel: **"Mesaj türleri tablosu"** — projede tanımladığın her envelope tipini, ne zaman kullanıldığını, hangi alanları içerdiğini bir tabloda topla.

### I. Kodda benim kendim uygulamam gereken iyileştirme görevleri

1. **Pydantic ile mesaj envelope modelleri tasarla.** En az şu türler: `user_message`, `assistant_chunk`, `assistant_done`, `error`, `system` (rate-limited, validation-failed vb. için). Frontend ile sözleşmen bu olacak. Görev: *[Risk Tablosu MEDIUM] Mesaj protokolü düz text.*

2. **`receive_text` → `receive_json`, `send_text` → `send_json`'a geç.** Kullanıcı tarafının da JSON göndereceğini bilmen gerek; eski düz text desteği için bir migration period bilinçli karar olabilir. Görev: aynı bulguya bağlı.

3. **Stream bittiğinde `assistant_done` mesajı gönder.** Frontend bunu görmeden "cevap bitti" demesin. Görev: *[Stream sinyali yok] Risk Tablosu.*

4. **Chat history pencerelemesi:** Bir strateji seç (sliding window mesaj-sayısı, token-bütçeli, vb.) ve uygula. Limiti config'e taşı. Görev: *[HIGH] Chat history sınırsız büyüme.*

5. **Gemini çağrısına timeout ekle.** `asyncio.wait_for` ile per-stream tavan veya per-chunk tavan — kararını gerekçelendir. Timeout durumunda kullanıcıya `error` envelope'u + uygun close code (D1'den hatırla). Görev: *[MEDIUM] Timeout yok.*

6. **Hata, validation fail, rate limit aşıldı mesajlarını da envelope ile gönder** (D3'te bu mesajlar düz text'ti; envelope'a taşı). Görev: D3'le entegrasyon.

7. **(Bilinçli erteleme)** Chat history'nin **persist** edilmesi (Redis/SQLite, reconnect'te restore) bu döngüde değil — Bölüm 6.6'daki "ürünleşme için HIGH" notuna saygı duyuyoruz ama bu öğrenme turunun kapsamı dışı. Erteleme gerekçesi: D5'teki katmanlama yapılmadan storage soyutlaması anlamsız.

8. **(Bilinçli erteleme)** Sliding window yerine summarization tabanlı pencere — ileri seviye; ilk uygulamada sliding window yeterli.

### J. Bu döngü tamamlandı mı, nasıl anlayacağım?

**Tamamlanma kriterleri:**
- [ ] Mesaj envelope'ları Pydantic modelleri olarak tanımlı.
- [ ] WebSocket I/O `_json` versiyonlarını kullanıyor.
- [ ] Stream sonu `assistant_done` ile sinyalleniyor.
- [ ] Chat history bir tavan üzerinde büyümüyor; tavanı tahmin edebiliyorsun.
- [ ] Gemini timeout sınırı belirli; tetiklenince düzgün davranıyor.
- [ ] Tüm sistem/hata mesajları envelope formatında.

**Manuel test senaryoları:**

1. **Envelope smoke test:** Frontend'den `{"type":"user_message","content":"merhaba"}` gönder; cevap olarak `{"type":"assistant_chunk", ...}` chunk'ları + son `{"type":"assistant_done"}` görmelisin.
2. **History pencere testi:** Tavanını N=10 mesaj seçtiysen, 15 mesaj at; 6. mesaja referans veren bir soru sor ("ilk mesajımı hatırlıyor musun?"). Beklenen: hatırlamıyor (çünkü pencere dışına düştü). Gerçekten kestiğini doğrulamak için modele giden istekteki mesaj sayısını da logla.
3. **Timeout testi:** Geçici olarak timeout'u çok kısa (örn. 0.1 saniye) yap, mesaj gönder. Timeout error envelope'u almalısın; bağlantı uygun şekilde davranmalı (kapanıyorsa close code'u kontrol et).
4. **Validation fail envelope testi:** Boş mesaj gönder. `{"type":"error", "code":"validation_failed", ...}` benzeri bir envelope almalısın.
5. **Rate limit envelope testi:** Hızlı bir döngü ile spam yap. Rate limit aşılınca `{"type":"system", "code":"rate_limited", ...}` benzeri envelope.

**Beklenen gözlemler:**
- Frontend dev tools'ta WS frame'leri tek tip değil; tipi açıkça okunabiliyor.
- Logda her stream için "history size = X tokens / Y messages" gibi bir özet (D2 loglamasından).
- Timeout senaryosunda asılı kalma yok.

**Olmaması gereken durumlar:**
- Düz text mesajların hâlâ akıyor olması (regression — eski kodun bir kısmı atlanmış).
- History pencerelemesi yapıldığı halde her mesajda toplam token sayısının lineer artmaya devam etmesi (kesme çalışmıyor).
- Stream sonunda `assistant_done`'un eksik olması (frontend spinner sonsuza döner).

### K. Döngü sonunda bana neyle dönmelisin?

1. Mesaj envelope şemalarının özeti (Pydantic alan adları, türleri, hangi yöne ait).
2. Stream lifecycle frame sırası (örn: `user_message in → assistant_chunk × N → assistant_done`).
3. History pencereleme algoritmasının seçimi + gerekçesi.
4. Timeout stratejinin seçimi (per-stream vs per-chunk) + gerekçesi.
5. Manuel testlerin sonuçları, özellikle history pencere testi.
6. Frontend'i de güncelledin mi? Güncellediysen kısa not; güncellemediysen yarattığın incompatibility'nin farkında olduğunun teyidi.
7. Açık kalan sorular — özellikle Gemini'nin chat history mutation davranışı konusunda.

---

## Döngü 5 — Kod Organizasyonu, LLM Soyutlaması, Lifespan

### A. Bu döngünün temel amacı
İlk dört döngüde işlevsel doğruluğu kurdun; şimdi tek dosya `main.py` üç ayrı sorumluluğu (web route, ws route, LLM çağrısı) ve config + logging setup + business logic'i barındırıyor. Bu döngü, kodu sürdürülebilir bir yapıya kavuşturur: router'lara böl, business logic'i `services`'e ayır, LLM'i bir interface arkasına koy (vendor lock-in'i azalt + test edilebilirlik), client lifecycle'ını `lifespan` handler'a bağla. Bu döngünün öğrenme cevheri "FastAPI'da modüler yapı" + "interface based design" + "lifecycle to lifespan binding"dir.

### B. Review raporundaki hangi bulgular bu döngüye giriyor?

- **[Bölüm 1.1, 1.2, Bölüm 9, Risk Tablosu]** Lifecycle yönetimi yok / katmanlar iç içe / soyutlama yok / config dağınık (D2'de kısmen çözüldü, mimari yer D5'te).
- **[MEDIUM — Bölüm 7.6, Risk Tablosu]** LLM soyutlaması yok.
- **[Bölüm 9.2, 9.3]** Dosya bölünmesi önerisi; isimlendirme problemleri (`read_item`, `item.html`, `e`, `e1`, `data`).
- **[LOW — Bölüm 3.1, 9.4]** Kullanılmayan import (D2'de henüz silinmediyse).
- **[Bölüm 1.1, Risk Tablosu]** Graceful shutdown / lifespan handler.

### C. Bu döngü neden bu sırada ele alınmalı?
İlk dört döngüde davranışı kurdun, davranış doğruyken refactor yapmak güvenli; davranış yanlışken refactor yapmak hatayı taşır. Ayrıca refactor için en az bir manuel test repertuvarın olması gerek — D1-D4'te bunu inşa ettin. Bu döngünün ertelenmesi de bir seçenekti; ama D6'da test yazacaksan önce test edilebilir bir yapı gerek, ve katmanlama olmadan unit test yazılamaz — sadece e2e test yazılabilir. Bu yüzden D5, D6'nın ön koşulu.

Neden sondan önce değil? Çünkü ertelenirse her sonraki ek özellik (auth dependency, rate limit middleware, history persistence) tek dosyaya gömülmeye devam eder ve refactor maliyeti üstel büyür.

### D. Döngü sonunda projede beklenen kalite artışı
- **Sürdürülebilirlik:** Her dosyanın tek bir sorumluluğu var; yeni özellik eklerken nereye dokunacağın belli.
- **Kod organizasyonu:** Router / service / config / schema ayrımı net.
- **Hata dayanıklılığı:** Client lifecycle uygulamaya bağlı; graceful shutdown'a hazır.
- **WebSocket lifecycle (uygulama seviyesi):** Lifespan ile startup/shutdown'da kaynak yönetimi.
- **Test edilebilirlik (zemin):** D6'da unit test yazılabilir bir yapı oluşur.

### E. Öğrenmem gereken teknik kavramlar

**FastAPI**
- `APIRouter` ile router-bazlı bölünme. — Route'ları dosyalara dağıtmanın yolu.
- `lifespan` async context manager. — startup/shutdown event'inin yeni resmi yolu (eski `@app.on_event` deprecated).
- `Depends` ile service injection. — Endpoint'lere servisi geçirme.
- Application state (`app.state` veya lifespan yielded objesi). — Uzun ömürlü kaynakları taşıma yeri.

**Python**
- Protocol / ABC ile interface tanımlama. — `LLMProvider` abstract'ı için.
- Constructor dependency injection patterni. — Service'in test edilebilir olması için.
- Module organization: relative vs absolute import, `__init__.py`'nin rolü. — Paket yapısı kurulurken.

**Production backend**
- Resource lifecycle binding (uygulama açılışında alıp kapanışta serbest bırakma). — 12-factor "backing services" alışkanlığı.
- Graceful shutdown sinyali (SIGTERM) → bağlı kullanıcıları uyararak kapatma. — D6'ya bağlanır ama temeli burada atılır.

**LLM / Gemini entegrasyonu**
- Provider-agnostic interface tasarımı: hangi metotlar minimum gerek (`stream(message, history) → AsyncIterator[str]` gibi). — Vendor lock-in'i azaltmak için.

### F. Okumam gereken resmi dokümantasyonlar

- **FastAPI dokümantasyonu**
  - "Bigger Applications - Multiple Files" → tüm sayfa, en kritik kaynak
  - "Lifespan Events" → `lifespan` async context manager pattern
  - "Dependencies" → `Depends` ile global dependency
  - "Settings and Environment Variables" → "Settings in a Dependency"

- **Starlette dokümantasyonu**
  - "Lifespan" referansı

- **Python dokümantasyonu**
  - `typing` modülü → `Protocol` (PEP 544)
  - `abc` modülü → ABC, abstractmethod
  - "Modules" → packages, `__init__.py`

- **12-factor**
  - "VI. Processes" — stateless işlemler, lifespan'la nasıl uyumlu
  - "IX. Disposability" — graceful shutdown felsefesi

### G. Dokümantasyon okurken cevaplamam gereken odak soruları

1. `lifespan` async context manager nasıl çalışır? `yield`'den önceki kısım ne zaman, sonraki kısım ne zaman çalışır?
2. Genai client'ı lifespan'da oluşturup yield ile aşağı verirken, endpoint'ler ona nasıl ulaşır — `app.state` mi, `request.app.state` mi, dependency mi?
3. `APIRouter`'ı kullanırken `prefix`, `tags`, `dependencies` parametreleri ne işe yarar? Bu projede ws router'ı için hangileri uygun?
4. WebSocket endpoint bir router içine alındığında auth dependency'si nasıl yazılır? HTTP endpoint'lerden farkı?
5. Python `Protocol` (structural typing) ile `ABC` (nominal typing) arasındaki fark nedir? `LLMProvider` için hangisi daha doğru?
6. `LLMProvider` interface'i hangi metotları tanımlamalı — sadece `stream`, yoksa `count_tokens`, `set_system_instruction` de? "Minimum interface" prensibi neyi söyler?
7. Service'leri her istek başına mı oluşturmak (request-scoped), yoksa uygulama ömrü boyunca tek instance mı tutmak doğru? Bu projedeki Gemini client paylaşımıyla uyum nasıl olur?
8. **(Projeme özel)** Şu an `chat` objesi per-connection, `client` modül seviyesi. Refactor sonrası: `client` lifespan'da, `chat` her bağlantı için service'in yarattığı bir nesne — bu doğru bir kavramsal eşleştirme mi? `LLMProvider` interface'i hem connection-bağlı state'i (chat) hem connection-bağımsız state'i (client) nasıl temsil eder?
9. **(Projeme özel)** `read_item` ve `item.html` isimlerini şimdi (D5'te) değiştirmek için doğru zaman mı? Yoksa daha sonra mı? Refactor sırasında çok şey aynı anda değişmeli mi, küçük adımlar mı?
10. **(Karşılaştırma)** Service'i (a) FastAPI'nin `Depends` sistemiyle inject etmek vs (b) modül-seviyesi singleton vs (c) lifespan'da `app.state`'e koymak — bu üçü arasındaki ergonomi farkı? Hangisi test için en kolayı?
11. `lifespan` shutdown kısmında WebSocket bağlantıları açıkken ne yapılmalı? Hepsine "kapanıyoruz" mesajı gönderip 1001 ile mi kapatmalı?
12. Refactor sırasında nasıl emin olurum davranışı bozmadığımı — küçük adımlar + manuel test her adımda mı, yoksa bir kerede yapıp toplu test mi? Hangisi daha az risk?

### H. Öğrenme notlarımı hangi formatta çıkarmalıyım?

| Alan | İçerik |
|---|---|
| Kavram | … |
| Kendi cümlemle açıklama | … |
| Bu projedeki karşılığı | … |
| Refactor öncesi nerede yaşıyordu | … |
| Refactor sonrası nereye taşındı | … |
| Bu taşıma neyi kolaylaştırıyor | … |
| Açık kalan sorum | … |

Ek alan: **"Sorumluluk matrisi"** — her yeni dosya için: ne içerir, ne içermez. Bu, scope creep'i önler.

### I. Kodda benim kendim uygulamam gereken iyileştirme görevleri

Refactor stratejik bir görev — sıra önemli. Bilinçli olarak **küçük adımlar, her adımda test** prensibi.

1. **Önce: dosya yapısını taslakla.** Kâğıt üzerinde veya bir markdown'da: `app/main.py`, `app/config.py`, `app/routers/web.py`, `app/routers/ws.py`, `app/services/chat_service.py`, `app/services/llm_provider.py`, `app/schemas/messages.py`, `app/logging_config.py`. Henüz kodu taşıma. Görev: planlama.

2. **Sonra: `config.py`'yi ayır** (D2'de oluşturduğun Settings burada). Test et. Görev: *[Bölüm 9.2] Dosya bölünmesi.*

3. **Logger setup'ını `logging_config.py`'ye ayır.** Test et.

4. **Mesaj schema'larını (D4'tekiler) `schemas/messages.py`'ye taşı.** Test et.

5. **HTTP route'unu (web sayfası) `routers/web.py`'ye taşı.** Bu sırada `read_item` → `index` (veya `render_chat_page`), `item.html` → `chat.html`. Görev: *[LOW] İsimlendirme.* Test et.

6. **`LLMProvider` interface'ini tasarla.** Protocol veya ABC ile. En az bir metot: `async def stream(message: str, history: list[...]) -> AsyncIterator[str]`. (Tasarımda hangi parametreleri history'e koyacağına D4'ten dönerek karar ver.) Görev: *[MEDIUM] LLM soyutlaması.*

7. **`GeminiProvider` (somut implementasyon) yaz.** Bu yine kendi başına bir görev — interface'i Gemini SDK'sının üstünde gerçekle.

8. **`ChatService` yaz.** Bu service: `LLMProvider`'ı kullanır, history pencerelemesini uygular (D4), rate limit'i uygular (D3 — buraya çekmek de bir seçenek; ya da WS router'da bırakırsın, karar senin). Görev: *[Bölüm 1.1, 9.2] Katmanlar iç içe.*

9. **WS endpoint'i `routers/ws.py`'ye taşı.** Service'i `Depends` ile inject et. Görev: aynı bulgu.

10. **`lifespan` handler yaz.** Gemini client'ı lifespan'da oluştur; shutdown'da varsa cleanup. Modül seviyesi `client = ...` satırını kaldır. Görev: *[Bölüm 1.1] Lifecycle yönetimi.*

11. **Kullanılmayan import'u sil.** `from google.genai import types` — kullanıyorsan sil; kullanıyorsan ya da config çağrılarında geçiyorsa yerinde kalır. Görev: *[LOW] Kullanılmayan import.*

12. **(Bilinçli erteleme)** `ConnectionManager` (aktif bağlantıları takip eden sınıf) bu döngüde değil — D6'da metrics + graceful shutdown ile birlikte gelecek. Şimdi eklemek scope'u genişletir.

### J. Bu döngü tamamlandı mı, nasıl anlayacağım?

**Tamamlanma kriterleri:**
- [ ] `main.py` artık ~30 satır FastAPI app + include_router + lifespan, başka iş yapmıyor.
- [ ] Web ve WS route'ları ayrı dosyalarda.
- [ ] LLM çağrıları bir provider arkasında.
- [ ] Business logic `ChatService` içinde.
- [ ] Gemini client lifespan'da oluşuyor.
- [ ] Magic isimler temiz: `read_item` → `index`, `item.html` → `chat.html`, `e/e1` → anlamlı isimler.
- [ ] Tüm önceki davranışlar aynı (D1-D4 testleri hâlâ geçiyor).
- [ ] Kullanılmayan import'lar temiz.

**Manuel test senaryoları:**

D1-D4'ün **tüm** test senaryolarını tekrar koş. Refactor'un başarı kriteri: hiçbir davranış değişmemiş olması. Ek olarak:

1. **Lifespan startup logu:** Uygulama başladığında "Gemini client initialized" gibi bir log görmelisin.
2. **Lifespan shutdown:** Uygulamayı Ctrl+C ile kapat. "Shutting down... client closed" gibi bir log akmalı; asılı kalma OLMAMALI.
3. **Provider mock testi (manuel):** `GeminiProvider` yerine geçici bir `FakeProvider` yaz (chunk olarak "test test test" döndürsün). WS'e bağlan, mesaj gönder. Frontend "test test test" görmeli. Sonra geri al. Bu, soyutlamanın işe yaradığını teyit eder — D6'da unit test bu sayede yazılabilecek.

**Beklenen gözlemler:**
- Davranış aynı.
- Logda startup/shutdown event'leri görünür.
- Provider değişimi tek satırla mümkün.

**Olmaması gereken durumlar:**
- Davranış değişmiş olması (regression).
- `main.py`'de hâlâ business logic.
- Modül seviyesinde `genai.Client(...)` kalıntısı.
- WS endpoint'in service yerine doğrudan SDK'ya bağlı kalması.

### K. Döngü sonunda bana neyle dönmelisin?

1. Yeni dosya yapısının tam haritası ve her dosyanın 1-2 cümlelik sorumluluğu.
2. `LLMProvider` interface'inin metotları (sadece imza listesi yeterli; gövde değil).
3. Lifespan handler'ın akışı (startup'ta ne, shutdown'da ne).
4. Refactor sırasında karşılaştığın sürpriz davranış değişikliği oldu mu? Olduysa nasıl çözdün?
5. "Sorumluluk matrisi" tablosu.
6. D1-D4 testlerinin sonuçlarını tekrar koşmuş olmanın teyidi.
7. `FakeProvider` denemen — soyutlamanın gerçekten işe yarayıp yaramadığının teyidi.
8. Açık kalan sorular — özellikle `Depends` ile service injection patterni.

---

## Döngü 6 — Test, Gözlemlenebilirlik ve Production-Readiness

### A. Bu döngünün temel amacı
Önceki beş döngüde işlevselliği ve mimariyi kurdun; ama hâlâ bir refactor güveni (test) ve operasyonel görünürlüğü (metrics, health endpoint, graceful shutdown) eksik. Bu döngü, projeyi "çalışan ama kör" durumdan "izlenebilir ve değiştirilebilir" duruma taşır. Burada öğrenme cevheri: minimum efforla maksimum güven veren test stratejisi + ne ölçeceğini bilmek (vs her şeyi ölçmek).

### B. Review raporundaki hangi bulgular bu döngüye giriyor?

- **[Bölüm 3.8, Risk Tablosu]** Test yok.
- **[Bölüm 3.4, 6.4, 6.5, Risk Tablosu]** WebSocket lifecycle gözlemleme (heartbeat, ConnectionManager).
- **[Risk Tablosu]** Graceful shutdown.
- **[Bölüm 3.8, Risk Tablosu]** Health endpoint, metrics, tracing.
- **[Bölüm 3.8]** Dockerfile/deployment notları.
- **[Bölüm 3.8]** Dependency dosyası / pinleme.
- **[Bölüm 7.8]** SDK sürüm pinleme.

### C. Bu döngü neden bu sırada ele alınmalı?
Çünkü test, soyutlama (D5) olmadan yazılamaz — `GeminiProvider`'a gerçek API çağrısı yapan test ne yararlı ne ekonomiktir; fake provider'la unit test ise D5'in soyutlaması sayesinde mümkün. Aynı şekilde metrics ve health endpoint, `lifespan` (D5) ve logging (D2) altyapısının üstüne kuruluyor. Graceful shutdown, lifespan'ın shutdown tarafının (D5) doğal genişlemesi.

Neden son sırada? Çünkü test edilecek davranış D1-D5'te netleşmiş olmalı; aksi takdirde geçici davranışı test edip sonra refactor'da test'i kırma sarmalına girersin.

### D. Döngü sonunda projede beklenen kalite artışı
- **Sürdürülebilirlik:** Refactor güveni var; davranış kıran değişiklikleri test yakalıyor.
- **Gözlemlenebilirlik:** Aktif bağlantı sayısı, mesaj sayısı, ortalama stream süresi gibi metrikler bir yerden okunabilir.
- **Production-readiness:** Health endpoint, deployment'in başlangıç noktası. Graceful shutdown deploy sırasında bağlantı kopuşunu makul karşılıyor.
- **Hata dayanıklılığı:** Heartbeat / zombie connection tespiti devrede.

### E. Öğrenmem gereken teknik kavramlar

**Test**
- pytest temelleri: fixture, parametrize, marker. — Test yazmanın araçları.
- `pytest-asyncio`. — Async test fonksiyonları için.
- FastAPI `TestClient` (HTTP) ve `WebSocketTestSession` (WS test API'sı). — Endpoint test etmek için.
- Mock ile fake provider injection. — Gerçek Gemini çağırmadan unit test.
- Test piramidi (unit ≫ integration > e2e). — Hangi test ne kadar yazılır.

**Production backend**
- Liveness vs readiness probe ayrımı. — Sadece "/health" değil; iki kavram var.
- Graceful shutdown: SIGTERM sinyalini yakalayıp lifespan shutdown'ı tetikleme. — Container ortamı için kritik.
- Dependency pinning (`requirements.txt` `==`, veya `pyproject.toml` ile uv/poetry). — Reproducible build.

**Gözlemlenebilirlik / observability**
- Metrics: counter, gauge, histogram farkı. — Hangi olay hangi tipte ölçülür.
- Prometheus client (opsiyonel, ileri). — Endpoint'ten metric expose.
- OpenTelemetry tracing (kavramsal, implementasyon değil). — İleride entegrasyon için zemin.

**WebSocket**
- Heartbeat (ping/pong) deseni. — Half-open connection tespiti.
- ConnectionManager pattern. — Aktif bağlantı havuzu, broadcast, hedefli mesaj.

### F. Okumam gereken resmi dokümantasyonlar

- **FastAPI dokümantasyonu**
  - "Testing" → tüm sayfa
  - "Testing WebSockets" → ayrı alt başlık
  - "Lifespan Events" → graceful shutdown akışı (D5'ten devam)

- **Starlette dokümantasyonu**
  - "TestClient" → WebSocket test session API

- **pytest dokümantasyonu**
  - "Getting started"
  - "How to use fixtures"
  - **pytest-asyncio** ayrı paket → README

- **Python `asyncio` dokümantasyonu**
  - "Coroutines and Tasks" → tasks, cancellation (D5'te dokunduğun konu burada perçinlenir)

- **Prometheus / OpenTelemetry**
  - Prometheus "metric types" sayfası (kavramsal okuma; entegrasyon opsiyonel)
  - OpenTelemetry "concepts" → "tracing", "spans" (sadece kavramsal)

- **12-factor**
  - "IX. Disposability" → graceful shutdown (D5'ten devam, derinlik)

- **uvicorn dokümantasyonu**
  - "Settings" → workers, timeout, graceful shutdown ayarları
  - WebSocket keepalive / ping interval ayarları

### G. Dokümantasyon okurken cevaplamam gereken odak soruları

1. FastAPI `TestClient` ile WebSocket testi nasıl yazılır? `websocket_connect` context manager'ı ne kadar gerçekçi simulasyon sağlar?
2. Unit test ile entegrasyon testi arasındaki sınır bu projede nereden geçer? `ChatService`'i `FakeProvider` ile test etmek unit mi, integration mı?
3. `pytest-asyncio` ile fixture'lar nasıl async olur? Event loop scope'u (function/session) ne fark eder?
4. Liveness probe ne testler, readiness probe ne testler? Bu projede `/health` endpoint'i hangisini kapsamalı?
5. SIGTERM ile SIGKILL arasındaki fark uvicorn için pratik olarak ne demek? Graceful timeout kaç saniye olmalı?
6. WebSocket heartbeat'i kim göndermeli — sunucu mu, istemci mi, ikisi de mi? RFC 6455'in tavsiyesi nedir?
7. Counter, gauge, histogram arasındaki farkı bu projedeki şu olaylar için ne seçerdin: (a) aktif bağlantı sayısı, (b) toplam gelen mesaj sayısı, (c) stream süresi, (d) Gemini hata sayısı.
8. **(Projeme özel)** `ChatService`'i test ederken history pencerelemesi gibi davranışlar nasıl test edilir? "20 mesajdan sonra eski mesajlar düşmeli" testini yazmak için fixture'da neler hazırlanır?
9. **(Projeme özel)** Graceful shutdown'da açık WS bağlantılarına ne yapmalı — `close(code=1001)` ile uyararak mı kapatmalı (going away), yoksa lifespan zaten uvicorn'u beklerken bağlantılar kendi düşer mi?
10. Bağımlılıkları `==` ile pinleyip mi tutmalı, `~=` ile minor güncellemelere açık mı bırakmalı? Bu projedeki SDK sürüm hassasiyeti (raporun 7.8'i) için hangisi doğru?
11. **(Karşılaştırma)** Sadece e2e (TestClient ile WS) test mi yazmalı, yoksa `ChatService` için ayrı unit test de mi? Bu boyuttaki proje için ROI dengesi nerede?
12. ConnectionManager kuracaksan, hangi veri yapısı uygun (`dict[conn_id, websocket]` mı `set[websocket]` mi)? Hangi operasyonların hızlı olması gerek?

### H. Öğrenme notlarımı hangi formatta çıkarmalıyım?

| Alan | İçerik |
|---|---|
| Kavram | … |
| Kendi cümlemle açıklama | … |
| Bu projedeki karşılığı | … |
| Üretebileceğim gözlem | Bu eklendiğinde ne soruyu cevaplayabilirim |
| Maliyeti / efor | Eklemenin getirdiği maintenance yükü |
| Açık kalan sorum | … |

Ek alan: **"Test envanteri"** — yazdığın her test için: ne test ediyor, fake mi gerçek mi kullanıyor, ne kadar sürede çalışıyor.

### I. Kodda benim kendim uygulamam gereken iyileştirme görevleri

1. **`requirements.txt` veya `pyproject.toml` ile bağımlılıkları pinle.** En azından `fastapi`, `uvicorn`, `google-genai`, `pydantic`, `pydantic-settings`, `python-dotenv`, `jinja2` versiyonları sabitlensin. SDK için raporun 7.8'i gereği özel dikkat. Görev: *[Bölüm 3.8] Dependency dosyası eksik.*

2. **Health endpoint ekle.** `/health` (liveness) ve isteğe bağlı `/ready` (readiness — Gemini client init olmuş mu?). Görev: *[Risk Tablosu] Health endpoint yok.*

3. **`ChatService` için unit test yaz.** `FakeProvider` ile en az şu davranışlar test edilsin:
   - History pencerelemesi (D4'ün davranışı).
   - Rate limit (D3'ün davranışı — eğer ChatService'e taşıdıysan).
   Görev: *[Bölüm 3.8] Test yok.*

4. **WS endpoint için en az 1 entegrasyon testi yaz.** FastAPI `TestClient` `websocket_connect` ile happy path: bağlan, mesaj yolla, chunk al, done al. Görev: aynı.

5. **Auth fail için 1 negative test yaz.** Yanlış token ile bağlanmaya çalış; reject edildiğini doğrula.

6. **ConnectionManager ekle** (basit haliyle). Aktif WS bağlantılarını tutsun; bir gauge metric için kaynak olsun. Lifespan shutdown'da bu manager üzerinden tüm bağlantılara `close(code=1001)` gönder. Görev: *[Risk Tablosu] Graceful shutdown + Bölüm 6.5 ConnectionManager yok.*

7. **Basit metric kaydı.** Tam Prometheus integration zorunlu değil; ilk adımda log üzerinden bile sayılabilir ("dakikada X mesaj"). İlerde gerçek Prometheus eklenebilir. Görev: *[Risk Tablosu] Metrics yok.*

8. **Heartbeat / ping-pong düşüncesi.** uvicorn default ping interval'ı zaten var; bunu config ile ayarla veya kabul et — kararını gerekçele. Aktif olarak kendin app seviyesinde ping yollamayı bilinçli olarak şu an yapma; uvicorn seviyesinin yeterli olduğuna dair gözlemini doğrula. Görev: *[MEDIUM] Heartbeat / zombie connection.*

9. **README'ye mimari kararlar bölümü.** Her döngüde aldığın kararlar (close code seçimi, rate limit algoritması, history pencereleme yaklaşımı vs) kısa kısa yazılı olsun. Görev: *[Bölüm 3.8] README'de mimari belgeleme yok.*

10. **(Bilinçli erteleme)** Dockerfile, reverse proxy notları, OpenTelemetry tam entegrasyonu bu turun dışında. Bunlar production deploy adımına bağlı; yol haritasının "ikinci turu"nun konusu.

### J. Bu döngü tamamlandı mı, nasıl anlayacağım?

**Tamamlanma kriterleri:**
- [ ] `pytest` çalışıyor ve en az 4-5 test geçiyor.
- [ ] Testlerin en az biri WS, biri ChatService, biri auth fail.
- [ ] `/health` endpoint'i 200 OK dönüyor.
- [ ] Aktif bağlantı sayısı bir yerden gözlemlenebilir.
- [ ] Uygulamayı SIGTERM ile kapattığında bağlı WS istemcileri 1001 alıyor.
- [ ] `requirements.txt` (veya eşdeğeri) pinli.
- [ ] README'de mimari kararlar var.

**Manuel test senaryoları:**

1. **Test suite koşumu:** `pytest` → tüm testler geçer.
2. **Health endpoint smoke test:** `curl http://localhost:8000/health` → 200.
3. **Graceful shutdown:** İki tarayıcıda WS bağla, sonra sunucuya SIGTERM gönder (Ctrl+C). İki tarayıcı da close frame almalı (kod 1001 / "going away"). Loglarda "shutdown başladı → tüm bağlantılar bilgilendirildi → kapatıldı" akışı.
4. **Connection sayacı:** İki tarayıcı bağla; metric/log "active=2" göstermeli. Birini kapat; "active=1" e dönmeli.
5. **Dependency reproducibility:** `pip install -r requirements.txt` ile temiz bir venv'de çalıştır; aynı davranış.

**Beklenen gözlemler:**
- Test failure'lar gerçek bug yakalıyor (deneyerek: bir davranışı bilinçli boz, testin yakaladığını gör).
- Health endpoint ekstra bir state state göstermiyor — sadece "ayakta mıyım".
- Shutdown loglarda gürültü değil, akıcı.

**Olmaması gereken durumlar:**
- Testlerin gerçek Gemini API'sini çağırması (faturalama).
- Health endpoint'in DB / external service kontrolü gibi pahalı işler yapması.
- Shutdown'ın bağlantı kopararak zorla kapatması (graceful değil).
- Pin'siz bağımlılıklar → "geliştirme makinemde çalışıyor" sorunu.

### K. Döngü sonunda bana neyle dönmelisin?

1. Yazdığın testlerin listesi ve her birinin ne test ettiği.
2. Bilinçli bozma deneyin: bir davranışı bozdun mu, test yakaladı mı?
3. Health endpoint'in stratejisi (sadece liveness mi, readiness de var mı, gerekçe).
4. Graceful shutdown gözlemin: SIGTERM sonrası akışın ne olduğu.
5. ConnectionManager'ın temel tasarımı (veri yapısı, ne operasyon destekliyor).
6. Metric stratejin (log mu, Prometheus mu, neden).
7. README'ndeki mimari kararlar bölümünün başlıkları.
8. Açık kalan sorular — özellikle "OpenTelemetry'i ne zaman eklerim" gibi ileri konular.

---

## 5. Özel Bölümler

### 5.1. Genel Öğrenme Stratejisi

**Yaklaşım felsefesi:** "Önce sağlam temel, sonra özellik." Bu projede klasik "önce çalışsın sonra güzelleşsin" tuzağına düşmemek kritik, çünkü çalışan ama yanlış davranan bir backend zararlı olabilir (özellikle LLM faturası). Lifecycle ve hata yönetimi (D1) ile başlamak, sonraki her şeyin altyapısı olduğu için doğru karardır.

**Sıralama mantığı:**
- **D1-D2 (lifecycle + altyapı)** seri olmak zorunda. Bu ikisi olmadan sonrası kör.
- **D3 (güvenlik)** D1-D2'nin üstüne kurulmalı; ama D3'ün üç alt başlığı (auth, rate limit, generation config) **kendi içinde paralel** çalışılabilir.
- **D4 (protokol + context)** D3'le kısmen paralel ilerleyebilir, ama envelope'u tasarlamadan rate limit hata mesajlarını "geçici düz text" olarak gönderdiğin için bağımlı bir sıra var.
- **D5 (refactor)** kesinlikle D1-D4'ün sonrasına bekler. Refactor + davranış değişikliği aynı anda yapılırsa hata kaynağı bulmak imkansızlaşır.
- **D6 (test + observability)** D5 olmadan unit test yazılamaz; bağımlı.

**Tuzaklar:**

1. **Premature abstraction.** D5'i çok erken yapma cazibesi yüksek — "şimdi interface çıkarayım" demek isteyebilirsin. Davranışı doğru kurmadan soyutlama, yanlış soyutlamayı kalıcılaştırır.

2. **Kargo kült refactor.** Raporda gördüğün önerilen dosya yapısını birebir kopyalama. Önce *neden* o bölünmeye ihtiyacın olduğunu içselleştir; sonra kendi bölünmeni yap. "FastAPI tutorial'ında böyleydi" iyi bir gerekçe değil.

3. **Kuyruğa giren karmaşıklık.** Her döngüde "bir küçük bonus daha eklesem" cazibesi var. Mesela D3'te auth eklerken JWT'ye atlamak gibi. Cazibeye direnmek için: her döngünün **bilinçli erteleme** listesi var; oraya yaz, sonraya bırak.

4. **Test of the test.** D6'da çok kapsamlı test yazma cazibesi. ROI düşük testlerden kaçın — gerçek bir bug yakalayabilecek minimum sayıda test daha değerli.

5. **Logging gözüne kestirme.** D2 → `print('x')` yerine `logger.info('x')` koyup "tamam structured oldu" deme. Structured = aranabilir alanlar (`extra={"conn_id": ...}`). Bunun farkını gözden kaçırma.

6. **"AI yazsın da gözden geçireyim" tuzağı.** Bu projenin asıl değeri AI'a kod yazdırmadan kurgulaman. Bir an "şu küçük helper'ı AI'a yazdırsam" demek isteyebilirsin — yazdırma. Yazdırılan kodun arkasındaki kararları sen vermezsen, projenin sana kazandıracağı sezgiyi kaybedersin.

**Paralel-seri karışımı:**

```
D1 ──► D2 ──► D3 (auth ║ rate-limit ║ generation-config) ──► D4 ──► D5 ──► D6
                       └─────── paralel ────────┘
```

D3'ün üç alt görevini eş zamanlı çalışabilirsin; geri kalan sıralama bağımlıdır.

**Ne ertelemeli?** Aşağıdaki 5.3'te detaylı; ama özet: persistent storage, JWT, Prometheus tam entegrasyonu, Dockerfile, OpenTelemetry, multi-cihaz oturum. Bunlar bu turun dışında.

---

### 5.2. Review Bulgularının Yeniden Haritalanması

Aşağıdaki tablo raporun **her** bulgusunu içeriyor. Hiçbir bulgu kaybolmadığını teyit et.

| Review Bulgusu | Öncelik | Hangi Döngüde Ele Alınacak? | Neden Bu Döngüde? | Ertelenecekse Sebep |
|---|---|---|---|---|
| `/ws` anonim erişime açık (5.1, 5.8) | CRITICAL | D3 | Auth lifecycle (D1) ve audit log (D2) ön koşul; ondan sonra gelmeli | — |
| Rate limit yok (5.2) | CRITICAL | D3 | Aynı şekilde D1-D2'nin üstüne kurulur | — |
| `max_output_tokens` ve generation config yok (5.4, 7.5, 7.7) | CRITICAL | D3 (temel) + D4 (rafine) | Maliyet kontrolü güvenlikle birlikte ele alınmalı | — |
| Ham exception kullanıcıya gönderiliyor (5.6, 8.5) | HIGH | D1 | Lifecycle ile birlikte — try/except yapısı zaten dokunuluyor | — |
| `WebSocketDisconnect` yakalanmıyor (6.2) | HIGH | D1 | Lifecycle'ın merkezi | — |
| Chat history sınırsız büyüme (7.2) | HIGH | D4 | Generation config'in (D3) doğal devamı | — |
| Input validation yok (5.3) | HIGH | D3 | Güvenlik bloğunun parçası | — |
| API key fail-fast yok (5.5) | HIGH | D2 | Config katmanının doğrudan parçası | — |
| `print` ile logging (3.3, 8.3) | HIGH | D2 | Tüm gözlemlenebilirlik buna dayanıyor | — |
| Pydantic Settings kullanılmamış (3.2) | HIGH | D2 | Config katmanı | — |
| User ↔ developer log ayrımı (8.2) | HIGH | D2 (correlation ID kısmı) + D1 (kullanıcı mesajı kısmı) | İki döngüye bölünmüş bir kavram | — |
| `chunk.text` None olabilir (7.4) | MEDIUM | D1 | Defensive handling lifecycle ile birlikte | — |
| Origin / CORS kontrolü (5.7) | MEDIUM (auth eklenince HIGH) | D3 | Auth'la birlikte konuşulur | — |
| Gemini çağrısına timeout yok (7.3) | MEDIUM | D4 | Timeout + lifecycle entegrasyonu | — |
| Graceful close ve close code yok (6.7) | MEDIUM | D1 | Lifecycle'ın parçası | — |
| Mesaj protokolü düz text (3.5, 3.7) | MEDIUM | D4 | Protokol blokunun kalbi | — |
| Stream sonu sinyali yok (3.5) | MEDIUM | D4 | Aynı blok | — |
| LLM soyutlaması yok (7.6) | MEDIUM | D5 | Önce davranışı doğru kur, sonra soyutla | — |
| Stream sırasında disconnect (6.3) | MEDIUM | D1 (temel) + D4 (timeout açısından) | Lifecycle'ın incelikli kısmı | — |
| Zombie connection / heartbeat (6.4) | MEDIUM | D6 | uvicorn ayarı yeterli olabilir; observability ile beraber | — |
| ConnectionManager yok (6.5) | MEDIUM | D6 | Graceful shutdown + metrics ile birlikte | — |
| Chat history persistence (6.6, 7.1) | MEDIUM (öğrenme için LOW) | **Ertelendi** | — | Redis/SQLite eklemek bu turun kapsamı dışı; ikinci tur konusu |
| System instruction yok (7.7) | MEDIUM | D3 (config'in parçası) | Generation config'le birlikte | — |
| SDK sürüm pinleme (7.8) | MEDIUM | D6 | Dependency yönetimiyle birlikte | — |
| Kullanılmayan import (3.1, 9.4) | LOW | D5 | Refactor sırasında temizlik | — |
| `read_item`, `item.html` isimleri (9.3) | LOW | D5 | Dosya bölünmesi sırasında | — |
| Type hints / docstring (3.1, 9.3) | LOW | D5 (refactor sırasında ekleyebilirsin) + D6 (README) | İlerleyici olarak | — |
| Magic string (model adı, template adı) (3.1) | LOW | D2 (model) + D5 (template) | Config + refactor | — |
| Tek dosya yapısı (1.1, 1.2, 9.1, 9.2) | İlerideki büyüme için açık | D5 | Refactor'un ana hedefi | — |
| Test yok (3.8) | %100 eksik | D6 | Soyutlama (D5) gerekli | — |
| Health endpoint, metrics, tracing (3.8) | %100 eksik | D6 (health + basit metric); tracing **ertelendi** | — | Tracing OpenTelemetry tam entegrasyon ikinci tur konusu |
| Dockerfile/deployment (3.8) | — | **Ertelendi** | — | Deploy adımı; öğrenme turunun dışı |
| Dependency dosyası (3.8) | — | D6 | Pinleme için | — |
| README'de mimari kararlar (3.8) | — | D6 (her döngüde notlar toplanır, D6'da konsolide edilir) | — | — |
| Graceful shutdown (Risk Tablosu) | %100 eksik | D5 (lifespan temeli) + D6 (ConnectionManager ile uygulama) | Bağımlı zincir | — |
| `accept` başarısızlığı gözlemlenebilir değil (6.1) | LOW | D2 (logging eklenince dolaylı çözülür) | — | — |
| `e`, `e1` isimlendirme (9.3) | LOW | D5 | Refactor sırasında | — |

**Toplam bulgu sayısı:** 35+ adet bulgunun her biri ya bir döngüye atandı ya da bilinçli olarak ertelendi (4 erteleme: persistent storage, JWT, Prometheus/OTel tam entegrasyon, Dockerfile).

---

### 5.3. Şimdilik Ertelenecek Konular

| Konu | Neden ertelendi | Hangi noktada gündeme alınmalı | Bilmen gereken risk |
|---|---|---|---|
| **Chat history persistence (Redis/SQLite)** | Storage soyutlaması D5'in katmanlaması yapılmadan anlamsız; ayrıca bu projenin asıl odağı değil. | Kullanıcılarla sahada test ediliyorsa, "reconnect'te geçmiş gitti" şikayeti gelirse. | Şu an reconnect'te tüm history kaybolur. UX kötü ama veri kaybı yok (zaten tutulmuyor). |
| **JWT / refresh token / kullanıcı sistemi** | Statik token mekanizması (D3) öğrenme için yeterli; JWT eklemek kavramsal yükü iki katına çıkarır. | Birden fazla kullanıcı tanımak gerektiğinde, ya da audit'te "kim ne yaptı" sorusu doğduğunda. | Statik token kaybolursa tüm sistem etkilenir; rotasyon manuel. |
| **Prometheus / OpenTelemetry tam entegrasyon** | Log-based counter'lar D6'da yeterli görünürlük verir. Tam entegrasyon ayrı bir öğrenme alanı. | Birden fazla servis çalışmaya başladığında ya da SLO/SLI takibine geçildiğinde. | Şu an sadece log üzerinden gözlem var; rate-of-change grafiği yok. |
| **Dockerfile + reverse proxy + production deploy** | Öğrenme turunun kapsamı uygulama içi; container'lama ve nginx ayrı bir tur. | Projeyi gerçekten bir VPS'e veya cloud'a koymaya hazır olduğunda. | Şu an deploy edilemez; sadece lokalde çalışıyor. |
| **Summarization-tabanlı history pencereleme** | Sliding window (D4) ilk adım için yeterli ve öğretici; summarization yan etkili (özet de model çağrısı). | Konuşmaların uzun olduğu durumlarda kullanıcı "uzaktaki bağlamı kaybediyor" şikayeti yapınca. | Pencere dışı bağlam kaybolur; kullanıcı için fark edilebilir. |
| **Retry / circuit breaker** | Timeout (D4) temeli kurar; retry ayrı bir desen ve trade-off'ları var (idempotency vs maliyet). | Gemini'den geçici hatalar artmaya başladığında. | Geçici network hatasında stream kopar; kullanıcının yeniden denemesi gerek. |
| **Multi-device session** | Persistence olmadan zaten yapılamaz. | Persistence eklendikten sonra. | Kullanıcı iki sekmede aynı sohbeti açamaz. |
| **Token-başına gerçek bütçeleme** | `max_output_tokens` (D3) ilk savunma; gerçek per-user budget storage gerektirir. | Faturayı kullanıcıya bölmek gerektiğinde. | Bir kullanıcı diğerinden daha fazla token harcayabilir; izleyemezsin. |

---

### 5.4. İlk Çalışma Oturumunun Net Görevi

**Başlangıç noktası:** Döngü 1.

**İlk oturumda okuyacağın 4 resmi dokümantasyon başlığı (tam adlarıyla):**

1. **FastAPI dokümantasyonu →** "Advanced User Guide" → "WebSockets" sayfasının tamamı, özellikle "Handling disconnections and multiple clients" alt bölümü.
2. **Starlette dokümantasyonu →** WebSockets bölümü, özellikle `WebSocket` sınıfı referansı ve `WebSocketDisconnect` exception.
3. **MDN WebSocket API →** "CloseEvent" sayfası, "Status codes" tablosu.
4. **Python `asyncio` dokümantasyonu →** "Coroutines and Tasks" sayfasında "Task Cancellation" alt başlığı.

**İlk oturumda çıkarman gereken ilk notlar (hangi kavramlar üstüne):**

- `WebSocketDisconnect` ne zaman fırlar, ne ifade eder.
- Close codes: 1000, 1001, 1008, 1011, 4000-4999 — her birinin somut anlamı + bu projem için hangi senaryoda hangisi.
- `try / except / finally` davranışı — özellikle `finally` async fonksiyonda nasıl çalışır.
- "Kullanıcıya ne kadar bilgi göstermek meşru?" sorusuna kendi cümlenle yanıt.

**İlk oturum sonunda ne üretmiş olman gerekir:**

- Bir not dosyası (markdown önerilir): yukarıdaki kavramlar tablo formatında doldurulmuş.
- **Henüz kod değişikliği yok.** İlk oturum *anlama* oturumu; ikinci oturum *değiştirme* oturumu.
- Bir karar listesi: "Beklenmedik exception'da close code 1011 mi kullanacağım, custom 4xxx mi?", "WebSocketDisconnect olduğunda send_text denemeyeceğim — bu kararın gerekçesi ne?"

**İlk oturumda henüz dokunmaman gereken konular:**

- Auth, rate limit, generation config (D3 konusu).
- Logging refactor (D2 konusu).
- Dosya bölünmesi (D5 konusu).
- Test yazımı (D6 konusu).
- Mesaj envelope (D4 konusu).

**Niye bu kadar dar?** Çünkü scope creep en büyük öğrenme düşmanı. İlk oturumda sadece "WebSocket lifecycle'ı doğru anladım mı?" sorusunu net cevaplamak yeterli. Geri kalan otomatik gelir.

---

### 5.5. Bu Sürecin Sonunda Elde Etmen Gereken Yetkinlikler

**FastAPI becerisi**
- Bir FastAPI uygulamasını router'lara, service'lere, schema'lara, config'e ve logging'e ayırarak modüler bir yapı kurabilmek.
- `Depends` ile dependency injection patternini hem HTTP hem WebSocket endpoint'lerinde uygulayabilmek.
- `lifespan` async context manager ile uygulama başlangıcı/kapanışında kaynak yönetimi yapabilmek.
- WebSocket endpoint'inde auth dependency'sini handshake öncesi düzgün konumlandırmak.

**WebSocket becerisi**
- Bir WebSocket endpoint'inde lifecycle olaylarını (`accept` → mesaj döngüsü → `disconnect` → `close`) yanlış yorumlamadan handle etmek.
- Hangi close code'un hangi senaryoda kullanılması gerektiğine kendi başına karar verebilmek.
- Stream sırasındaki disconnect'i, normal disconnect'ten ve beklenmedik exception'dan ayırt etmek.
- Frontend ile yapılandırılmış (JSON envelope) mesaj sözleşmesi tasarlayabilmek.

**Async Python sezgisi**
- `WebSocketDisconnect`, `CancelledError`, `TimeoutError` arasındaki davranış farkını ayırt etmek.
- `asyncio.wait_for` ile timeout uygulamak, timeout sonrası lifecycle'ı doğru yönetmek.
- Async generator'ı erken çıkışta düzgün temizlemek (`finally`, `aclose`).
- "Tek event loop, çok bağlantı" zihinsel modelini kullanabilmek.

**Güvenlik bakışı**
- Bir endpoint'in attack surface'ini (anonim erişim, rate limit, input validation, origin) sistematik bir checklist olarak değerlendirebilmek.
- "Bu mesaj kullanıcıya bilgi sızdırır mı?" sorusunu refleks haline getirmek.
- Auth fail durumunda hangi close code, hangi log seviyesi, kullanıcıya hangi mesaj — bu üçünü ayrı düşünebilmek.
- CSWSH gibi WebSocket'e özgü saldırıların farkında olmak ve origin kontrolünün rolünü kavramak.

**LLM maliyet ve davranış kontrolü**
- `max_output_tokens`, `temperature`, `system_instruction`, `safety_settings` arasındaki rolleri ayırabilmek.
- Chat history büyümesinin maliyet üzerindeki kümülatif etkisini hesaplayabilmek ve pencereleme stratejisi seçebilmek.
- Streaming bir LLM çağrısının timeout, disconnect ve cancellation senaryolarında nasıl davrandığını tahmin edebilmek.
- LLM çağrısını bir provider interface'in arkasına alarak vendor lock-in'i azaltabilmek.

**Production backend düşüncesi**
- 12-factor prensiplerinin (özellikle config, logs, disposability) bu projedeki somut karşılıklarını gösterebilmek.
- Liveness vs readiness probe ayrımını yapabilmek; bir `/health` endpoint'inin neye dokunması gerektiğine karar verebilmek.
- Graceful shutdown senaryosunu uygulayabilmek: SIGTERM → lifespan shutdown → bağlı kullanıcılara 1001 → temiz çıkış.
- Dependency pinning'in neden gerektiğini ve bu projedeki SDK sürümü gibi hassasiyetlere nasıl uygulanması gerektiğini açıklayabilmek.

**Gözlemlenebilirlik refleksleri**
- `print` yerine seviyeli logging kullanmak, her log satırına yapılandırılmış bağlam (correlation ID, conn_id) eklemek.
- Bir olay olduğunda "bu log satırından sonra olayı yeniden inşa edebilir miyim?" sorusunu sormak.
- Hangi olayın counter, hangisinin gauge, hangisinin histogram olduğunu seçebilmek.
- Kullanıcıya gösterilen hata mesajı ile developer log'unun bilinçli ayrımını yapabilmek.

**Kod organizasyonu ve bakım disiplini**
- Bir refactor'u küçük adımlara bölüp her adımda manuel test'le doğrulamak — refactor sırasında davranış değiştirmeme disiplini.
- Interface'i implementasyondan önce ne kadar düşüneceğine karar verebilmek (premature abstraction'a düşmeden).
- "Bu özelliği şimdi mi eklerim, sonra mı?" sorusunu trade-off analiziyle cevaplamak; bilinçli erteleme yapabilmek.
- Kod kalitesi (isim, type hint, docstring) ile mimari kalite (katmanlama, soyutlama) arasındaki farkı görmek; ikisini ayrı zamanlamalarla iyileştirebilmek.

---

## Son Söz

Bu yol haritası altı döngü boyunca yaklaşık 35 review bulgusunu öğrenme bloklarına dağıttı. Hiçbir bulgu kaybolmadı; bilinçli ertelenenler de açıkça işaretlendi.

Sana balık tutmadım; oltayı doğru sallamayı planlamana yardım ettim. Her döngüde sen okuyacaksın, sen düşüneceksin, sen kodlayacaksın. Ben her döngünün sonunda K bölümünde belirtilen çıktılarla geldiğinde reviewer moduna geçeceğim: doğru anlamış mısın, doğru uygulamış mısın, bir yerde kavramsal boşluk var mı, ileride sorun çıkaracak bir tercih yapmış mısın — bunları değerlendireceğim.

İlk hareketin Bölüm 5.4'te: Döngü 1, dokümantasyon okuma oturumu, henüz kod yok. Bir not dosyası ve karar listesiyle geri döndüğünde başlarız.

Hazır olduğunda haber ver.