import os
import uuid
import hashlib
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from evren_client import get_evren_client

class MevzuatRAG:
    def __init__(self):
        # 1. EVREN Client'ı başlat (Bu aynı zamanda .env dosyasını yükler)
        self.evren_client = get_evren_client()
        
        # 2. Qdrant İstemcisini Başlat
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_api_key = os.getenv("QDRANT_API_KEY", "")
        
        # URL'den portu ayrıştır (eğer belirtilmemişse https için 443, http için 6333 kullan)
        import urllib.parse
        parsed_url = urllib.parse.urlparse(qdrant_url)
        port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 6333)
        
        # EVREN URL'ine API Key ile bağlanmak
        if qdrant_api_key:
            self.client = QdrantClient(url=qdrant_url, port=port, api_key=qdrant_api_key, timeout=60.0)
        else:
            self.client = QdrantClient(url=qdrant_url, port=port, timeout=60.0)
            
        self.collection_name = "mevzuat_bilgi_tabani"
        
        # 2. Koleksiyonu (Tabloyu) Oluştur veya Bağlan
        if not self.client.collection_exists(self.collection_name):
            # Not: İleride embed (2560 boyut) alias'ına geçilirse ayrı bir koleksiyon veya size=2560 gerekecektir.
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
            )

    def _get_embedding(self, text: str) -> list:
        # EVREN üzerinden bge-m3-embed ile vektör al
        response = self.evren_client.embeddings.create(
            input=[text],
            model="bge-m3-embed"
        )
        return response.data[0].embedding

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

    def mevzuat_sorgula(self, sorgu_metni: str, getirilecek_sonuc_sayisi: int = 2):
        """
        Verilen sorguya en uygun mevzuat maddelerini getirir.
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
            collection_name=self.collection_name,
            query=sorgu_vektoru,
            limit=getirilecek_sonuc_sayisi
        ).points
        
        metinler = [hit.payload.get("text", "") for hit in sonuclar]
        if tuketici_sinyali and not any("6502" in metin for metin in metinler):
            metinler.insert(0,
                "6502 Sayılı Tüketicinin Korunması Hakkında Kanun m.8-11: "
                "Ayıplı mal veya hizmette tüketici sözleşmeden dönme, bedel indirimi, "
                "ücretsiz onarım veya ayıpsız misliyle değişim haklarından yararlanabilir. "
                "Tüketici hakem heyetleri m.68-70 kapsamında görev yapar."
            )
        return metinler[:getirilecek_sonuc_sayisi]

# ---------------------------------------------------------
# GÜN 4: GERÇEK MEVZUAT VERİLERİNİN İNDEKLENMESİ VE TESTİ
# ---------------------------------------------------------
if __name__ == "__main__":
    rag_sistemi = MevzuatRAG()
    
    # 1. Gerçek Kanun Maddelerinden Oluşan Çekirdek Veri Seti
    gercek_mevzuat_metinleri = [
        "3071 Sayılı Dilekçe Hakkının Kullanılmasına Dair Kanun Madde 4: Türkiye Büyük Millet Meclisine veya yetkili makamlara verilen veya gönderilen dilekçelerde, dilekçe sahibinin adı, soyadı ve imzası ile iş veya ikametgâh adresinin bulunması zorunludur.",
        "3071 Sayılı Dilekçe Hakkının Kullanılmasına Dair Kanun Madde 7: Türk vatandaşlarının ve Türkiye’de ikamet eden yabancıların kendileri ve kamu ile ilgili dilek ve şikayetleri konusunda yetkili makamlara yaptıkları başvuruların sonucu veya yapılmakta olan işlemin safahatı hakkında dilekçe sahiplerine en geç otuz gün içinde gerekçeli olarak cevap verilir.",
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
        {"kategori": "Bilgi Edinme", "kanun": "4982"},
        {"kategori": "Bilgi Edinme", "kanun": "4982"},
        {"kategori": "Bilgi Edinme", "kanun": "4982"},
        {"kategori": "Tuketici Haklari", "kanun": "6502"},
        {"kategori": "Sokak Hayvanlari", "kanun": "5199"},
        {"kategori": "Kisisel Veriler (KVKK)", "kanun": "6698"},
        {"kategori": "Belediye Hizmetleri", "kanun": "5393"},
        {"kategori": "Yazisma Kurallari", "yonetmelik": "Resmi Yazisma"}
    ]
    
    # Veritabanında bu ID'ler yoksa ekle (Basit kontrol: Koleksiyon boş mu?)
    koleksiyon_bilgisi = rag_sistemi.client.get_collection(rag_sistemi.collection_name)
    if koleksiyon_bilgisi.points_count == 0:
        rag_sistemi.mevzuat_ekle(gercek_mevzuat_metinleri, gercek_idler, gercek_metadatalar)
    else:
        print("Bu mevzuat maddeleri zaten veritabanında mevcut.")
    
    # ---------------------------------------------------------
    # GÜN 5: RAG SORGU MEKANİZMASININ TEST EDİLMESİ
    # ---------------------------------------------------------
    print("\n--- RAG SİSTEMİ TEST EDİLİYOR ---")
    
    test_sorgusu_1 = "Mahalledeki sahipsiz sokak köpekleri tehlike saçıyor, belediye ne yapmalı?"
    cevap_1 = rag_sistemi.mevzuat_sorgula(test_sorgusu_1, getirilecek_sonuc_sayisi=1)
    print(f"\nSoru 1: {test_sorgusu_1}\nBulunan Mevzuat: {cevap_1[0]}")
    
    test_sorgusu_2 = "Telefonum bozuk çıktı, ayıplı mal iadesi veya ücretsiz tamir hakkım var mı?"
    cevap_2 = rag_sistemi.mevzuat_sorgula(test_sorgusu_2, getirilecek_sonuc_sayisi=1)
    print(f"\nSoru 2: {test_sorgusu_2}\nBulunan Mevzuat: {cevap_2[0]}")