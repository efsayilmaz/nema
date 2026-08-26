import streamlit as st

from utils.backend_client import gorev1_analiz
from utils.sample_data import SAMPLE_DOCS

st.set_page_config(
    page_title="Evrak Analizi",
    page_icon="📋",
    layout="wide",
)

# --------------------------------------------------------------------------
# Kurumsal Tema, Kristal Sidebar ve Buton Stilleri (Ana Sayfa ile Birebir Aynı)
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

    /* Sol Menü İsimlerini Düzenleme */
    /* 1. app -> Ana Sayfa */
    ul[data-testid="stSidebarNavItems"] li:nth-child(1) span {
        display: none !important;
    }
    ul[data-testid="stSidebarNavItems"] li:nth-child(1) a::after {
        content: "Ana Sayfa" !important;
        font-weight: 500 !important;
    }

    /* 2. Gorev 1 Siniflandirma -> Evrak Analizi (Aktif Sayfa) */
    ul[data-testid="stSidebarNavItems"] li:nth-child(2) span {
        display: none !important;
    }
    ul[data-testid="stSidebarNavItems"] li:nth-child(2) a::after {
        content: "Evrak Analizi" !important;
        font-weight: 600 !important;
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
    
    /* Kurumsal Metrik Kartları */
    div[data-testid="stMetric"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 16px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
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

_ACILIYET_RENK = {"Normal": "", "İvedi": "", "Çok İvedi": ""}

# --------------------------------------------------------------------------
# Ana İçerik
# --------------------------------------------------------------------------
st.title("Evrak Sınıflandırma ve İçerik Analizi")

st.markdown(
    """
    <div class="system-desc">
        Evrak metnini yapıştırın, bir dosya yükleyin ya da örnek bir senaryo seçin. 
        Akıllı ajan mimarisi evrakı analiz ederek türünü, konusunu, gönderen bilgilerini, 
        kritik varlıkları, eksik bilgileri ve ilgili mevzuatı otomatik olarak çıkaracaktır.
    </div>
    """,
    unsafe_allow_html=True,
)

secim = st.selectbox("Örnek evrak seç (opiyonel)", ["— Seçiniz —"] + [d["baslik"] for d in SAMPLE_DOCS])
if secim != "— Seçiniz —":
    secilen = next(d for d in SAMPLE_DOCS if d["baslik"] == secim)
    st.session_state.evrak_metni = secilen["metin"]

st.session_state.evrak_metni = st.text_area(
    "Evrak metni", value=st.session_state.evrak_metni, height=200,
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
    " Evrakı analiz et",
    type="primary",
    disabled=not (st.session_state.evrak_metni and st.session_state.evrak_metni.strip()),
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

    st.markdown("---")
    ust1, ust2, ust3, ust4 = st.columns(4)
    ust1.metric("Evrak Türü", s.get("evrak_turu", "—"))
    ust2.metric("Evrak Tarihi", s.get("evrak_tarihi") or "Belirtilmemiş")
    ust3.metric("Sayı / Kayıt No", s.get("sayi_veya_kayit_no") or "Belirtilmemiş")
    aciliyet = s.get("aciliyet_durumu", "Normal")
    ust4.metric("Aciliyet Durumu", f"{_ACILIYET_RENK.get(aciliyet, '')} {aciliyet}")

    st.markdown(f"**Konu:** {s.get('konu', '—')}")
    st.markdown("**Kısa Özet**")
    st.info(s.get("kisa_ozet", "—"))

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Gönderen Bilgileri**")
        st.markdown(f"- **Tür:** {gonderen.get('gonderen_tipi') or '—'}")
        st.markdown(f"- **Ad/Unvan:** {gonderen.get('ad_soyad_veya_unvan') or '⚠️ Belirtilmemiş'}")
        st.markdown(f"- **Kimlik/Vergi No:** {gonderen.get('kimlik_veya_vergi_no') or '⚠️ Belirtilmemiş'}")
        st.markdown(f"- **İletişim:** {gonderen.get('iletisim_bilgisi') or '⚠️ Belirtilmemiş'}")

        st.markdown("**Eksik Bilgiler**")
        eksikler = s.get("eksik_bilgiler", [])
        if eksikler:
            for e in eksikler:
                st.markdown(f"- ⚠️ {e}")
        else:
            st.markdown("- Eksik bilgi tespit edilmedi")

    with c2:
        st.markdown("**Tespit Edilen Varlıklar**")
        st.markdown(f"- **Kurumlar:** {', '.join(varliklar.get('kurumlar', [])) or '—'}")
        st.markdown(f"- **Lokasyonlar:** {', '.join(varliklar.get('lokasyonlar', [])) or '—'}")
        st.markdown(f"- **Tarihler:** {', '.join(varliklar.get('tarihler', [])) or '—'}")

        st.markdown("**İlgili Mevzuat Önerisi**")
        for m in s.get("ilgili_mevzuat_onerisi", []):
            st.markdown(f"- {m}")

    with st.expander("Ham JSON Çıktı (Backend Kontrolü)"):
        st.json(s)

    st.divider()
    st.page_link(
        "pages/2_Gorev_2_Taslak_Yonlendirme.py",
        label="→  Yazı Taslağı Oluştur",
    )