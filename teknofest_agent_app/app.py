import streamlit as st
import sys
import os

# Proje kök dizini ve app dizinini sys.path'e ekleyelim
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..'))
for path in [current_dir, root_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

st.set_page_config(
    page_title="Kamu Evrak Ajan Sistemi",
    page_icon="🗂️",
    layout="wide",
)

# --------------------------------------------------------------------------
# Kurumsal Tema, Kristal Sidebar ve Global Stiller
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
        font-size: 1.05rem;
        line-height: 1.6;
        margin-bottom: 1.5rem;
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

    /* A4 Belge Görünümü */
    .document-card {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 20px 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }
    .doc-meta {
        font-size: 0.95rem;
        color: #334155;
        margin-bottom: 6px;
    }
    
    /* Kurumsal Metrik Kartları */
    div[data-testid="stMetric"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 16px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    }

    /* Sekmeleri Renkli ve Kurumsal Yanyana Butonlara Dönüştürme */
    div[data-testid="stTabs"] > div[role="tablist"] {
        display: flex;
        gap: 12px;
        background-color: #f1f5f9;
        padding: 8px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        margin-bottom: 24px;
        margin-top: 10px;
    }
    button[data-testid="stTab"] {
        flex: 1 1 auto;
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        padding: 10px 18px !important;
        color: #1e293b !important;
        font-weight: 600 !important;
        font-size: 0.93rem !important;
        text-align: center !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    }
    button[data-testid="stTab"]:hover {
        background-color: #e2edf8 !important;
        color: #1e3a8a !important;
        border-color: #93c5fd !important;
        transform: translateY(-1px);
        box-shadow: 0 3px 6px rgba(30, 58, 138, 0.08) !important;
    }
    button[data-testid="stTab"][aria-selected="true"] {
        background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%) !important;
        color: #ffffff !important;
        border-color: #1e3a8a !important;
        box-shadow: 0 3px 10px rgba(30, 58, 138, 0.28) !important;
        transform: translateY(-1px);
    }
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
    div[data-testid="stTabs"] [data-baseweb="tab-border"] {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Global Session State
# --------------------------------------------------------------------------
defaults = {
    "backend_url": "http://127.0.0.1:8000",
    "demo_mode": False,
    "evrak_metni": "",
    "gorev1_sonuc": None,
    "gorev2_sonuc": None,
    "ajan_log": [],
    "islenen_dosya": None,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --------------------------------------------------------------------------
# Global Sidebar (Ayarlar)
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
# Modern Streamlit Navigasyon Tanımı (Doğrudan Türkçe Başlıklar)
# --------------------------------------------------------------------------
pages = [
    st.Page("views/0_Ana_Sayfa.py", title="Ana Sayfa", default=True),
    st.Page("views/1_Evrak_Analizi.py", title="Evrak Analizi"),
    st.Page("views/2_Taslak_Olusturma.py", title="Taslak Oluşturma"),
    st.Page("views/arsiv.py", title="Emsal Taslak Arşivi"),
    st.Page("views/3_Sistem_Demosu.py", title="Sistem Demosu"),
]

pg = st.navigation(pages)
pg.run()