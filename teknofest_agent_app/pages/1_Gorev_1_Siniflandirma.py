import streamlit as st

from utils.backend_client import gorev1_analiz
from utils.sample_data import SAMPLE_DOCS

st.set_page_config(page_title="Görev 1 - Sınıflandırma", page_icon="📥", layout="wide")

for key, value in {
    "backend_url": "", "demo_mode": True, "evrak_metni": "",
    "gorev1_sonuc": None, "gorev2_sonuc": None, "ajan_log": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

_ACILIYET_RENK = {"Normal": "🟢", "İvedi": "🟠", "Çok İvedi": "🔴"}

st.title("📥 Görev 1: Evrak Sınıflandırma ve İçerik Analizi")
st.caption("Şartname madde 6.4.1")

st.markdown(
    "Evrak metnini yapıştırın, bir dosya yükleyin ya da örnek bir senaryo seçin. "
    "Sistem evrakı okuyacak; türünü, konusunu, gönderen bilgilerini, önemli "
    "varlıkları, eksik bilgileri ve ilgili mevzuatı çıkaracaktır."
)

secim = st.selectbox("Örnek evrak seç (opsiyonel)", ["— Seçiniz —"] + [d["baslik"] for d in SAMPLE_DOCS])
if secim != "— Seçiniz —":
    secilen = next(d for d in SAMPLE_DOCS if d["baslik"] == secim)
    st.session_state.evrak_metni = secilen["metin"]

st.session_state.evrak_metni = st.text_area(
    "Evrak metni", value=st.session_state.evrak_metni, height=220,
    placeholder="Evrak metnini buraya yapıştırın...",
)

yuklenen = st.file_uploader(
    "veya bir dosya yükleyin (.txt, .pdf, .png, .jpg, .jpeg)",
    type=["txt", "pdf", "png", "jpg", "jpeg"],
    help="Taranmış/görsel evraklar için OCR işlemi backend tarafında yapılır "
         "(bkz. Şartname madde 6.4.1). Bu arayüz dosyayı sadece backend'e iletir.",
)
if yuklenen is not None:
    if yuklenen.name.lower().endswith(".txt"):
        st.session_state.evrak_metni = yuklenen.read().decode("utf-8", errors="ignore")
        st.session_state.yuklenen_dosya = None
    else:
        # .pdf / .png / .jpg / .jpeg — OCR bu arayüzde değil, backend'de yapılır.
        st.session_state.yuklenen_dosya = {
            "ad": yuklenen.name,
            "tur": yuklenen.type,
            "veri": yuklenen.getvalue(),
        }
        if yuklenen.type in ("image/png", "image/jpeg"):
            st.image(yuklenen, caption=yuklenen.name, width=300)
        else:
            st.markdown(f"📄 **{yuklenen.name}** yüklendi.")
        st.info(
            "Bu dosya OCR ile okunmak üzere backend'e gönderilecektir; demo modunda "
            "OCR simüle edilmez. Şimdilik test edebilmek için evrak metnini yukarıdaki "
            "kutuya elle yapıştırabilir ya da bir örnek senaryo seçebilirsiniz."
        )

calistir = st.button(
    "🔍 Evrakı analiz et", type="primary",
    disabled=not st.session_state.evrak_metni.strip(),
)

if calistir:
    with st.spinner("Ajanlar evrakı işliyor..."):
        sonuc, log, hata = gorev1_analiz(
            st.session_state.evrak_metni,
            base_url=st.session_state.backend_url,
            demo_mode=st.session_state.demo_mode,
            log=st.session_state.ajan_log,
        )
    st.session_state.gorev1_sonuc = sonuc
    st.session_state.gorev2_sonuc = None  # görev 1 değişince görev 2 sonucu geçersiz olur
    st.session_state.ajan_log = log
    if hata:
        st.warning(hata)
    else:
        st.success("Analiz tamamlandı.")

if st.session_state.gorev1_sonuc:
    s = st.session_state.gorev1_sonuc
    gonderen = s.get("gonderen", {}) or {}
    varliklar = s.get("varliklar", {}) or {}

    ust1, ust2, ust3, ust4 = st.columns(4)
    ust1.metric("Evrak türü", s.get("evrak_turu", "—"))
    ust2.metric("Evrak tarihi", s.get("evrak_tarihi") or "Belirtilmemiş")
    ust3.metric("Sayı / kayıt no", s.get("sayi_veya_kayit_no") or "Belirtilmemiş")
    aciliyet = s.get("aciliyet_durumu", "Normal")
    ust4.metric("Aciliyet durumu", f"{_ACILIYET_RENK.get(aciliyet, '')} {aciliyet}")

    st.markdown(f"**Konu:** {s.get('konu', '—')}")
    st.markdown("**Kısa özet**")
    st.info(s.get("kisa_ozet", "—"))

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Gönderen bilgileri**")
        st.markdown(f"- Tür: {gonderen.get('gonderen_tipi') or '—'}")
        st.markdown(f"- Ad/Unvan: {gonderen.get('ad_soyad_veya_unvan') or '⚠️ Belirtilmemiş'}")
        st.markdown(f"- Kimlik/Vergi No: {gonderen.get('kimlik_veya_vergi_no') or '⚠️ Belirtilmemiş'}")
        st.markdown(f"- İletişim: {gonderen.get('iletisim_bilgisi') or '⚠️ Belirtilmemiş'}")

        st.markdown("**Eksik bilgiler**")
        eksikler = s.get("eksik_bilgiler", [])
        if eksikler:
            for e in eksikler:
                st.markdown(f"- ⚠️ {e}")
        else:
            st.markdown("- ✅ Eksik bilgi tespit edilmedi")

    with c2:
        st.markdown("**Tespit edilen varlıklar**")
        st.markdown(f"- Kurumlar: {', '.join(varliklar.get('kurumlar', [])) or '—'}")
        st.markdown(f"- Lokasyonlar: {', '.join(varliklar.get('lokasyonlar', [])) or '—'}")
        st.markdown(f"- Tarihler: {', '.join(varliklar.get('tarihler', [])) or '—'}")

        st.markdown("**İlgili mevzuat önerisi**")
        for m in s.get("ilgili_mevzuat_onerisi", []):
            st.markdown(f"- 📖 {m}")

    with st.expander("Ham JSON çıktı (backend kontrolü için)"):
        st.json(s)

    st.divider()
    st.page_link(
        "pages/2_Gorev_2_Taslak_Yonlendirme.py",
        label="→ Görev 2'ye devam et (yazı taslağı oluştur)",
    )