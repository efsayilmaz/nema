import streamlit as st
import os
import sys
import json
import uuid
import datetime

# Proje kök dizini sys.path'e ekleyelim
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '../..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from utils.arsiv_db import arsiv_verilerini_getir, mevzuat_degisiklik_tara
    from utils.secure_logger import audit_logger
except ImportError:
    def arsiv_verilerini_getir(): return []
    def mevzuat_degisiklik_tara(x): return []
    audit_logger = None

# ──────────────────────────────────────────────────────────────
# Arşiv Sayfası
# ──────────────────────────────────────────────────────────────
st.title("Emsal Taslak Arşivi")

st.markdown(
    """
    <div class="system-desc">
        Kurumunuza ulaşan evraklara daha önce verilen cevaplardan,
        KVKK filtrelemesinden geçerek anonimleştirilmiş ve hukuki denetimi sağlanmış 'Emsal Karar' taslakları.
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# ──────────────────────────────────────────────────────────────
# Sektör filtresi
# ──────────────────────────────────────────────────────────────
arsiv_verileri = arsiv_verilerini_getir()

tum_sektorler = sorted(set(k.get("sektor", "Genel") for k in arsiv_verileri))
secilen_sektor = st.selectbox(
    "Sektör Filtresi:",
    options=["Tümü"] + tum_sektorler,
    index=0,
)
if secilen_sektor != "Tümü":
    arsiv_verileri = [k for k in arsiv_verileri if k.get("sektor") == secilen_sektor]

# Geçerlilik filtresi
gecerlilik_filtre = st.selectbox(
    "Geçerlilik Durumu:",
    options=["Tümü", "gecerli", "incelemede", "gecersiz"],
    index=0,
)
if gecerlilik_filtre != "Tümü":
    arsiv_verileri = [k for k in arsiv_verileri if k.get("gecerlilik_durumu", "gecerli") == gecerlilik_filtre]

if not arsiv_verileri:
    st.warning("Seçilen filtreye uygun kayıt bulunamadı.")
    st.stop()

# Arama çubuğu
arama = st.text_input("🔍 Arşivde Ara (Konu veya ID ile):", placeholder="Örn: Bilgi edinme")

_DURUM_RENK = {
    "gecerli":     "🟢",
    "incelemede":  "🟡",
    "gecersiz":    "🔴",
}

for kayit in arsiv_verileri:
    if arama and arama.lower() not in kayit.get("konu", "").lower() \
              and arama.lower() not in kayit.get("id", "").lower():
        continue

    durum = kayit.get("gecerlilik_durumu", "gecerli")
    durum_ikon = _DURUM_RENK.get(durum, "⚪")

    with st.container():
        st.markdown(f"### {durum_ikon} {kayit['konu']}")

        st.markdown(f"""
        **ID:** `{kayit['id']}` &nbsp;|&nbsp; **Tarih:** `{kayit['tarih']}` &nbsp;|&nbsp; **Kategori:** `{kayit.get('sektor', '—')}` &nbsp;|&nbsp; **Durum:** `{durum}`  
        **RAG Hit Sayısı:** `{kayit.get('kullanım_sayisi', 0)}` &nbsp;|&nbsp; **Referans Sayacı:** `{kayit.get('referans_sayaci', 0)}`
        """)

        st.markdown(f"**Uyumlu Mevzuat:** `{kayit.get('uyumlu_mevzuat', '—')}`")
        ilgili_maddeler = kayit.get("ilgili_kanun_maddeleri", [])
        if ilgili_maddeler:
            st.markdown(f"**İlgili Kanun Maddeleri:** {', '.join(ilgili_maddeler)}")
        st.markdown(f"**Onaylayan Roller:** {', '.join(kayit.get('onaylayanlar', []))}")

        # F12 — Traceability: kaynak emsal bağlantısı
        kaynak_emsaller = kayit.get("kaynak_emsal_idleri", [])
        if kaynak_emsaller:
            st.markdown(f"**Kaynak Emsal(ler):** {', '.join(kaynak_emsaller)}")

        with st.expander("Görüntüle (Anonimleştirilmiş İçerik)", expanded=False):
            st.info("Aşağıdaki metin, maskeleme katmanlarından geçmiş olup RAG sistemini beslemek üzere tutulmaktadır.")
            st.markdown(
                f'''
                <div style="background-color:#f8fafc;padding:15px;border-radius:8px;
                    border:1px solid #e2e8f0;white-space:pre-wrap;
                    font-family:monospace;color:#334155;">
{kayit.get("anonim_metin", "")}
                </div>
                ''',
                unsafe_allow_html=True,
            )

        st.divider()

# ──────────────────────────────────────────────────────────────
# G16 — Mevzuat Değişikliği Tetikleyici (Yönetici Paneli)
# ──────────────────────────────────────────────────────────────
with st.expander("⚙️ Yönetici: Mevzuat Değişikliği Tetikle (G16)", expanded=False):
    st.warning(
        "Bu araç, değişen mevzuat maddelerine referans veren arşiv kayıtlarını "
        "otomatik olarak 'incelemede' durumuna çeker."
    )
    degisen_maddeler_str = st.text_area(
        "Değişen Kanun Maddeleri (her satıra bir tane):",
        placeholder="Örn:\n5393/m.14\n3071/m.7",
    )
    if st.button("🔄 Mevzuat Değişikliği Tara ve Geçersizleştir"):
        if not degisen_maddeler_str.strip():
            st.error("En az bir kanun maddesi giriniz.")
        else:
            maddeler = [m.strip() for m in degisen_maddeler_str.strip().splitlines() if m.strip()]
            etkilenenler = mevzuat_degisiklik_tara(maddeler)
            if etkilenenler:
                st.success(f"✅ {len(etkilenenler)} kayıt 'incelemede' durumuna alındı: {etkilenenler}")
                if audit_logger:
                    audit_logger.log_action(
                        actor="yonetici",
                        action="AUTO_INVALIDATE",
                        document_id="toplu",
                        purpose="Mevzuat değişikliği nedeniyle otomatik geçersizleştirme",
                        details={"degisen_maddeler": maddeler, "etkilenen_sayisi": len(etkilenenler)},
                    )
            else:
                st.info("Bu maddelere referans veren aktif kayıt bulunamadı.")

st.divider()

