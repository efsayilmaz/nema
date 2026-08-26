import streamlit as st
from utils.backend_client import gorev2_taslak

st.set_page_config(
    page_title="Taslak Oluşturma",
    page_icon="",
    layout="wide",
)

# --------------------------------------------------------------------------
# Kurumsal Tema, Kristal Sidebar ve A4 Belge Görünümü
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
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
        padding: 10px 14px;
        background-color: #f8fafc;
        border-radius: 0 8px 8px 0;
    }
    
    /* ASİL & KRİSTAL BUZ MAVİSİ SIDEBAR */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f0f5fa 0%, #e2edf8 100%) !important;
        border-right: 1px solid #d0e1f0 !important;
        box-shadow: 2px 0 10px rgba(15, 23, 42, 0.03);
    }

    /* Sol Menü İsimlerini Düzenleme */
    ul[data-testid="stSidebarNavItems"] li:nth-child(1) span { display: none !important; }
    ul[data-testid="stSidebarNavItems"] li:nth-child(1) a::after { content: "Ana Sayfa" !important; font-weight: 500 !important; }

    ul[data-testid="stSidebarNavItems"] li:nth-child(2) span { display: none !important; }
    ul[data-testid="stSidebarNavItems"] li:nth-child(2) a::after { content: "Evrak Analizi" !important; font-weight: 500 !important; }

    ul[data-testid="stSidebarNavItems"] li:nth-child(3) span { display: none !important; }
    ul[data-testid="stSidebarNavItems"] li:nth-child(3) a::after { content: "Taslak Oluşturma" !important; font-weight: 600 !important; }

    ul[data-testid="stSidebarNavItems"] li:nth-child(4) span { display: none !important; }
    ul[data-testid="stSidebarNavItems"] li:nth-child(4) a::after { content: "Sistem Demosu" !important; font-weight: 500 !important; }

    /* A4 Resmi Belge Kartı */
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
        padding: 10px 14px;
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

_DURUM_RENK = {"İşleme Alındı": "", "Kullanıcı Bekleniyor": "", "Onay Bekliyor": ""}

# --------------------------------------------------------------------------
# Ana Başlık ve Giriş
# --------------------------------------------------------------------------
st.title("Resmî Yazı Taslaklama ve Birim Yönlendirme")

st.markdown(
    """
    <div class="system-desc">
        Evrak Analizi çıktısına dayalı olarak ilgili mevzuata uygun resmî yazı taslağı oluşturulur, 
        sevk edilecek kurum/birimler belirlenir ve vatandaş bilgilendirme metni üretilir.
    </div>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.gorev1_sonuc:
    st.warning("Önce Evrak Analizi modülünde bir evrak analiz etmelisiniz.")
    st.page_link("pages/1_Gorev_1_Siniflandirma.py", label="← Evrak Analizine Git")
    st.stop()

analiz = st.session_state.gorev1_sonuc

# Üst Bilgi Çubuğu
with st.container():
    st.markdown(f"**İncelenen Evrak:** `{analiz.get('evrak_turu', '—')}` | **Konu:** *{analiz.get('konu', '—')}*")
    with st.expander("Görev 1 Analiz Verilerini İncele"):
        st.json(analiz)

# Eksik Bilgiler
ek_bilgi = ""
eksikler = [e for e in analiz.get("eksik_bilgiler", []) if e]
if eksikler:
    st.warning("Eksik bilgiler tespit edildi: " + ", ".join(eksikler))
    ek_bilgi = st.text_input("Ek Bilgi / Not Girişi (Opsiyonel):", placeholder="Taslağa eklenecek notları yazın...")

if st.button("Resmi Yazı Taslağı ve Yönlendirme Oluştur", type="primary", use_container_width=True):
    with st.spinner("Ajanlar mevzuat kurallarına göre taslak ve sevk kararını hazırlıyor..."):
        sonuc, log, hata = gorev2_taslak(
            analiz,
            ek_bilgi=ek_bilgi or None,
            base_url=st.session_state.backend_url,
            demo_mode=st.session_state.demo_mode,
            log=st.session_state.ajan_log,
        )
    st.session_state.gorev2_sonuc = sonuc
    st.session_state.ajan_log = log
    if hata:
        st.warning(hata)
    else:
        st.success("İşlem başarıyla tamamlandı.")

# --------------------------------------------------------------------------
# Sonuç Alanları (Düzenli & Derli Toplu Görünüm)
# --------------------------------------------------------------------------
if st.session_state.gorev2_sonuc:
    s = st.session_state.gorev2_sonuc
    yonlendirme = s.get("yonlendirme_karari", {}) or {}
    taslak = s.get("resmi_yazi_taslagi", {}) or {}
    bilgilendirme = s.get("kullanici_bilgilendirme", {}) or {}

    st.markdown("---")

    # 1. Yönlendirme ve Sevk Kararı (Kompakt 3'lü Metrik)
    st.subheader("Yönlendirme ve Sevk Kararı")
    m1, m2, m3 = st.columns(3)
    m1.metric("İşlem Yapacak Kurum", yonlendirme.get("islem_yapacak_ana_kurum", "—"))
    m2.metric("Gereği İçin Sevk Birimi", yonlendirme.get("geregi_icin_yonlendirilecek_birim", "—"))
    bilgi_birimleri = yonlendirme.get("bilgi_icin_iletilecek_birimler", [])
    m3.metric("Bilgi Birimleri", ", ".join(bilgi_birimleri) if bilgi_birimleri else "Yok")

    if yonlendirme.get("yonlendirme_gerekcesi"):
        st.info(f"**Yönlendirme Gerekçesi:** {yonlendirme.get('yonlendirme_gerekcesi')}")

    st.divider()

    # 2. Resmî Yazı Taslağı (Belge Formatında)
    st.subheader("Resmî Yazı Taslağı")
    
    # Üst Bilgi Satırı
    h_col1, h_col2 = st.columns([3, 1])
    with h_col1:
        st.markdown(f"**Konu:** {taslak.get('konu', '—')}")
        st.markdown(f"**İlgi:** {taslak.get('ilgi', '—')}")
    with h_col2:
        st.markdown(f"**Yazı Türü:** `{taslak.get('yazi_turu', '—')}`")
        st.markdown(f"**İmza:** `{taslak.get('imza_makami', '—')}`")

    # Metin Düzenleme Alanı
    duzenlenmis_govde = st.text_area(
        "Yazı Gövde Metni",
        value=taslak.get("govde_metni", ""),
        height=180,
        help="Gerekirse doğrudan üzerinde düzeltme yapabilirsiniz.",
    )

    tam_metin = (
        f"KONU: {taslak.get('konu', '')}\n\n"
        f"İlgi: {taslak.get('ilgi', '')}\n\n"
        f"{duzenlenmis_govde}\n\n"
        f"{taslak.get('imza_makami', '')}"
    )

    # İndirme ve Durum Çubuğu
    btn_c, info_c = st.columns([1, 2.5], vertical_alignment="center")
    with btn_c:
        st.download_button(
            "⬇ Taslağı İndir (.txt)",
            tam_metin,
            file_name="resmi_yazi_taslagi.txt",
            use_container_width=True,
        )
    with info_c:
        durum = bilgilendirme.get("sistem_aksiyon_durumu", "—")
        st.markdown(f"**Sistem Durumu:** {_DURUM_RENK.get(durum, '')} **{durum}**")

    # Vatandaş Mesajı
    st.success(f"**Vatandaş Bilgilendirme:** {bilgilendirme.get('kullaniciya_gosterilecek_mesaj', '—')}")

    with st.expander("Ham JSON Çıktısı"):
        st.json(s)