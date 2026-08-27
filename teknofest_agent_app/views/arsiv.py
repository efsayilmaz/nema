import streamlit as st

# --------------------------------------------------------------------------
# Arşiv Sayfası
# --------------------------------------------------------------------------
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

import os
import sys

# Proje kök dizini sys.path'e ekleyelim
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '../..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from utils.arsiv_db import arsiv_verilerini_getir
except ImportError:
    def arsiv_verilerini_getir():
        return []

arsiv_verileri = arsiv_verilerini_getir()

if not arsiv_verileri:
    st.warning("Emsal Taslak Arşivi henüz boş. 'Taslak Oluşturma' sayfasından onayladığınız belgeler burada listelenecektir.")
    st.stop()


# Arama çubuğu
arama = st.text_input("🔍 Arşivde Ara (Konu veya ID ile):", placeholder="Örn: Bilgi edinme")

for kayit in arsiv_verileri:
    if arama.lower() not in kayit["konu"].lower() and arama.lower() not in kayit["id"].lower():
        continue
        
    with st.container():
        st.markdown(f"### 📄 {kayit['konu']}")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Kayıt ID", kayit["id"])
        c2.metric("Eklenme Tarihi", kayit["tarih"])
        c3.metric("RAG Hit Sayısı", str(kayit["kullanım_sayisi"]))
        c4.metric("Kategori", kayit["sektor"])
        
        st.markdown(f"**Uyumlu Mevzuat:** `{kayit['uyumlu_mevzuat']}`")
        st.markdown(f"**Onaylayan Roller:** {', '.join(kayit['onaylayanlar'])}")
        
        with st.expander("Görüntüle (Anonimleştirilmiş İçerik)", expanded=True):
            st.info("Aşağıdaki metin, maskeleme katmanlarından geçmiş olup RAG sistemini beslemek üzere vektör veritabanında tutulmaktadır.")
            st.markdown(f'''
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; white-space: pre-wrap; font-family: monospace; color: #334155;">
{kayit["anonim_metin"]}
            </div>
            ''', unsafe_allow_html=True)
            
        st.divider()
