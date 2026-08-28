"""
manuel_inceleme.py — B5: Manuel İnceleme Kuyruk Yönetim Paneli
===============================================================
KVKK denetimini geçemeyen (MANUEL_INCELEME durumundaki) taslakların
yöneticiler tarafından görüntüleneceği ve işleme alınacağı panel.
"""

import streamlit as st
import os
import sys
import json
import datetime
from pathlib import Path

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '../..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from utils.secure_logger import audit_logger
except ImportError:
    audit_logger = None

KUYRUK_DOSYASI = Path(root_dir) / "logs" / "manuel_inceleme_kuyrugu.jsonl"

# ──────────────────────────────────────────────────────────────
# Başlık
# ──────────────────────────────────────────────────────────────
st.title("🚨 Manuel İnceleme Kuyruğu")
st.markdown(
    """
    <div class="system-desc">
        KVKK denetimini geçemeyen (özel veri sızıntısı riski tespit edilen) taslaklar
        buraya düşer. Her kaydı inceleyerek <strong>Onayla</strong> veya <strong>Reddet</strong>
        işlemi yapabilirsiniz.
    </div>
    """,
    unsafe_allow_html=True,
)
st.divider()


def _kuyruk_yukle() -> list[dict]:
    """Kuyruktaki tüm kayıtları okur."""
    if not KUYRUK_DOSYASI.exists():
        return []
    kayitlar = []
    with open(KUYRUK_DOSYASI, "r", encoding="utf-8") as f:
        for satir in f:
            satir = satir.strip()
            if satir:
                try:
                    kayitlar.append(json.loads(satir))
                except json.JSONDecodeError:
                    continue
    return kayitlar


def _kuyruk_guncelle(guncellenmis: list[dict]) -> None:
    """Güncellenmiş listeyi kuyruğa geri yazar."""
    KUYRUK_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
    with open(KUYRUK_DOSYASI, "w", encoding="utf-8") as f:
        for kayit in guncellenmis:
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")


# ──────────────────────────────────────────────────────────────
# Yönetici kimlik doğrulama (basit sicil no)
# ──────────────────────────────────────────────────────────────
yonetici_sicil = st.text_input(
    "Yönetici Sicil No (işlem yapmak için zorunlu):",
    placeholder="Örn: YNT-2026-0001",
    key="mi_yonetici_sicil",
)

st.divider()

# ──────────────────────────────────────────────────────────────
# Kuyruk listesi
# ──────────────────────────────────────────────────────────────
kuyruk = _kuyruk_yukle()

# Durum filtresi
filtre = st.selectbox(
    "Durum Filtresi:",
    options=["Tümü", "bekliyor", "onaylandi", "reddedildi"],
    index=0,
)
if filtre != "Tümü":
    gosterilen = [k for k in kuyruk if k.get("durum") == filtre]
else:
    gosterilen = kuyruk

if not gosterilen:
    st.info("Seçilen filtreye uygun kuyruk kaydı bulunamadı. 🎉")
    st.stop()

st.markdown(f"**Toplam:** {len(kuyruk)} kayıt | **Gösterilen:** {len(gosterilen)} | "
            f"**Bekleyen:** {sum(1 for k in kuyruk if k.get('durum') == 'bekliyor')}")
st.divider()

