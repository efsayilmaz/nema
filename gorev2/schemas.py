"""
gorev2/schemas.py
TEKNOFEST 2026 Yapay Zeka Dil Ajanları Yarışması - Görev 2 Pydantic Veri Şemaları

Bu modül, Görev 2 (Resmî Yazı Taslaklama ve Birim Yönlendirme) kapsamında üretilecek
yapılandırılmış çıktıların Pydantic veri şemalarını içerir.
"""

from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field, field_validator


class YaziTuru(str, Enum):
    """Resmî yazı türleri için enum tanımı."""
    EKSIK_BILGI_BELGE_TALEBI = "Eksik Bilgi/Belge Talebi"
    UST_YAZI = "Üst Yazı"
    CEVAP_YAZISI = "Cevap Yazısı"
    BILGILENDIRME_METNI = "Bilgilendirme Metni"


class AksiyonDurumu(str, Enum):
    """Sistem aksiyon durumları için enum tanımı."""
    KULLANICI_BEKLENIYOR = "Kullanıcı Bekleniyor"
    ISLEME_ALINDI = "İşleme Alındı"
    ONAY_BEKLIYOR = "Onay Bekliyor"


class YonlendirmeKarari(BaseModel):
    """Evrakın hangi kuruma/birime yönlendirileceğine dair karar şeması."""
    islem_yapacak_ana_kurum: str = Field(
        ...,
        description="Evrakla ilgili asıl işlemi yürütecek ana kurum (örn: İlgili İlçe/Büyükşehir Belediye Başkanlığı, Atatürk Üniversitesi Dekanlığı vb.)"
    )
    geregi_icin_yonlendirilecek_birim: str = Field(
        ...,
        description="Evrakın gereğinin yapılması için sevk edileceği alt birim (örn: Veteriner İşleri Müdürlüğü, Fizik Bölümü Başkanlığı vb.)"
    )
    bilgi_icin_iletilecek_birimler: List[str] = Field(
        default_factory=list,
        description="Evrak hakkında bilgi sahibi olması gereken diğer birimlerin listesi"
    )
    yonlendirme_gerekcesi: str = Field(
        ...,
        description="Evrakın neden bu kuruma ve birime yönlendirildiğini açıklayan ayrıntılı gerekçe"
    )


