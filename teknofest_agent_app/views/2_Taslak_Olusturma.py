import streamlit as st
import sys
import os
import uuid
import datetime
import json

# Proje kök dizini ve app dizinini sys.path'e ekleyelim
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.abspath(os.path.join(current_dir, '..'))
root_dir = os.path.abspath(os.path.join(current_dir, '../..'))
for path in [app_dir, root_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

from utils.backend_client import gorev2_taslak
# C6 — Kalıcı onay yöneticisi (session_state'e bağımlı değil)
from utils.onay_yonetici import (
    onay_token_uret,
    icerik_onayi_kaydet,
    kvkk_onayi_kaydet,
    onay_durumu_getir,
    onay_iptal_et,
)

_DURUM_RENK = {"İşleme Alındı": "", "Kullanıcı Bekleniyor": "", "Onay Bekliyor": ""}

# ──────────────────────────────────────────────────────────────
# Ana Başlık ve Giriş
# ──────────────────────────────────────────────────────────────
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

with st.container():
    st.markdown(f"**İncelenen Evrak:** `{analiz.get('evrak_turu', '—')}` | **Konu:** *{analiz.get('konu', '—')}*")

taslak_olur = analiz.get("taslak_olusturulabilir_mi", True)
derece = analiz.get("eksik_bilgi_derecesi", "")

ek_bilgi = ""
eksikler = [e for e in analiz.get("eksik_bilgiler", []) if e]

if not taslak_olur:
    st.error(
        f"Mevzuat Uyarısı ({derece}):\n\n"
        f"{analiz.get('isleme_devam_gerekcesi', '3071 Sayılı Kanun gereğince kimlik/talep bilgisi olmadan taslak üretilemez.')}\n\n"
        f"Taslağın oluşturulabilmesi için lütfen aşağıdaki alana eksik olan zorunlu bilgileri giriniz."
    )
    ek_bilgi = st.text_input("Zorunlu Ek Bilgi / Kimlik Girişi:", placeholder="Örn: Başvuru Sahibi: Ahmet Yılmaz, T.C.: 12345678901")
elif eksikler:
    st.warning("Tamamlanabilir İdari Eksiklikler: " + ", ".join(eksikler))
    ek_bilgi = st.text_input("Ek Bilgi / Not Girişi (Opsiyonel):", placeholder="Taslağa eklenecek notlar...")

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

# ──────────────────────────────────────────────────────────────
# Sonuç Alanları
# ──────────────────────────────────────────────────────────────
if st.session_state.gorev2_sonuc:
    s = st.session_state.gorev2_sonuc
    yonlendirme = s.get("yonlendirme_karari", {}) or {}
    taslak = s.get("resmi_yazi_taslagi", {}) or {}
    bilgilendirme = s.get("kullanici_bilgilendirme", {}) or {}

    st.markdown("---")

    st.subheader("Yönlendirme ve Sevk Kararı")
    m1, m2, m3 = st.columns(3)
    m1.metric("İşlem Yapacak Kurum", yonlendirme.get("islem_yapacak_ana_kurum", "—"))
    m2.metric("Gereği İçin Sevk Birimi", yonlendirme.get("geregi_icin_yonlendirilecek_birim", "—"))
    bilgi_birimleri = yonlendirme.get("bilgi_icin_iletilecek_birimler", [])
    m3.metric("Bilgi Birimleri", ", ".join(bilgi_birimleri) if bilgi_birimleri else "Yok")

    if yonlendirme.get("yonlendirme_gerekcesi"):
        st.info(f"**Yönlendirme Gerekçesi:** {yonlendirme.get('yonlendirme_gerekcesi')}")

    st.divider()

    st.subheader("Resmî Yazı Taslağı")
    h_col1, h_col2 = st.columns([3, 1])
    with h_col1:
        st.markdown(f"**Konu:** {taslak.get('konu', '—')}")
        st.markdown(f"**İlgi:** {taslak.get('ilgi', '—')}")
    with h_col2:
        st.markdown(f"**Yazı Türü:** `{taslak.get('yazi_turu', '—')}`")
        st.markdown(f"**İmza:** `{taslak.get('imza_makami', '—')}`")

    duzenlenmis_govde = st.text_area(
        "Nihai Resmî Yazı (Düzenlenebilir)",
        value=taslak.get("govde_metni", ""),
        height=350,
        help="Gerekirse doğrudan üzerinde düzeltme yapabilirsiniz.",
    )
    tam_metin = duzenlenmis_govde

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

    st.success(f"**Vatandaş Bilgilendirme:** {bilgilendirme.get('kullaniciya_gosterilecek_mesaj', '—')}")

    st.divider()

    # ──────────────────────────────────────────────────────────
    # Arşivleme ve Çift İnsan Onayı (C6 — kalıcı, dosya tabanlı)
    # ──────────────────────────────────────────────────────────
    st.subheader("🔒 Güvenlik ve Arşiv Onayı")
    st.info(
        "Arşive kayıt için onay vermeniz gerekmektedir:\n"
        "1. **İçerik Uzmanı** — Taslağın hukuki/içerik doğruluğunu onaylar.\n"
        "Onay sonrası sistem **otomatik olarak** KVKK maskelemesini (anonimleştirme) yapar ve taslağı arşive ekler."
    )

    # C6 — Taslağa özgü deterministik token (sayfa yenilemesine dayanıklı)
    onay_token = onay_token_uret(
        taslak_konu=taslak.get("konu", ""),
        taslak_govde=taslak.get("govde_metni", ""),
    )
    mevcut_onay = onay_durumu_getir(onay_token)

    # ── Onay durumu gösterge paneli ──────────────────────────
    adim1_durum = "✅ Tamamlandı" if mevcut_onay and mevcut_onay.get("durum") == "tamamlandi" else "⏳ Bekliyor"
    st.metric("Arşiv Onayı", adim1_durum)
    if mevcut_onay:
        st.caption(
            f"Onaylayan: `{mevcut_onay.get('icerik_onaylayan')}` "
            f"| {mevcut_onay.get('icerik_onay_zamani', '')[:19].replace('T', ' ')} UTC"
        )

    st.divider()

    if not mevcut_onay or mevcut_onay.get("durum") != "tamamlandi":
        with st.expander("📋 İçerik / Hukuki Doğruluk Onayı", expanded=True):
            icerik_onaylayan = st.text_input(
                "İçerik Uzmanı Sicil No:",
                key="icerik_onaylayan_sicil",
                placeholder="Örn: ICU-2026-0042",
            )
            if st.button("✅ Onayla ve Otomatik Maskeleyerek Arşive Ekle", use_container_width=True, type="primary"):
                if not icerik_onaylayan.strip():
                    st.error("Sicil numarası zorunludur.")
                else:
                    icerik_onayi_kaydet(
                        onay_token=onay_token,
                        onaylayan_sicil=icerik_onaylayan.strip(),
                        konu=taslak.get("konu", "BILINMIYOR"),
                        evrak_turu=analiz.get("evrak_turu", ""),
                    )
                    try:
                        from utils.secure_logger import audit_logger as _logger
                        _logger.log_action(
                            actor=icerik_onaylayan.strip(),
                            action="APPROVE_CONTENT",
                            document_id=taslak.get("konu", "BILINMIYOR")[:60],
                            purpose="İçerik/hukuki doğruluk onayı",
                            details={"onay_token": onay_token, "evrak_turu": analiz.get("evrak_turu")},
                        )
                    except Exception as _e:
                        st.warning(f"Log yazılamadı: {_e}")
                    
                    # Otomatik KVKK Maskeleme Başlıyor
                    try:
                        from gorev2.arsiv_ajani import arsiv_kayit_talebi_olustur
                        from evren_client import get_evren_client
                        from utils.arsiv_db import arsive_ekle

                        mevzuat_listesi = analiz.get("ilgili_mevzuat_onerisi", [])
                        uyumlu_mevzuat = mevzuat_listesi[0] if mevzuat_listesi else "Belirtilmedi"
                        sektor = analiz.get("evrak_turu", "Genel İdari")

                        with st.spinner("🤖 Otomatik KVKK Maskelemesi (Anonimleştirme) yapılıyor..."):
                            talep = arsiv_kayit_talebi_olustur(tam_metin, sektor, get_evren_client())

                        if talep["guvenlik_durumu"] == "MANUEL_INCELEME":
                            st.error(
                                "⚠️ KVKK denetiminde sızıntı riski tespit edildi! "
                                "(Özel veri kalmış olabilir)"
                            )
                            with st.expander("Denetim Raporu Detayı"):
                                st.json(talep["denetim_raporu"])
                            st.error("🚨 Bu evrak arşive EKLENMEDİ. Manuel inceleme kuyruğuna alındı.")
                            onay_kaydi_sahte = {"icerik_onaylayan": icerik_onaylayan.strip(), "kvkk_onaylayan": "SISTEM_OTOMASYON"}
                            _manuel_inceleme_kuyruğuna_yaz(talep, sektor, taslak, analiz, onay_kaydi_sahte)
                            onay_iptal_et(onay_token)
                            st.rerun()
                        else:
                            talep_id = f"ARS-{datetime.date.today().strftime('%Y-%m')}-{str(uuid.uuid4())[:4].upper()}"
                            _logger.log_action(
                                actor="SISTEM_OTOMASYON",
                                action="APPROVE_KVKK",
                                document_id=talep_id,
                                purpose="Otomatik KVKK anonimleştirme",
                                details={
                                    "onay_token": onay_token,
                                    "icerik_onaylayan": icerik_onaylayan.strip(),
                                    "denetim_raporu": talep["denetim_raporu"],
                                },
                            )
                            _logger.log_action(
                                actor="sistem",
                                action="ARCHIVE_WRITE",
                                document_id=talep_id,
                                purpose="Emsal taslak arşive eklendi",
                                details={"sektor": sektor, "konu": taslak.get("konu")},
                            )
                            yeni_kayit = {
                                "id": talep_id,
                                "sektor": sektor,
                                "tarih": datetime.date.today().strftime("%Y-%m-%d"),
                                "konu": taslak.get("konu", "Belirtilmedi"),
                                "onaylayanlar": [
                                    f"İçerik Uzmanı: {icerik_onaylayan.strip()}",
                                ],
                                "anonim_metin": talep["anonim_taslak"],
                                "uyumlu_mevzuat": uyumlu_mevzuat,
                                "evrak_turu": analiz.get("evrak_turu", ""),
                                "ilgili_kanun_maddeleri": analiz.get("ilgili_mevzuat_onerisi", []),
                            }
                            arsive_ekle(yeni_kayit)
                            # Sistemi tamamlandı moduna alalım
                            kvkk_onayi_kaydet(onay_token, "SISTEM_OTOMASYON")
                            
                            st.success(
                                f"🎉 Taslak başarıyla maskelendi ve arşive eklendi!\n\n"
                                f"📋 **Kayıt ID:** `{talep_id}`"
                            )
                            with st.expander("Görüntüle: Arşive Eklenen Maskelenmiş (Anonim) Metin", expanded=True):
                                st.write(talep["anonim_taslak"])
                            # st.rerun() # Rerun atarsak maskelenmiş metin hemen kaybolur (başa döner/refresh atar).
                            # O yüzden success state'inde kalsın.
                    except Exception as e:
                        st.error(f"Kayıt sırasında hata: {str(e)}")
                        onay_iptal_et(onay_token)
    else:
        st.success(f"🎉 **Bu taslak arşive kaydedildi.** Onaylayan: `{mevcut_onay.get('icerik_onaylayan')}`")
        if st.button("🔄 Yeni Arşiv Kaydı Başlat"):
            onay_iptal_et(onay_token)
            st.rerun()


def _manuel_inceleme_kuyruğuna_yaz(talep: dict, sektor: str, taslak: dict, analiz: dict, onay_kaydi: dict = None):
    """B5 — MANUEL_INCELEME durumundaki vakaları kalıcı kuyruğa yazar."""
    kuyruk_dosyasi = os.path.join(root_dir, "logs", "manuel_inceleme_kuyrugu.jsonl")
    os.makedirs(os.path.dirname(kuyruk_dosyasi), exist_ok=True)
    kayit = {
        "talep_id": talep.get("talep_id", str(uuid.uuid4())),
        "tarih": datetime.datetime.utcnow().isoformat() + "Z",
        "sektor": sektor,
        "konu": taslak.get("konu", ""),
        "evrak_turu": analiz.get("evrak_turu", ""),
        "icerik_onaylayan": (onay_kaydi or {}).get("icerik_onaylayan", "bilinmiyor"),
        "kvkk_onaylayan": (onay_kaydi or {}).get("kvkk_onaylayan", "bilinmiyor"),
        "guvenlik_durumu": talep["guvenlik_durumu"],
        "denetim_raporu": talep["denetim_raporu"],
        "durum": "bekliyor",
    }
    with open(kuyruk_dosyasi, "a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
