# Kod Rehberi — Neyin Neden Yazıldığı

Bu dosya, projenin her parçasını "ne için var / nasıl çalışır / neden böyle yazıldı / AI mühendisliği açısından dersi" şeklinde anlatır. Amaç: kodu ezberlemek değil, **kararların arkasındaki mantığı** kavramak.

> Nasıl kullan: Her oturumda **tek bir dosyayı** al, bu rehberdeki bölümünü oku, sonra gerçek dosyayı PyCharm'da yanına aç ve satırları eşleştir. Takıldığın yere breakpoint koyup debug et.

---

## 0. Büyük resim (önce bu otursun)

Bir kullanıcı mesajının yolculuğu:

```
Tarayıcı (chat.html)
   → ws.py        : origin + token kontrolü, accept, doğrulama, rate limit
   → chat_service : son N turn'ü seç (pencereleme), provider'ı çağır
   → llm_provider : history + yeni mesaj → Gemini'ye gönder, parça parça yanıt
   → Gemini API
   ← chunk chunk geri akar → ws.py kullanıcıya yollar
   ← chat_service : turn'ü history'e ekler
```

Katmanlama mantığı: **her dosyanın tek bir sorumluluğu var.** Bu, AI ürünlerinde kritik — model değişir, sağlayıcı değişir, protokol değişir; iyi katmanlama bu değişiklikleri tek bir dosyaya hapseder.

---

## 1. `app/config.py` — Ayarların tek kaynağı

**Ne için var:** API anahtarı, model adı, token, izinli origin'ler gibi tüm ayarları tek yerden, doğrulanmış şekilde okur.

**Nasıl çalışır:** `pydantic-settings` kütüphanesi `.env` dosyasını ve ortam değişkenlerini okuyup bir `Settings` nesnesine çevirir. `@field_validator`'lar değerleri **uygulama açılırken** doğrular (boş API key → açılışta hata).

**Neden böyle:**
- Ayarları koda gömmek (hardcode) yerine dışarıdan almak → aynı kod hem local hem production'da çalışır (12-factor "config" prensibi).
- `settings` modül seviyesinde bir kez oluşturulur → tek kaynak (singleton). Test ederken bu "tuzak" oluyordu: `monkeypatch.setenv` çalışmaz, `setattr(settings, ...)` gerekir.

**AI mühendisliği dersi:** API anahtarları, model isimleri, sıcaklık (temperature) gibi parametreler **asla koda gömülmez** — config'den gelir. Bir modeli diğeriyle değiştirmek tek satır env değişikliği olmalı.

---

## 2. `app/logging_config.py` — Gözlemlenebilirliğin temeli

**Ne için var:** Log formatını kurar ve her log satırına bağlantı kimliği (`connection_id`) ekleyen bir adaptör sağlar.

**Nasıl çalışır:** `setup_logging()` log seviyesini ve formatını ayarlar. `ConnectionLoggerAdapter` her mesajın başına `connection_id` ekler → hangi logun hangi kullanıcıya ait olduğunu görebilirsin.

**Neden böyle:** `print()` ile log atmak production'da işe yaramaz. Aranabilir, seviyelendirilmiş (INFO/WARNING/ERROR), bağlam içeren loglar gerekir.

**AI mühendisliği dersi:** LLM uygulamalarında "neden bu yanıt geldi", "hangi istek pahalıydı", "nerede takıldı" sorularını ancak iyi loglarla cevaplarsın. Gözlemlenebilirlik sonradan eklenen değil, baştan kurulan bir şeydir.

---

## 3. `app/schemas/messages.py` — Mesaj sözleşmesi (contract)

**Ne için var:** Sunucu ile tarayıcı arasında gidip gelen mesajların **tipini** tanımlar: `chunk`, `done`, `error`, `system`, `user_message`.

**Nasıl çalışır:** Her mesaj tipi bir Pydantic `BaseModel`. `type` alanı `Literal` ile sabitlenmiş → yanlış tip gönderilirse Pydantic reddeder.

