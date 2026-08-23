import time

import streamlit as st

from utils.backend_client import gorev1_analiz, gorev2_taslak
from utils.sample_data import SAMPLE_DOCS

st.set_page_config(page_title="Uçtan Uca Demo", page_icon="🎬", layout="wide")

for key, value in {
    "backend_url": "", "demo_mode": True, "evrak_metni": "",
    "gorev1_sonuc": None, "gorev2_sonuc": None, "ajan_log": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

st.title("🎬 Uçtan Uca Demo Senaryosu")
st.caption(
    "Jüri sunumu için: evrak girişinden yazı taslağı ve birim yönlendirmesine "
    "kadar tüm akışı tek adımda, canlı olarak izleyin. (Şartname madde 8)"
)

secim = st.selectbox("Demo senaryosu seçin", [d["baslik"] for d in SAMPLE_DOCS])
secilen = next(d for d in SAMPLE_DOCS if d["baslik"] == secim)
st.text_area("Evrak metni (önizleme)", value=secilen["metin"], height=160, disabled=True)

if st.session_state.demo_mode:
    st.info(
        "Demo modu açık: bu senaryolar için ekibin gerçek örnek çıktıları (gorev1.txt / "
        "gorev2.txt) gösterilecek; farklı bir metin girilirse sezgisel (heuristic) mock devreye girer."
    )
elif not st.session_state.backend_url:
    st.warning("Demo modu kapalı ama backend adresi girilmemiş — sidebar'dan ayarlayın ya da demo modunu açın.")

if st.button("▶️ Demoyu çalıştır", type="primary"):
    log = st.session_state.ajan_log

    adim1 = st.empty()
    with st.spinner("Evrak Analiz Ajanı çalışıyor..."):
        t0 = time.time()
        analiz, log, hata1 = gorev1_analiz(
            secilen["metin"],
            base_url=st.session_state.backend_url,
            demo_mode=st.session_state.demo_mode,
            log=log,
        )
    adim1.success(
        f"✅ Evrak Analiz Ajanı tamamlandı ({time.time() - t0:.2f} sn) — "
        f"Tür: {analiz['evrak_turu']} | Aciliyet: {analiz.get('aciliyet_durumu', '—')}"
    )
    if hata1:
        st.warning(hata1)

    adim2 = st.empty()
    with st.spinner("Yazı Taslaklama ve Yönlendirme Ajanı çalışıyor..."):
        t0 = time.time()
        taslak, log, hata2 = gorev2_taslak(
            analiz,
            base_url=st.session_state.backend_url,
            demo_mode=st.session_state.demo_mode,
            log=log,
        )
    birim = taslak["yonlendirme_karari"]["geregi_icin_yonlendirilecek_birim"]
    adim2.success(f"✅ Yazı Taslaklama Ajanı tamamlandı ({time.time() - t0:.2f} sn) — Birim: {birim}")
    if hata2:
        st.warning(hata2)

    st.session_state.gorev1_sonuc = analiz
    st.session_state.gorev2_sonuc = taslak
    st.session_state.ajan_log = log

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📥 Görev 1 çıktısı")
        st.json(analiz)
    with c2:
        st.subheader("✍️ Görev 2 çıktısı")
        st.json(taslak)

    st.divider()
    st.subheader("📄 Nihai resmi yazı")
    govde_taslak = taslak["resmi_yazi_taslagi"]
    nihai_metin = (
        f"KONU: {govde_taslak.get('konu', '')}\n\n"
        f"İlgi: {govde_taslak.get('ilgi', '')}\n\n"
        f"{govde_taslak.get('govde_metni', '')}\n\n"
        f"{govde_taslak.get('imza_makami', '')}"
    )
    st.code(nihai_metin, language=None)
    st.download_button("⬇️ Nihai yazıyı indir (.txt)", nihai_metin, file_name="resmi_yazi.txt")

    st.subheader("💬 Kullanıcıya gösterilecek mesaj")
    st.success(taslak["kullanici_bilgilendirme"]["kullaniciya_gosterilecek_mesaj"])

if st.session_state.ajan_log:
    st.divider()
    with st.expander("🧵 Tüm ajan işlem günlüğü"):
        st.table(st.session_state.ajan_log)
