from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class AciliyetDurumu(str, Enum):
    NORMAL = "Normal"
    IVEDI = "İvedi"
    COK_IVEDI = "Çok İvedi"


class EksikBilgiDerecesi(str, Enum):
    KRITIK_ENGELLENMIS = "Kritik (Taslak Üretilemez / İşleme Alınamaz)"
    TAMAMLANABILIR = "Tamamlanabilir (Eksik Belge Talebi Yazılabilir)"
    EKSIKSIZ = "Eksiksiz (Doğrudan Üst Yazı Yazılabilir)"


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
    taslak_olusturulabilir_mi: bool = Field(
        default=True,
        description="Mevzuata göre resmi taslak üretilip Görev 2'ye geçilebilir mi?"
    )
    derece: EksikBilgiDerecesi = Field(
        default=EksikBilgiDerecesi.EKSIKSIZ,
        description="Eksik bilgilerin mevzuattaki ağırlık derecesi."
    )
    gerekce: str = Field(
        default="Tüm yasal şartlar sağlanmıştır.",
        description="Mevzuata dayalı işleme devam / durdurma gerekçesi."
    )
    zorunlu_eksikler: List[EksikBilgiDegerlendirmesi] = Field(
        default_factory=list,
        description="3071 m.4/6, 4982 m.6 uyarınca yokluğu işlemi engelleyen kritik eksikler."
    )
    tamamlanabilir_eksikler: List[EksikBilgiDegerlendirmesi] = Field(
        default_factory=list,
        description="Eksik Belge Talebi yazısıyla tamamlatılabilecek idari eksikler."
    )
    zorunlu_olmayan_eksikler: List[EksikBilgiDegerlendirmesi] = Field(
        default_factory=list,
        description="Geriye dönük uyumluluk için tamamlanabilir eksikler kopyası."
    )


class Gorev1CiktiSemasi(BaseModel):
    evrak_turu: str
    sektor: str = Field(
        default="genel",
        description="Evrak içeriğinin ait olduğu sektörel alan (örn: sağlık, hukuk, savunma, eğitim, belediye, tüketici, bilgi, genel). Hiçbirine uymuyorsa 'genel' seçin."
    )
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
    taslak_olusturulabilir_mi: bool = Field(
        default=True,
        description="Mevzuata göre Görev 2'ye geçilip taslak oluşturulabilir mi?"
    )
    eksik_bilgi_derecesi: Optional[str] = Field(
        default=None,
        description="Kritik (Engellenmiş), Tamamlanabilir veya Eksiksiz"
    )
    isleme_devam_gerekcesi: Optional[str] = Field(
        default=None,
        description="Mevzuata dayalı gerekçe özeti"
    )
    yasal_yanit_suresi: Optional[str] = Field(
        default=None,
        description="Lookup tablosundan deterministik olarak bulunan yasal yanıt süresi."
    )
    aciliyet_durumu: AciliyetDurumu
