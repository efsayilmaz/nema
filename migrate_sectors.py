import sys; sys.path.insert(0, '.')
import json
from teknofest_agent_app.utils.arsiv_db import arsiv_verilerini_getir, _arsiv_kaydet
from rag import MevzuatRAG
from teknofest_agent_app.utils.secure_logger import audit_logger

rag = MevzuatRAG()
kayitlar = arsiv_verilerini_getir()

# Qdrant'tan onceki hatali koleksiyondaki verileri silecegiz. UUID'leri lazim olacak.
# O yuzden arsiv_ekle_veya_atla ile yeni sektore gonderecegiz ama eskisini de silelim.

# Manuel inceleme kuyrugu dosyasi
INCELEME_DOSYASI = "teknofest_agent_app/logs/manuel_inceleme_kuyrugu.jsonl"
def kuyruga_ekle(kayit):
    import os
    os.makedirs(os.path.dirname(INCELEME_DOSYASI), exist_ok=True)
    with open(INCELEME_DOSYASI, "a", encoding="utf-8") as f:
        # Kuyruk nesnesi semasi: document_id, content, type="legacy_arsiv_onayi", status="bekliyor"
        item = {
            "document_id": kayit["id"],
            "type": "legacy_arsiv_onayi",
            "content": kayit,
            "status": "bekliyor"
        }
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

sayac = 0
for k in kayitlar:
    eski_sektor = k.get("sektor", "genel")
    if isinstance(eski_sektor, dict): eski_sektor = "genel"
    yeni_sektor = eski_sektor
    
    # Basit bir kelime analizi ile sektor bulalim
    metin = (k.get("anonim_metin") or "").lower()
    if "oksijen" in metin or "hasta" in metin or "sağlık" in metin:
        yeni_sektor = "sağlık"
    elif "park" in metin or "salıncak" in metin or "çukur" in metin or "belediye" in metin:
        yeni_sektor = "belediye"
    elif "okul" in metin or "öğrenci" in metin or "çatı" in metin:
        yeni_sektor = "eğitim"
        
    print(f"[{k['id']}] Eski Sektor: {eski_sektor} -> Yeni Sektor: {yeni_sektor}")
    
    if yeni_sektor != eski_sektor or k.get("_legacy_otomat_onayi"):
        k["sektor"] = yeni_sektor
        
        # Legacy ise kuyruga ekle
        if k.get("_legacy_otomat_onayi"):
            kuyruga_ekle(k)
            print(f"  -> Legacy kayit inceleme kuyruguna alindi.")
        
        # Qdrant: Eski kaydi "taslak_arsivi_genel" veya eski sektor koleksiyonundan sil (Eger hash_id ayni kalirsa aslinda ayni id ile overwrite edemez cunku baska koleksiyonda).
        # UUID nasil uretiliyordu: hash_id = str(uuid.UUID(hashlib.md5(metin.encode("utf-8")).hexdigest()))
        import uuid, hashlib
        hash_id = str(uuid.UUID(hashlib.md5(metin.encode("utf-8")).hexdigest()))
        
        from rag import _koleksiyon_adi_sec
        eski_kol = _koleksiyon_adi_sec(eski_sektor)
        yeni_kol = _koleksiyon_adi_sec(yeni_sektor)
        
        if eski_kol != yeni_kol:
            try:
                rag.client.delete(collection_name=eski_kol, points_selector=[hash_id])
                print(f"  -> Qdrant: {eski_kol} icinden {hash_id} silindi.")
            except Exception as e:
                pass
                
        # Qdrant'a yeni sektorde ekle
        rag.arsiv_ekle_veya_atla(metin, k["id"], yeni_sektor, k)
        sayac += 1

if sayac > 0:
    _arsiv_kaydet(kayitlar)
    print(f"Migration tamamlandi. {sayac} kayit guncellendi ve tasindi.")
else:
    print("Guncellenecek kayit bulunamadi.")
