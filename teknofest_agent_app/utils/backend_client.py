"""
BACKEND API İSTEMCİSİ
-----------------------------------------------------------------
Bu dosya SADECE bir istemci katmanıdır. Ajan/LLM mantığının kendisi burada
YOKTUR — o, Görev 1 ve Görev 2'yi geliştiren takım arkadaşlarının ayrı bir
backend serviste yürüttüğü mantıktır. Bu dosyanın tek işi, arayüzden gelen
isteği backend'e HTTP ile iletmek ve gelen cevabı arayüzün beklediği
formatta geri döndürmek.

ŞEMA KAYNAĞI: Bu dosyadaki tüm alan adları, ekibin hazırladığı örnek veri
seti (gorev1.txt / gorev2.txt) ile BİREBİR aynıdır. Şema değişirse SADECE bu
dosyayı güncellemek yeterli; pages/ altındaki sayfa kodlarının hiçbiri
değişmez (onlar bu fonksiyonların döndürdüğü sözlüğü kullanır).

===================================================================
GÖREV 1 ÇIKTI ŞEMASI (backend'den beklenen JSON)
===================================================================
{
  "evrak_turu": "Şikayet / İhbar | Dilekçe | İtiraz Metni | Kurumlararası Resmî Yazı | Bilgi Edinme Talebi | Teftiş Raporu | ...",
  "konu": "string",
  "evrak_tarihi": "GG.AA.YYYY veya null",
  "sayi_veya_kayit_no": "string veya null",
  "gonderen": {
    "gonderen_tipi": "Gerçek Kişi | Tüzel Kişi / Şirket | Kamu Kurumu",
    "ad_soyad_veya_unvan": "string veya null",
    "kimlik_veya_vergi_no": "string veya null",
    "iletisim_bilgisi": "string veya null"
  },
  "kisa_ozet": "string",
  "varliklar": {
    "kurumlar": ["string", ...],
    "lokasyonlar": ["string", ...],
    "tarihler": ["string", ...]
  },
  "ilgili_mevzuat_onerisi": ["string", ...],
  "eksik_bilgiler": ["string", ...],
    "isleme_devam_edilebilirlik_durumu": {
        "zorunlu_eksikler": [{"bilgi": "string", "mevzuat_maddesi": "string", "sonuc": "string"}],
        "zorunlu_olmayan_eksikler": [{"bilgi": "string", "mevzuat_maddesi": "string", "sonuc": "string"}]
    },
  "aciliyet_durumu": "Normal | İvedi | Çok İvedi"
}

===================================================================
GÖREV 2 ÇIKTI ŞEMASI (backend'den beklenen JSON)
===================================================================
Girdi: Görev 1'in tam çıktısı ({"analiz_sonucu": {...}, "ek_bilgi": "..." veya null})

{
  "yonlendirme_karari": {
    "islem_yapacak_ana_kurum": "string",
    "geregi_icin_yonlendirilecek_birim": "string",
    "bilgi_icin_iletilecek_birimler": ["string", ...],
    "yonlendirme_gerekcesi": "string"
  },
  "resmi_yazi_taslagi": {
    "yazi_turu": "Üst Yazı | Cevap Yazısı | Bilgilendirme Metni | Eksik Bilgi/Belge Talebi",
    "konu": "string",
    "ilgi": "string",
    "govde_metni": "string",
    "imza_makami": "string"
  },
  "kullanici_bilgilendirme": {
    "kullaniciya_gosterilecek_mesaj": "string",
    "sistem_aksiyon_durumu": "İşleme Alındı | Kullanıcı Bekleniyor | Onay Bekliyor"
  }
}

===================================================================
BEKLENEN UÇ NOKTALAR
===================================================================
POST {BASE_URL}/api/v1/evrak-isle
body (Görev 1 için): {"ham_metin": "<string>"}
body (Görev 2 için): {"ham_metin": "", "gorev1_ciktisi": {...}, "ek_bilgi": "<string|null>"}
"""

import re
import time

import requests

from utils.sample_data import SAMPLE_DOCS

REQUEST_TIMEOUT_SN = 90


# --------------------------------------------------------------------------
# Bilinen örneklerle eşleştirme (gerçek ekip verisiyle demo)
# --------------------------------------------------------------------------

def _bilinen_ornek_bul_metinle(evrak_metni):
    normalized = (evrak_metni or "").strip()
    for ornek in SAMPLE_DOCS:
        if ornek["metin"].strip() == normalized:
            return ornek
    return None


