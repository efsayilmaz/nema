import json
import os
import re
import time
from typing import Dict, Any, Union, Optional

from evren_client import get_evren_client, validate_response_content
from pydantic import BaseModel, Field

from gorev2.schemas import (
    YonlendirmeKarari,
    ResmiYaziTaslagi,
    YaziTuru,
    Gorev1CiktiSemasi
)

TASLAK_YONLENDIRME_PROMPT = """
Sen kamu kurumlarında görev yapan kıdemli ve uzman bir evrak işleme, yönlendirme ve resmî yazışma yapay zeka ajanısın.
Sana Görev 1 aşamasında analiz edilmiş, özeti ve özellikleri çıkarılmış bir evrak verisi (JSON formatında) sunulacaktır.

GÖREVİN:
Verilen evrak analizini dikkatle inceleyerek aşağıdaki iki temel bileşenden oluşan yapılandırılmış çıktıyı üretmektir:

1. YÖNLENDİRME KARARI (`yonlendirme_karari`):
   - `islem_yapacak_ana_kurum`: Evrakla ilgili asıl yetkili ve görevli ana kamu kurumu/idare (örn: İlgili İlçe/Büyükşehir Belediye Başkanlığı, Atatürk Üniversitesi Dekanlığı vb.).
   - `geregi_icin_yonlendirilecek_birim`: Doğrudan alt birim / müdürlük / bölüm (örn: Zabıta Müdürlüğü, Fizik Bölümü Başkanlığı vb.).
   - `bilgi_icin_iletilecek_birimler`: Bilgilendirilmesi gereken diğer ilgili yan birimlerin listesi.
   - `yonlendirme_gerekcesi`: Mevzuat, aciliyet ve görev alanına dayanan açıklayıcı gerekçe.

2. RESMÎ YAZI TASLAĞI (`resmi_yazi_taslagi`):
   - `yazi_turu`: Yalnızca şu 3 değerden biri olmalıdır: "Üst Yazı", "Cevap Yazısı", "Bilgilendirme Metni". (Eksik Bilgi/Belge Talebi bu ajanın sorumluluğunda değildir).
   - `konu`: Resmî yazının özü ve mevzuata uygun konusu.
   - `ilgi`: Evraka referans veren resmî ilgi tutma cümlesi (örn: "14.11.2025 tarihli ve E-27584916-302-124 numaralı dilekçe.").
   - `govde_metni`: Yazının yalnızca özü, kararı ve gerekçesini anlatan sade içerik metni. Başlık, İlgi, Arz/Rica, İmza GİBİ ŞABLONLARI kesinlikle EKLEMEYİN. Sadece asıl paragrafı yazın.
   - `imza_makami`: Yazıyı imzalayacak/onaylayacak yetkili makam unvanı (örn: Dekan Yardımcısı, Birim Amiri, Daire Başkanı vb.).

ZORUNLU RESMÎ YAZI METNİ ÜRETİM KURALLARI (ASLA İHLAL EDİLEMEZ):
1. BAŞLIK VE YER TUTUCU (PLACEHOLDER) YASAĞI:
   - Evrakta belirtilmeyen veya taslak ifadeler olan "T.C. / KAMU KURUMU", "[Kurum Adı]", "..." gibi yer tutucuları asla kullanmayın. Belgelerden gerçek kurum ve makam adını tam ve eksiksiz tespit edip kullanın.
2. STANDART YAZI BLOKLARI:
   - Alıcı Makam Bloğu tam adıyla ve yönelme eki getirilerek BÜYÜK HARFLERLE yazılmalıdır (Örn: "SOSYAL GÜVENLİK KURUMU BAŞKANLIĞINA"). Varsa ilgi satırını ekleyin.
3. ARZ / RİCA KESİNLİĞİ:
   - "Gereğini/Bilgilerinize arz/rica ederim" gibi alternatifli veya eğik çizgili (/) ifadeler KESİNLİKLE YASAKTIR. Hiyerarşiye göre sadece tek bir kesin ifade seçin:
     * Üst makama: "Gereğini arz ederim." veya "Bilgilerinizi ve gereğini arz ederim."
     * Alt makama/vatandaşa: "Gereğini rica ederim."
     * Bilgilendirme amaçlı üst makama: "Bilgilerinize arz ederim."
4. TÜRKÇE BÜYÜK HARF (İ/I) DÜZELTME KURALI:
   - Türkçe büyük harf dönüşümlerinde noktalı "İ" karakterini koruyun. "TALEBI" -> "TALEBİ", "IÇIN" -> "İÇİN", "ILGILI" -> "İLGİLİ", "BILGILERINIZE" -> "BİLGİLERİNİZE".
5. VERİ VE KİMLİK DOĞRULUĞU:
   - 11 haneli numaraları T.C. Kimlik No, 10 haneli numaraları Vergi Kimlik No olarak etiketleyin/doğrulayın.

YALNIZCA geçerli bir JSON nesnesi döndür. Markdown, açıklama veya düşünme metni YAZMA.
"""