**Neden böyle:** Frontend ve backend'in aynı dili konuşması için net bir sözleşme şart. `user_message` gelen veriyi **doğrular** (şema dışı veri reddedilir); diğerleri giden veriyi **biçimlendirir**.

**AI mühendisliği dersi:** Streaming LLM yanıtlarında "bu bir parça mı (chunk), bitti mi (done), hata mı (error)" ayrımı kritik. Frontend'in "yazıyor..." göstergesini kapatması için `done` sinyalini bilmesi gerekir. Tip güvenliği = daha az bug.

---

## 4. `app/services/llm_provider.py` — LLM soyutlaması (en önemli AI parçası)

**Ne için var:** Gemini'yi (veya gelecekte başka bir modeli) tek bir arayüz arkasına koyar.

**Nasıl çalışır:**
- `LLMProvider` bir `Protocol` (arayüz): "bir LLM sağlayıcısı `stream(message, history)` metoduna sahip olmalı" der.
- `GeminiProvider` bu arayüzü Gemini SDK'sıyla gerçekler: history + yeni mesajı `types.Content` listesine çevirir, `generate_content_stream` ile parça parça yanıt alır, her parçayı `yield` eder.

**Neden böyle:**
- **Vendor lock-in'i azaltır:** Yarın Gemini yerine başka model gelirse, sadece yeni bir `XProvider` yazarsın; geri kalan kod hiç değişmez.
- **Test edilebilirlik:** Testlerde gerçek Gemini yerine `FakeProvider` koyabiliyoruz (faturasız, hızlı). Bu, `Protocol` sayesinde mümkün.

**AI mühendisliği dersi:** Bu, AI backend'lerinin **en kritik desenlerinden biri.** Gerçek şirketlerde modeller sürekli değişir (maliyet, performans, yeni sürüm). LLM çağrısını bir arayüz arkasına almak, sistemini modele bağımlı olmaktan kurtarır. `yield`/streaming ise LLM ürünlerinin olmazsa olmazı — kullanıcı 10 saniye boş ekrana bakmasın, kelime kelime görsün.

---

## 5. `app/services/chat_service.py` — İş mantığı (history + maliyet + rate limit)

**Ne için var:** Bir bağlantının sohbet mantığını yönetir: geçmişi tutar, modele kaç turn gönderileceğine karar verir, hız sınırını uygular.

**Nasıl çalışır:**
- `_windowed_history()`: geçmişin **son N turn'ünü** keser (`history[-(N*2):]`). 1 turn = 1 user + 1 model = 2 `Content`.
- `stream_response()`: pencerelenmiş geçmiş + yeni mesajı provider'a verir, yanıtı `yield` eder, sonra hem soruyu hem cevabı geçmişe ekler.
- `check_rate_limit()`: kayan pencere (sliding window) — son 10 saniyede 5'ten fazla mesaj varsa reddeder. `time.monotonic()` kullanır (sistem saati değişse bile bozulmaz).

**Neden böyle:**
- **Maliyet kontrolü:** LLM'e her seferinde tüm geçmişi göndermek token maliyetini sınırsız büyütür. Pencereleme bunu sabit tutar — bu projenin en önemli para-tasarrufu kararı.
- **State bağlantıya ait:** `_history` ve `_timestamps` her bağlantı için ayrı. Bu yüzden `ChatService` her bağlantıda yeniden oluşturulur (paylaşılmaz).

**AI mühendisliği dersi:** "Context window" yönetimi AI mühendisliğinin kalbidir. Modele ne kadar geçmiş göndereceğin = maliyet × kalite dengesi. Pencereleme en basit strateji; ileride "özetleme" (summarization), "önemli mesajları seçme" gibi stratejiler gelir. Bu dosya o kapının anahtarı.

---

## 6. `app/services/connection_manager.py` — Aktif bağlantı takibi + metrikler