for idx, kayit in enumerate(gosterilen):
    durum = kayit.get("durum", "bekliyor")
    durum_ikon = {"bekliyor": "🟡", "onaylandi": "🟢", "reddedildi": "🔴"}.get(durum, "⚪")

    with st.container(border=True):
        col_baslik, col_durum = st.columns([4, 1])
        with col_baslik:
            st.markdown(f"### {durum_ikon} {kayit.get('konu', 'Konu Yok')}")
        with col_durum:
            st.markdown(f"**{durum.upper()}**")

        c1, c2, c3 = st.columns(3)
        c1.metric("Talep ID", kayit.get("talep_id", "—")[:12] + "...")
        c2.metric("Sektör", kayit.get("sektor", "—"))
        c3.metric("Tarih", kayit.get("tarih", "—")[:10])

        icerik_on = kayit.get("icerik_onaylayan", "bilinmiyor")
        kvkk_on   = kayit.get("kvkk_onaylayan", "bilinmiyor")
        st.caption(f"İçerik Onaylayan: `{icerik_on}` | KVKK Onaylayan: `{kvkk_on}`")

        with st.expander("🔍 Denetim Raporu"):
            rapor = kayit.get("denetim_raporu", {})
            st.json(rapor)

            # Sızıntı özeti
            leaked = rapor.get("stage2_leaked", [])
            if leaked:
                st.error(f"⚠️ Tespit edilen sızıntılar: {leaked}")
            regex_temiz = rapor.get("regex_clean", True)
            if not regex_temiz:
                st.error("⚠️ Regex katmanı: kirli (TC No / telefon / IBAN bulundu)")

        # İşlem butonları — sadece bekleyen kayıtlar için
        if durum == "bekliyor" and yonetici_sicil.strip():
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            talep_id = kayit.get("talep_id", "")

            with btn_col1:
                if st.button(f"✅ Onayla (arşive ekle)", key=f"onayla_{idx}_{talep_id[:8]}",
                             use_container_width=True):
                    # Yönetici manuel inceleme sonrası arşive eklemeyi onayladı
                    try:
                        from utils.arsiv_db import arsive_ekle
                        yeni_kayit = {
                            "id": f"ARS-MI-{datetime.date.today().strftime('%Y-%m')}-{talep_id[:4].upper()}",
                            "sektor": kayit.get("sektor", "Genel"),
                            "konu": kayit.get("konu", ""),
                            "tarih": datetime.date.today().isoformat(),
                            "onaylayanlar": [
                                f"İçerik: {icerik_on}",
                                f"KVKK: {kvkk_on}",
                                f"Manuel İnceleme Onayı: {yonetici_sicil.strip()} @ {datetime.datetime.utcnow().isoformat()}Z",
                            ],
                            "anonim_metin": "[Manuel inceleme sonrası onaylandı - orijinal metin silinmiştir]",
                            "guvenlik_notu": "Manuel inceleme sonrası yetkili onayı ile eklendi.",
                            "evrak_turu": kayit.get("evrak_turu", ""),
                        }
                        arsive_ekle(yeni_kayit)
                        # Kuyruğu güncelle
                        for k in kuyruk:
                            if k.get("talep_id") == talep_id:
                                k["durum"] = "onaylandi"
                                k["isleyen_yonetici"] = yonetici_sicil.strip()
                                k["islem_zamani"] = datetime.datetime.utcnow().isoformat() + "Z"
                        _kuyruk_guncelle(kuyruk)
                        if audit_logger:
                            audit_logger.log_action(
                                actor=yonetici_sicil.strip(),
                                action="MANUAL_REVIEW_APPROVE",
                                document_id=talep_id,
                                purpose="Manuel inceleme sonrası arşive ekleme onayı",
                                details={"sektor": kayit.get("sektor"), "konu": kayit.get("konu")},
                            )
                        st.success("✅ Onaylandı ve arşive eklendi.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Hata: {e}")

            with btn_col2:
                if st.button(f"🔴 Reddet (arşive ekleme)", key=f"reddet_{idx}_{talep_id[:8]}",
                             use_container_width=True):
                    for k in kuyruk:
                        if k.get("talep_id") == talep_id:
                            k["durum"] = "reddedildi"
                            k["isleyen_yonetici"] = yonetici_sicil.strip()
                            k["islem_zamani"] = datetime.datetime.utcnow().isoformat() + "Z"
                    _kuyruk_guncelle(kuyruk)
                    if audit_logger:
                        audit_logger.log_action(
                            actor=yonetici_sicil.strip(),
                            action="MANUAL_REVIEW_REJECT",
                            document_id=talep_id,
                            purpose="Manuel inceleme sonrası red — KVKK sızıntısı onaylanamadı",
                            details={"sektor": kayit.get("sektor"), "konu": kayit.get("konu")},
                        )
                    st.warning("🔴 Reddedildi. Arşive eklenmedi.")
                    st.rerun()

            with btn_col3:
                if st.button(f"🗑️ Kuyruktan Sil", key=f"sil_{idx}_{talep_id[:8]}",
                             use_container_width=True):
                    guncellenmis = [k for k in kuyruk if k.get("talep_id") != talep_id]
                    _kuyruk_guncelle(guncellenmis)
                    if audit_logger:
                        audit_logger.log_action(
                            actor=yonetici_sicil.strip(),
                            action="QUEUE_DELETE",
                            document_id=talep_id,
                            purpose="Manuel inceleme kuyruğundan silme",
                            details={},
                        )
                    st.info("🗑️ Kuyruktan silindi.")
                    st.rerun()

        elif durum == "bekliyor" and not yonetici_sicil.strip():
            st.warning("⚠️ İşlem yapmak için yukarıdan Yönetici Sicil No giriniz.")

        elif durum in ("onaylandi", "reddedildi"):
            isleyen = kayit.get("isleyen_yonetici", "bilinmiyor")
            islem_z  = kayit.get("islem_zamani", "")[:19].replace("T", " ")
            st.caption(f"İşleyen: `{isleyen}` | Zaman: `{islem_z} UTC`")