class TaslakYonlendirmeCiktisi(BaseModel):
    """Taslak ve Yönlendirme Ajanı çıktı şeması."""
    yonlendirme_karari: YonlendirmeKarari = Field(
        ...,
        description="Evrak yönlendirme kararı ve birim bilgileri"
    )
    resmi_yazi_taslagi: ResmiYaziTaslagi = Field(
        ...,
        description="Hazırlanan resmî yazı taslağı"
    )


def _normalize_input(girdi_verisi: Union[dict, str, BaseModel, Gorev1CiktiSemasi]) -> str:
    """Görev 1 girdisini JSON string formatına dönüştürür."""
    if isinstance(girdi_verisi, BaseModel) or hasattr(girdi_verisi, "model_dump_json"):
        return girdi_verisi.model_dump_json(indent=2, exclude_none=False)
    elif isinstance(girdi_verisi, dict):
        return json.dumps(girdi_verisi, ensure_ascii=False, indent=2)
    elif isinstance(girdi_verisi, str):
        try:
            parsed = json.loads(girdi_verisi)
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            return girdi_verisi
    else:
        return str(girdi_verisi)


def tr_upper(text: str) -> str:
    """Türkçe karakterleri koruyarak büyük harfe dönüştürür."""
    if not text:
        return ""
    mapping = {
        'i': 'İ',
        'ı': 'I',
        'ş': 'Ş',
        'ğ': 'Ğ',
        'ü': 'Ü',
        'ö': 'Ö',
        'ç': 'Ç'
    }
    result = []
    for char in text:
        if char in mapping:
            result.append(mapping[char])
        elif char.islower():
            result.append(char.upper())
        else:
            result.append(char)
    return "".join(result)


def duzelt_turkce_buyuk_harf(text: str) -> str:
    """Metin içindeki yaygın hatalı Türkçe büyük harf kullanımlarını düzeltir."""
    if not text:
        return ""
    
    corrections = {
        r"\bTALEBI\b": "TALEBİ",
        r"\bIÇIN\b": "İÇİN",
        r"\bICIN\b": "İÇİN",
        r"\bILGILI\b": "İLGİLİ",
        r"\bBILGILERINIZE\b": "BİLGİLERİNİZE",
        r"\bBILGILERINI\b": "BİLGİLERİNİ",
        r"\bBILGI\b": "BİLGİ",
        r"\bBILGISI\b": "BİLGİSİ",
        r"\bBILGILER\b": "BİLGİLER",
        r"\bGEREGINI\b": "GEREĞİNİ",
        r"\bGEREGINE\b": "GEREĞİNE",
        r"\bBELIRTILEN\b": "BELİRTİLEN",
        r"\bBELIRTILMEMIS\b": "BELİRTİLMEMİŞ",
        r"\bBIRIM\b": "BİRİM",
        r"\bBIRIMI\b": "BİRİMİ",
        r"\bBIRIMLERI\b": "BİRİMLERİ",
        r"\bBIRIMLER\b": "BİRİMLER",
        r"\bISTEK\b": "İSTEK",
        r"\bISTEGI\b": "İSTEĞİ",
        r"\bISLEM\b": "İŞLEM",
        r"\bISLEMI\b": "İŞLEMİ",
        r"\bISLEMLER\b": "İŞLEMLER",
        r"\bINSAN\b": "İNSAN",
        r"\bILÇE\b": "İLÇE",
        r"\bIL\b": "İL",
        r"\bILISKIN\b": "İLİŞKİN",
        r"\bIMZA\b": "İMZA",
        r"\bIVEDILI\b": "İVEDİLİ",
        r"\bIVEDI\b": "İVEDİ",
        r"\bSAYILI\b": "SAYILI",
        r"\bKANUNU\b": "KANUNU",
        r"\bYONETMELIGI\b": "YÖNETMELİĞİ",
        r"\bDEKANLIGI\b": "DEKANLIĞI",
        r"\bREKTORLUGU\b": "REKTÖRLÜĞÜ",
        r"\bMUDURLUGU\b": "MÜDÜRLÜĞÜ",
        r"\bBASKANLIGI\b": "BAŞKANLIĞI",
        r"\bVALILIGI\b": "VALİLİĞİ",
        r"\bBELEDIYESI\b": "BELEDİYESİ",
        r"\bBELEDIYE\b": "BELEDİYE",
        r"\bTÜRKÇE\b": "TÜRKÇE",
    }
    
    for pattern, replacement in corrections.items():
        text = re.sub(pattern, replacement, text)
        
    return text


