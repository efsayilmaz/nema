# Kamu Evrak Ajan Sistemi — Arayüz (Frontend)

TEKNOFEST **Yapay Zeka Dil Ajanları Yarışması** (1. Senaryo) için hazırlanmış
Streamlit arayüzü.

> ⚠️ Bu proje **sadece arayüz (frontend) katmanıdır**. Ajan/LLM mantığı
> (evrak sınıflandırma, mevzuat eşleştirme, yazı taslaklama, yönlendirme)
> ayrı bir backend serviste çalışır ve takım arkadaşları tarafından
> geliştirilir. Arayüz backend'e HTTP ile bağlanır; backend hazır olmadığı
> sürece **demo modu** ile çalışır.

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Şema — ekibin veri setiyle birebir uyumlu

Bu arayüz, `gorev1.txt` / `gorev2.txt` dosyalarındaki örnek çıktı şemasını
temel alır. Tam şema ve alan açıklamaları `utils/backend_client.py`
dosyasının başındaki docstring'de.

**Görev 1 çıktısı:** `evrak_turu`, `konu`, `evrak_tarihi`, `sayi_veya_kayit_no`,
`gonderen` (gonderen_tipi, ad_soyad_veya_unvan, kimlik_veya_vergi_no,
iletisim_bilgisi), `kisa_ozet`, `varliklar` (kurumlar, lokasyonlar, tarihler),
`ilgili_mevzuat_onerisi`, `eksik_bilgiler`, `aciliyet_durumu`.

**Görev 2 çıktısı:** `yonlendirme_karari` (islem_yapacak_ana_kurum,
geregi_icin_yonlendirilecek_birim, bilgi_icin_iletilecek_birimler,
yonlendirme_gerekcesi), `resmi_yazi_taslagi` (yazi_turu, konu, ilgi,
govde_metni, imza_makami), `kullanici_bilgilendirme`
(kullaniciya_gosterilecek_mesaj, sistem_aksiyon_durumu).

## Backend entegrasyonu — arkadaşların için

Beklenen uç noktalar:

- `POST {BASE_URL}/api/gorev1` → `{"evrak_metni": "..."}` gönder, Görev 1 şemasını al
- `POST {BASE_URL}/api/gorev2` → `{"analiz_sonucu": {...}, "ek_bilgi": "..."}` gönder, Görev 2 şemasını al

Backend hazır olduğunda arayüzde yapman gereken tek şey: sidebar'dan
**"Demo modu"**nu kapat ve **Backend API adresi**ni gir.

Kontrat değişirse SADECE `utils/backend_client.py` içindeki
`_map_gorev1_response` / `_map_gorev2_response` fonksiyonlarını güncelle —
sayfa kodlarının hiçbirine dokunmana gerek yok.

## Demo verisi

`utils/sample_data.py` içindeki 4 örnek, ekibin `string.txt` /
`gorev1.txt` / `gorev2.txt` dosyalarından **birebir alınmış gerçek
girdi-çıktı üçlüleridir**. Demo modunda bu örneklerden biri seçilirse,
arayüz gerçek ekip çıktısını gösterir; farklı bir metin girilirse basit
sezgisel (heuristic) bir mock devreye girer.

## Klasör yapısı

```
app.py                              # Ana sayfa, sidebar, session_state
pages/
  1_Gorev_1_Siniflandirma.py        # Görev 1
  2_Gorev_2_Taslak_Yonlendirme.py   # Görev 2
  3_Demo_Uctan_Uca.py               # Jüri sunumu için tam akış
utils/
  backend_client.py                 # API istemcisi + şema kontratı + mock
  sample_data.py                    # Gerçek ekip verisinden örnekler
.streamlit/config.toml              # Tema
```
