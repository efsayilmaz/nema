import os
import re

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import docx
except ImportError:
    docx = None

# SISTEM GEREKSINIMLERI NOTU:
# Bu modülün OCR yeteneklerini kullanabilmesi için sistemde Tesseract'ın kurulu olması gerekir.
# Ubuntu/Debian:
# sudo apt-get install tesseract-ocr tesseract-ocr-tur
#
# Poppler kütüphanesi pdf2image için gereklidir:
# Ubuntu/Debian: sudo apt-get install poppler-utils
# Windows (Tesseract ve Poppler) için binary kurulumlar yapılıp, Path'e eklenmelidir.

def normalize_metin(metin: str) -> str:
    """
    Metin içerisindeki fazla boşlukları ve satır sonu gürültülerini temizler.
    Tüm satır atlamalarını ve boşlukları tek bir boşluğa indirger.
    """
    if not metin:
        return ""
    
    # OCR çıktısındaki fazla boşlukları ve alt alta inmeleri temizler
    return " ".join(metin.split())


def _pdf_metin_cikar(dosya_yolu: str) -> dict:
    if not pypdf:
        raise ImportError("pypdf kütüphanesi kurulu değil. Lütfen 'pip install pypdf' çalıştırın.")
        
    sayfa_sayisi = 0
    metin_parcalari = []
    
    with open(dosya_yolu, "rb") as f:
        reader = pypdf.PdfReader(f)
        sayfa_sayisi = len(reader.pages)
        for sayfa in reader.pages:
            sayfa_metni = sayfa.extract_text()
            if sayfa_metni:
                metin_parcalari.append(sayfa_metni)
                
    ham_metin = "\n".join(metin_parcalari)
    
    # Eğer metin yok veya çok kısaysa muhtemelen PDF görselden (taranmış) ibarettir.
    if len(ham_metin.strip()) < 20:
        return {"yeterli_metin": False, "sayfa_sayisi": sayfa_sayisi}
        
    return {
        "yeterli_metin": True,
        "sayfa_sayisi": sayfa_sayisi,
        "ham_metin": normalize_metin(ham_metin),
        "okuma_yontemi": "pdf_metin"
    }


def _pdf_ocr_cikar(dosya_yolu: str) -> dict:
    if not convert_from_path or not pytesseract:
        raise ImportError("pdf2image veya pytesseract kütüphaneleri eksik. "
                          "Lütfen 'pip install pdf2image pytesseract' çalıştırın.")
                          
    goruntuler = convert_from_path(dosya_yolu)
    sayfa_sayisi = len(goruntuler)
    metin_parcalari = []
    
    for goruntu in goruntuler:
        # Türkçe dil paketi ile OCR işlemi
        sayfa_metni = pytesseract.image_to_string(goruntu, lang='tur')
        metin_parcalari.append(sayfa_metni)
        
    ham_metin = normalize_metin("\n".join(metin_parcalari))
    
    guven_notu = None
    if len(ham_metin) < 20:
        guven_notu = "OCR düşük güvenilirlikte, manuel kontrol önerilir"
        
    return {
        "okuma_yontemi": "ocr",
        "ham_metin": ham_metin,
        "sayfa_sayisi": sayfa_sayisi,
        "guven_notu": guven_notu
    }


def _gorsel_ocr_cikar(dosya_yolu: str) -> dict:
    if not Image or not pytesseract:
        raise ImportError("Pillow veya pytesseract kütüphaneleri eksik. "
                          "Lütfen 'pip install Pillow pytesseract' çalıştırın.")
                          
    goruntu = Image.open(dosya_yolu)
    ham_metin = pytesseract.image_to_string(goruntu, lang='tur')
    ham_metin = normalize_metin(ham_metin)
    
    guven_notu = None
    if len(ham_metin) < 20:
        guven_notu = "OCR düşük güvenilirlikte, manuel kontrol önerilir"
        
    return {
        "okuma_yontemi": "ocr",
        "ham_metin": ham_metin,
        "sayfa_sayisi": 1,
        "guven_notu": guven_notu
    }


def _docx_oku(dosya_yolu: str) -> dict:
    if not docx:
        raise ImportError("python-docx kütüphanesi eksik. Lütfen 'pip install python-docx' çalıştırın.")
        
    doc = docx.Document(dosya_yolu)
    paragraflar = [p.text for p in doc.paragraphs]
    ham_metin = normalize_metin("\n".join(paragraflar))
    
    return {
        "okuma_yontemi": "docx",
        "ham_metin": ham_metin,
        "sayfa_sayisi": 1, # DOCX sayfalarını hesaplamak karmaşıktır, 1 olarak varsayıyoruz
        "guven_notu": None
    }
    

