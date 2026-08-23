from typing import List, Optional

from pydantic import BaseModel, Field


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


class Gorev1CiktiSemasi(BaseModel):
    evrak_turu: str
    konu: str
    evrak_tarihi: Optional[str] = None
    sayi_veya_kayit_no: Optional[str] = None
    gonderen: GonderenSemasi
    kisa_ozet: str
    varliklar: VarliklarSemasi
    ilgili_mevzuat_onerisi: List[str] = Field(default_factory=list)
    eksik_bilgiler: List[str] = Field(default_factory=list)
    aciliyet_durumu: str
