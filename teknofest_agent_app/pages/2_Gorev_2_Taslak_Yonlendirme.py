import streamlit as st

from utils.backend_client import gorev2_taslak

st.set_page_config(page_title="Görev 2 - Taslak ve Yönlendirme", page_icon="✍️", layout="wide")

for key, value in {
    "backend_url": "", "demo_mode": True, "evrak_metni": "",
    "gorev1_sonuc": None, "gorev2_sonuc": None, "ajan_log": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

_DURUM_RENK = {"İşleme Alındı": "🟢", "Kullanıcı Bekleniyor": "🟡", "Onay Bekliyor": "🟠"}

st.title("✍️ Görev 2: Resmî Yazı Taslaklama ve Birim Yönlendirme")
st.caption("Şartname madde 6.4.2")

if not st.session_state.gorev1_sonuc:
    st.warning("Önce Görev 1'de bir evrak analiz etmelisiniz.")
    st.page_link("pages/1_Gorev_1_Siniflandirma.py", label="← Görev 1'e git")
    st.stop()

analiz = st.session_state.gorev1_sonuc
st.markdown(f"**Analiz edilen evrak:** {analiz.get('evrak_turu', '—')} — {analiz.get('konu', '—')}")
with st.expander("Görev 1 analiz sonucunu görüntüle"):
    st.json(analiz)

ek_bilgi = ""
eksikler = [e for e in analiz.get("eksik_bilgiler", []) if e]
if eksikler:
    st.warning("Görev 1'de tespit edilen eksik bilgiler (taslağı etkileyebilir):")
    for e in eksikler:
        st.markdown(f"- {e}")
    ek_bilgi = st.text_area("Eksik bilgileri buraya girebilirsiniz (opsiyonel)")

if st.button("📝 Yazı taslağı ve yönlendirme oluştur", type="primary"):
    with st.spinner("Ajanlar taslağı hazırlıyor..."):
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

if st.session_state.gorev2_sonuc:
    s = st.session_state.gorev2_sonuc
    yonlendirme = s.get("yonlendirme_karari", {}) or {}
    taslak = s.get("resmi_yazi_taslagi", {}) or {}
    bilgilendirme = s.get("kullanici_bilgilendirme", {}) or {}

    st.subheader("📮 Yönlendirme kararı")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("İşlem yapacak ana kurum", yonlendirme.get("islem_yapacak_ana_kurum", "—"))
        st.metric("Gereği için yönlendirilecek birim", yonlendirme.get("geregi_icin_yonlendirilecek_birim", "—"))
    with c2:
        bilgi_birimleri = yonlendirme.get("bilgi_icin_iletilecek_birimler", [])
        st.markdown("**Bilgi için iletilecek birimler**")
        st.markdown(", ".join(bilgi_birimleri) if bilgi_birimleri else "—")
        st.markdown("**Yönlendirme gerekçesi**")
        st.info(yonlendirme.get("yonlendirme_gerekcesi", "—"))

    st.divider()
    st.subheader("📄 Resmî yazı taslağı")
    tc1, tc2 = st.columns([2, 1])
    with tc1:
        st.markdown(f"**Konu:** {taslak.get('konu', '—')}")
        st.markdown(f"**İlgi:** {taslak.get('ilgi', '—')}")
        duzenlenmis_govde = st.text_area(
            "Gövde metni (görüntüleyin ve gerekirse düzenleyin)",
            value=taslak.get("govde_metni", ""), height=220,
        )
        tam_metin = (
            f"KONU: {taslak.get('konu', '')}\n\n"
            f"İlgi: {taslak.get('ilgi', '')}\n\n"
            f"{duzenlenmis_govde}\n\n"
            f"{taslak.get('imza_makami', '')}"
        )
        st.download_button("⬇️ Taslağı indir (.txt)", tam_metin, file_name="resmi_yazi_taslagi.txt")
    with tc2:
        st.metric("Yazı türü", taslak.get("yazi_turu", "—"))
        st.metric("İmza makamı", taslak.get("imza_makami", "—"))

    st.divider()
    st.subheader("💬 Kullanıcı bilgilendirme")
    durum = bilgilendirme.get("sistem_aksiyon_durumu", "—")
    st.markdown(f"**Sistem aksiyon durumu:** {_DURUM_RENK.get(durum, '')} {durum}")
    st.success(bilgilendirme.get("kullaniciya_gosterilecek_mesaj", "—"))

    with st.expander("Ham JSON çıktı (backend kontrolü için)"):
        st.json(s)