**Ne için var:** O an açık olan tüm WebSocket bağlantılarını izler; metrik (aktif sayı, toplam mesaj) ve düzgün kapanış (graceful shutdown) için kaynak sağlar.

**Nasıl çalışır:** Bir `dict[connection_id, websocket]` tutar. `register`/`unregister` ile bağlantı ekler/çıkarır. `active_count` (gauge) ve `total_messages` (counter) metrikleri. `close_all(1001)` tüm bağlantılara "gidiyorum" sinyali yollar.

**Neden böyle:** "Kaç kişi bağlı?", "kaç mesaj işlendi?" sorularını cevaplayabilmek için birinin bağlantıları sayması gerekir. Tek bir merkezi yer = `ConnectionManager`.

**AI mühendisliği dersi:** Metrik tipleri (counter = hep artan toplam, gauge = anlık değer) gözlemlenebilirliğin ABC'si. Üretimde "kaç eşzamanlı kullanıcı", "saniyede kaç istek" gibi metrikler kapasite planlaması ve maliyet için şarttır.

---

## 7. `app/routers/web.py` — HTTP uçları

**Ne için var:** Üç HTTP ucu: `/` (sohbet sayfası), `/health` (ayakta mıyım?), `/metrics` (sayılar).

**Nasıl çalışır:** `APIRouter` ile route'ları gruplar. `/health` Gemini client hazır mı diye bakar (hazırsa 200, değilse 503). `/metrics` ConnectionManager'dan sayıları döndürür.

**Neden böyle:** Health endpoint, deployment'ın temel taşı — yük dengeleyiciler (load balancer) ve container orkestratörleri (Kubernetes) bu ucu yoklayarak servisin ayakta olup olmadığını anlar.

**AI mühendisliği dersi:** Liveness (ayakta mı?) vs readiness (istek almaya hazır mı?) ayrımı. Bir LLM servisi açılırken model yüklemesi uzun sürebilir; readiness probe "henüz hazır değilim, bana istek yollama" demeni sağlar.

---

## 8. `app/routers/ws.py` — WebSocket endpoint (protokolün kalbi)

**Ne için var:** Asıl gerçek-zamanlı sohbet burada olur. Bağlantıyı kabul eder, mesaj döngüsünü çevirir, hataları yönetir.

