import json
from unittest.mock import patch, MagicMock
import pytest

from gorev2.agent import calistir_gorev2
from gorev2.schemas import Gorev2CiktiSemasi, AksiyonDurumu, YaziTuru


class DummyChoice:
    def __init__(self, content: str):
        self.message = MagicMock()
        self.message.content = content
        self.finish_reason = "stop"


class DummyCompletion:
    def __init__(self, content: str):
        self.choices = [DummyChoice(content)]


def test_calistir_gorev2_without_missing_info():
    # Setup mock responses for the two sub-agents using escape sequences to be encoding-safe
    mock_taslak_yonlendirme_json = json.dumps({
        "yonlendirme_karari": {
            "islem_yapacak_ana_kurum": "Atat\u00fcrk \u00dcniversitesi Fen Fak\u00fcltesi Dekanl\u0131\u011f\u0131",
            "geregi_icin_yonlendirilecek_birim": "Fizik B\u00f6l\u00fcm\u00fc",
            "bilgi_icin_iletilecek_birimler": [],
            "yonlendirme_gerekcesi": "\u00d6\u011frenci s\u0131nav notu itiraz\u0131 Fizik B\u00f6l\u00fcm\u00fc taraf\u0131ndan incelenmelidir."
        },
        "resmi_yazi_taslagi": {
            "yazi_turu": "\u00dcst Yaz\u0131",
            "konu": "S\u0131nav Notu \u0130tiraz\u0131",
            "ilgi": "14.11.2025 tarihli dilek\u00e7e",
            "govde_metni": "Fizik B\u00f6l\u00fcm\u00fc 2. s\u0131n\u0131f \u00f6\u011frencisi Emre KARADA\u011e'\u0131n s\u0131nav notuna maddi hata itiraz\u0131 incelenmek \u00fczere ekte g\u00f6nderilmi\u015ftir. Gere\u011fini rica ederim.",
            "imza_makami": "Dekan Yard\u0131mc\u0131s\u0131"
        }
    })

    mock_kullanici_iletisim_json = json.dumps({
        "kullanici_bilgilendirme": {
            "kullaniciya_gosterilecek_mesaj": "Ba\u015fvurunuz al\u0131nm\u0131\u015f olup ilgili birime sevk edilmi\u015ftir.",
            "sistem_aksiyon_durumu": "\u0130\u015fleme Al\u0131nd\u0131"
        },
        "resmi_yazi_taslagi": None
    })

    # Evrak mock data (No missing info)
    girdi_verisi = {
        "evrak_turu": "Dilek\u00e7e",
        "konu": "Ara s\u0131nav notuna itiraz hk.",
        "evrak_tarihi": "14.11.2025",
        "sayi_veya_kayit_no": None,
        "gonderen": {
            "gonderen_tipi": "Ger\u00e7ek Ki\u015fi",
            "ad_soyad_veya_unvan": "Emre KARADA\u011e",
            "kimlik_veya_vergi_no": "27584916302",
            "iletisim_bilgisi": "emre@email.com"
        },
        "kisa_ozet": "Fizik B\u00f6l\u00fcm\u00fc \u00f6\u011frencisinin maddi hata itiraz\u0131.",
        "varliklar": {"kurumlar": ["Atat\u00fcrk \u00dcniversitesi", "Fizik B\u00f6l\u00fcm\u00fc"], "lokasyonlar": [], "tarihler": ["14.11.2025"]},
        "ilgili_mevzuat_onerisi": [],
        "eksik_bilgiler": [],
        "aciliyet_durumu": "Normal"
    }

    # Mock get_evren_client
    with patch("gorev2.agent.get_evren_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Configure client.chat.completions.create to return the responses sequentially
        mock_client.chat.completions.create.side_effect = [
            DummyCompletion(mock_taslak_yonlendirme_json),
            DummyCompletion(mock_kullanici_iletisim_json)
        ]

        # Run orchestrator
        sonuc = calistir_gorev2(girdi_verisi, api_key="dummy")

        # Verify output
        assert isinstance(sonuc, Gorev2CiktiSemasi)
        assert sonuc.yonlendirme_karari.islem_yapacak_ana_kurum == "Atat\u00fcrk \u00dcniversitesi Fen Fak\u00fcltesi Dekanl\u0131\u011f\u0131"
        assert sonuc.yonlendirme_karari.geregi_icin_yonlendirilecek_birim == "Fizik B\u00f6l\u00fcm\u00fc"
        assert sonuc.kullanici_bilgilendirme.sistem_aksiyon_durumu == AksiyonDurumu.ISLEME_ALINDI
        assert sonuc.resmi_yazi_taslagi.yazi_turu == YaziTuru.UST_YAZI
        
        # Check formatting was applied
        assert "T.C." in sonuc.resmi_yazi_taslagi.govde_metni
        assert "ATAT\u00dcRK \u00dcN\u0130VERS\u0130TES\u0130 FEN FAK\u00dcLTES\u0130 DEKANLI\u011eI F\u0130Z\u0130K B\u00d6L\u00dcM\u00dcNE" in sonuc.resmi_yazi_taslagi.govde_metni


def test_calistir_gorev2_with_missing_info():
    # Setup mock responses for the two sub-agents
    mock_taslak_yonlendirme_json = json.dumps({
        "yonlendirme_karari": {
            "islem_yapacak_ana_kurum": "Belediye",
            "geregi_icin_yonlendirilecek_birim": "Zab\u0131ta M\u00fcd\u00fcrl\u00fc\u011f\u00fc",
            "bilgi_icin_iletilecek_birimler": [],
            "yonlendirme_gerekcesi": "G\u00fcr\u00fclt\u00fc \u015fikayeti Zab\u0131ta taraf\u0131ndan denetlenmelidir."
        },
        "resmi_yazi_taslagi": {
            "yazi_turu": "\u00dcst Yaz\u0131",
            "konu": "G\u00fcr\u00fclt\u00fc \u015eikayeti",
            "ilgi": "20.08.2026 tarihli dilek\u00e7e",
            "govde_metni": "G\u00fcr\u00fclt\u00fc \u015fikayeti iletilmi\u015ftir.",
            "imza_makami": "Birim Sorumlusu"
        }
    })

    # User communication agent detects missing info and produces Eksik Bilgi/Belge Talebi
    mock_kullanici_iletisim_json = json.dumps({
        "kullanici_bilgilendirme": {
            "kullaniciya_gosterilecek_mesaj": "Ba\u015fvurunuzda T.C. Kimlik Numaras\u0131 eksiktir. L\u00fctfen tamamlay\u0131n\u0131z.",
            "sistem_aksiyon_durumu": "Kullan\u0131c\u0131 Bekleniyor"
        },
        "resmi_yazi_taslagi": {
            "yazi_turu": "Eksik Bilgi/Belge Talebi",
            "konu": "Eksik Bilgi ve Belge Talebi",
            "ilgi": "20.08.2026 tarihli dilek\u00e7e",
            "govde_metni": "M\u00fcd\u00fcrl\u00fc\u011f\u00fcm\u00fcze yap\u0131lan ba\u015fvurunuzda T.C. Kimlik Numaras\u0131 eksik tespit edilmi\u015ftir. \u0130\u015fleminizin devam edebilmesi i\u00e7in bu bilgiyi tamamlaman\u0131z\u0131 rica ederiz.",
            "imza_makami": "Zab\u0131ta M\u00fcd\u00fcr\u00fc"
        }
    })

    # Evrak mock data (Has missing info)
    girdi_verisi = {
        "evrak_turu": "\u015eikayet",
        "konu": "G\u00fcr\u00fclt\u00fc \u015eikayeti",
        "evrak_tarihi": "20.08.2026",
        "sayi_veya_kayit_no": None,
        "gonderen": {
            "gonderen_tipi": "Ger\u00e7ek Ki\u015fi",
            "ad_soyad_veya_unvan": "Murat \u00d6ZT\u00dcRK",
            "kimlik_veya_vergi_no": None,  # Missing TC
            "iletisim_bilgisi": "0532 999 88 77"
        },
        "kisa_ozet": "G\u00fcr\u00fclt\u00fc \u015fikayeti dilek\u00e7esi.",
        "varliklar": {"kurumlar": ["Belediye"], "lokasyonlar": [], "tarihler": ["20.08.2026"]},
        "ilgili_mevzuat_onerisi": [],
        "eksik_bilgiler": ["T.C. Kimlik Numaras\u0131"],
        "aciliyet_durumu": "İvedi"
    }

    # Mock get_evren_client
    with patch("gorev2.agent.get_evren_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_client.chat.completions.create.side_effect = [
            DummyCompletion(mock_taslak_yonlendirme_json),
            DummyCompletion(mock_kullanici_iletisim_json)
        ]

        # Run orchestrator
        sonuc = calistir_gorev2(girdi_verisi, api_key="dummy")

        # Verify output (should use the draft from user communication agent)
        assert isinstance(sonuc, Gorev2CiktiSemasi)
        assert sonuc.kullanici_bilgilendirme.sistem_aksiyon_durumu == AksiyonDurumu.KULLANICI_BEKLENIYOR
        assert sonuc.resmi_yazi_taslagi.yazi_turu == YaziTuru.EKSIK_BILGI_BELGE_TALEBI
        
        # Check formatting was applied and uses "Gereğini rica ederim."
        assert "Gere\u011fini rica ederim." in sonuc.resmi_yazi_taslagi.govde_metni
        assert "ZABITA M\u00dcD\u00dcRL\u00dc\u011e\u00dcNE" in sonuc.resmi_yazi_taslagi.govde_metni
