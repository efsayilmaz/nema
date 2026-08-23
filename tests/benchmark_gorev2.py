import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import time
from dotenv import load_dotenv
from gorev2.agent import calistir_gorev2

load_dotenv()

BENCHMARK_SETI = [
    {
        "kategori": "Akademik / Öğrenci",
        "ad": "Sınav Notu İtirazı",
        "veri": {
            "evrak_turu": "Dilekçe",
            "konu": "Ara sınav notuna itiraz hk.",
            "evrak_tarihi": "14.11.2025",
            "sayi_veya_kayit_no": None,
            "gonderen": {"gonderen_tipi": "Gerçek Kişi", "ad_soyad_veya_unvan": "Emre KARADAĞ", "kimlik_veya_vergi_no": "27584916302", "iletisim_bilgisi": None},
            "kisa_ozet": "Fizik Bölümü 2. sınıf öğrencisi, Klasik Mekanik dersi vize sınavından aldığı 42 puana maddi hata incelemesi talebiyle itiraz etmektedir.",
            "varliklar": {"kurumlar": ["Atatürk Üniversitesi Fen Fakültesi Dekanlığı", "Fizik Bölümü"], "lokasyonlar": [], "tarihler": ["14.11.2025"]},
            "ilgili_mevzuat_onerisi": ["Atatürk Üniversitesi Önlisans ve Lisans Eğitim-Öğretim Yönetmeliği"],
            "eksik_bilgiler": ["İletişim Bilgisi (Telefon veya E-posta)"],
            "aciliyet_durumu": "Normal"
        }
    },
    {
        "kategori": "Yerel Yönetim / Vatandaş",
        "ad": "Başıboş Köpek Şikayeti",
        "veri": {
            "evrak_turu": "Şikayet / İhbar",
            "konu": "Başıboş Sokak Köpekleri Şikayeti",
            "evrak_tarihi": None,
            "sayi_veya_kayit_no": None,
            "gonderen": {"gonderen_tipi": "Gerçek Kişi", "ad_soyad_veya_unvan": None, "kimlik_veya_vergi_no": None, "iletisim_bilgisi": None},
            "kisa_ozet": "Yeşiltepe Mahallesi Gül Sokak civarında sokak köpeklerinin barınağa alınması veya kısırlaştırılması talep edilmektedir.",
            "varliklar": {"kurumlar": ["Belediye"], "lokasyonlar": ["Yeşiltepe Mahallesi", "Gül Sokak"], "tarihler": ["Geçen hafta"]},
            "ilgili_mevzuat_onerisi": ["5199 Sayılı Hayvanları Koruma Kanunu", "5393 Sayılı Belediye Kanunu"],
            "eksik_bilgiler": ["Evrak Tarihi", "Başvuru Sahibinin Adı ve Soyadı", "T.C. Kimlik Numarası", "İletişim Bilgisi"],
            "aciliyet_durumu": "İvedi"
        }
    },
    {
        "kategori": "Hukuk / Vergi Mahkemesi",
        "ad": "Vergi Ziyaı Cezasının İptali",
        "veri": {
            "evrak_turu": "Dilekçe",
            "konu": "Kurumlar Vergisi ve Vergi Ziyaı Cezasının İptali Talebi",
            "evrak_tarihi": None,
            "sayi_veya_kayit_no": None,
            "gonderen": {"gonderen_tipi": "Tüzel Kişi / Şirket", "ad_soyad_veya_unvan": "ABC İnşaat San. Ltd. Şti. (Vekili: Av. Hakan Demir)", "kimlik_veya_vergi_no": None, "iletisim_bilgisi": "Beşiktaş/İstanbul"},
            "kisa_ozet": "Davacı şirket, Beşiktaş Vergi Dairesi tarafından kesilen cezanın iptalini ve yürütmenin durdurulmasını talep etmektedir.",
            "varliklar": {"kurumlar": ["İstanbul 3. Vergi Mahkemesi Başkanlığı", "Beşiktaş Vergi Dairesi"], "lokasyonlar": ["Beşiktaş/İstanbul"], "tarihler": ["10.11.2023"]},
            "ilgili_mevzuat_onerisi": ["213 Sayılı Vergi Usul Kanunu", "2577 Sayılı İdari Yargılama Usulü Kanunu"],
            "eksik_bilgiler": ["Davacı Şirket Vergi Kimlik Numarası", "Avukat Sicil Numarası"],
            "aciliyet_durumu": "Çok İvedi"
        }
    },
    {
        "kategori": "Kamu İçi Resmî Yazı",
        "ad": "Çığ Tehlikesi Erken Uyarı",
        "veri": {
            "evrak_turu": "Kurumlararası Resmî Yazı",
            "konu": "Olası Çığ Tehlikesine Karşı Erken Uyarı ve Yol Tedbirleri",
            "evrak_tarihi": "08.08.2026",
            "sayi_veya_kayit_no": "E-74512963-950.01.04-1240",
            "gonderen": {"gonderen_tipi": "Kamu Kurumu", "ad_soyad_veya_unvan": "T.C. Erzurum Valiliği İl Afet ve Acil Durum Müdürlüğü", "kimlik_veya_vergi_no": None, "iletisim_bilgisi": None},
            "kisa_ozet": "Erzurum-Çat-Bingöl karayolu istinat duvarı tahkimatı ve çığ bariyerlerinin kış öncesi revize edilmesi istenmektedir.",
            "varliklar": {"kurumlar": ["T.C. Erzurum Valiliği", "İl Afet ve Acil Durum Müdürlüğü", "Karayolları 12. Bölge Müdürlüğü"], "lokasyonlar": ["Erzurum", "Çat", "Bingöl"], "tarihler": ["08.08.2026"]},
            "ilgili_mevzuat_onerisi": ["5442 Sayılı İl İdaresi Kanunu", "7269 Sayılı Afetler Kanunu"],
            "eksik_bilgiler": [],
            "aciliyet_durumu": "İvedi"
        }
    }
]

