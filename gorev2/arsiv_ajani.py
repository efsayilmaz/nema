import re
import uuid
import json
from typing import Tuple

def regex_katmani_kontrol(metin: str) -> bool:
    """Regex tabanlı son güvenlik ağı (3. Katman)."""
    if re.search(r'\b\d{11}\b', metin):
        return False
    if re.search(r'05\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}', metin):
        return False
    if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', metin):
        return False
    if re.search(r'TR\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}', metin):
        return False
        
    # Unvan sonrasında açıkta kalmış isim tespiti (Örn: Av. Burak Kaya)
    if re.search(r'(Av\.|Dr\.|Sn\.|Prof\.|Doç\.|Yrd\.\s*Doç\.)\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+', metin):
        return False
        
    return True

def _get_stage1_prompt(taslak_metni: str) -> str:
    return f"""Sen uzman bir Veri Güvenliği ve KVKK denetçisisin.
Görev: Aşağıdaki resmî yazı taslağını anonimleştirirken, KURUMSAL bilgileri KORU, metindeki İSTİSNASIZ HER gerçek kişi adı-soyadını MASKELE.

ASLA MASKELENMEYECEK (İDARİ/KURUMSAL ALANLAR - BEYAZ LİSTE):
- Gönderen ve Alıcı KURUM adları (T.C. Valiliği, Müdürlük, Bakanlık, Başkanlık vb.)
- Kurumların resmi/idari adresleri
- Resmî yazının kendi yapısal blokları: "Sayı:" bloğundaki evrak kayıt numaraları (örn: E-71073638), "Tarih:" bloğundaki yazının düzenlenme tarihi, "Konu:" ve "İlgi:" ibareleri.
- Kanun, Yönetmelik veya mevzuat numaraları ve madde adları.
- Kurumu temsil eden makam unvanları (Birim Amiri, İl Sağlık Müdürü vb.).

KESİN KURAL (KİŞİ İSİMLERİ İÇİN):
- Metindeki İSTİSNASIZ HER gerçek kişi adı-soyadını maskele. Kişinin kim olduğu (vatandaş, vekil, avukat, doktor, tanık, şikayetçi, üçüncü şahıs) FARK ETMEZ.
- İNSAN ismi geçen HER YER maskelenecek. Unvan varsa unvanı bırak, sadece ismi maskele: 'Av. [AD_SOYAD]', 'Dr. [AD_SOYAD]' gibi. 
- Placeholder olarak [AD_SOYAD], [TC_KİMLİK], [ADRES], [İLETİŞİM], [SAĞLIK_VERİSİ], [DOLAYLI_TANIMLAYICI] gibi genel veya rol belirten etiketler (örn. [VEKİL_AD_SOYAD], [TANIK_AD_SOYAD]) kullanabilirsin ama mutlaka insan isimlerini GİZLE.
- Şüpheye düştüğünde MASKELE - bu kesin ve istisnasız bir kuraldır.

DİĞER MASKELENECEKLER:
- T.C. Kimlik, Telefon, E-posta, IBAN vb.
- Özel Nitelikli Veri (Teşhis, kan grubu vb.) ve Dolaylı Teşhis Ediciler (örn: "78 yaşındaki hasta").

FEW-SHOT ÖRNEKLER:
Girdi: "Sayı: E-12345-67 Tarih: 28.08.2026 ... Kadıköy Caferağa Mah. Moda Cad. No:14 adresinde ikamet eden 78 yaşındaki KOAH hastası Fatma Yılmaz'ın 92 satürasyon değeri... İmza: İl Sağlık Müdürü"
Çıktı: {{"masked_text": "Sayı: E-12345-67 Tarih: 28.08.2026 ... Kadıköy [ADRES] adresinde ikamet eden [DOLAYLI_TANIMLAYICI] [AD_SOYAD]'ın [SAĞLIK_VERİSİ] değeri... İmza: İl Sağlık Müdürü", "detected_entities": ["Caferağa Mah. Moda Cad. No:14", "78 yaşındaki KOAH hastası", "Fatma Yılmaz", "92 satürasyon"]}}

Girdi: "İlgi: 27.08.2026 tarihli ve Av. Burak Kaya vekilliğinde iletilen ihtarname. İlgili yazıda müvekkil Mehmet Öz'e ait..."
Çıktı: {{"masked_text": "İlgi: 27.08.2026 tarihli ve Av. [VEKİL_AD_SOYAD] vekilliğinde iletilen ihtarname. İlgili yazıda müvekkil [VATANDAŞ_AD_SOYAD]'e ait...", "detected_entities": ["Burak Kaya", "Mehmet Öz"]}}

Girdi: "Olay esnasında orada bulunan tanık Ayşe Demir'in beyanına göre..."
Çıktı: {{"masked_text": "Olay esnasında orada bulunan tanık [TANIK_AD_SOYAD]'in beyanına göre...", "detected_entities": ["Ayşe Demir"]}}

Lütfen sadece JSON objesi döndür (Markdown backtick kullanma).
Format: {{"masked_text": "...", "detected_entities": ["...", "..."]}}

Şimdi bu metni anonimleştir:
{taslak_metni}"""

