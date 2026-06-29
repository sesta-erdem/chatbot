# Pazara Çıkış Kiti (Döngü 12)

Bu döngüde kod ikincil; **paketlemek ve satmak** birincil. Bu dosya yazılı malzemeyi (konumlanma, pitch, şablonlar) içerir. Gerçek-dünya adımları (profil açma, teklif gönderme, video çekme, yorum isteme) **senin** işin — aşağıda "Sadece senin yapabileceklerin" bölümünde işaretli.

> Zihniyet: Müşteri "FastAPI bilen biri" aramaz, **"şu acımı çözecek biri"** arar. Bütün metinler problem diliyle yazılır.

---

## 1. Niş cümlesi (kim için + hangi acı + nasıl kanıt)

Üç versiyon — hangisi somut bir müşteri yüzü çağrıştırıyor, ona göre seç:

- **(EN, dar)** "I build AI assistants that let small companies chat with their own documents — upload a PDF, get sourced answers. Live demo: [link]"
- **(EN, geniş)** "I build custom AI chat backends (FastAPI + Gemini + RAG) for support, document and proposal workflows. Live demo: [link]"
- **(TR)** "Küçük işletmeler için kendi dokümanlarıyla konuşan AI asistanlar kuruyorum — PDF yükle, kaynaklı cevap al. Canlı demo: [link]"

İlk işler için **dar olanı** öner: somut acı = somut müşteri.

## 2. Pitch — üç uzunluk

**30 saniye (sözlü prova et — IELTS speaking'e de yarar):**
> "I build AI assistants that answer from a company's own documents. You upload your PDFs, ask a question in plain language, and the bot answers with the exact source — page and file. It's built on FastAPI and Google Gemini with vector search, fully authenticated and dockerized. Here's a 60-second demo: [link]."

**2 dakika (teklif/görüşme):** yukarısı + "Most teams waste hours digging through PDFs and old docs. I turn that pile into a chat box your team can ask. Each answer cites its source so people trust it. I scope tightly, deliver in days, and you own the code."

**15 dakika (mülakat):** mimariyi anlat — WebSocket streaming, JWT/RBAC, pgvector RAG, token-budget context, Docker/CI. README + KOD_REHBERI.md zaten bu anlatının iskeleti.

## 3. Üç paket (aynı teknoloji, üç müşteri dili)

| Paket | Müşteri cümlesi | Teknik karşılığı (hazır) | Ek iş |
|---|---|---|---|
| **Doküman asistanı** | "PDF'lerinizle konuşun, kaynaklı cevap" | D10 RAG + D11 arayüz | cila + seed veri |
| **Site chatbot widget'ı** | "Tek `<script>` ile sitenize sohbet" | mevcut WS + chat; gömülebilir embed | küçük embed script |
| **Telegram botu** | "Müşteri Telegram'dan sorsun" | webhook = bildiğin FastAPI POST ucu | ~yarım gün |

## 4. Teklif şablonu (problem-odaklı — ilk 2 cümle senden değil müşteriden bahseder)

```
Merhaba [isim],

[İlandaki spesifik problem] — bunu çözmek için tam olarak böyle bir asistan kurdum:
[1 cümle mini-çözüm, ilana özel]. Benzerinin canlı demosu: [link] (PDF yükleyip
soru sorabilirsiniz).

Sizin durumunuzda [ilana özel tek detay] kısmını nasıl ele alıyorsunuz —
[tek net soru]?

Kapsamı net yazıp birkaç günde teslim ediyorum; kod tamamen sizin olur.
[isim]
```

Kural: şablonu olduğu gibi gönderme; her ilana **2 cümle özel** ekle.

## 5. Kapsam belgesi şablonu (scope creep'e karşı)

```
PROJE: [ad]
DAHİL:
  - [özellik 1], [özellik 2], [özellik 3]
  - 1 ortam kurulumu (Docker), 1 deploy
  - 2 revizyon turu
DAHİL DEĞİL (ayrı teklif):
  - [ödeme, multi-tenancy, başka format, vb.]
TESLİM TANIMI: [çalışan demo linki + repo + kısa README]
SÜRE: [X gün]  ·  FİYAT: [sabit]  ·  REVİZYON: 2 (sonrası saatlik)
```

## 6. Kırmızı bayrak listesi (reddet)

- Kapsamı tanımsız: "önce yap, sonra konuşuruz"
- Sıfır bütçeli "ortaklık" / "portföyüne iyi olur" teklifleri
- "Basit bir şey" diyip her gün yeni özellik ekleyen
- Ödemeyi teslimden sonraya + belirsiz tarihe atan
- Tüm hakları + kaynak + süresiz destek isteyip tek seferlik fiyat veren

## 7. CRM-günlüğü şablonu (20 başvuru = hangi dil işe yarıyor verisi)

```
| Tarih | Platform | İlan/Müşteri | Teklif özeti | Sonuç | Öğrenilen |
|-------|----------|--------------|--------------|-------|-----------|
|       |          |              |              |       |           |
```

## 8. 60 saniyelik demo videosu senaryosu (kod DEĞİL, sonuç göster)

1. (0-10sn) Login → boş sohbet ekranı.
2. (10-25sn) "İK politikası PDF'ini" yükle → "yüklendi, N parça".
3. (25-45sn) "Yıllık izin kaç gün?" sor → cevap **streaming** akar, altında **kaynak rozeti** (dosya · sayfa).
4. (45-55sn) Dokümanda olmayan soru → "Dokümanlarda bulamadım" (dürüstlük).
5. (55-60sn) Logo/isim + "Want one for your docs? [link]".

## 9. Profil metinleri (kopyala, kişiselleştir)

**GitHub profil README (öne çıkan satır):**
> AI Backend Developer — FastAPI · WebSocket · Gemini · RAG (pgvector). I build production-grade AI chat backends. Live demo & write-up below.

**LinkedIn başlık:**
> AI Backend Developer | FastAPI + LLM/RAG | building document assistants

**Upwork/Bionluk özeti (giriş):**
> I build AI assistants that answer from your own documents, with sources. Streaming chat, authentication, vector search, dockerized — see my live demo. I scope tightly and deliver fast.

---

## Sadece senin yapabileceklerin (ben yapamam / yapmamalıyım)

- [ ] Upwork / Bionluk / LinkedIn **hesaplarını aç** ve profilleri yayınla (yukarıdaki metinlerle).
- [ ] Üç paketi **canlı deploy et** (Railway/compose) ve linklerini al.
- [ ] **60 sn demo videosunu çek** (senaryo §8).
- [ ] İlk **20 teklifi gönder** (§4) ve CRM-günlüğünü doldur (§7).
- [ ] Ağına **tek, zarif duyuru** at: "iş arıyorum" değil → "şunu kurdum, tanıdığına lazım olursa demo burada".
- [ ] İlk işi alınca: kapsamı **yazılı onaylat** (§5) → haftalık ilerleme mesajı → teslim → **yorum iste**.

> Not: Ben senin yerine hesap açamam, teklif/mesaj gönderemem, video çekemem. Bunların metnini/şablonunu hazırladım; tetiği sen çekeceksin. Hangi paketi önce deploy edeceğine karar verirsek, o paketin cilası + README + embed script gibi **kod tarafını** birlikte yaparız.
