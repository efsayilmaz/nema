from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

class AciliyetDurumu(str, Enum):
    NORMAL = "Normal"
    IVEDI = "İvedi"
    COK_IVEDI = "Çok İvedi"


class GonderenSemasi(BaseModel):
    gonderen_tipi: str = Field(
        description="Gerçek Kişi, Tüzel Kişi / Şirket veya Kamu Kurumu"
    )
    ad_soyad_veya_unvan: Optional[str] = None
    kimlik_veya_vergi_no: Optional[str] = None
    iletisim_bilgisi: Optional[str] = None


class VarliklarSemasi(BaseModel):
    kurumlar: List[str] = Field(default_factory=list)
    lokasyonlar: List[str] = Field(default_factory=list)
    tarihler: List[str] = Field(default_factory=list)


class EksikBilgiDegerlendirmesi(BaseModel):
    bilgi: str
    mevzuat_maddesi: str
    sonuc: str


class IslemeDevamEdilebilirlikSemasi(BaseModel):
    zorunlu_eksikler: List[EksikBilgiDegerlendirmesi] = Field(default_factory=list)
    zorunlu_olmayan_eksikler: List[EksikBilgiDegerlendirmesi] = Field(default_factory=list)


class Gorev1CiktiSemasi(BaseModel):
    evrak_turu: str
    evrak_ozeti: str = Field(
        default="",
        description="Özetleme ajanının evrakın niyetini ve gerekçesini anlatan kısa özeti."
    )
    konu: str = Field(
        description="Evrakın niyetini ve gerekçesini kendi cümlesiyle anlatan yeni konu. Evrak kimliği, kurum, alıcı, gönderen, tarih, sayı, adres veya 'Konu:' içermez."
    )
    evrak_tarihi: Optional[str] = None
    sayi_veya_kayit_no: Optional[str] = None
    gonderen: GonderenSemasi
    kisa_ozet: str = Field(
        description="Evrakın niyetini ve gerekçesini 1-3 özgün cümleyle anlatır. Evrak kimliği, kurum, alıcı, gönderen, tarih, sayı, adres veya belge başlığını tekrarlamaz."
    )
    varliklar: VarliklarSemasi
    onemli_bilgi_unsurlari: List[str] = Field(
        default_factory=list,
        description="Sınıflandırma ve bilgi çıkarım ajanının belirlediği önemli unsurlar."
    )
    ilgili_mevzuat_onerisi: List[str] = Field(default_factory=list)
    eksik_bilgiler: List[str] = Field(default_factory=list)
    isleme_devam_edilebilirlik_durumu: IslemeDevamEdilebilirlikSemasi = Field(
        default_factory=IslemeDevamEdilebilirlikSemasi
    )
    yasal_yanit_suresi: Optional[str] = Field(
        default=None,
        description="Lookup tablosundan deterministik olarak bulunan yasal yanıt süresi."
    )
    aciliyet_durumu: AciliyetDurumu
