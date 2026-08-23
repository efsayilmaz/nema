import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import time
from dotenv import load_dotenv
from gorev2.agent import calistir_gorev2

load_dotenv()

# VERİ SETİNDE OLMAYAN YENİ TEST SENARYOSU
veri_seti_disi_senaryo = {
    "evrak_turu": "Şikayet / İhbar",
    "konu": "Gece Saatlerinde Canlı Müzik Gürültüsü ve Desibel Aşımı Şikayeti",
    "evrak_tarihi": "20.08.2026",
    "sayi_veya_kayit_no": None,
    "gonderen": {
        "gonderen_tipi": "Gerçek Kişi",
        "ad_soyad_veya_unvan": "Murat ÖZTÜRK",
        "kimlik_veya_vergi_no": "19283746501",
        "iletisim_bilgisi": "0532 999 88 77 - murat.ozturk@email.com"
    },
    "kisa_ozet": "Kültür Mahallesi Barbaros Caddesi No:12 adresinde yeni açılan eğlence mekanının gece 24:00'ten sonra canlı müzik yayını yaptığı, ses sınırlarını aştığı ve çevre sakinlerini rahatsız ettiği belirtilerek işletmenin canlı müzik ruhsatının ve ses yalıtımının denetlenmesi talep edilmektedir.",
    "varliklar": {
        "kurumlar": [
            "İlgili İlçe Belediye Başkanlığı",
            "Zabıta Müdürlüğü",
            "Çevre Koruma ve Kontrol Müdürlüğü"
        ],
        "lokasyonlar": [
            "Kültür Mahallesi",
            "Barbaros Caddesi No:12"
        ],
        "tarihler": [
            "20.08.2026",
            "Son 1 aydır"
        ]
    },
    "ilgili_mevzuat_onerisi": [
        "2872 Sayılı Çevre Kanunu",
        "Çevresel Gürültü Kontrol Yönetmeliği",
        "5393 Sayılı Belediye Kanunu"
    ],
    "eksik_bilgiler": [],
    "aciliyet_durumu": "İvedi"
}

if __name__ == "__main__":
    print("--- VERİ SETİ DIŞI YENİ SENARYO TESTİ BAŞLATILIYOR ---\n")
    t0 = time.time()
    sonuc = calistir_gorev2(veri_seti_disi_senaryo)
    gecen_sure = time.time() - t0
    
    print(f"Tamamlanma Süresi: {gecen_sure:.2f} saniye\n")
    print(json.dumps(sonuc.model_dump(), indent=2, ensure_ascii=False))
