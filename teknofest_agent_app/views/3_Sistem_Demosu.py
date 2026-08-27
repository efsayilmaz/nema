import time
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

from utils.backend_client import gorev1_analiz, gorev2_taslak
from utils.sample_data import SAMPLE_DOCS

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

    if analiz.get("taslak_olusturulabilir_mi") is False:
        adim2 = st.empty()
        adim2.error(
            f"⛔ Mevzuat Engeli ({analiz.get('eksik_bilgi_derecesi', 'Kritik')}): "
            f"{analiz.get('isleme_devam_gerekcesi', 'Zorunlu kimlik/talep bilgisi olmadan resmi yazı taslağı oluşturulamaz.')}"
        )
        st.session_state.gorev1_sonuc = analiz
        st.session_state.gorev2_sonuc = None
        st.session_state.ajan_log = log
        st.divider()
        st.subheader("Evrak Analiz Özeti")
        st.markdown(f"**Evrak Türü:** `{analiz.get('evrak_turu', '—')}` | **Gönderen:** *{(analiz.get('gonderen') or {}).get('ad_soyad_veya_unvan') or 'Belirtilmemiş'}*")
        st.markdown(f"**Konu:** {analiz.get('konu', '—')}")
        st.stop()

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
        st.subheader("Görev 1: Analiz ve Sınıflandırma")
        with st.container(border=True):
            st.markdown(f"**Evrak Türü:** `{analiz.get('evrak_turu', '—')}` | **Aciliyet:** `{analiz.get('aciliyet_durumu', 'Normal')}`")
            gonderen_ad = (analiz.get('gonderen') or {}).get('ad_soyad_veya_unvan') or '—'
            st.markdown(f"**Gönderen:** {gonderen_ad}")
            st.markdown(f"**Konu:** {analiz.get('konu', '—')}")
            st.markdown(f"**Özet:** {analiz.get('kisa_ozet', '—')}")
            mevzuatlar = analiz.get('ilgili_mevzuat_onerisi', [])
            if mevzuatlar:
                st.markdown(f"**İlgili Mevzuat:** {', '.join(mevzuatlar)}")
    with c2:
        st.subheader("Görev 2: Yönlendirme ve Sevk")
        with st.container(border=True):
            yon = taslak.get("yonlendirme_karari", {}) or {}
            bilgi = taslak.get("kullanici_bilgilendirme", {}) or {}
            taslak_govde = taslak.get("resmi_yazi_taslagi", {}) or {}
            st.markdown(f"**İşlem Yapacak Kurum:** `{yon.get('islem_yapacak_ana_kurum', '—')}`")
            st.markdown(f"**Gereği Birimi:** `{yon.get('geregi_icin_yonlendirilecek_birim', '—')}`")
            st.markdown(f"**Yazı Türü:** `{taslak_govde.get('yazi_turu', '—')}`")
            if yon.get("yonlendirme_gerekcesi"):
                st.markdown(f"**Gerekçe:** {yon.get('yonlendirme_gerekcesi')}")
            st.markdown(f"**Vatandaş Bilgilendirme:** {bilgi.get('kullaniciya_gosterilecek_mesaj', '—')}")

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
