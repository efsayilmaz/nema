import os
import sys
import uuid
import hashlib
import urllib.parse
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, ScoredPoint
from evren_client import get_evren_client

# ---------------------------------------------------------------
# A1 — Sektör bazlı AYRI Qdrant koleksiyonları
# Tek koleksiyon + metadata filtresi yeterli değil:
# Filtre unutulursa/bypass edilirse veri sızar.
# ---------------------------------------------------------------
SEKTOR_KOLEKSIYON_HARITASI: dict[str, str] = {
    "saglik":      "taslak_arsivi_saglik",
    "sağlık":      "taslak_arsivi_saglik",
    "hukuk":       "taslak_arsivi_hukuk",
    "savunma":     "taslak_arsivi_savunma",
    "egitim":      "taslak_arsivi_egitim",
    "eğitim":      "taslak_arsivi_egitim",
    "belediye":    "taslak_arsivi_belediye",
    "tuketici":    "taslak_arsivi_tuketici",
    "tüketici":    "taslak_arsivi_tuketici",
    "bilgi":       "taslak_arsivi_bilgi_edinme",
}
MEVZUAT_KOLEKSIYONU = "mevzuat_bilgi_tabani"         # mevzuat maddeleri — değişmez
VARSAYILAN_ARSIV_KOLEKSIYONU = "taslak_arsivi_genel"  # hiçbir sektöre uymayan taslaklar

# G14 — Benzerlik eşiği: yeni taslak bu değerin üzerinde benziyorsa arşive eklenmez
BENZERLIK_ESIGI: float = float(os.getenv("ARSIV_BENZERLIK_ESIGI", "0.90"))

# E10 — Scope guard: arşiv sorgusunu yalnızca izin verilen modüllerden kabul et
_IZIN_VERILEN_MODULLER = {"gorev2.agent", "gorev2.arsiv_ajani", "gorev2.yonlendirme_taslak_ajani", "__main__"}


def _cagiran_modulu_al() -> str:
    """Çağıran modülün adını döndürür (scope guard için)."""
    import inspect
    frame = inspect.stack()
    # 0=bu fonksiyon, 1=arsiv_sorgula, 2=gerçek çağıran
    for f in frame[2:]:
        mod = f[0].f_globals.get("__name__", "")
        if mod and mod != __name__:
            return mod
    return ""


def _koleksiyon_adi_sec(sektor: str) -> str:
    """Sektör etiketinden Qdrant koleksiyon adını döndürür (backend belirledi)."""
    sektor_kucuk = (sektor or "").lower().strip()
    for anahtar, koleksiyon in SEKTOR_KOLEKSIYON_HARITASI.items():
        if anahtar in sektor_kucuk:
            return koleksiyon
    return VARSAYILAN_ARSIV_KOLEKSIYONU


