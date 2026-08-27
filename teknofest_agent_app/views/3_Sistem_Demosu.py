import time
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

from utils.backend_client import gorev1_analiz, gorev2_taslak
from utils.sample_data import SAMPLE_DOCS

# --------------------------------------------------------------------------
# Sayfa Başlığı ve Açıklama
# --------------------------------------------------------------------------
st.title("Uçtan Uca Sistem Demosu")

st.markdown(
    """
    <style>
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
    <div class="system-desc">
        Evrak girişinden resmî yazı taslağı ve yetkili birim yönlendirmesine kadar 
        tüm çok ajanlı karar destek akışını tek adımda ve canlı olarak simüle edin.
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Session State Başlatma
# --------------------------------------------------------------------------
if "demo_evrak_metni" not in st.session_state:
    st.session_state.demo_evrak_metni = SAMPLE_DOCS[0]["metin"]
if "demo_secilen_ornek" not in st.session_state:
    st.session_state.demo_secilen_ornek = SAMPLE_DOCS[0]["baslik"]
if "demo_ek_bilgi" not in st.session_state:
    st.session_state.demo_ek_bilgi = ""
if "demo_islenen_dosya" not in st.session_state:
    st.session_state.demo_islenen_dosya = None

# --------------------------------------------------------------------------
# 1. BÖLÜM: Evrak Girişi ve Ön Hazırlık
# --------------------------------------------------------------------------
st.subheader("1. Evrak Girişi")

giris_yontemi = st.radio(
    "Giriş yöntemi seçiniz:",
    ["Örnek Senaryo", "Manuel Metin Girişi", "Dosya Yükleme (.pdf, .docx, .txt)"],
    horizontal=True,
)

if giris_yontemi == "Örnek Senaryo":
    secilen_baslik = st.selectbox(
        "Senaryo seçiniz:",
        [d["baslik"] for d in SAMPLE_DOCS],
        index=[d["baslik"] for d in SAMPLE_DOCS].index(st.session_state.demo_secilen_ornek)
        if st.session_state.demo_secilen_ornek in [d["baslik"] for d in SAMPLE_DOCS]
        else 0,
    )
    if secilen_baslik != st.session_state.demo_secilen_ornek:
        st.session_state.demo_secilen_ornek = secilen_baslik
        secilen_doc = next(d for d in SAMPLE_DOCS if d["baslik"] == secilen_baslik)
        st.session_state.demo_evrak_metni = secilen_doc["metin"]
        st.rerun()

elif giris_yontemi == "Dosya Yükleme (.pdf, .docx, .txt)":
    yuklenen = st.file_uploader(
        "Dosya seçiniz:",
        type=["txt", "pdf", "docx", "png", "jpg", "jpeg"],
        help="Yüklenen dosya metin çıkarma modülüyle taranıp aşağıdaki düzenleme alanına aktarılır.",
    )
    if yuklenen is not None:
        if st.session_state.demo_islenen_dosya != yuklenen.name:
            if evrak_oku is None:
                st.error("evrak_okuyucu modülü bulunamadı.")
            else:
                with st.spinner(f"'{yuklenen.name}' okunuyor..."):
                    uzanti = os.path.splitext(yuklenen.name)[1].lower()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=uzanti) as tmp_file:
                        tmp_file.write(yuklenen.getvalue())
                        tmp_path = tmp_file.name
                    try:
                        sonuc = evrak_oku(tmp_path)
                        if "hata" in sonuc:
                            st.error(f"Dosya okuma hatası: {sonuc['hata']}")
                        else:
                            st.session_state.demo_evrak_metni = sonuc.get("ham_metin", "")
                            st.session_state.demo_islenen_dosya = yuklenen.name
                            if sonuc.get("guven_notu"):
                                st.warning(sonuc["guven_notu"])
                            st.success(f"Dosya içeriği aktarıldı: {yuklenen.name}")
                            st.rerun()
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
    else:
        st.session_state.demo_islenen_dosya = None

# Düzenlenebilir Evrak Metni Alanı
st.session_state.demo_evrak_metni = st.text_area(
    "Evrak metni (üzerinde değişiklik yapabilirsiniz):",
    value=st.session_state.demo_evrak_metni,
    height=200,
    placeholder="Evrak metnini buraya yapıştırabilir veya yazabilirsiniz...",
)

# Bilgi ve Hızlı İşlem Satırı
col_info, col_btn1, col_btn2 = st.columns([3.6, 1.2, 1.2], vertical_alignment="center")
with col_info:
    metin_uzunlugu = len(st.session_state.demo_evrak_metni)
    kelime_sayisi = len(st.session_state.demo_evrak_metni.split()) if st.session_state.demo_evrak_metni.strip() else 0
    st.caption(f"Metin boyutu: {kelime_sayisi} kelime, {metin_uzunlugu} karakter")

with col_btn1:
    if st.button("Metni Temizle", use_container_width=True):
        st.session_state.demo_evrak_metni = ""
        st.rerun()

with col_btn2:
    if st.button("Örneği Sıfırla", use_container_width=True):
        st.session_state.demo_evrak_metni = SAMPLE_DOCS[0]["metin"]
        st.session_state.demo_secilen_ornek = SAMPLE_DOCS[0]["baslik"]
        st.rerun()

# Ek Bilgi / Not Girişi
with st.expander("Ek Bilgi / Not Girişi (İsteğe Bağlı)", expanded=False):
    st.session_state.demo_ek_bilgi = st.text_input(
        "Evraka eklenecek idari not veya kimlik bilgisi:",
        value=st.session_state.demo_ek_bilgi,
        placeholder="Örn: Başvuru Sahibi: Ahmet Yılmaz, T.C.: 12345678901",
    )

if st.session_state.demo_mode:
    st.info("Demo modu aktif: Test verileri ve yerel kurallar üzerinden simülasyon yapılmaktadır.")
elif not st.session_state.backend_url:
    st.warning("Backend API adresi tanımlanmamış. Sol menüden bağlantı adresini kontrol ediniz.")

st.divider()

# --------------------------------------------------------------------------
# 2. BÖLÜM: Sıralı Ajan Akışı
# --------------------------------------------------------------------------
st.subheader("2. Karar Destek Süreci")

calistir_butonu = st.button(
    "Süreci Başlat",
    type="primary",
    disabled=not bool(st.session_state.demo_evrak_metni and st.session_state.demo_evrak_metni.strip()),
    use_container_width=True,
)

if calistir_butonu:
    log = []
    st.session_state.evrak_metni = st.session_state.demo_evrak_metni

    with st.status("Ajan karar destek süreci yürütülüyor...", expanded=True) as durum:
        # 1. Adım: Görev 1 - Evrak Analizi
        st.write("1. Adım: Evrak Analiz Ajanı çalışıyor...")
        t0 = time.time()
        analiz, log, hata1 = gorev1_analiz(
            st.session_state.demo_evrak_metni,
            base_url=st.session_state.backend_url,
            demo_mode=st.session_state.demo_mode,
            log=log,
        )
        sure1 = time.time() - t0
        st.write(
            f"1. Adım tamamlandı ({sure1:.2f} sn) — "
            f"Tür: {analiz.get('evrak_turu', '—')} | "
            f"Aciliyet: {analiz.get('aciliyet_durumu', 'Normal')}"
        )
        if hata1:
            st.warning(f"Adım 1 uyarısı: {hata1}")

        # 2. Adım: Mevzuat Analizi ve Şekil Şartı Kontrolü
        st.write("2. Adım: Mevzuat uyum ve şekil şartı kontrolleri yapılıyor...")
        time.sleep(0.2)
        mevzuatlar = analiz.get("ilgili_mevzuat_onerisi", [])
        eksikler = analiz.get("eksik_bilgiler", [])
        st.write(
            f"2. Adım tamamlandı — "
            f"{len(mevzuatlar)} ilgili mevzuat eşleştirildi, "
            f"{len(eksikler)} eksiklik kontrolü tamamlandı."
        )

        # 3. Adım: Mevzuat Engeli Kontrolü (3071 m.4/6)
        taslak_olur = analiz.get("taslak_olusturulabilir_mi", True)
        ek_bilgi_var = bool(st.session_state.demo_ek_bilgi and st.session_state.demo_ek_bilgi.strip())

        if not taslak_olur and not ek_bilgi_var:
            durum.update(label="Mevzuat engeli tespit edildi.", state="error", expanded=True)
            st.error(
                f"Mevzuat Uyarısı ({analiz.get('eksik_bilgi_derecesi', 'Kritik')}): "
                f"{analiz.get('isleme_devam_gerekcesi', '3071 Sayılı Kanun gereğince kimlik/talep bilgisi olmadan taslak üretilemez.')}"
            )
            st.session_state.gorev1_sonuc = analiz
            st.session_state.gorev2_sonuc = None
            st.session_state.ajan_log = log
            st.stop()

        # 4. Adım: Görev 2 - Yetkili Kurum ve Birim Yönlendirme
        st.write("3. Adım: Yetkili Kurum ve Sevk Birimi belirleniyor...")
        t1 = time.time()
        taslak, log, hata2 = gorev2_taslak(
            analiz,
            ek_bilgi=st.session_state.demo_ek_bilgi or None,
            base_url=st.session_state.backend_url,
            demo_mode=st.session_state.demo_mode,
            log=log,
        )
        sure2 = time.time() - t1
        yonlendirme = taslak.get("yonlendirme_karari", {}) or {}
        birim = yonlendirme.get("geregi_icin_yonlendirilecek_birim", "—")
        ana_kurum = yonlendirme.get("islem_yapacak_ana_kurum", "—")
        st.write(
            f"3. Adım tamamlandı ({sure2:.2f} sn) — "
            f"Kurum: {ana_kurum} | Birim: {birim}"
        )

        # 5. Adım: Görev 2 - Resmî Yazı Taslağı ve Bilgilendirme
        st.write("4. Adım: Resmî yazı taslağı ve bilgilendirme metni oluşturuluyor...")
        time.sleep(0.2)
        durum.update(label="İşlem tamamlandı.", state="complete", expanded=False)

    st.session_state.gorev1_sonuc = analiz
    st.session_state.gorev2_sonuc = taslak
    st.session_state.ajan_log = log

# --------------------------------------------------------------------------
# 3. BÖLÜM: Çıktılar ve Karar Destek Paneli
# --------------------------------------------------------------------------
if st.session_state.gorev1_sonuc and st.session_state.gorev2_sonuc:
    analiz = st.session_state.gorev1_sonuc
    taslak = st.session_state.gorev2_sonuc
    yonlendirme = taslak.get("yonlendirme_karari", {}) or {}
    resmi_yazi = taslak.get("resmi_yazi_taslagi", {}) or {}
    bilgilendirme = taslak.get("kullanici_bilgilendirme", {}) or {}

    st.markdown("---")
    st.subheader("3. Karar Destek Çıktıları")

    # Temel Metrikler
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Evrak Türü", analiz.get("evrak_turu", "—"))
    kpi2.metric("Aciliyet Durumu", analiz.get("aciliyet_durumu", "Normal"))
    kpi3.metric("Yetkili Ana Kurum", yonlendirme.get("islem_yapacak_ana_kurum", "—"))
    kpi4.metric("Sevk Edilen Birim", yonlendirme.get("geregi_icin_yonlendirilecek_birim", "—"))

    # Sekmeli Detay Görünümü
    tab_yazi, tab_analiz, tab_yonlendirme, tab_log = st.tabs([
        "Resmî Yazı Taslağı",
        "Evrak Analizi ve Mevzuat",
        "Yönlendirme ve Bilgilendirme",
        "İşlem Günlüğü",
    ])

    # ----------------------------------------------------------------------
    # SEKME 1: Resmî Yazı Taslağı
    # ----------------------------------------------------------------------
    with tab_yazi:
        st.markdown("##### Resmî Yazışma Taslağı")
        
        c_meta1, c_meta2 = st.columns([3, 1])
        with c_meta1:
            st.markdown(f"**Konu:** {resmi_yazi.get('konu', '—')}")
            st.markdown(f"**İlgi:** {resmi_yazi.get('ilgi', '—')}")
        with c_meta2:
            st.markdown(f"**Yazı Türü:** `{resmi_yazi.get('yazi_turu', '—')}`")
            st.markdown(f"**İmza Makamı:** `{resmi_yazi.get('imza_makami', '—')}`")

        govde = st.text_area(
            "Taslak Gövde Metni",
            value=resmi_yazi.get("govde_metni", ""),
            height=180,
            key="demo_taslak_govde_metni",
            help="Gerekirse doğrudan üzerinde düzenleme yapabilirsiniz.",
        )

        tam_nihai_metin = (
            f"T.C.\n"
            f"{yonlendirme.get('islem_yapacak_ana_kurum', 'İLGİLİ KURUM')}\n"
            f"{yonlendirme.get('geregi_icin_yonlendirilecek_birim', 'İLGİLİ BİRİM')}\n\n"
            f"Sayı  : {analiz.get('sayi_veya_kayit_no') or '[SAYI BELİRTİLECEK]'}\n"
            f"Tarih : {analiz.get('evrak_tarihi') or time.strftime('%d.%m.%Y')}\n"
            f"Konu  : {resmi_yazi.get('konu', '')}\n\n"
            f"İlgi  : {resmi_yazi.get('ilgi', '')}\n\n"
            f"{govde}\n\n"
            f"{' ' * 40}{resmi_yazi.get('imza_makami', 'Birim Amiri')}\n"
            f"{' ' * 40}İmza"
        )

        btn_col1, btn_col2 = st.columns([1.2, 2.8], vertical_alignment="center")
        with btn_col1:
            st.download_button(
                "Yazıyı İndir (.txt)",
                tam_nihai_metin,
                file_name="resmi_yazi_taslagi.txt",
                use_container_width=True,
            )
        with btn_col2:
            durum_mesaj = bilgilendirme.get("sistem_aksiyon_durumu", "İşleme Alındı")
            st.markdown(f"**Sistem Durumu:** `{durum_mesaj}`")

    # ----------------------------------------------------------------------
    # SEKME 2: Evrak Analizi ve Mevzuat
    # ----------------------------------------------------------------------
    with tab_analiz:
        col_g1_left, col_g1_right = st.columns(2)
        with col_g1_left:
            st.markdown("##### Temel Bilgiler")
            with st.container(border=True):
                st.markdown(f"**Konu:** {analiz.get('konu', '—')}")
                st.markdown(f"**Özet:** {analiz.get('kisa_ozet', '—')}")
                st.markdown(f"**Evrak Tarihi:** {analiz.get('evrak_tarihi') or 'Belirtilmemiş'}")
                st.markdown(f"**Kayıt / Sayı No:** {analiz.get('sayi_veya_kayit_no') or 'Belirtilmemiş'}")

            st.markdown("##### Gönderen Bilgileri")
            gonderen = analiz.get("gonderen", {}) or {}
            with st.container(border=True):
                st.markdown(f"**Gönderen Tipi:** `{gonderen.get('gonderen_tipi', '—')}`")
                st.markdown(f"**Ad Soyad / Unvan:** {gonderen.get('ad_soyad_veya_unvan') or 'Belirtilmemiş'}")
                st.markdown(f"**Kimlik / Vergi No:** {gonderen.get('kimlik_veya_vergi_no') or 'Belirtilmemiş'}")
                st.markdown(f"**İletişim:** {gonderen.get('iletisim_bilgisi') or 'Belirtilmemiş'}")

        with col_g1_right:
            st.markdown("##### Tespit Edilen Varlıklar")
            varliklar = analiz.get("varliklar", {}) or {}
            with st.container(border=True):
                kurumlar_list = varliklar.get("kurumlar", [])
                lokasyon_list = varliklar.get("lokasyonlar", [])
                tarih_list = varliklar.get("tarihler", [])
                st.markdown(f"**Kurumlar:** {', '.join(kurumlar_list) if kurumlar_list else '—'}")
                st.markdown(f"**Lokasyonlar:** {', '.join(lokasyon_list) if lokasyon_list else '—'}")
                st.markdown(f"**Tarihler:** {', '.join(tarih_list) if tarih_list else '—'}")

            st.markdown("##### İlgili Mevzuat ve Şekil Şartları")
            with st.container(border=True):
                mevzuat_list = analiz.get("ilgili_mevzuat_onerisi", [])
                if mevzuat_list:
                    for m in mevzuat_list:
                        st.markdown(f"- {m}")
                else:
                    st.markdown("—")
                
                eksik_list = analiz.get("eksik_bilgiler", [])
                if eksik_list:
                    st.markdown("**Tespit Edilen Eksiklikler:**")
                    for e in eksik_list:
                        st.markdown(f"- {e}")
                else:
                    st.success("Zorunlu veya şekil şartı eksikliği bulunmamaktadır.")

    # ----------------------------------------------------------------------
    # SEKME 3: Yönlendirme ve Bilgilendirme
    # ----------------------------------------------------------------------
    with tab_yonlendirme:
        col_y1, col_y2 = st.columns(2)
        with col_y1:
            st.markdown("##### Yönlendirme ve Sevk Kararı")
            with st.container(border=True):
                st.markdown(f"**İşlem Yapacak Ana Kurum:** `{yonlendirme.get('islem_yapacak_ana_kurum', '—')}`")
                st.markdown(f"**Gereği İçin Sevk Birimi:** `{yonlendirme.get('geregi_icin_yonlendirilecek_birim', '—')}`")
                bilgi_birim = yonlendirme.get("bilgi_icin_iletilecek_birimler", [])
                st.markdown(f"**Bilgi İçin İletilecek Birimler:** {', '.join(bilgi_birim) if bilgi_birim else 'Yok'}")
                if yonlendirme.get("yonlendirme_gerekcesi"):
                    st.info(f"**Gerekçe:** {yonlendirme.get('yonlendirme_gerekcesi')}")

        with col_y2:
            st.markdown("##### Vatandaş Bilgilendirme Metni")
            with st.container(border=True):
                st.markdown("**Bildirim Metni:**")
                st.success(bilgilendirme.get("kullaniciya_gosterilecek_mesaj", "—"))
                st.caption(f"Sistem Durumu: {bilgilendirme.get('sistem_aksiyon_durumu', 'İşleme Alındı')}")

    # ----------------------------------------------------------------------
    # SEKME 4: Ajan İşlem Günlüğü
    # ----------------------------------------------------------------------
    with tab_log:
        st.markdown("##### İşlem Günlüğü")
        if st.session_state.ajan_log:
            st.table(st.session_state.ajan_log)
        else:
            st.info("Henüz log kaydı oluşmadı.")

elif st.session_state.gorev1_sonuc and not st.session_state.gorev2_sonuc:
    analiz = st.session_state.gorev1_sonuc
    st.markdown("---")
    st.subheader("3. Ön İnceleme ve Mevzuat Engeli Raporu")
    
    st.error(
        f"Mevzuat Uyarısı ({analiz.get('eksik_bilgi_derecesi', 'Kritik')}): "
        f"{analiz.get('isleme_devam_gerekcesi', '3071 Sayılı Kanun gereğince kimlik/talep bilgisi olmadan taslak üretilemez.')}"
    )

    with st.container(border=True):
        st.markdown(f"**Evrak Türü:** `{analiz.get('evrak_turu', '—')}` | **Konu:** *{analiz.get('konu', '—')}*")
        st.markdown(f"**Özet:** {analiz.get('kisa_ozet', '—')}")
        eksikler = analiz.get("eksik_bilgiler", [])
        if eksikler:
            st.markdown("**Tespit Edilen Eksiklikler:** " + ", ".join([f"`{e}`" for e in eksikler]))

    st.markdown("##### Eksik Bilgileri Tamamlama:")
    ek_bilgi_input = st.text_input(
        "Zorunlu Eksik Bilgiler (Ad-Soyad, T.C. Kimlik No, İletişim vb.):",
        placeholder="Örn: Başvuru Sahibi: Mehmet Kaya, T.C.: 11223344556",
        key="demo_hata_ek_bilgi",
    )

    if st.button("Eksik Bilgilerle Taslağı Oluştur", type="primary", disabled=not bool(ek_bilgi_input.strip())):
        st.session_state.demo_ek_bilgi = ek_bilgi_input
        with st.spinner("Görev 2 Ajanı çalıştırılıyor..."):
            taslak, log, hata = gorev2_taslak(
                analiz,
                ek_bilgi=ek_bilgi_input,
                base_url=st.session_state.backend_url,
                demo_mode=st.session_state.demo_mode,
                log=st.session_state.ajan_log,
            )
        st.session_state.gorev2_sonuc = taslak
        st.session_state.ajan_log = log
        st.rerun()
