# Yol Haritası III — İngiltere'de İlk Junior AI İşi (Tem 2026 → Tem 2027)

**Dayanak:** UK pazar analizi (Adzuna, 2.094 ilan, 1 Tem 2026) + skill-gap matrisi + mevcut proje durumu.
**Bu haritayı öncekilerden ayıran gerçek:** Döngü 1–12'nin **kodu bitti** (CI yeşil, tek komutla deploy, canlı doğrulanmış). Rar'daki takvim "her ay bir döngü inşa et" varsayıyordu; artık inşa edilecek şey pazarın istediği **5 yeni parça**, öğrenilecek şey ise **mevcut kod** (tersine mühendislik). Harita bu ikisini tek ritme bağlar.

---

## 1. Pazarın söyledikleri (özet)

| Bulgu | Sayı | Sonuç |
|---|---|---|
| **Agentic AI / Agents** | 115 ilan — **1 numaralı tema** | Haritada yoktu → **D10.5 (yeni inşa)** |
| LLM + GenAI | 94 + 68 | Çekirdek — proje tam üstünde ✓ |
| **AWS / Azure** | 52 + 51 | Railway sinyal vermiyor → **AWS free tier deploy** |
| MLOps / evals | 22 | **Eval seti + CI** (D6'nın LLM uzantısı) |
| RAG / React | 15 / 20 | D10 + D11 karşılıyor ✓ (React'i **TS'e** taşı) |
| Gerçek junior ilan | 56 açık + 1.069 seviyesiz havuz | Londra odak; %60 eşleşme = başvur |
| Junior maaş | £35–37,5k medyan (Londra) | Beklenti çıpası |

**Bilinçli boşluklar (savunmasıyla):** Klasik ML/PyTorch ("derinleşmeyi LLM sistemlerinde seçtim"), Kubernetes (junior beklentisi değil; Docker yeter), fine-tuning (önce RAG+prompt), LangChain (soyutlamayı elle kurdum — 1 günlük okuma turu D10.5 sonunda).

## 2. İki ray: Öğren (A) + İnşa (B)

**Ray A — Tersine mühendislik (D5→D12):** Kod hazır; sen kurcalayacaksın. Her döngüde: oku → boz → gözle → geri al → öğrenme notu (H şablonu) → K-raporu → Claude review. Debugger + FakeProvider deneyleri bu rayın araçları.

**Ray B — Pazar parçaları (yeni kod):** Her biri, ilgili döngünün tersine-mühendislik çalışmasının **final ödevi** — öğrendiğin katmanın üstüne kendi elinle bir şey eklersin:

| # | Parça | Bağlı döngü | Kapattığı boşluk |
|---|---|---|---|
| B1 | **İkinci LLM sağlayıcı** (Claude API veya OpenAI-uyumlu) — LLMProvider'a yeni sınıf | D5 (soyutlama) | "Provider-agnostic" CV satırı; soyutlamanın gerçek testi |
| B2 | **LLM eval seti**: 15-20 golden soru + basit skorlayıcı script, CI'a bağlı | D6 (test) | MLOps/evals sinyali; "cevabın iyi olduğunu nereden biliyorsun?" |
| B3 | **AWS free tier deploy** (tek EC2 + mevcut compose; ECS'e not düş) | D8 (Docker) | Cloud boşluğu — CV'de "AWS" |
| B4 | **D10.5 Agents/tool-use**: Gemini function calling; "dokümanda ara"(=RAG) + "hesapla" + 1 araç daha arasında seçen agent döngüsü; MCP'yi okuma düzeyinde tanı | D10 (RAG) | **Pazarın 1 numarası** — portföyün amiral parçası |
| B5 | **React → TypeScript** geçişi (`react-ts`) | D11 (frontend) | TS sinyali (27 ilan) |

## 3. Aylık takvim (güncel)

Yaz ritmi (07:00–19:00 mesai): hafta içi 3-4 akşam × 45-60 dk **okuma/kurcalama**, Cmt 3-4 sa + Paz 2-3 sa **kod**. Okul döneminde hafta içi artar.

| Ay | Ray A (öğren) | Ray B (inşa) | Dış dünya |
|---|---|---|---|
| **Tem 2026** | D5: katmanlar, Protocol, lifespan — FakeProvider deneyi, debugger turu | **B1** ikinci sağlayıcı | — |
| **Ağu 2026** | D6: testler, metrics — bilinçli bozma deneyleri | **B2** eval seti CI'a | Medium #1 (soyutlama/eval) |
| **Eyl 2026** | D7: DB, migration — psql'de gez, migration yaz/boz | — (hafif ay) | Graduate scheme taraması; pazar verisi yenile |
| **Eki 2026** | D8: Docker, CI — imajı söküp incele | **B3** AWS deploy | ⚠️ **MSc/rota kararı** |
| **Kas 2026** | D9: JWT, RBAC — token boz, exp kısalt, IDOR dene | — | MSc rotasıysa başvurular |
| **Ara 2026** | D10 (1/2): ingestion — chunk_size/overlap ile oyna | — | IELTS hazırlık (rotaysa) |
| **Oca 2027** | D10 (2/2): retrieval — threshold/top_k deneyleri, **deney günlüğü** | — | IELTS; Medium #2 (RAG — amiral yazı) |
| **Şub 2027** | — | **B4 Agents (D10.5)** — ayın tamamı | Pazar verisi: agents hâlâ 1 mi? |
| **Mar 2027** | D11: React zihinsel modeli | **B5** TypeScript geçişi | LinkedIn/GitHub İngilizce |
| **Nis 2027** | D12: portföy, demo video, CV final | — | **Başvurular: haftada 10+** |
| **May 2027** | Mülakat hazırlığı (soru bankası, STAR, system design) | — | İlk mülakatlar |
| **Haz–Tem 2027** | Buffer | Buffer | Freelance ilk işler; gidiş |

## 4. Rota kararı (Ekim 2026'ya kadar)

1. **MSc + Graduate visa** (Eyl 2027 girişi): başvuru Kas–Ara 2026, IELTS 6.5+. "Tem 2027'de iş" → "Eyl 2027 MSc + part-time sektör girişi"ne evrilir; portföy aynı, boşa iş yok.
2. **Doğrudan sponsorship:** junior'da zor ama AI'da imkânsız değil; gov.uk sponsor register'dan hedef listesi; başvuru Mart 2027'de erken başlar.
3. **Remote-first UK (B planı):** Türkiye'den remote başla, içeriden transfer.

## 5. Kontrol noktaları

- **Eki 2026:** Rota kararı verildi mi? A-rayı D8'e geldi mi? (Gerideysen: B5'i MVP'ye indir, paket sayısını düşür.)
- **Oca 2027:** D10 öğrenimi bitti mi? RAG yazısı çıktı mı? B1-B3 tamam mı?
- **Nis 2027:** Demo video + CV hazır mı? Değilse 2-3 hafta ertele ama **Mayıs'ı kaçırma** (UK mülakat süreçleri 4-8 hafta).

## 6. Kesinti kuralları

1. Hiçbir hafta sıfır çekme — en kötü hafta 2 saat okuma.
2. Döngü uzarsa böl, atlama — sonrakiler öncekine yaslanıyor.
3. Yeni parlak fikir → not al, D12 sonrasına park et. **"Yeni proje yok"** — takvimin sigortası.
4. B parçaları A'nın önüne geçmesin: anlamadığın katmanın üstüne inşa etme.
