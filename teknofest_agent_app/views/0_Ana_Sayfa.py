import streamlit as st

# --------------------------------------------------------------------------
# Ana Sayfa İçeriği
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
        st.page_link("views/1_Evrak_Analizi.py", label="Analize Başla →")

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
        st.page_link("views/2_Taslak_Olusturma.py", label="Taslak Oluştur →")

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
        st.page_link("views/3_Sistem_Demosu.py", label="Demoyu Başlat →")

st.divider()

if st.session_state.ajan_log:
    with st.expander("Son ajan işlem günlüğü"):
        st.table(st.session_state.ajan_log[-10:])