def _txt_oku(dosya_yolu: str) -> dict:
    # Olası farklı encoding türlerine karşın esnek deneme
    ham_metin = ""
    for enc in ['utf-8', 'cp1254', 'iso-8859-9']:
        try:
            with open(dosya_yolu, 'r', encoding=enc) as f:
                ham_metin = f.read()
            break
        except UnicodeDecodeError:
            continue
            
    ham_metin = normalize_metin(ham_metin)
    
    return {
        "okuma_yontemi": "txt",
        "ham_metin": ham_metin,
        "sayfa_sayisi": 1,
        "guven_notu": None
    }


def evrak_oku(dosya_yolu: str) -> dict:
    """
    Girdi olarak verilen dosyayı okur, metni temizler ve bir dictionary formatında döndürür.
    Çıktıdaki 'ham_metin' alanı Görev 1 ajanı (LLM) için prompt'a verilmeye hazırdır.
    
    Return format:
    {
        "kaynak_dosya": str,
        "okuma_yontemi": "pdf_metin" | "ocr" | "docx" | "txt",
        "ham_metin": str,
        "sayfa_sayisi": int,
        "guven_notu": str | None   # OCR belirsizse uyarı
    }
    """
    if not os.path.exists(dosya_yolu):
        return {"hata": f"Dosya bulunamadı: {dosya_yolu}"}
        
    uzanti = os.path.splitext(dosya_yolu)[1].lower()
    
    try:
        if uzanti == '.pdf':
            # İlk tercih: Eğer pdf ise seçilebilir metin var mı kontrolü
            pdf_sonuc = _pdf_metin_cikar(dosya_yolu)
            if pdf_sonuc["yeterli_metin"]:
                return {
                    "kaynak_dosya": dosya_yolu,
                    "okuma_yontemi": pdf_sonuc["okuma_yontemi"],
                    "ham_metin": pdf_sonuc["ham_metin"],
                    "sayfa_sayisi": pdf_sonuc["sayfa_sayisi"],
                    "guven_notu": None
                }
            else:
                # Metin bulunamadı veya çok az, demek ki PDF görüntü tabanlı (taranmış)
                ocr_sonuc = _pdf_ocr_cikar(dosya_yolu)
                ocr_sonuc["kaynak_dosya"] = dosya_yolu
                return ocr_sonuc
                
        elif uzanti in ['.jpg', '.jpeg', '.png']:
            ocr_sonuc = _gorsel_ocr_cikar(dosya_yolu)
            ocr_sonuc["kaynak_dosya"] = dosya_yolu
            return ocr_sonuc
            
        elif uzanti == '.docx':
            docx_sonuc = _docx_oku(dosya_yolu)
            docx_sonuc["kaynak_dosya"] = dosya_yolu
            return docx_sonuc
            
        elif uzanti == '.txt':
            txt_sonuc = _txt_oku(dosya_yolu)
            txt_sonuc["kaynak_dosya"] = dosya_yolu
            return txt_sonuc
            
        else:
            return {"hata": f"Desteklenmeyen veya tanımlanmamış dosya formatı: {uzanti}"}
            
    except Exception as e:
        return {"hata": f"Dosya okuma sırasında hata oluştu: {str(e)}"}


if __name__ == "__main__":
    # Test Bloğu
    import tempfile
    
    print("Evrak Okuyucu Test Ediliyor...\n")
    
    # 1. TXT Testi (Temizlik ve Normalizasyon)
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode='w', encoding='utf-8') as f:
        f.write("TEKNOFEST\n\n\n\n\nKamu      Evrak    Sistemi\nBu   bir\test metnidir.")
        test_txt = f.name
        
    print(f"--- TXT TESTİ ({test_txt}) ---")
    sonuc_txt = evrak_oku(test_txt)
    print(sonuc_txt)
    os.remove(test_txt)
    
    print("\n------------------------------\n")
    print("GÖREV 1 (Analiz) Entegrasyon Örneği:")
    print("def gorev1_ajani_calistir(ham_metin):")
    print("    pass")
    print("\n# Örnek Kullanım:")
    print('# sonuc = evrak_oku("ornek_belge.pdf")')
    print('# if "hata" not in sonuc:')
    print('#     gorev1_ajani_calistir(ham_metin=sonuc["ham_metin"])')
