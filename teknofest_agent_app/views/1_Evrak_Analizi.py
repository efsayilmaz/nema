import streamlit as st
import sys
import os
import tempfile

# Proje kök dizini ve app dizinini sys.path'e ekleyelim
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.abspath(os.path.join(current_dir, '..'))
root_dir = os.path.abspath(os.path.join(current_dir, '../..'))
for path in [app_dir, root_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    from evrak_okuyucu import evrak_oku
except ImportError:
    evrak_oku = None

from utils.backend_client import gorev1_analiz
from utils.sample_data import SAMPLE_DOCS

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
    st.session_state.islenen_dosya = None

yuklenen = st.file_uploader(
    "Veya bir dosya yükleyin (.txt, .pdf, .docx)",
    type=["txt", "pdf", "docx"],
    help="Yüklenen dosyalar OCR ve metin çıkarma modülüyle analiz edilip metin kutusuna aktarılır.",
)

if yuklenen is not None:
    # Dosya değişmişse veya ilk defa yüklenmişse OCR çalışsın
    if st.session_state.get("islenen_dosya") != yuklenen.name:
        if evrak_oku is None:
            st.error("evrak_okuyucu modülü yüklenemedi!")
        else:
            with st.spinner(f"{yuklenen.name} okunuyor... (OCR işlemi gerekliyse birkaç saniye sürebilir)"):
                uzanti = os.path.splitext(yuklenen.name)[1].lower()
                # Temp dosya oluştur
                with tempfile.NamedTemporaryFile(delete=False, suffix=uzanti) as tmp_file:
                    tmp_file.write(yuklenen.getvalue())
                    tmp_path = tmp_file.name
                
                try:
                    sonuc = evrak_oku(tmp_path)
                    if "hata" in sonuc:
                        st.error(f"Dosya okuma hatası: {sonuc['hata']}")
                    else:
                        st.session_state.evrak_metni = sonuc.get("ham_metin", "")
                        st.session_state.islenen_dosya = yuklenen.name
                        if sonuc.get("guven_notu"):
                            st.warning(sonuc["guven_notu"])
                        st.success(f"Dosya okundu: {yuklenen.name} ({sonuc.get('okuma_yontemi')})")
                        st.rerun() # Metin alanını güncellemek için sayfayı yeniden yükle
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

    # İşlenmiş dosyayı görsel olarak önizle
    if yuklenen.type in ("image/png", "image/jpeg"):
        st.image(yuklenen, caption=yuklenen.name, width=250)
    else:
        st.markdown(f"📄 **{yuklenen.name}** sisteme aktarıldı.")
else:
    st.session_state.islenen_dosya = None

st.session_state.evrak_metni = st.text_area(
    "Evrak metni (Üzerinde değişiklik yapabilirsiniz)", 
    value=st.session_state.evrak_metni, 
    height=250,
    placeholder="Evrak metnini buraya yapıştırın veya yukarıdan bir dosya yükleyin...",
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
    if s.get("ozet_basarili", True):
        st.info(s.get("kisa_ozet", "—"))
    else:
        st.warning("Özet oluşturulamadı; ham metin gösteriliyor.")
        st.text_area("Ham Evrak Metni", value=st.session_state.evrak_metni, height=220, disabled=True)

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
        mevzuat = s.get("ilgili_mevzuat_onerisi", [])
        if mevzuat:
            for m in mevzuat:
                st.markdown(f"- {m}")
        else:
            st.markdown("- Mevzuat tespit edilemedi")

    st.markdown("**İşleme Devam Edilebilirlik ve Mevzuat Derecelendirmesi**")
    devam_durumu = s.get("isleme_devam_edilebilirlik_durumu", {}) or {}
    taslak_olur = s.get("taslak_olusturulabilir_mi", devam_durumu.get("taslak_olusturulabilir_mi", True))
    derece = s.get("eksik_bilgi_derecesi", devam_durumu.get("derece", "Eksiksiz (Doğrudan Üst Yazı Yazılabilir)"))
    gerekce = s.get("isleme_devam_gerekcesi", devam_durumu.get("gerekce", ""))
    zorunlu_eksikler = devam_durumu.get("zorunlu_eksikler", [])
    tamamlanabilir_eksikler = devam_durumu.get("tamamlanabilir_eksikler") or devam_durumu.get("zorunlu_olmayan_eksikler", [])

    with st.container(border=True):
        if not taslak_olur:
            st.error(
                f"⛔ **Mevzuat Engeli: {derece}**\n\n"
                f"{gerekce}"
            )
            if zorunlu_eksikler:
                st.markdown("**Zorunlu Eksiklikler (3071 m.4/6, 4982 m.6):**")
                for eksik in zorunlu_eksikler:
                    st.markdown(
                        f"- 🔴 **{eksik.get('bilgi', 'Belirtilmemiş')}:** "
                        f"*{eksik.get('mevzuat_maddesi', 'İlgili Kanun')}* — {eksik.get('sonuc', 'İşlem engellenir.')}"
                    )
            st.info("💡 **Ajan Notu:** Bu evrak mevzuat gereği doğrudan sevk edilemez. Taslak oluşturabilmek için lütfen sol menüden veya evrak metninden başvuru sahibi kimlik/talep bilgilerini ekleyiniz.")
        elif tamamlanabilir_eksikler or "Tamamlanabilir" in str(derece):
            st.warning(
                f"⚠️ **Mevzuat Değerlendirmesi: {derece}**\n\n"
                f"{gerekce}"
            )
            st.markdown("**Tamamlatılabilecek İdari Eksiklikler:**")
            for eksik in tamamlanabilir_eksikler:
                st.markdown(
                    f"- 🟡 **{eksik.get('bilgi', 'Belirtilmemiş')}:** "
                    f"*{eksik.get('mevzuat_maddesi', 'İlgili Kanun/Yönetmelik')}* — {eksik.get('sonuc', 'Eksik Belge Talebi yazısıyla tamamlanabilir.')}"
                )
        else:
            st.success(
                f"✅ **Mevzuata Uygunluk: {derece}**\n\n"
                f"{gerekce or 'Evrak yasal ve idari unsurları tam taşımaktadır. Doğrudan üst yazı üretilebilir.'}"
            )

    with st.expander("Ham JSON Çıktı (Backend Kontrolü)"):
        st.json(s)

    st.divider()
    if taslak_olur:
        btn_label = "→  Eksik Belge Talebi Taslağı Oluştur (Görev 2)" if tamamlanabilir_eksikler else "→  Resmi Yazı Taslağı Oluştur (Görev 2)"
        st.page_link(
            "views/2_Taslak_Olusturma.py",
            label=btn_label,
        )
    else:
        st.button("⛔ Görev 2 Engellendi (Mevzuat Gereği Taslak Oluşturulamaz)", disabled=True, use_container_width=True)