def append_direction_suffix(text: str) -> str:
    """Kamu kurum adına resmi yazışma kurallarına uygun yönelme eki ekler."""
    text = text.strip()
    if not text:
        return ""
    
    text = re.sub(r'[.:\s]+$', '', text)
    text_upper = tr_upper(text)
    
    if text_upper.endswith(("NA", "NE", "YA", "YE", "A", "E")):
        return text_upper

    suffixes = [
        ("BAŞKANLIĞI", "BAŞKANLIĞINA"),
        ("MÜDÜRLÜĞÜ", "MÜDÜRLÜĞÜNE"),
        ("DEKANLIĞI", "DEKANLIĞINA"),
        ("REKTÖRLÜĞÜ", "REKTÖRLÜĞÜNE"),
        ("DAİRESİ", "DAİRESİNE"),
        ("VALİLİĞİ", "VALİLİĞİNE"),
        ("KAYMAKAMLIĞI", "KAYMAKAMLIĞINA"),
        ("BAKANLIĞI", "BAKANLIĞINA"),
        ("KOMUTANLIĞI", "KOMUTANLIĞINA"),
        ("MÜŞAVİRLİĞİ", "MÜŞAVİRLİĞİNE"),
        ("ŞEFLİĞİ", "ŞEFLİĞİNE"),
        ("ODASI", "ODASINA"),
        ("BİRLİĞİ", "BİRLİĞİNE"),
        ("ŞİRKETİ", "ŞİRKETİNE"),
        ("VAKFI", "VAKFINA"),
        ("DERNEĞİ", "DERNEĞİNE"),
        ("BÖLÜMÜ", "BÖLÜMÜNE"),
        ("FAKÜLTESİ", "FAKÜLTESİNE"),
        ("KURUMU", "KURUMUNA"),
        ("MERKEZİ", "MERKEZİNE"),
        ("ŞUBESİ", "ŞUBESİNE"),
        ("ÜNİVERSİTESİ", "ÜNİVERSİTESİNE"),
        ("BELEDİYESİ", "BELEDİYESİNE"),
        ("SAYMANLIĞI", "SAYMANLIĞINA"),
    ]
    
    for suffix, suffixed in suffixes:
        if text_upper.endswith(suffix):
            return text_upper[:-len(suffix)] + suffixed
            
    last_char = text_upper[-1] if text_upper else ""
    vowels = "AIEİOÖUÜ"
    last_vowel = ""
    for char in reversed(text_upper):
        if char in vowels:
            last_vowel = char
            break
            
    if last_vowel in "AIOU":
        suffix_to_add = "NA" if last_char in vowels else "A"
    else:
        suffix_to_add = "NE" if last_char in vowels else "E"
        
    return text_upper + suffix_to_add