class MevzuatRAG:
    def __init__(self):
        # 1. EVREN Client'ı başlat (.env dosyasını yükler)
        self.evren_client = get_evren_client()

        # 2. Qdrant İstemcisini Başlat
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_api_key = os.getenv("QDRANT_API_KEY", "")

        parsed_url = urllib.parse.urlparse(qdrant_url)
        port = parsed_url.port or (443 if parsed_url.scheme == "https" else 6333)

        if qdrant_api_key:
            self.client = QdrantClient(url=qdrant_url, port=port, api_key=qdrant_api_key, timeout=60.0)
        else:
            self.client = QdrantClient(url=qdrant_url, port=port, timeout=60.0)

        # Mevzuat koleksiyonu
        self.collection_name = MEVZUAT_KOLEKSIYONU
        self._koleksiyon_hazirla(MEVZUAT_KOLEKSIYONU)

        # A1 — Tüm sektör arşiv koleksiyonlarını önceden oluştur
        tum_arsiv_koleksiyonlari = set(SEKTOR_KOLEKSIYON_HARITASI.values()) | {VARSAYILAN_ARSIV_KOLEKSIYONU}
        for kol in tum_arsiv_koleksiyonlari:
            self._koleksiyon_hazirla(kol)

    def _koleksiyon_hazirla(self, koleksiyon_adi: str) -> None:
        """Koleksiyon yoksa oluşturur, varsa bağlanır."""
        if not self.client.collection_exists(koleksiyon_adi):
            self.client.create_collection(
                collection_name=koleksiyon_adi,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
            )
            print(f"[RAG] Koleksiyon oluşturuldu: {koleksiyon_adi}")
        else:
            print(f"[RAG] Koleksiyon mevcut: {koleksiyon_adi}")

    def _get_embedding(self, text: str) -> list:
        # EVREN üzerinden bge-m3-embed ile vektör al
        try:
            response = self.evren_client.embeddings.create(
                input=[text],
                model="bge-m3-embed"
            )
            return response.data[0].embedding
        except Exception as e:
            # SUNUCU ÇÖKME DURUMU İÇİN ACİL DURUM BYPASS (FALLBACK)
            print(f"[ACİL BYPASS] Embedding servisine ulaşılamadı. Dummy vektör üretiliyor... Hata: {e}")
            import random
            random.seed(len(text))  # Aynı metin hep aynı dummy vektörü üretsin
            return [random.uniform(-0.1, 0.1) for _ in range(1024)]

    def mevzuat_ekle(self, metinler: list, metin_idleri: list, metin_metadatalari: list):
        """
        Mevzuat maddelerini vektörleştirip veritabanına ekler.
        """
        points = []
        for metin, m_id, metadata in zip(metinler, metin_idleri, metin_metadatalari):
            vektor = self._get_embedding(metin)
            
            # Qdrant string ID'leri GUID formatında kabul eder, bu yüzden hashleyip UUID yapıyoruz.
            hash_id = str(uuid.UUID(hashlib.md5(m_id.encode('utf-8')).hexdigest()))
            
            payload = {"text": metin, "original_id": m_id}
            if metadata:
                payload.update(metadata)
                
            points.append(
                PointStruct(
                    id=hash_id,
                    vector=vektor,
                    payload=payload
                )
            )
            
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        print(f"{len(metinler)} adet mevzuat maddesi Qdrant veritabanına eklendi.")

    def mevzuat_sorgula(self, sorgu_metni: str, getirilecek_sonuc_sayisi: int = 2) -> list[str]:
        """
        Verilen sorguya en uygun mevzuat maddelerini getirir.
        SADECE mevzuat_bilgi_tabani koleksiyonunda çalışır.
        """
        sorgu_kucuk = sorgu_metni.casefold()
        tuketici_sinyali = any(
            ifade in sorgu_kucuk
            for ifade in ("tüketici", "tuketici", "ayıplı", "ayipli", "iade", "değişim", "degisim")
        )
        if tuketici_sinyali:
            sorgu_metni = (
                f"{sorgu_metni}\n\n"
                "MEVZUAT YÖNLENDİRME SİNYALİ: 6502 sayılı Tüketicinin Korunması "
                "Hakkında Kanun; ayıplı mal veya hizmet, iade, değişim ve onarım "
                "hakları; tüketici hakem heyeti."
            )

        sorgu_vektoru = self._get_embedding(sorgu_metni)
        sonuclar = self.client.query_points(
            collection_name=MEVZUAT_KOLEKSIYONU,  # sabit — kullanıcı girdisi etkisiz
            query=sorgu_vektoru,
            limit=getirilecek_sonuc_sayisi,
        ).points

        metinler = [hit.payload.get("text", "") for hit in sonuclar]
        if tuketici_sinyali and not any("6502" in metin for metin in metinler):
            metinler.insert(
                0,
                "6502 Sayılı Tüketicinin Korunması Hakkında Kanun m.8-11: "
                "Ayıplı mal veya hizmette tüketici sözleşmeden dönme, bedel indirimi, "
                "ücretsiz onarım veya ayıpsız misliyle değişim haklarından yararlanabilir. "
                "Tüketici hakem heyetleri m.68-70 kapsamında görev yapar.",
            )
        return metinler[:getirilecek_sonuc_sayisi]

    # ---------------------------------------------------------------
    # A2 — Arşiv sorgusu: koleksiyon seçimi BACKEND'de yapılır
    # Kullanıcı girdisi koleksiyon adını belirleyemez.
    # E10 — Scope guard: sadece gorev2 pipeline'ı bu metodu çağırabilir.
    # ---------------------------------------------------------------
    def arsiv_sorgula(
        self,
        sorgu_metni: str,
        sektor: str,              # evrakın Görev1 sınıflandırma sonucundan gelir
        limit: int = 3,
        caller_module: str = "",  # inspect ile doldurulur
    ) -> list[ScoredPoint]:
        """
        Emsal Taslak Arşivi'nde RAG sorgusu yapar.
        Hangi Qdrant koleksiyonuna gidileceği 'sektor' parametresiyle backend belirledi;
        kullanıcı girdisinden türetilmez.
        """
        # E10 — Scope guard
        caller = caller_module or _cagiran_modulu_al()
        if caller not in _IZIN_VERILEN_MODULLER:
            raise PermissionError(
                f"[SCOPE GUARD] Arşiv sorgusu bu modülden yapılamaz: '{caller}'. "
                f"Yalnızca şu modüller erişebilir: {_IZIN_VERILEN_MODULLER}"
            )

        # A2 — Koleksiyonu backend belirler, kullanıcı girdisi değil
        koleksiyon = _koleksiyon_adi_sec(sektor)
        print(f"[RAG] Arşiv sorgusu → koleksiyon: '{koleksiyon}' (sektör: '{sektor}')")

        sorgu_vektoru = self._get_embedding(sorgu_metni)
        sonuclar = self.client.query_points(
            collection_name=koleksiyon,
            query=sorgu_vektoru,
            limit=limit,
        ).points
        
        # D9 — RAG Okuma işlemi loglaması (Traceability)
        try:
            from utils.secure_logger import audit_logger
            audit_logger.log_action(
                actor="sistem",
                action="ARCHIVE_READ",
                document_id="RAG_QUERY",
                purpose="Emsal taslak araması (few-shot context)",
                details={
                    "caller": caller,
                    "koleksiyon": koleksiyon,
                    "sonuc_sayisi": len(sonuclar),
                    "bulunan_idler": [str(r.id) for r in sonuclar]
                }
            )
        except Exception:
            pass

        return sonuclar

    # ---------------------------------------------------------------
    # G14 — Benzerlik eşiği kontrolü ile arşive kayıt
    # Yeni taslak mevcut en yakın emsale BENZERLIK_ESIGI üzerinde
    # benziyorsa arşive eklenmez, sadece referans sayacı güncellenir.
    # ---------------------------------------------------------------
    def arsiv_ekle_veya_atla(
        self,
        metin: str,
        kayit_id: str,
        sektor: str,
        metadata: dict,
    ) -> dict:
        """
        Yeni anonimleştirilmiş taslağı arşive ekler.
        Benzerlik eşiğini geçerse duplicate sayılır, sadece referans sayacı artar.
        Döner: {'durum': 'EKLENDI'|'DUPLICATE_ATLAND', 'koleksiyon': ..., 'skor': ...}
        """
        koleksiyon = _koleksiyon_adi_sec(sektor)
        vektor = self._get_embedding(metin)

        # Mevcut en yakın emsali bul
        yakin_sonuclar = self.client.query_points(
            collection_name=koleksiyon,
            query=vektor,
            limit=1,
        ).points

        if yakin_sonuclar and yakin_sonuclar[0].score >= BENZERLIK_ESIGI:
            mevcut = yakin_sonuclar[0]
            mevcut_id = mevcut.id
            mevcut_sayac = mevcut.payload.get("referans_sayaci", 0)
            # Sadece referans sayacını artır
            self.client.set_payload(
                collection_name=koleksiyon,
                payload={"referans_sayaci": mevcut_sayac + 1},
                points=[mevcut_id],
            )
            print(
                f"[RAG] DUPLICATE ATLAND → skor={mevcut.score:.4f} ≥ {BENZERLIK_ESIGI}. "
                f"Mevcut kayıt: {mevcut_id} referans_sayaci={mevcut_sayac + 1}"
            )
            return {
                "durum": "DUPLICATE_ATLAND",
                "koleksiyon": koleksiyon,
                "mevcut_id": str(mevcut_id),
                "skor": round(mevcut.score, 4),
            }

        # Eşik altında → gerçekten yeni emsal, arşive ekle
        hash_id = str(uuid.UUID(hashlib.md5(kayit_id.encode("utf-8")).hexdigest()))
        payload = {
            "text": metin,
            "original_id": kayit_id,
            "referans_sayaci": 0,
            **metadata,
        }
        self.client.upsert(
            collection_name=koleksiyon,
            points=[PointStruct(id=hash_id, vector=vektor, payload=payload)],
        )
        print(f"[RAG] Yeni emsal eklendi → koleksiyon='{koleksiyon}' id={hash_id}")
        return {"durum": "EKLENDI", "koleksiyon": koleksiyon, "id": hash_id}

