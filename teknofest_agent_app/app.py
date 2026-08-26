import streamlit as st

st.set_page_config(
    page_title="Kamu Evrak Ajan Sistemi",
    page_icon="🗂️",
    layout="wide",
)

# --------------------------------------------------------------------------
# Kurumsal Tema, Kristal Sidebar ve Buton Stilleri
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
        font-size: 1.08rem;
        line-height: 1.6;
        margin-bottom: 2rem;
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
        font-weight: 600 !important;
    }

    /* 2. Gorev 1 Siniflandirma -> Evrak Analizi */
    ul[data-testid="stSidebarNavItems"] li:nth-child(2) span {
        display: none !important;
    }
    ul[data-testid="stSidebarNavItems"] li:nth-child(2) a::after {
        content: " Evrak Analizi" !important;
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

    /* 4. Demo Uctan Uca -> Sistem Demosu */
    ul[data-testid="stSidebarNavItems"] li:nth-child(4) span {
        display: none !important;
    }
    ul[data-testid="stSidebarNavItems"] li:nth-child(4) a::after {
        content: "Sistem Demosu" !important;
        font-weight: 500 !important;
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

    /* Kart Başlık ve Açıklamaları */
    .module-title {
        color: #1e3a8a;
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .module-desc {
        color: #475569;
        font-size: 0.95rem;
        margin: 0;
    }

    /* Streamlit Page Link'lerini Kurumsal Butona Dönüştürme */
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

defaults = {
    "backend_url": "",
    "demo_mode": True,
    "evrak_metni": "",
    "gorev1_sonuc": None,
    "gorev2_sonuc": None,
    "ajan_log": [],
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------
with st.sidebar:
    st.header("Ayarlar")

    st.session_state.demo_mode = st.toggle(
        "Demo modu",
        value=st.session_state.demo_mode,
        help="Açıkken backend'e istek atılmaz, örnek/sahte veri gösterilir. "
             "Backend hazır olmadan arayüzü test etmek veya jüri demosunda "
             "internet kesintisine karşı yedek plan için kullanılabilir.",
    )

    if not st.session_state.demo_mode:
        st.session_state.backend_url = st.text_input(
            "Backend API adresi",
            value=st.session_state.backend_url,
            placeholder="https://backend-servisiniz.example.com",
            help="Ajan/LLM mantığının çalıştığı servisin adresi. "
                 "Beklenen uç noktalar: POST /api/gorev1 ve POST /api/gorev2 "
                 "(bkz. utils/backend_client.py içindeki kontrat).",
        )

    st.divider()

# --------------------------------------------------------------------------
# Ana içerik
# --------------------------------------------------------------------------
st.title("Kamu Evrak ve Yazışma Süreçleri için Akıllı Agent Destek Sistemi")

st.markdown(
    """
    <div class="system-desc">
        Kamu kurumlarına intikal eden evrakların analiz, mevzuat uyumlandırma, taslak oluşturma ve sevk süreçlerini 
        yapay zekâ tabanlı akıllı ajan mimarisiyle uçtan uca yöneten dijital karar destek platformudur.
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------- Modül 1: Evrak Analizi -----------------
with st.container():
    c_info, c_btn = st.columns([3.8, 1.2], vertical_alignment="center")
    with c_info:
        st.markdown(
            """
            <div style="padding-left: 4px;">
                <div class="module-title">Evrak Analizi</div>
                <p class="module-desc">Gelen resmî evrakların sınıflandırılması, özet çıkarımı ve mevzuat uyum analizi.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c_btn:
        st.page_link("pages/1_Gorev_1_Siniflandirma.py", label="Analize Başla →")

st.divider()

# ----------------- Modül 2: Taslak Oluşturma -----------------
with st.container():
    c_info, c_btn = st.columns([3.8, 1.2], vertical_alignment="center")
    with c_info:
        st.markdown(
            """
            <div style="padding-left: 4px;">
                <div class="module-title">Taslak Oluşturma</div>
                <p class="module-desc">İlgili mevzuat doğrultusunda resmî yazı taslaklama ve yetkili birim yönlendirmesi.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c_btn:
        st.page_link("pages/2_Gorev_2_Taslak_Yonlendirme.py", label="Taslak Oluştur →")

st.divider()

# ----------------- Modül 3: Demo -----------------
with st.container():
    c_info, c_btn = st.columns([3.8, 1.2], vertical_alignment="center")
    with c_info:
        st.markdown(
            """
            <div style="padding-left: 4px;">
                <div class="module-title">Sistem Demosu</div>
                <p class="module-desc">Tüm ajan akışının eşzamanlı çalıştığı uçtan uca interaktif jüri sunum simülasyonu.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c_btn:
        st.page_link("pages/3_Demo_Uctan_Uca.py", label="Demoyu Başlat →")

st.divider()

if st.session_state.ajan_log:
    with st.expander("Son ajan işlem günlüğü"):
        st.table(st.session_state.ajan_log[-10:])