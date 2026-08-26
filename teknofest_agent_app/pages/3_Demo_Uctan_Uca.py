import time
import streamlit as st

from utils.backend_client import gorev1_analiz, gorev2_taslak
from utils.sample_data import SAMPLE_DOCS

st.set_page_config(
    page_title="Sistem Demosu",
    page_icon="",
    layout="wide",
)

# --------------------------------------------------------------------------
# Kurumsal Tema, Kristal Sidebar ve Menü Ayarları
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Kurumsal Font ve Başlık Ayarları */
    h1 {
        color: #0f172a;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .system-desc {
        color: #334155;
        font-size: 1.02rem;
        line-height: 1.6;
        margin-bottom: 1.2rem;
        border-left: 4px solid #1e3a8a;
        padding-left: 14px;
        background-color: #f8fafc;
        padding-top: 10px;
        padding-bottom: 10px;
        border-radius: 0 8px 8px 0;
    }
    
    /* ASİL & KRİSTAL BUZ MAVİSİ SIDEBAR */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f0f5fa 0%, #e2edf8 100%) !important;
        border-right: 1px solid #d0e1f0 !important;
        box-shadow: 2px 0 10px rgba(15, 23, 42, 0.03);
    }

    /* Sol Menüdeki Sayfa Bağlantıları */
    ul[data-testid="stSidebarNavItems"] li div a {
        background-color: transparent !important;
        color: #1e293b !important;
        font-weight: 500 !important;
        border-radius: 6px !important;
        margin-bottom: 2px !important;
        transition: all 0.2s ease !important;
    }

    /* Sol Menü İsimlerini Düzenleme */
    /* 1. app -> Ana Sayfa */
    ul[data-testid="stSidebarNavItems"] li:nth-child(1) span {
        display: none !important;
    }
    ul[data-testid="stSidebarNavItems"] li:nth-child(1) a::after {
        content: "Ana Sayfa" !important;
        font-weight: 500 !important;
    }

    /* 2. Gorev 1 Siniflandirma -> Evrak Analizi */
    ul[data-testid="stSidebarNavItems"] li:nth-child(2) span {
        display: none !important;
    }
    ul[data-testid="stSidebarNavItems"] li:nth-child(2) a::after {
        content: "Evrak Analizi" !important;
        font-weight: 500 !important;
    }

    /* 3. Gorev 2 Taslak Yonlendirme -> Taslak Oluşturma */
    ul[data-testid="stSidebarNavItems"] li:nth-child(3) span {
        display: none !important;
    }
    ul[data-testid="stSidebarNavItems"] li:nth-child(3) a::after {
        content: "Taslak Oluşturma" !important;
        font-weight: 500 !important;
    }

    /* 4. Demo Uctan Uca -> Sistem Demosu (Aktif Sayfa) */
    ul[data-testid="stSidebarNavItems"] li:nth-child(4) span {
        display: none !important;
    }
    ul[data-testid="stSidebarNavItems"] li:nth-child(4) a::after {
        content: "Sistem Demosu" !important;
        font-weight: 600 !important;
    }

    /* Sol Menü Hover */
    ul[data-testid="stSidebarNavItems"] li div a:hover {
        background: rgba(255, 255, 255, 0.8) !important;
        color: #1e3a8a !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
    }

    /* Sol Menü Seçili/Aktif Sayfa */
    ul[data-testid="stSidebarNavItems"] li div a[aria-current="page"] {
        background: #ffffff !important;
        color: #1e3a8a !important;
        font-weight: 600 !important;
        border-left: 3px solid #1e3a8a !important;
        box-shadow: 0 2px 6px rgba(30, 58, 138, 0.08) !important;
    }

    /* Buton Tasarımları */
    div[data-testid="stPageLink-NavLink"] {
        background-color: #1e3a8a !important;
        border-radius: 6px !important;
        padding: 10px 18px !important;
        text-align: center !important;
        transition: background-color 0.2s ease, transform 0.1s ease !important;
        border: 1px solid #1e3a8a !important;
        width: 100% !important;
    }
    div[data-testid="stPageLink-NavLink"] * {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        text-decoration: none !important;
    }
    div[data-testid="stPageLink-NavLink"]:hover {
        background-color: #172554 !important;
        border-color: #172554 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 10px rgba(30, 58, 138, 0.2);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

for key, value in {
    "backend_url": "", "demo_mode": True, "evrak_metni": "",
    "gorev1_sonuc": None, "gorev2_sonuc": None, "ajan_log": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --------------------------------------------------------------------------
# Ana İçerik
# --------------------------------------------------------------------------
st.title("🎬 Uçtan Uca Sistem Demosu")

st.markdown(
    """
    <div class="system-desc">
        Evrak girişinden resmî yazı taslağı ve yetkili birim yönlendirmesine kadar 
        tüm çok ajanlı karar destek akışını tek adımda ve canlı olarak simüle edin.
    </div>
    """,
    unsafe_allow_html=True,
)

secim = st.selectbox("Demo senaryosu seçin", [d["baslik"] for d in SAMPLE_DOCS])
secilen = next(d for d in SAMPLE_DOCS if d["baslik"] == secim)
st.text_area("Evrak metni (önizleme)", value=secilen["metin"], height=150, disabled=True)

if st.session_state.demo_mode:
    st.info(
        " **Demo modu aktif:** Bu senaryolar için hazırlanmış örnek çıktılar gösterilmektedir. "
        "Farklı veya canlı servis testleri için sol menüden API adresinizi tanımlayabilirsiniz."
    )
elif not st.session_state.backend_url:
    st.warning("Demo modu kapalı ancak Backend API adresi girilmedi.")

if st.button("Demoyu Çalıştır", type="primary", use_container_width=True):
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
        f"Evrak Analiz Ajanı tamamlandı ({time.time() - t0:.2f} sn) — "
        f"Tür: {analiz.get('evrak_turu', '—')} | Aciliyet: {analiz.get('aciliyet_durumu', '—')}"
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
    birim = taslak.get("yonlendirme_karari", {}).get("geregi_icin_yonlendirilecek_birim", "—")
    adim2.success(f"Yazı Taslaklama Ajanı tamamlandı ({time.time() - t0:.2f} sn) — Birim: {birim}")
    if hata2:
        st.warning(hata2)

    st.session_state.gorev1_sonuc = analiz
    st.session_state.gorev2_sonuc = taslak
    st.session_state.ajan_log = log

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Görev 1 Analiz Çıktısı")
        st.json(analiz)
    with c2:
        st.subheader("Görev 2 Taslak ve Yönlendirme")
        st.json(taslak)

    st.divider()
    st.subheader("Nihai Resmî Yazı")
    govde_taslak = taslak.get("resmi_yazi_taslagi", {})
    nihai_metin = (
        f"KONU: {govde_taslak.get('konu', '')}\n\n"
        f"İlgi: {govde_taslak.get('ilgi', '')}\n\n"
        f"{govde_taslak.get('govde_metni', '')}\n\n"
        f"{govde_taslak.get('imza_makami', '')}"
    )
    st.code(nihai_metin, language=None)
    st.download_button("⬇ Nihai Yazıyı İndir (.txt)", nihai_metin, file_name="resmi_yazi.txt")

    st.subheader("Kullanıcı Bilgilendirme Mesajı")
    st.success(taslak.get("kullanici_bilgilendirme", {}).get("kullaniciya_gosterilecek_mesaj", "—"))

if st.session_state.ajan_log:
    st.divider()
    with st.expander("Tüm Ajan İşlem Günlüğü"):
        st.table(st.session_state.ajan_log)