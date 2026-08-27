import streamlit as st
import sys
import os

# Proje kök dizini ve app dizinini sys.path'e ekleyelim
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.abspath(os.path.join(current_dir, '..'))
root_dir = os.path.abspath(os.path.join(current_dir, '../..'))
for path in [app_dir, root_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

from utils.backend_client import gorev2_taslak

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
    st.page_link("views/1_Evrak_Analizi.py", label="← Evrak Analizine Git")
    st.stop()

analiz = st.session_state.gorev1_sonuc

# Üst Bilgi Çubuğu
with st.container():
    st.markdown(f"**İncelenen Evrak:** `{analiz.get('evrak_turu', '—')}` | **Konu:** *{analiz.get('konu', '—')}*")

taslak_olur = analiz.get("taslak_olusturulabilir_mi", True)
derece = analiz.get("eksik_bilgi_derecesi", "")

# Eksik Bilgiler & Ek Bilgi Girişi
ek_bilgi = ""
eksikler = [e for e in analiz.get("eksik_bilgiler", []) if e]

if not taslak_olur:
    st.error(
        f"Mevzuat Uyarısı ({derece}):\n\n"
        f"{analiz.get('isleme_devam_gerekcesi', '3071 Sayılı Kanun gereğince kimlik/talep bilgisi olmadan taslak üretilemez.')}\n\n"
        f"Taslağın oluşturulabilmesi için lütfen aşağıdaki alana eksik olan zorunlu bilgileri (Ad-Soyad, Konu vb.) giriniz."
    )
    ek_bilgi = st.text_input("Zorunlu Ek Bilgi / Kimlik Girişi (Gereklidir):", placeholder="Örn: Başvuru Sahibi: Ahmet Yılmaz, T.C.: 12345678901, Konu: ...")
elif eksikler:
    st.warning("Tamamlanabilir İdari Eksiklikler: " + ", ".join(eksikler))
    ek_bilgi = st.text_input("Ek Bilgi / Not Girişi (Opsiyonel):", placeholder="Taslağa veya cevaba eklenecek notları yazabilirsiniz...")

buton_devre_disi = (not taslak_olur and not (ek_bilgi and ek_bilgi.strip()))

if st.button(
    "Resmi Yazı Taslağı ve Yönlendirme Oluştur",
    type="primary",
    disabled=buton_devre_disi,
    use_container_width=True,
):
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
            "Taslağı İndir (.txt)",
            tam_metin,
            file_name="resmi_yazi_taslagi.txt",
            use_container_width=True,
        )
    with info_c:
        durum = bilgilendirme.get("sistem_aksiyon_durumu", "—")
        st.markdown(f"**Sistem Durumu:** {_DURUM_RENK.get(durum, '')} **{durum}**")

    # Vatandaş Mesajı
    st.success(f"**Vatandaş Bilgilendirme:** {bilgilendirme.get('kullaniciya_gosterilecek_mesaj', '—')}")