class ResmiYaziTaslagi(BaseModel):
    """Hazırlanacak resmî yazı taslağı şeması."""
    yazi_turu: YaziTuru = Field(
        ...,
        description="Hazırlanan resmî yazının türü ('Eksik Bilgi/Belge Talebi', 'Üst Yazı', 'Cevap Yazısı', 'Bilgilendirme Metni')"
    )
    konu: str = Field(
        ...,
        description="Resmî yazının konusu"
    )
    ilgi: str = Field(
        ...,
        description="Yazının ilgi tuttuğu evrak, dilekçe veya tarih/sayı bilgisi (örn: Tarihsiz, isimsiz ve imzasız başvuru.)"
    )
    govde_metni: str = Field(
        ...,
        description="Resmî yazışma kurallarına uygun, kurumsal üslup taşıyan gövde metni"
    )
    imza_makami: str = Field(
        ...,
        description="Yazıyı imzalayacak/onaylayacak makam unvanı (örn: Birim Amiri, Dekan Yardımcısı, İmar ve Şehircilik Müdürü vb.)"
    )

    @field_validator("yazi_turu", mode="before")
    @classmethod
    def _normalize_yazi_turu(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip()
            if "Eksik" in v_clean:
                return YaziTuru.EKSIK_BILGI_BELGE_TALEBI.value
            elif "Üst" in v_clean or "Ust" in v_clean:
                return YaziTuru.UST_YAZI.value
            elif "Cevap" in v_clean:
                return YaziTuru.CEVAP_YAZISI.value
            elif "Bilgilen" in v_clean:
                return YaziTuru.BILGILENDIRME_METNI.value
        return v


class KullaniciBilgilendirme(BaseModel):
    """Kullanıcıya gösterilecek bilgilendirme ve sistem aksiyon durumu şeması."""
    kullaniciya_gosterilecek_mesaj: str = Field(
        ...,
        description="Başvuru sahibine veya kullanıcıya sürecin durumunu açıklayan anlaşılır mesaj"
    )
    sistem_aksiyon_durumu: AksiyonDurumu = Field(
        ...,
        description="Sistemin mevcut aksiyon durumu ('Kullanıcı Bekleniyor', 'İşleme Alındı', 'Onay Bekliyor')"
    )

    @field_validator("sistem_aksiyon_durumu", mode="before")
    @classmethod
    def _normalize_aksiyon_durumu(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip()
            if "Bekleniyor" in v_clean and "Kullan" in v_clean:
                return AksiyonDurumu.KULLANICI_BEKLENIYOR.value
            elif "Alındı" in v_clean or "Alindi" in v_clean:
                return AksiyonDurumu.ISLEME_ALINDI.value
            elif "Onay" in v_clean:
                return AksiyonDurumu.ONAY_BEKLIYOR.value
        return v


class Gorev2CiktiSemasi(BaseModel):
    """Görev 2 çıktı veri şeması."""
    yonlendirme_karari: YonlendirmeKarari = Field(
        ...,
        description="Evrak yönlendirme kararı ve birim bilgileri"
    )
    resmi_yazi_taslagi: ResmiYaziTaslagi = Field(
        ...,
        description="Hazırlanan resmî yazı taslağı"
    )
    kullanici_bilgilendirme: KullaniciBilgilendirme = Field(
        ...,
        description="Kullanıcı bilgilendirme ve sistem aksiyon durumu"
    )


# --- Görev 1 Girdi Şemaları ---

class GonderenSemasi(BaseModel):
    """Görev 1 evrakı gönderen bilgisi şeması."""
    gonderen_tipi: Optional[str] = Field(default=None, description="Gönderen tipi (örn: Gerçek Kişi, Tüzel Kişi / Şirket, Kamu Kurumu)")
    ad_soyad_veya_unvan: Optional[str] = Field(default=None, description="Ad soyad veya unvan")
    kimlik_veya_vergi_no: Optional[str] = Field(default=None, description="T.C. Kimlik veya Vergi Numarası")
    iletisim_bilgisi: Optional[str] = Field(default=None, description="İletişim adresi / telefon")


class VarliklarSemasi(BaseModel):
    """Görev 1 varlıklar (kurumlar, lokasyonlar, tarihler) şeması."""
    kurumlar: List[str] = Field(default_factory=list, description="Metinde geçen kurumlar")
    lokasyonlar: List[str] = Field(default_factory=list, description="Metinde geçen lokasyonlar")
    tarihler: List[str] = Field(default_factory=list, description="Metinde geçen tarihler")


class Gorev1CiktiSemasi(BaseModel):
    """Görev 1 girdi veri şeması."""
    evrak_turu: Optional[str] = Field(default=None, description="Evrak türü")
    konu: Optional[str] = Field(default=None, description="Evrak konusu")
    evrak_tarihi: Optional[str] = Field(default=None, description="Evrak tarihi")
    sayi_veya_kayit_no: Optional[str] = Field(default=None, description="Sayı veya kayıt numarası")
    gonderen: Optional[GonderenSemasi] = Field(default=None, description="Gönderen bilgileri")
    kisa_ozet: Optional[str] = Field(default=None, description="Evrak kısa özeti")
    varliklar: Optional[VarliklarSemasi] = Field(default=None, description="Varlıklar (kurum, lokasyon, tarih)")
    ilgili_mevzuat_onerisi: List[str] = Field(default_factory=list, description="İlgili mevzuat önerileri")
    eksik_bilgiler: List[str] = Field(default_factory=list, description="Tespiti yapılan eksik bilgiler")
    aciliyet_durumu: Optional[str] = Field(default=None, description="Aciliyet durumu (Normal, İvedi, Çok İvedi vb.)")
