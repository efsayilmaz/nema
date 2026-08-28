"""
rbac.py — Rol Bazlı Erişim Kontrolü (D9)
=========================================
Desteklenen roller ve izinleri:

  agent          → ARCHIVE_READ, ARCHIVE_WRITE
  icerik_uzmani  → ARCHIVE_READ, CONTENT_APPROVE
  kvkk_sorumlusu → ARCHIVE_READ, KVKK_APPROVE
  yonetici       → ARCHIVE_READ, ARCHIVE_WRITE, ARCHIVE_DELETE, LOG_READ, CONTENT_APPROVE, KVKK_APPROVE
  auditor        → ARCHIVE_READ (salt-okunur), LOG_READ
  vatandas       → DELETION_REQUEST (sadece silme talebi oluşturabilir)

Header: X-Rol: <rol_adi>
"""

import os
from fastapi import Header, HTTPException, status
from enum import Enum


class Izin(str, Enum):
    ARCHIVE_READ     = "ARCHIVE_READ"
    ARCHIVE_WRITE    = "ARCHIVE_WRITE"
    ARCHIVE_DELETE   = "ARCHIVE_DELETE"
    LOG_READ         = "LOG_READ"
    CONTENT_APPROVE  = "CONTENT_APPROVE"
    KVKK_APPROVE     = "KVKK_APPROVE"
    DELETION_REQUEST = "DELETION_REQUEST"


# İzin Matrisi (D9)
ROL_IZIN_MATRISI: dict[str, set[Izin]] = {
    "agent": {
        Izin.ARCHIVE_READ,
        Izin.ARCHIVE_WRITE,
    },
    "icerik_uzmani": {
        Izin.ARCHIVE_READ,
        Izin.CONTENT_APPROVE,
    },
    "kvkk_sorumlusu": {
        Izin.ARCHIVE_READ,
        Izin.KVKK_APPROVE,
    },
    "yonetici": {
        Izin.ARCHIVE_READ,
        Izin.ARCHIVE_WRITE,
        Izin.ARCHIVE_DELETE,
        Izin.LOG_READ,
        Izin.CONTENT_APPROVE,
        Izin.KVKK_APPROVE,
    },
    "auditor": {
        Izin.ARCHIVE_READ,   # salt-okunur
        Izin.LOG_READ,
    },
    "vatandas": {
        Izin.DELETION_REQUEST,
    },
}


def _rol_dogrula(x_rol: str) -> str:
    """X-Rol header değerini temizler ve doğrular."""
    rol = (x_rol or "").strip().lower()
    if rol not in ROL_IZIN_MATRISI:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Geçersiz rol: '{x_rol}'. Geçerli roller: {list(ROL_IZIN_MATRISI.keys())}",
        )
    return rol


def izin_gerektir(*gerekli_izinler: Izin):
    """
    FastAPI Dependency factory.
    Kullanım:
        @app.delete("/arsiv/{id}", dependencies=[Depends(izin_gerektir(Izin.ARCHIVE_DELETE))])
    """
    def dep(x_rol: str = Header(default="yonetici", description="Kullanıcı rolü (örn: yonetici, auditor)")):
        rol = _rol_dogrula(x_rol)
        sahip_olunan = ROL_IZIN_MATRISI[rol]
        eksik = [i.value for i in gerekli_izinler if i not in sahip_olunan]
        if eksik:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"'{rol}' rolünün bu işlem için yetki(leri) eksik: {eksik}. "
                    f"Sahip olunan izinler: {[i.value for i in sahip_olunan]}"
                ),
            )
        return rol
    return dep


def rol_al(x_rol: str = Header(default="agent", description="Kullanıcı rolü")) -> str:
    """Header'dan rolü al, doğrula ve döndür (izin kontrolü yok, sadece kimlik)."""
    return _rol_dogrula(x_rol)