def _bilinen_ornek_bul_konuyla(konu):
    for ornek in SAMPLE_DOCS:
        if ornek["gorev1"]["konu"] == konu:
            return ornek
    return None


# --------------------------------------------------------------------------
# Sezgisel (heuristic) mock — bilinen örneklerden biri değilse devreye girer
# --------------------------------------------------------------------------

_KURUM_DESENI = re.compile(
    r"[A-ZÇĞİÖŞÜ][\wÇĞİÖŞÜçğıöşü\.]*(?:[ \t]+[A-ZÇĞİÖŞÜ][\wÇĞİÖŞÜçğıöşü\.]*){0,4}"
    r"[ \t]+(?:Müdürlüğü|Bakanlığı|Başkanlığı|Dairesi|Üniversitesi|Belediyesi|Belediye Başkanlığı|Fakültesi|Genel Müdürlüğü|Rektörlüğü)"
)
_LOKASYON_DESENI = re.compile(
    r"[A-ZÇĞİÖŞÜ][\wÇĞİÖŞÜçğıöşü]*[ \t]+(?:Mahallesi|Sokak|Sokağı|Caddesi|Bulvarı|İli|İlçesi)"
)
_TARIH_DESENI = re.compile(r"\d{1,2}[./]\d{1,2}[./]\d{2,4}")
_MEVZUAT_DESENI = re.compile(r"\d{3,4}\s+[Ss]ay[ıi]l[ıi][^.,\n]{0,80}?(?:Kanun\w*|Yönetmelik\w*)")
_SAYI_DESENI = re.compile(r"Sayı\s*:\s*([\w\-./]+)")
_KIMLIK_DESENI = re.compile(r"T\.?C\.?\s*(?:Kimlik)?\s*No\s*:?\s*(\d{10,11})")
_AD_SOYAD_DESENI = re.compile(r"(?:Ad[ıı]?\s*Soyad[ıı]?)\s*:\s*([^\n]+)")
_ILETISIM_DESENI = re.compile(r"(?:Adres|Telefon|İletişim)\s*:\s*([^\n]+)")
_KONU_DESENI = re.compile(r"Konu\s*:\s*([^\n]+)")