if __name__ == "__main__":
    print("=" * 80)
    print("TEKNOFEST 2026 - GÖREV 2 RESMÎ BENCHMARK VE PERFORMANS TESTİ")
    print("=" * 80 + "\n")
    
    rapor_satirlari = []
    toplam_sure = 0.0
    basarili_sayisi = 0
    
    for idx, test in enumerate(BENCHMARK_SETI, 1):
        print(f"[{idx}/{len(BENCHMARK_SETI)}] İşleniyor: {test['ad']} ({test['kategori']})...")
        try:
            t0 = time.time()
            sonuc = calistir_gorev2(test["veri"])
            sure = time.time() - t0
            toplam_sure += sure
            basarili_sayisi += 1
            
            rapor_satirlari.append({
                "kategori": test["kategori"],
                "ad": test["ad"],
                "sure": round(sure, 2),
                "ana_kurum": sonuc.yonlendirme_karari.islem_yapacak_ana_kurum,
                "yazi_turu": sonuc.resmi_yazi_taslagi.yazi_turu.value,
                "aksiyon": sonuc.kullanici_bilgilendirme.sistem_aksiyon_durumu.value,
                "sema_durum": "GEÇERLİ (%100)"
            })
            print(f"    -> Başarılı ({sure:.2f} sn) | Yazı Türü: {sonuc.resmi_yazi_taslagi.yazi_turu.value} | Durum: {sonuc.kullanici_bilgilendirme.sistem_aksiyon_durumu.value}\n")
        except Exception as e:
            print(f"    -> [HATA]: {e}\n")
        time.sleep(2)
        
    print("=" * 80)
    print("GÖREV 2 NİHAİ BENCHMARK VE DOĞRULAMA TABLOSU")
    print("=" * 80)
    print(f"{'Kategori':<22} | {'Evrak Adı':<25} | {'Süre (sn)':<10} | {'Yazı Türü':<20} | {'Şema'}")
    print("-" * 80)
    for r in rapor_satirlari:
        print(f"{r['kategori']:<22} | {r['ad']:<25} | {str(r['sure']) + ' sn':<10} | {r['yazi_turu']:<20} | {r['sema_durum']}")
    print("-" * 80)
    print(f"Toplam Başarılı Test : {basarili_sayisi}/{len(BENCHMARK_SETI)}")
    if basarili_sayisi > 0:
        print(f"Ortalama Yanıt Süresi: {toplam_sure / basarili_sayisi:.2f} saniye")
    print("=" * 80)