def _get_stage2_prompt(orijinal: str, maskelenmis: str) -> str:
    return f"""Sen BAĞIMSIZ bir KVKK Başdenetçisisin. 
Aşağıda bir evrakın orijinali ve 1. Aşama tarafından maskelenmiş hali verilmiştir. 
Görevin: Maskelenmiş metni inceleyip, İÇİNDE HERHANGİ BİR "VATANDAŞA/BAŞVURANA AİT" KİŞİSEL VEYA ÖZEL NİTELİKLİ VERİ KALIP KALMADIĞINI (ad, soyad, yaş, teşhis, tam adres, iletişim vb.) kontrol etmektir. 

ÖNEMLİ KURAL: Resmî kurum adları, resmî yazının kendi sayı ve tarihi, mevzuat bilgileri ve makam/imza bölümleri kişisel veri DEĞİLDİR ve SIZINTI SAYILAMAZ! Sadece vatandaş verisine odaklan.

Orijinal Metin:
{orijinal}

Maskelenmiş Metin:
{maskelenmis}

Eğer maskelenmiş metinde en ufak bir VATANDAŞA AİT teşhis edici özel/kişisel veri kaldıysa is_clean=false yap.
Sadece JSON döndür:
{{"is_clean": true/false, "leaked_entities": ["varsa_kacan_veri_1", ...]}}"""

def _koru_idari_bloklar(metin: str) -> tuple[str, dict]:
    """
    LLM çalışmadan önce 'Sayı :' ve 'Tarih :' bloklarını geçici token'larla korur.
    Döner: (korumalı_metin, {token: orijinal_deger} sözlüğü)
    """
    tokens = {}
    
    def _replace(m, prefix):
        token = f"__IDARI_{prefix}_{len(tokens)}__"
        tokens[token] = m.group(0)
        return token
    
    # Sayı bloğunu koru (E-12345, rakam-harf karışımı evrak no)
    korunmus = re.sub(
        r'(Sayı\s*:\s*)([\w\-\./ ]+)',
        lambda m: m.group(1) + _replace(m, 'SAYI') if m else m.group(0),
        metin
    )
    # Satır bazlı daha güvenli versiyon
    yeni_satirlar = []
    tokens = {}  # sıfırla
    for satir in metin.splitlines():
        satir_upper = satir.strip().upper()
        if satir_upper.startswith("SAYI") or satir_upper.startswith("SAY\u0130"):
            token = f"__IDARI_SAYI_{len(tokens)}__"
            tokens[token] = satir
            yeni_satirlar.append(token)
        elif satir_upper.startswith("TAR\u0130H"):
            token = f"__IDARI_TARIH_{len(tokens)}__"
            tokens[token] = satir
            yeni_satirlar.append(token)
        else:
            yeni_satirlar.append(satir)
    
    return "\n".join(yeni_satirlar), tokens

def _geri_yukle_idari_bloklar(metin: str, tokens: dict) -> str:
    """Korunan token'ları orijinal değerleriyle geri yükler."""
    for token, orijinal in tokens.items():
        metin = metin.replace(token, orijinal)
    return metin