**Nasıl çalışır (akış sırası):**
1. **Güvenlik kapısı:** origin + token kontrolü (yanlışsa 1008 ile kapat, `accept` bile etme).
2. `accept()` + `register()` (ConnectionManager'a ekle).
3. **`while True` döngüsü** (bağlantı açık kaldıkça her mesaj için):
   - `receive_json` + şema doğrulama
   - içerik kontrolü (boş / 2000 karakter / null byte)
   - rate limit
   - `record_message` + turn sayısı logu
   - `stream_response` ile yanıtı parça parça yolla → `done`
   - Gemini hatalarını (timeout, 503, 429) yakala
4. **Kapanış:** `WebSocketDisconnect` normal ayrılış (hata değil), beklenmedik hata → 1011, `finally` → `unregister`.

**Neden böyle:**
- WebSocket'in üç fazı (kabul → döngü → kapanış) net ayrılmış. Her fazın kendi hata yönetimi var.
- `WebSocketDisconnect`'i ayrı yakalamak önemli: kullanıcının sekmeyi kapatması bir **hata değil**, normal bir olay. Onu generic hata gibi ele alırsan loglar kirlenir ve kapalı sokete yazmaya çalışıp ikinci bir hata fırlatırsın.
- Ham hata mesajı kullanıcıya **sızdırılmaz** (güvenlik); detay logda kalır, kullanıcı sadece "ID: ..." görür.

**AI mühendisliği dersi:** Streaming LLM ürünleri neredeyse her zaman WebSocket veya SSE (Server-Sent Events) üzerinden çalışır. Bağlantı yaşam döngüsünü doğru yönetmek (kopma, timeout, idle) gerçek-zamanlı AI ürünlerinin temel becerisidir. "İstemci yanıt ortasında kaçtı" senaryosunu düzgün ele almak = production olgunluğu.

---

## 9. `app/main.py` — Uygulamanın montaj noktası

**Ne için var:** Her şeyi birleştirir: ~25 satır. Lifespan + router'lar.

**Nasıl çalışır:**
- `lifespan`: **açılışta** pahalı kaynakları kurar (`genai.Client`, `ConnectionManager`) ve `app.state`'e koyar; **kapanışta** açık bağlantıları kapatır.
- `app.include_router(...)` ile web ve ws route'larını ekler.

**Neden böyle:**
- Pahalı/uzun ömürlü kaynaklar (API client) her istekte değil, **uygulama ömrü boyunca bir kez** oluşturulur → `lifespan` + `app.state`.
- `main.py`'nin ince olması (sadece montaj) iyi bir işaret: iş mantığı servislerde, route'lar router'larda.

**AI mühendisliği dersi:** Model client'ları, bağlantı havuzları, tokenizer'lar gibi pahalı nesneler lifespan'da bir kez kurulur. Bunu her istekte yeniden yaratmak AI servislerinde ciddi performans/maliyet kaybıdır.

---

## 10. `tests/` — Güven ağı

**Ne için var:** Kodun "ne yapması gerektiğini" çalıştırılabilir biçimde sabitler. Bir şeyi bozarsan test yakalar.

**Nasıl çalışır:**
- `conftest.py`: `FakeProvider` (gerçek Gemini yerine) ve `TestClient` fixture'ı.
- `test_chat_service.py`: pencereleme, rate limit, history davranışları (unit testler).
- `test_ws_endpoint.py`: auth, happy path, doğrulama, /health, /metrics (entegrasyon testleri).
- `test_connection_manager.py`: bağlantı sayımı, close_all.

**Neden böyle:** `FakeProvider` sayesinde testler gerçek API çağırmaz → faturasız ve milisaniyeler içinde çalışır. Test piramidi: çok unit, az entegrasyon.

**AI mühendisliği dersi:** LLM kodunu test etmek zordur (yanıtlar değişken, çağrı pahalı). Çözüm: LLM'i bir arayüz arkasına alıp (madde 4) testte sahte yanıt vermek. "Modeli mock'la, kendi mantığını test et." Bu, AI sistemlerini güvenle değiştirebilmenin yolu.

---

## Tekrar planı (sınırlı zaman için)

Her gün **tek bir dosya** (yukarıdaki sırayla). Her dosya için 4 adım:

1. Bu rehberdeki bölümü oku (5 dk)
2. Gerçek dosyayı PyCharm'da aç, satırları eşleştir (5 dk)
3. Bir satıra breakpoint koy, bir testi debug et, değişkenleri izle (10 dk)
4. Nota kendi cümlenle yaz: "Bu dosya ... için var, en önemli kararı ..." (5 dk)

9 dosya = ~2 hafta, günde 25 dk. Sonunda tüm sistemi "neden" seviyesinde anlamış olursun.

## AI mühendisliğine giden köprü

Bu projede öğrendiğin her şey doğrudan AI backend işine bağlanır:
- **LLM soyutlama + streaming** → agent/chatbot backend'lerinin çekirdeği
- **Context/history yönetimi** → token maliyeti & RAG'in temeli
- **Async Python** → yüksek eşzamanlı LLM servisleri
- **Gözlemlenebilirlik** → "bu yanıt neden pahalı/yavaş" sorusu
- **Soyutlama + test** → modelleri güvenle değiştirebilmek

Bir sonraki adım (bu proje olgunlaştıkça): RAG (kendi verinle yanıt), tool/function calling, birden fazla model arasında yönlendirme, değerlendirme (eval) pipeline'ları.