def determine_arz_rica(yazi_turu: str, sender: str, recipient: str) -> str:
    """Makam hiyerarşisine göre doğru arz/rica ifadesini seçer."""
    sender = tr_upper(sender)
    recipient = tr_upper(recipient)
    
    admin_keywords = [
        "MÜDÜRLÜĞÜ", "DEKANLIĞI", "BAŞKANLIĞI", "VALİLİĞİ", "REKTÖRLÜĞÜ", 
        "BAKANLIĞI", "KOMUTANLIĞI", "ŞUBE", "ODASI", "BİRLİĞİ", "ŞEFLİĞİ", 
        "KAYMAKAMLIĞI", "DAİRESİ", "MAHKEMESİ"
    ]
    is_recipient_admin = any(kw in recipient for kw in admin_keywords)
    
    if not is_recipient_admin:
        return "Gereğini rica ederim."
        
    if yazi_turu == "Bilgilendirme Metni":
        return "Bilgilerinize arz ederim."
        
    superiors = ["DEKANLIĞI", "REKTÖRLÜĞÜ", "VALİLİĞİ", "BAŞKANLIĞI", "BAKANLIĞI", "KOMUTANLIĞI", "KAYMAKAMLIĞI", "MAHKEMESİ"]
    subordinates = ["MÜDÜRLÜĞÜ", "BÖLÜMÜ", "ŞEF", "SERVİSİ", "ŞUBESİ", "ODASI", "BİRLİĞİ", "DAİRESİ"]
    
    sender_is_superior = any(kw in sender for kw in superiors)
    recipient_is_subordinate = any(kw in recipient for kw in subordinates)
    sender_is_subordinate = any(kw in sender for kw in subordinates)
    recipient_is_superior = any(kw in recipient for kw in superiors)
    
    if sender_is_superior and recipient_is_subordinate:
        return "Gereğini rica ederim."
    elif sender_is_subordinate and recipient_is_superior:
        return "Gereğini arz ederim."
        
    if yazi_turu == "Eksik Bilgi/Belge Talebi":
        return "Gereğini rica ederim."
        
    return "Gereğini rica ederim."


def sanitize_arz_rica(text: str, yazi_turu: str, sender: str, recipient: str) -> str:
    """Eğik çizgili veya hatalı arz/rica ifadelerini temizleyip standartlaştırır."""
    text = text.strip()
    allowed = [
        "Gereğini arz ederim.",
        "Bilgilerinizi ve gereğini arz ederim.",
        "Gereğini rica ederim.",
        "Bilgilerinize arz ederim."
    ]
    if text in allowed:
        return text
        
    text_clean = text.rstrip(".")
    if "arz ederim" in text_clean.lower():
        if "bilgilerinize" in text_clean.lower() and "gereğini" in text_clean.lower():
            return "Bilgilerinizi ve gereğini arz ederim."
        elif "bilgilerinize" in text_clean.lower():
            return "Bilgilerinize arz ederim."
        else:
            return "Gereğini arz ederim."
    elif "rica ederim" in text_clean.lower():
        return "Gereğini rica ederim."
        
    return determine_arz_rica(yazi_turu, sender, recipient)


def dogrula_kimlik_ve_vergi_no(text: str) -> str:
    """T.C. Kimlik No (11 hane) ve Vergi Kimlik No (10 hane) etiketlerini doğrular."""
    if not text:
        return ""
    
    tc_numbers = re.findall(r'\b[1-9]\d{10}\b', text)
    vergi_numbers = re.findall(r'\b\d{10}\b', text)
    vergi_numbers = [n for n in vergi_numbers if len(n) == 10]
    
    for tc in tc_numbers:
        pattern = rf'(Vergi\s*(?:Kimlik)?\s*(?:No|Numarası)?\s*[:\-]?\s*){tc}\b'
        text = re.sub(pattern, lambda m: f"T.C. Kimlik Numarası: {tc}", text, flags=re.IGNORECASE)
        
    for vn in vergi_numbers:
        pattern = rf'((?:T\.?C\.?\s*(?:Kimlik)?\s*(?:No|Numarası)?)\s*[:\-]?\s*){vn}\b'
        text = re.sub(pattern, lambda m: f"Vergi Kimlik Numarası: {vn}", text, flags=re.IGNORECASE)
        
    return text


