import json
import unittest
from unittest.mock import patch

from gorev1 import calistir_gorev1
from gorev1.agent import _summary_breaks_rule


class DummyResponse:
    def __init__(self, payload):
        self.text = json.dumps(payload, ensure_ascii=False)


class DummyCompletions:
    def __init__(self):
        self.calls = []

    def create(
        self,
        model,
        messages,
        temperature,
    ):
        self.calls.append({"model": model, "messages": messages})
        return type("DummyCompletion", (), {"choices": [type(
            "DummyChoice", (), {"finish_reason": "stop", "message": type(
                "DummyMessage", (), {"content": json.dumps({
            "evrak_turu": "Şikayet / İhbar",
            "konu": "Çocuk parkı güvenliği",
            "evrak_tarihi": "15.08.2026",
            "sayi_veya_kayit_no": None,
            "gonderen": {
                "gonderen_tipi": "Gerçek Kişi",
                "ad_soyad_veya_unvan": "Test Kullanıcı",
                "kimlik_veya_vergi_no": None,
                "iletisim_bilgisi": None,
            },
            "kisa_ozet": "Parkta elektrik teline temas eden ağaç dalları nedeniyle çocukların güvenliği tehlike altındadır.",
            "varliklar": {
                "kurumlar": ["Belediye"],
                "lokasyonlar": ["Mahalle Parkı"],
                "tarihler": ["15.08.2026"],
            },
            "ilgili_mevzuat_onerisi": ["İçişleri Bakanlığı mevzuatı"],
            "eksik_bilgiler": [],
            "aciliyet_durumu": "İvedi",
                }, ensure_ascii=False)}
            )}
        )]})()


CASELER = [
    {
        "ad": "sikayet_kopek",
        "metin": "Merhaba mahallemizdeki köpekler geceleri havlıyor.",
        "beklenen_tur": "Şikayet",
        "beklenen_aciliyet": "İvedi",
    },
    {
        "ad": "ogrenci_not_itirazi",
        "metin": "Öğrenciyim notuma itiraz ediyorum.",
        "beklenen_tur": "İtiraz",
        "beklenen_aciliyet": "Normal",
    },
]


class Gorev1BenchmarkTest(unittest.TestCase):
    def test_summary_and_topic_reject_header_and_copy(self):
        payload = {
            "konu": "İLGİLİ BELEDİYE BAŞKANLIĞINA Tarih: 23.08.2026",
            "kisa_ozet": "İLGİLİ BELEDİYE BAŞKANLIĞINA Tarih: 23.08.2026",
            "evrak_tarihi": "23.08.2026",
            "varliklar": {"kurumlar": ["Belediye"], "tarihler": ["23.08.2026"]},
        }
        self.assertTrue(_summary_breaks_rule(payload))

    def test_summary_and_topic_reject_sender_identity(self):
        payload = {
            "konu": "Ayşe Yılmaz tarafından yapılan başvurunun değerlendirilmesi",
            "kisa_ozet": "Ayşe Yılmaz'ın başvurusu incelenerek işlem yapılması istenmektedir.",
            "gonderen": {
                "ad_soyad_veya_unvan": "Ayşe Yılmaz",
                "iletisim_bilgisi": "ayse@example.com",
            },
            "varliklar": {"kurumlar": [], "tarihler": []},
        }
        self.assertTrue(_summary_breaks_rule(payload))

    def test_case_coverage_and_schema(self):
        with patch("gorev1.agent.get_evren_client") as mock_client, patch("gorev1.agent.get_rag_sistemi") as mock_rag:
            mock_client.return_value.chat.completions = DummyCompletions()
            mock_rag.return_value.mevzuat_sorgula.return_value = []
            for case in CASELER:
                with self.subTest(case=case["ad"]):
                    sonuc = calistir_gorev1(case["metin"])
                    data = sonuc.model_dump()

                    self.assertIsInstance(data, dict)
                    self.assertIn("evrak_turu", data)
                    self.assertIn("konu", data)
                    self.assertIn("gonderen", data)
                    self.assertIn("kisa_ozet", data)
                    self.assertIn("varliklar", data)
                    self.assertIn("aciliyet_durumu", data)
                    self.assertIn(data["aciliyet_durumu"], {"Normal", "İvedi", "Çok İvedi"})

    def test_realistic_risk_detection(self):
        with patch("gorev1.agent.get_evren_client") as mock_client, patch("gorev1.agent.get_rag_sistemi") as mock_rag:
            mock_client.return_value.chat.completions = DummyCompletions()
            mock_rag.return_value.mevzuat_sorgula.return_value = []
            metin = "Çocuk parkında elektrik telleriyle temas eden dallar hayatı tehdit ediyor."
            sonuc = calistir_gorev1(metin)
            self.assertIn(sonuc.aciliyet_durumu, {"İvedi", "Çok İvedi"})
            self.assertTrue("çocuk" in sonuc.kisa_ozet.lower())


if __name__ == "__main__":
    unittest.main()