def _sezgisel_gorev1(evrak_metni):
    metin = evrak_metni or ""
    metin_kucuk = metin.lower()

    if "şikayet" in metin_kucuk or "ihbar" in metin_kucuk:
        evrak_turu = "Şikayet / İhbar"
    elif "itiraz" in metin_kucuk:
        evrak_turu = "İtiraz Metni"
    elif "bilgi edinme" in metin_kucuk:
        evrak_turu = "Bilgi Edinme Talebi"
    elif metin.strip().startswith("T.C.") and _SAYI_DESENI.search(metin):
        evrak_turu = "Kurumlararası Resmî Yazı"
    else:
        evrak_turu = "Dilekçe"

    konu_match = _KONU_DESENI.search(metin)
    if konu_match:
        konu = konu_match.group(1).strip()
    else:
        ilk_satir = next((s.strip() for s in metin.split("\n") if s.strip()), "Konu belirlenemedi")
        konu = ilk_satir[:80]

    tarih_match = _TARIH_DESENI.search(metin)
    evrak_tarihi = tarih_match.group(0) if tarih_match else None

    sayi_match = _SAYI_DESENI.search(metin)
    sayi_veya_kayit_no = sayi_match.group(1) if sayi_match else None

    if re.search(r"Ltd\.?\s*Şti|A\.Ş\.?|Şirketi", metin):
        gonderen_tipi = "Tüzel Kişi / Şirket"
    elif metin.strip().startswith("T.C.") and sayi_match:
        gonderen_tipi = "Kamu Kurumu"
    else:
        gonderen_tipi = "Gerçek Kişi"

    ad_match = _AD_SOYAD_DESENI.search(metin)
    ad_soyad = ad_match.group(1).strip() if ad_match else None

    kimlik_match = _KIMLIK_DESENI.search(metin)
    kimlik_no = kimlik_match.group(1) if kimlik_match else None

    iletisim_match = _ILETISIM_DESENI.search(metin)
    iletisim = iletisim_match.group(1).strip() if iletisim_match else None

    kurumlar = sorted(set(_KURUM_DESENI.findall(metin)))
    lokasyonlar = sorted(set(_LOKASYON_DESENI.findall(metin)))
    tarihler = sorted(set(_TARIH_DESENI.findall(metin)))
    mevzuat = sorted(set(m.strip() for m in _MEVZUAT_DESENI.findall(metin)))

    eksikler = []
    if not evrak_tarihi:
        eksikler.append("Evrak Tarihi")
    if not ad_soyad and gonderen_tipi == "Gerçek Kişi":
        eksikler.append("Başvuru Sahibinin Adı ve Soyadı")
    if not kimlik_no and gonderen_tipi != "Kamu Kurumu":
        eksikler.append("T.C. Kimlik Numarası")
    if not iletisim:
        eksikler.append("İletişim Bilgisi (Telefon/E-posta)")
    if "imza" not in metin_kucuk:
        eksikler.append("İmza")

    if any(k in metin_kucuk for k in ["hayati tehlike", "çok ivedi", "acil müdahale"]):
        aciliyet = "Çok İvedi"
    elif any(k in metin_kucuk for k in ["ivedi", "acil", "tehlike", "haciz"]):
        aciliyet = "İvedi"
    else:
        aciliyet = "Normal"

    if not ad_soyad and gonderen_tipi == "Gerçek Kişi":
        taslak_olur = False
        derece = "Kritik (Taslak Üretilemez / İşleme Alınamaz)"
        gerekce = "3071 Sayılı Kanun m.4/6 gereğince başvuru sahibinin adı-soyadı olmadan resmi yazı taslağı oluşturulamaz."
        zorunlu = [{"bilgi": "Başvuru Sahibinin Adı ve Soyadı", "mevzuat_maddesi": "3071 Sayılı Kanun Madde 4 ve 6", "sonuc": "Kimliksiz başvuru incelenemez."}]
        tamamlanabilir = []
    elif eksikler:
        taslak_olur = True
        derece = "Tamamlanabilir (Eksik Belge Talebi Yazılabilir)"
        gerekce = "Evrakta bazı şekil/idari eksiklikler bulunmakla birlikte başvuru sahibi belirlidir. Görev 2'de Eksik Belge Talebi yazısı oluşturulabilir."
        zorunlu = []
        tamamlanabilir = [{"bilgi": e, "mevzuat_maddesi": "3071 Sayılı Kanun", "sonuc": "Eksik Belge Talebi yazısıyla tamamlanabilir."} for e in eksikler]
    else:
        taslak_olur = True
        derece = "Eksiksiz (Doğrudan Üst Yazı Yazılabilir)"
        gerekce = "Evrak yasal ve idari unsurları tam taşımaktadır. Doğrudan yetkili makama üst yazı üretilebilir."
        zorunlu = []
        tamamlanabilir = []

    cumleler = [c.strip() for c in metin.replace("\n", " ").split(".") if len(c.strip()) > 10]
    if cumleler:
        kisa_ozet = ". ".join(cumleler[:2]) + "."
        ozet_basarili = True
    else:
        kisa_ozet = metin[:200]
        ozet_basarili = bool(metin.strip())

    return {
        "evrak_turu": evrak_turu,
        "konu": konu,
        "evrak_tarihi": evrak_tarihi,
        "sayi_veya_kayit_no": sayi_veya_kayit_no,
        "gonderen": {
            "gonderen_tipi": gonderen_tipi,
            "ad_soyad_veya_unvan": ad_soyad,
            "kimlik_veya_vergi_no": kimlik_no,
            "iletisim_bilgisi": iletisim,
        },
        "kisa_ozet": kisa_ozet,
        "evrak_ozeti": kisa_ozet,
        "ozet_basarili": ozet_basarili,
        "varliklar": {
            "kurumlar": kurumlar,
            "lokasyonlar": lokasyonlar,
            "tarihler": tarihler,
        },
        "ilgili_mevzuat_onerisi": mevzuat or ["Resmî Yazışmalarda Uygulanacak Usul ve Esaslar Hakkında Yönetmelik"],
        "eksik_bilgiler": eksikler,
        "isleme_devam_edilebilirlik_durumu": {
            "taslak_olusturulabilir_mi": taslak_olur,
            "derece": derece,
            "gerekce": gerekce,
            "zorunlu_eksikler": zorunlu,
            "tamamlanabilir_eksikler": tamamlanabilir,
            "zorunlu_olmayan_eksikler": tamamlanabilir,
        },
        "taslak_olusturulabilir_mi": taslak_olur,
        "eksik_bilgi_derecesi": derece,
        "isleme_devam_gerekcesi": gerekce,
        "aciliyet_durumu": aciliyet,
    }