def _format_resmi_yazi(taslak: ResmiYaziTaslagi, yonlendirme: Optional[YonlendirmeKarari] = None, girdi_dict: Optional[dict] = None) -> str:
    """LLM'den gelen saf içeriği resmi yazışma kurallarına göre şablona oturtur."""
    from datetime import datetime
    import random
    
    sender_kurum = ""
    sender_birim = ""
    
    if girdi_dict:
        gonderen = girdi_dict.get("gonderen", {})
        if gonderen.get("gonderen_tipi") == "Kamu Kurumu" and gonderen.get("ad_soyad_veya_unvan"):
            unvan = gonderen.get("ad_soyad_veya_unvan", "")
            unvan_clean = re.sub(r'^T\.?C\.?\s*', '', unvan, flags=re.IGNORECASE).strip()
            sender_kurum = unvan_clean
        else:
            varliklar = girdi_dict.get("varliklar", {})
            kurumlar = varliklar.get("kurumlar", [])
            if kurumlar:
                first_kurum = kurumlar[0]
                first_kurum_clean = re.sub(r'^T\.?C\.?\s*', '', first_kurum, flags=re.IGNORECASE).strip()
                sender_kurum = first_kurum_clean
                
    if not sender_kurum:
        if yonlendirme and getattr(yonlendirme, "islem_yapacak_ana_kurum", ""):
            sender_kurum = re.sub(r'^T\.?C\.?\s*', '', yonlendirme.islem_yapacak_ana_kurum, flags=re.IGNORECASE).strip()
        else:
            sender_kurum = "BELEDİYE BAŞKANLIĞI"
        
    sender_header = f"T.C.\n{tr_upper(sender_kurum)}"
    if sender_birim:
        sender_header += f"\n{tr_upper(sender_birim)}"
        
    for placeholder in ["T.C. / KAMU KURUMU", "KAMU KURUMU", "[KURUM ADI]", "[BİRİM ADI]", "..."]:
        sender_header = sender_header.replace(placeholder, "")
    sender_header = "\n".join([line for line in sender_header.splitlines() if line.strip()])
    
    if not sender_header.startswith("T.C."):
        sender_header = f"T.C.\n{sender_header}"

    # Generate a realistic dynamic number deterministic to this draft's topic if not provided
    random.seed(hash(taslak.konu) if taslak.konu else None)
    rand_kurum = random.randint(10000000, 99999999)
    rand_sira = random.randint(100, 9999)
    sayi = f"E-{rand_kurum}-950.01.04-{rand_sira}"
    
    if girdi_dict:
        girdi_sayi = girdi_dict.get("sayi_veya_kayit_no")
        if girdi_sayi and girdi_sayi.strip().lower() not in ["", "null", "none", "belirtilmemiş"]:
            sayi = girdi_sayi.strip()
            
    tarih = datetime.now().strftime("%d.%m.%Y")
    if girdi_dict:
        girdi_tarih = girdi_dict.get("evrak_tarihi")
        if girdi_tarih and girdi_tarih.strip().lower() not in ["", "null", "none", "belirtilmemiş"]:
            tarih = girdi_tarih.strip()

    alici = "İLGİLİ MAKAMA"
    if yonlendirme:
        ana_kurum = getattr(yonlendirme, "islem_yapacak_ana_kurum", "")
        birim = getattr(yonlendirme, "geregi_icin_yonlendirilecek_birim", "")
        if ana_kurum or birim:
            alici = f"{ana_kurum} {birim}".strip()
            
    alici_makam_blogu = append_direction_suffix(alici)

    ilgi_satiri = ""
    if taslak.ilgi and taslak.ilgi.strip().lower() not in ["", "null", "none", "belirtilmemiş"]:
        ilgi_val = taslak.ilgi.strip()
        if not ilgi_val.lower().startswith("ilgi"):
            ilgi_satiri = f"İlgi: {ilgi_val}"
        else:
            ilgi_satiri = "İlgi:" + ilgi_val[5:]
            
    ilgi_part = f"\n{ilgi_satiri}\n" if ilgi_satiri else "\n"

    yazi_turu_val = getattr(taslak.yazi_turu, "value", str(taslak.yazi_turu))
    
    govde = taslak.govde_metni.strip()
    pattern_clean = r'(?:gereğini|bilgilerinizi?\s*(?:ve\s*gereğini)?)\s*(?:arz/rica|arz|rica)\s*ederim\.?$'
    govde = re.sub(pattern_clean, "", govde, flags=re.IGNORECASE).strip()
    govde = re.sub(r'(?:arz/rica|arz\s*ve\s*rica|arz|rica)\s*ederim\.?$', "", govde, flags=re.IGNORECASE).strip()
    govde = re.sub(r'bilgilerinize\s*sunarım\.?$', "", govde, flags=re.IGNORECASE).strip()
    govde = re.sub(r'bilgilerinize\s*arz\s*ederim\.?$', "", govde, flags=re.IGNORECASE).strip()
    govde = govde.rstrip(",. ")

    raw_arz_rica = ""
    last_sentences = re.findall(r'[^.!?]+[.!?]?', taslak.govde_metni)
    if last_sentences:
        last_s = last_sentences[-1].strip()
        if "arz" in last_s.lower() or "rica" in last_s.lower():
            raw_arz_rica = last_s
            
    arz_rica = sanitize_arz_rica(raw_arz_rica, yazi_turu_val, sender_kurum, alici)
    imza = taslak.imza_makami.strip()

    full_text = f"""{sender_header}

Sayı  : {sayi}
Konu  : {tr_upper(taslak.konu)}
Tarih : {tarih}

{alici_makam_blogu}
{ilgi_part}
{govde}.

{arz_rica}

{imza}
"""
    full_text = duzelt_turkce_buyuk_harf(full_text)
    full_text = dogrula_kimlik_ve_vergi_no(full_text)
    
    return full_text