def hibrit_anonimlestirme(client, taslak_metni: str) -> tuple[str, str, dict]:
    """2 Aşamalı LLM Doğrulaması ve Regex Katmanı."""
    
    # 0. AŞAMA: İDARİ BLOKLARI KORU (Sayı/Tarih satırları LLM'e gösterilmez)
    korunmus_metin, idari_tokens = _koru_idari_bloklar(taslak_metni)
    print(f"[AŞAMA 0] {len(idari_tokens)} idari blok koruma altına alındı: {list(idari_tokens.values())}")
    
    # 1. AŞAMA: MASKELEME
    print("[AŞAMA 1] LLM maskeleme çağrılıyor...")
    try:
        resp1 = client.chat.completions.create(
            model="llm-large",
            messages=[{"role": "user", "content": _get_stage1_prompt(korunmus_metin)}],
            temperature=0.0
        )
        content1 = resp1.choices[0].message.content.strip()
        if content1.startswith("```json"): content1 = content1[7:-3]
        elif content1.startswith("```"): content1 = content1[3:-3]
        
        stage1_data = json.loads(content1)
        anonim_metin_llm = stage1_data.get("masked_text", "")
        if not anonim_metin_llm: raise ValueError("JSON içinde masked_text bulunamadı")
        
        # İdari blokları geri yükle
        anonim_metin = _geri_yukle_idari_bloklar(anonim_metin_llm, idari_tokens)
        print(f"[AŞAMA 1] Maskeleme tamamlandı. İlk 200 karakter: {anonim_metin[:200]}")
    except Exception as e:
        print(f"[AŞAMA 1] HATA: {e}")
        return "[MASKELEME_HATASI]", "MANUEL_INCELEME", {"hata": str(e)}

    # 2. AŞAMA: BAĞIMSIZ DENETİM
    print("[AŞAMA 2] Bağımsız denetim çağrılıyor...")
    try:
        resp2 = client.chat.completions.create(
            model="llm-fast",
            messages=[{"role": "user", "content": _get_stage2_prompt(taslak_metni, anonim_metin)}],
            temperature=0.0
        )
        content2 = resp2.choices[0].message.content.strip()
        if content2.startswith("```json"): content2 = content2[7:-3]
        elif content2.startswith("```"): content2 = content2[3:-3]
        
        stage2_data = json.loads(content2)
        is_clean = stage2_data.get("is_clean", False)
        leaked = stage2_data.get("leaked_entities", [])
        print(f"[AŞAMA 2] is_clean={is_clean}, leaked={leaked}")
    except Exception as e:
        print(f"[AŞAMA 2] HATA: {e}")
        is_clean = False
        leaked = ["JSON_PARSING_ERROR"]

    # 3. AŞAMA: REGEX KONTROLÜ
    regex_temiz = regex_katmani_kontrol(anonim_metin)
    print(f"[AŞAMA 3] Regex temiz mi: {regex_temiz}")

    durum = "KABUL" if (is_clean and regex_temiz) else "MANUEL_INCELEME"
    rapor = {
        "stage1_detected": stage1_data.get("detected_entities", []),
        "stage2_is_clean": is_clean,
        "stage2_leaked": leaked,
        "regex_clean": regex_temiz
    }
    return anonim_metin, durum, rapor


def arsiv_kayit_talebi_olustur(taslak_metni: str, sektor: str, client) -> dict:
    """Arşiv kuyruğu için talebi oluşturur."""
    anonim_metin, guvenlik_durumu, rapor = hibrit_anonimlestirme(client, taslak_metni)
    
    return {
        "talep_id": str(uuid.uuid4()),
        "orijinal_taslak": taslak_metni,
        "anonim_taslak": anonim_metin,
        "sektor": sektor,
        "guvenlik_durumu": guvenlik_durumu,
        "denetim_raporu": rapor,
        "onay_durumu": {"icerik_onayi": False, "kvkk_onayi": False},
        "onaylayacak_roller": ["icerik_uzmani", "kvkk_sorumlusu"]
    }