_BIRIM_HARITASI = {
    "Şikayet / İhbar": "Denetim ve Şikayet Değerlendirme Birimi",
    "İtiraz Metni": "İlgili Teknik/Hukuk İnceleme Birimi",
    "Bilgi Edinme Talebi": "Bilgi Edinme Birimi (CİMER / Halkla İlişkiler)",
    "Kurumlararası Resmî Yazı": "İlgili İdari/Teknik Birim",
    "Teftiş Raporu": "Hukuk Hizmetleri Genel Müdürlüğü",
    "Dilekçe": "Evrak Kayıt ve Yönlendirme Birimi",
}


def _sezgisel_gorev2(analiz_sonucu, ek_bilgi):
    evrak_turu = analiz_sonucu.get("evrak_turu", "Dilekçe")
    konu = analiz_sonucu.get("konu", "")
    gonderen = analiz_sonucu.get("gonderen", {}) or {}
    ad_soyad = gonderen.get("ad_soyad_veya_unvan") or "İlgili başvuru sahibi"
    evrak_tarihi = analiz_sonucu.get("evrak_tarihi") or "tarihsiz"
    kurumlar = (analiz_sonucu.get("varliklar", {}) or {}).get("kurumlar", [])

    ana_kurum = kurumlar[0] if kurumlar else "İlgili Kurum"
    birim = _BIRIM_HARITASI.get(evrak_turu, "Genel Evrak Birimi")

    eksikler = [e for e in analiz_sonucu.get("eksik_bilgiler", []) if e]
    ek_bilgi_var = bool(ek_bilgi)
    kalan_eksikler = [] if ek_bilgi_var else eksikler

    if kalan_eksikler:
        yazi_turu = "Eksik Bilgi/Belge Talebi"
        govde = (
            f"İlgide kayıtlı başvurunuz ({konu}) incelenmiştir. Değerlendirmenin tamamlanabilmesi ve "
            f"{birim} tarafından işleme alınabilmesi için aşağıdaki bilgi/belgelerin tarafımıza "
            f"iletilmesi gerekmektedir: " + ", ".join(kalan_eksikler) + "."
        )
    elif evrak_turu == "Dilekçe":
        yazi_turu = "Üst Yazı"
        govde = (
            f"İlgide kayıtlı dilekçe ile {ad_soyad}, {konu} konusunda başvuruda bulunmaktadır. "
            f"İlgili mevzuat hükümleri uyarınca talebin incelenerek sonucun ilgilisine bildirilmesi "
            f"hususunda gereğini rica ederim."
        )
    elif evrak_turu == "İtiraz Metni":
        yazi_turu = "Üst Yazı"
        govde = (
            f"İlgide kayıtlı itiraz dilekçesi ile {ad_soyad}, {konu} hakkında itirazda bulunmaktadır. "
            f"Konunun incelenerek yasal süre içerisinde gereğinin yapılması hususunda rica ederim."
        )
    else:
        yazi_turu = "Üst Yazı"
        govde = (
            f"İlgide kayıtlı {evrak_tarihi} tarihli yazı ile {konu} talep edilmektedir. "
            f"Gereğinin yapılması hususunda rica ederim."
        )

    return {
        "yonlendirme_karari": {
            "islem_yapacak_ana_kurum": ana_kurum,
            "geregi_icin_yonlendirilecek_birim": birim,
            "bilgi_icin_iletilecek_birimler": [],
            "yonlendirme_gerekcesi": f"{evrak_turu} niteliğindeki başvurunun {birim} görev alanına girmesi.",
        },
        "resmi_yazi_taslagi": {
            "yazi_turu": yazi_turu,
            "konu": f"{konu} Hk." if konu else "Başvuru İncelemesi Hk.",
            "ilgi": f"{evrak_tarihi} tarihli başvuru.",
            "govde_metni": govde,
            "imza_makami": "Birim Amiri",
        },
        "kullanici_bilgilendirme": {
            "kullaniciya_gosterilecek_mesaj": (
                f"Başvurunuz ({konu}) alınmış olup, eksik bilgilerin ({', '.join(kalan_eksikler)}) tamamlanması beklenmektedir."
                if kalan_eksikler else
                f"Başvurunuz ({konu}) alınmış ve {birim} birimine yönlendirilmiştir."
            ),
            "sistem_aksiyon_durumu": "Kullanıcı Bekleniyor" if kalan_eksikler else "İşleme Alındı",
        },
    }


# --------------------------------------------------------------------------
# Backend cevabını arayüzün beklediği şemaya eşleyen fonksiyonlar
# (Backend'in alan adları şemadan farklıysa SADECE burayı güncelle.)
# --------------------------------------------------------------------------