def calistir_yonlendirme_taslak_ajani(
    client,
    model: str,
    girdi_verisi: Union[dict, str, BaseModel, Gorev1CiktiSemasi]
) -> TaslakYonlendirmeCiktisi:
    """
    Görev 1 analiz çıktısını alarak yönlendirme kararı ve resmi yazı taslağını üretir.
    """
    schema_str = json.dumps(TaslakYonlendirmeCiktisi.model_json_schema(), ensure_ascii=False)
    sistem_mesaji = f"""{TASLAK_YONLENDIRME_PROMPT}

Beklenen JSON Şeması:
{schema_str}"""

    input_json_str = _normalize_input(girdi_verisi)
    user_prompt = f"Aşağıdaki Görev 1 evrak analiz verisini inceleyerek Yönlendirme ve Resmi Yazı Taslağı çıktısını JSON olarak oluştur:\n\n{input_json_str}"

    messages = [
        {"role": "system", "content": sistem_mesaji},
        {"role": "user", "content": user_prompt}
    ]

    max_deneme = 3
    son_hata = None

    for deneme in range(max_deneme):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1
            )

            raw_text = validate_response_content(response)

            if "<think>" in raw_text:
                if "</think>" in raw_text:
                    raw_text = raw_text.split("</think>")[-1].strip()
                else:
                    raw_text = re.sub(r"^<think>.*?(?=\{)", "", raw_text, flags=re.DOTALL).strip()

            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
            raw_text = re.sub(r"\s*```\s*$", "", raw_text, flags=re.MULTILINE)
            raw_text = raw_text.strip()

            start_idx = raw_text.find("{")
            end_idx = raw_text.rfind("}")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                raw_text = raw_text[start_idx:end_idx + 1]

            raw_text = re.sub(r"//[^\n]*", "", raw_text)
            raw_text = re.sub(r"/\*.*?\*/", "", raw_text, flags=re.DOTALL)
            raw_text = re.sub(r",\s*([}\]])", r"\1", raw_text)

            try:
                cikti = TaslakYonlendirmeCiktisi.model_validate_json(raw_text)
            except Exception:
                payload = json.loads(raw_text)
                cikti = TaslakYonlendirmeCiktisi.model_validate(payload)

            return cikti

        except Exception as e:
            son_hata = e
            hata_str = str(e).lower()
            if "rate limit" in hata_str or "429" in hata_str:
                time.sleep(4)
            elif "json" in hata_str or "validation" in hata_str:
                time.sleep(1)
            else:
                time.sleep(2)

    if son_hata is not None:
        raise son_hata
    raise RuntimeError("Maksimum deneme sayısına ulaşıldı ve bir hata yakalanamadı.")
