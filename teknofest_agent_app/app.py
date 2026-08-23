import streamlit as st

st.set_page_config(
    page_title="Kamu Evrak Ajan Sistemi",
    page_icon="🗂️",
    layout="wide",
)

# --------------------------------------------------------------------------
# Oturum durumu (session_state) — sayfalar arasında paylaşılan veri
# --------------------------------------------------------------------------
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
    st.header("⚙️ Ayarlar")

    st.session_state.demo_mode = st.toggle(
        "Demo modu (mock veri)",
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
        if not st.session_state.backend_url:
            st.warning("Backend adresi girilmedi — istekler otomatik olarak mock veriye düşecek.")

    st.divider()
    st.caption("Kullanılan veri: kurgu/örnek evrak metinleri. Gerçek kamu verisi kullanılmamaktadır.")
    st.caption("Bu ekran yalnızca arayüz katmanıdır; ajan mantığı ayrı bir backend serviste çalışır.")

# --------------------------------------------------------------------------
# Ana içerik
# --------------------------------------------------------------------------
st.title("🗂️ Kamu Evrak ve Yazışma Süreçleri için Akıllı Agent Destek Sistemi")
st.caption("TEKNOFEST Yapay Zeka Dil Ajanları Yarışması — 1. Senaryo")

st.markdown(
    """
Bu arayüz, kamu kurumlarına ulaşan evrakların **okunması, sınıflandırılması,
mevzuat eşleştirmesi, resmi yazı taslağı oluşturulması ve doğru birime
yönlendirilmesi** sürecini yürüten çok ajanlı sistemin ön yüzüdür. Ajan/LLM
mantığı ayrı bir backend serviste çalışır; bu uygulama yalnızca o servise
istek gönderip sonucu görselleştirir.
"""
)

col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("📥 Görev 1")
    st.write("Evrak sınıflandırma ve içerik analizi")
    st.page_link("pages/1_Gorev_1_Siniflandirma.py", label="Görev 1'e git →")
with col2:
    st.subheader("✍️ Görev 2")
    st.write("Resmî yazı taslaklama ve birim yönlendirme")
    st.page_link("pages/2_Gorev_2_Taslak_Yonlendirme.py", label="Görev 2'ye git →")
with col3:
    st.subheader("🎬 Demo")
    st.write("Uçtan uca tam akış (jüri sunumu için)")
    st.page_link("pages/3_Demo_Uctan_Uca.py", label="Demoyu başlat →")

st.divider()



if st.session_state.ajan_log:
    with st.expander("🕓 Son ajan işlem günlüğü"):
        st.table(st.session_state.ajan_log[-10:])