def _map_gorev1_response(data):
    raw_json = data.get("ham_json")
    gorev1_data = data.get("gorev1_ciktisi", data)
    gonderen = gorev1_data.get("gonderen", {}) or {}
    varliklar = gorev1_data.get("varliklar", {}) or {}
    devam = gorev1_data.get(
        "isleme_devam_edilebilirlik_durumu",
        {"zorunlu_eksikler": [], "tamamlanabilir_eksikler": [], "zorunlu_olmayan_eksikler": []},
    )
    taslak_olur = gorev1_data.get("taslak_olusturulabilir_mi", devam.get("taslak_olusturulabilir_mi", True))
    derece = gorev1_data.get("eksik_bilgi_derecesi", devam.get("derece"))
    gerekce = gorev1_data.get("isleme_devam_gerekcesi", devam.get("gerekce"))

    return {
        "evrak_turu": gorev1_data.get("evrak_turu", "Bilinmiyor"),
        "konu": gorev1_data.get("konu", ""),
        "evrak_tarihi": gorev1_data.get("evrak_tarihi"),
        "sayi_veya_kayit_no": gorev1_data.get("sayi_veya_kayit_no"),
        "gonderen": {
            "gonderen_tipi": gonderen.get("gonderen_tipi", "Bilinmiyor"),
            "ad_soyad_veya_unvan": gonderen.get("ad_soyad_veya_unvan"),
            "kimlik_veya_vergi_no": gonderen.get("kimlik_veya_vergi_no"),
            "iletisim_bilgisi": gonderen.get("iletisim_bilgisi"),
        },
        "kisa_ozet": gorev1_data.get("kisa_ozet") or gorev1_data.get("evrak_ozeti") or "",
        "evrak_ozeti": gorev1_data.get("evrak_ozeti") or gorev1_data.get("kisa_ozet") or "",
        "ozet_basarili": bool(gorev1_data.get("kisa_ozet") or gorev1_data.get("evrak_ozeti")),
        "varliklar": {
            "kurumlar": varliklar.get("kurumlar", []),
            "lokasyonlar": varliklar.get("lokasyonlar", []),
            "tarihler": varliklar.get("tarihler", []),
        },
        "ilgili_mevzuat_onerisi": gorev1_data.get("ilgili_mevzuat_onerisi", []),
        "eksik_bilgiler": gorev1_data.get("eksik_bilgiler", []),
        "isleme_devam_edilebilirlik_durumu": devam,
        "taslak_olusturulabilir_mi": taslak_olur,
        "eksik_bilgi_derecesi": derece,
        "isleme_devam_gerekcesi": gerekce,
        "aciliyet_durumu": gorev1_data.get("aciliyet_durumu", "Normal"),
        "ham_json": raw_json,
    }


def _map_gorev2_response(data):
    yonlendirme = data.get("yonlendirme_karari", {}) or {}
    taslak = data.get("resmi_yazi_taslagi", {}) or {}
    bilgilendirme = data.get("kullanici_bilgilendirme", {}) or {}
    return {
        "yonlendirme_karari": {
            "islem_yapacak_ana_kurum": yonlendirme.get("islem_yapacak_ana_kurum", "Bilinmiyor"),
            "geregi_icin_yonlendirilecek_birim": yonlendirme.get("geregi_icin_yonlendirilecek_birim", "Bilinmiyor"),
            "bilgi_icin_iletilecek_birimler": yonlendirme.get("bilgi_icin_iletilecek_birimler", []),
            "yonlendirme_gerekcesi": yonlendirme.get("yonlendirme_gerekcesi", ""),
        },
        "resmi_yazi_taslagi": {
            "yazi_turu": taslak.get("yazi_turu", "Bilinmiyor"),
            "konu": taslak.get("konu", ""),
            "ilgi": taslak.get("ilgi", ""),
            "govde_metni": taslak.get("govde_metni", ""),
            "imza_makami": taslak.get("imza_makami", ""),
        },
        "kullanici_bilgilendirme": {
            "kullaniciya_gosterilecek_mesaj": bilgilendirme.get("kullaniciya_gosterilecek_mesaj", ""),
            "sistem_aksiyon_durumu": bilgilendirme.get("sistem_aksiyon_durumu", "İşleme Alındı"),
        },
    }


# --------------------------------------------------------------------------
# Frontend'in kullandığı asıl fonksiyonlar
# --------------------------------------------------------------------------