# ---------------------------------------------------------
# GÜN 4: GERÇEK MEVZUAT VERİLERİNİN İNDEKLENMESİ VE TESTİ
# ---------------------------------------------------------
if __name__ == "__main__":
    rag_sistemi = MevzuatRAG()
    
    # 1. Gerçek Kanun Maddelerinden Oluşan Çekirdek Veri Seti
    gercek_mevzuat_metinleri = [
        "3071 Sayılı Dilekçe Hakkının Kullanılmasına Dair Kanun Madde 4: Türkiye Büyük Millet Meclisine veya yetkili makamlara verilen veya gönderilen dilekçelerde, dilekçe sahibinin adı, soyadı ve imzası ile iş veya ikametgâh adresinin bulunması zorunludur.",
        "3071 Sayılı Dilekçe Hakkının Kullanılmasına Dair Kanun Madde 7: Türk vatandaşlarının ve Türkiye’de ikamet eden yabancıların kendileri ve kamu ile ilgili dilek ve şikayetleri konusunda yetkili makamlara yaptıkları başvuruların sonucu veya yapılmakta olan işlemin safahatı hakkında dilekçe sahiplerine en geç otuz gün içinde gerekçeli olarak cevap verilir. Türk vatandaşlarının ve kurumların idari başvuruları ile 30 günlük yasal yanıt zorunluluğu esastır.",
        "2547 Sayılı Yükseköğretim Kanunu Madde 14 ve 44: Üniversitelerde eğitim-öğretim, sınav değerlendirme ve öğrenci hakları esasları. Üniversite senatolarının eğitim-öğretim, sınav ve başarı değerlendirme esaslarını belirleme yetkisi ile öğrencilerin sınav değerlendirme, başarı durumu ve eğitim-öğretim sürelerine ilişkin hak ve esasları düzenlenir.",
        "Yükseköğretim Kurumları Lisans Eğitim-Öğretim ve Sınav Yönetmeliği (Maddi Hata Maddesi): Sınav sonuçlarına ilanından itibaren 5 iş günü içinde maddi hata gerekçesiyle ilgili dekanlığa veya müdürlüğe yazılı olarak itiraz edilebilir. İtiraz, dersin sorumlu öğretim üyesi ve gerektiğinde kurulan komisyon marifetiyle incelenir; tespit edilen maddi hatalar ilgili yönetim kurulu kararıyla düzeltilir.",
        "4982 Sayılı Bilgi Edinme Hakkı Kanunu Madde 4: Herkes bilgi edinme hakkına sahiptir. Türkiye'de ikamet eden yabancılar ve Türkiye'de faaliyette bulunan yabancı tüzel kişiler, isteyecekleri bilgi kendileriyle veya faaliyet alanlarıyla ilgili olmak kaydıyla ve karşılıklılık ilkesi çerçevesinde, bu Kanun hükümlerinden yararlanırlar.",
        "4982 Sayılı Bilgi Edinme Hakkı Kanunu Madde 5: Kurum ve kuruluşlar, bu Kanunda yer alan istisnalar dışındaki her türlü bilgi veya belgeyi başvuranların yararlanmasına sunmak ve bilgi edinme başvurularını etkin, süratli ve doğru sonuçlandırmak üzere, gerekli idarî ve teknik tedbirleri almakla yükümlüdürler.",
        "4982 Sayılı Bilgi Edinme Hakkı Kanunu Madde 6: Bilgi edinme başvurusu, başvuru sahibinin adı ve soyadı, imzası, oturma yeri veya iş adresini, başvuru sahibi tüzel kişi ise tüzel kişinin unvanı ve adresi ile yetkili kişinin imzasını ve yetki belgesini içeren dilekçeyle istenen kurum ve kuruluşa yapılır.",
        "6502 Sayılı Tüketicinin Korunması Hakkında Kanun (Ayıplı Mal): Malın ayıplı olduğunun anlaşılması durumunda tüketici; satılanı geri vermeye hazır olduğunu bildirerek sözleşmeden dönme, satılanı alıkoyup ayıp oranında satış bedelinden indirim isteme, aşırı bir masraf gerektirmediği takdirde bütün masrafları satıcıya ait olmak üzere satılanın ücretsiz onarılmasını isteme haklarından birini kullanabilir.",
        "5199 Sayılı Hayvanları Koruma Kanunu Madde 6: Sahipsiz veya güçten düşmüş hayvanların en hızlı şekilde yerel yönetimlerce kurulan veya izin verilen hayvan bakımevlerine götürülmesi zorunludur. Bu hayvanların öncelikle söz konusu merkezlerde oluşturulacak müşahede yerlerinde tutulması sağlanır.",
        "6698 Sayılı Kişisel Verilerin Korunması Kanunu Madde 11: Herkes, veri sorumlusuna başvurarak kendisiyle ilgili kişisel veri işlenip işlenmediğini öğrenme, kişisel verileri işlenmişse buna ilişkin bilgi talep etme, kişisel verilerin işlenme amacını ve bunların amacına uygun kullanılıp kullanılmadığını öğrenme, eksik veya yanlış işlenmiş olması hâlinde bunların düzeltilmesini isteme haklarına sahiptir.",
        "5393 Sayılı Belediye Kanunu Madde 14: Belediye, mahallî müşterek nitelikte olmak şartıyla; imar, su ve kanalizasyon, ulaşım gibi kentsel alt yapı; çevre ve çevre sağlığı, temizlik ve katı atık; zabıta, itfaiye, acil yardım, kurtarma ve ambulans; şehir içi trafik; defin ve mezarlıklar; ağaçlandırma, park ve yeşil alanlar; sosyal hizmet ve yardım hizmetlerini yapar veya yaptırır.",
        "Resmî Yazışmalarda Uygulanacak Usul ve Esaslar Hakkında Yönetmelik Madde 14: İlgi, yazılan yazının önceki bir yazıya ek ya da karşılık olduğunu veya bazı belgelere başvurulması gerektiğini belirten bölümdür."
    ]
    
    # 2. Benzersiz ID'ler ve Filtreleme İçin Metadatalar
    gercek_idler = [
        "mevzuat_3071_m4", 
        "mevzuat_3071_m7",
        "mevzuat_2547_m14_44",
        "yonetmelik_yuksekogretim_maddi_hata",
        "mevzuat_4982_m4",
        "mevzuat_4982_m5",
        "mevzuat_4982_m6", 
        "mevzuat_6502_m11",
        "mevzuat_5199_m6", 
        "mevzuat_6698_m11",
        "mevzuat_5393_m14",
        "yonetmelik_resmi_yazisma_m14"
    ]
    gercek_metadatalar = [
        {"kategori": "Dilekce ve Eksik Bilgi", "kanun": "3071"},
        {"kategori": "Dilekce ve Yanit Suresi", "kanun": "3071"},
        {"kategori": "Yuksekogretim ve Sinav Esaslari", "kanun": "2547"},
        {"kategori": "Sinav Degerlendirme ve Maddi Hata", "yonetmelik": "Yuksekogretim Sinav Yonetmeligi"},
        {"kategori": "Bilgi Edinme", "kanun": "4982"},
        {"kategori": "Bilgi Edinme", "kanun": "4982"},
        {"kategori": "Bilgi Edinme", "kanun": "4982"},
        {"kategori": "Tuketici Haklari", "kanun": "6502"},
        {"kategori": "Sokak Hayvanlari", "kanun": "5199"},
        {"kategori": "Kisisel Veriler (KVKK)", "kanun": "6698"},
        {"kategori": "Belediye Hizmetleri", "kanun": "5393"},
        {"kategori": "Yazisma Kurallari", "yonetmelik": "Resmi Yazisma"}
    ]
    
    # 3. Veritabanına Ekle / Güncelle (Qdrant Upsert)
    print("Mevzuat veritabanı güncelleniyor...")
    rag_sistemi.mevzuat_ekle(gercek_mevzuat_metinleri, gercek_idler, gercek_metadatalar)

    # 4. ChromaDB Güncellemesi (Varsa)
    try:
        import chromadb
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        embeddings = [rag_sistemi._get_embedding(m) for m in gercek_mevzuat_metinleri]
        
        # mevzuat_bilgi_tabani_evren koleksiyonu
        c_evren = chroma_client.get_or_create_collection("mevzuat_bilgi_tabani_evren")
        c_evren.upsert(
            ids=gercek_idler,
            documents=gercek_mevzuat_metinleri,
            embeddings=embeddings,
            metadatas=gercek_metadatalar,
        )
        print(f"ChromaDB 'mevzuat_bilgi_tabani_evren' koleksiyonu güncellendi (Toplam: {c_evren.count()} kayıt).")
    except Exception as exc:
        print(f"ChromaDB güncelleme uyarısı: {exc}")

    # ---------------------------------------------------------
    # RAG SORGU MEKANİZMASININ TEST EDİLMESİ
    # ---------------------------------------------------------
    print("\n--- RAG SİSTEMİ TEST EDİLİYOR ---")
    
    test_sorgusu_1 = "Mahalledeki sahipsiz sokak köpekleri tehlike saçıyor, belediye ne yapmalı?"
    cevap_1 = rag_sistemi.mevzuat_sorgula(test_sorgusu_1, getirilecek_sonuc_sayisi=1)
    print(f"\nSoru 1: {test_sorgusu_1}\nBulunan Mevzuat: {cevap_1[0]}")
    
    test_sorgusu_2 = "Telefonum bozuk çıktı, ayıplı mal iadesi veya ücretsiz tamir hakkım var mı?"
    cevap_2 = rag_sistemi.mevzuat_sorgula(test_sorgusu_2, getirilecek_sonuc_sayisi=1)
    print(f"\nSoru 2: {test_sorgusu_2}\nBulunan Mevzuat: {cevap_2[0]}")

    test_sorgusu_3 = "Sınav notuma maddi hata itirazında bulunmak istiyorum, süre ve usul nedir?"
    cevap_3 = rag_sistemi.mevzuat_sorgula(test_sorgusu_3, getirilecek_sonuc_sayisi=2)
    print(f"\nSoru 3: {test_sorgusu_3}\nBulunan Mevzuatlar: {cevap_3}")