def _log_ekle(log, ajan_adi, girdi_ozeti, cikti_ozeti, sure, kaynak):
    log.append({
        "Ajan": ajan_adi,
        "Girdi (özet)": (girdi_ozeti or "")[:60],
        "Çıktı (özet)": (cikti_ozeti or "")[:60],
        "Süre (sn)": round(sure, 2),
        "Kaynak": kaynak,
    })
    return log


def gorev1_analiz(evrak_metni, base_url=None, demo_mode=True, log=None):
    """
    Görev 1: Evrak Sınıflandırma ve İçerik Analizi.
    Dönüş: (sonuc_dict, guncellenmis_log, hata_mesaji_veya_None)
    """
    log = log if log is not None else []
    t0 = time.time()

    if demo_mode or not base_url:
        bilinen = _bilinen_ornek_bul_metinle(evrak_metni)
        sonuc = bilinen["gorev1"] if bilinen else _sezgisel_gorev1(evrak_metni)
        kaynak = "bilinen örnek" if bilinen else "sezgisel mock"
        _log_ekle(log, "Evrak Analiz Ajanı", evrak_metni, sonuc["evrak_turu"], time.time() - t0, kaynak)
        return sonuc, log, None

    try:
        r = requests.post(f"{base_url.rstrip('/')}/api/v1/gorev1",
                           json={"ham_metin": evrak_metni},
                           headers={"X-Rol": "yonetici"}, 
                           timeout=REQUEST_TIMEOUT_SN)
        r.raise_for_status()
        state_response = r.json()
        sonuc = _map_gorev1_response(state_response)
        _log_ekle(log, "Evrak Analiz Ajanı", evrak_metni, sonuc["evrak_turu"], time.time() - t0, "backend")
        return sonuc, log, None
    except Exception as exc:
        sonuc = _sezgisel_gorev1(evrak_metni)
        _log_ekle(log, "Evrak Analiz Ajanı", evrak_metni, sonuc["evrak_turu"], time.time() - t0, "mock (hata sonrası)")
        return sonuc, log, f"Özetleme başarısız; ham metin gösteriliyor. Backend hatası: {exc}"


def gorev2_taslak(analiz_sonucu, ek_bilgi=None, base_url=None, demo_mode=True, log=None):
    """
    Görev 2: Resmî Yazı Taslaklama ve Birim Yönlendirme.
    Dönüş: (sonuc_dict, guncellenmis_log, hata_mesaji_veya_None)
    """
    log = log if log is not None else []
    t0 = time.time()
    girdi_ozeti = analiz_sonucu.get("konu", analiz_sonucu.get("evrak_turu", "?"))

    if demo_mode or not base_url:
        bilinen = _bilinen_ornek_bul_konuyla(analiz_sonucu.get("konu", ""))
        sonuc = bilinen["gorev2"] if bilinen else _sezgisel_gorev2(analiz_sonucu, ek_bilgi)
        kaynak = "bilinen örnek" if bilinen else "sezgisel mock"
        _log_ekle(log, "Yazı Taslaklama ve Yönlendirme Ajanı", girdi_ozeti,
                  sonuc["yonlendirme_karari"]["geregi_icin_yonlendirilecek_birim"], time.time() - t0, kaynak)
        return sonuc, log, None

    try:
        r = requests.post(f"{base_url.rstrip('/')}/api/v1/gorev2",
                           json={"gorev1_ciktisi": analiz_sonucu, "ek_bilgi": ek_bilgi},
                           headers={"X-Rol": "yonetici"},
                           timeout=REQUEST_TIMEOUT_SN)
        r.raise_for_status()
        state_response = r.json()
        sonuc = _map_gorev2_response(state_response.get("gorev2_ciktisi", {}))
        _log_ekle(log, "Yazı Taslaklama ve Yönlendirme Ajanı", girdi_ozeti,
                  sonuc["yonlendirme_karari"]["geregi_icin_yonlendirilecek_birim"], time.time() - t0, "backend")
        return sonuc, log, None
    except Exception as exc:
        sonuc = _sezgisel_gorev2(analiz_sonucu, ek_bilgi)
        _log_ekle(log, "Yazı Taslaklama ve Yönlendirme Ajanı", girdi_ozeti,
                  sonuc["yonlendirme_karari"]["geregi_icin_yonlendirilecek_birim"], time.time() - t0, "mock (hata sonrası)")
        return sonuc, log, f"Backend'e ulaşılamadı, örnek veri gösteriliyor. Hata: {exc}"
