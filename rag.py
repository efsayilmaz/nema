import chromadb
from chromadb.utils import embedding_functions

class MevzuatRAG:
    def __init__(self, db_yolu="./chroma_db"):
        # 1. ChromaDB İstemcisini Başlat (Veriler yerel diskte saklanacak)
        self.client = chromadb.PersistentClient(path=db_yolu)
        
        # 2. Embedding Modelini Belirle (Türkçe performansı yüksek model)
        self.embedding_fonksiyonu = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-m3"
        )
        
        # 3. Koleksiyonu (Tabloyu) Oluştur veya Bağlan
        self.koleksiyon = self.client.get_or_create_collection(
            name="mevzuat_bilgi_tabani",
            embedding_function=self.embedding_fonksiyonu
        )

    def mevzuat_ekle(self, metinler: list, metin_idleri: list, metin_metadatalari: list):
        """
        Mevzuat maddelerini vektörleştirip veritabanına ekler.
        """
        self.koleksiyon.add(
            documents=metinler,
            ids=metin_idleri,
            metadatas=metin_metadatalari
        )
        print(f"{len(metinler)} adet mevzuat maddesi veritabanına eklendi.")

    def mevzuat_sorgula(self, sorgu_metni: str, getirilecek_sonuc_sayisi: int = 2):
        """
        Verilen sorguya en uygun mevzuat maddelerini getirir.
        """
        sonuclar = self.koleksiyon.query(
            query_texts=[sorgu_metni],
            n_results=getirilecek_sonuc_sayisi
        )
        return sonuclar["documents"][0]

# ---------------------------------------------------------
# GÜN 4: GERÇEK MEVZUAT VERİLERİNİN İNDEKLENMESİ VE TESTİ
# ---------------------------------------------------------
if __name__ == "__main__":
    rag_sistemi = MevzuatRAG()
    
    # 1. Gerçek Kanun Maddelerinden Oluşan Çekirdek Veri Seti
    gercek_mevzuat_metinleri = [
        "3071 Sayılı Dilekçe Hakkının Kullanılmasına Dair Kanun Madde 4: Türkiye Büyük Millet Meclisine veya yetkili makamlara verilen veya gönderilen dilekçelerde, dilekçe sahibinin adı, soyadı ve imzası ile iş veya ikametgâh adresinin bulunması zorunludur.",
        "4982 Sayılı Bilgi Edinme Hakkı Kanunu Madde 6: Bilgi edinme başvurusu, başvuru sahibinin adı ve soyadı, imzası, oturma yeri veya iş adresini, başvuru sahibi tüzel kişi ise tüzel kişinin unvanı ve adresi ile yetkili kişinin imzasını ve yetki belgesini içeren dilekçeyle istenen kurum ve kuruluşa yapılır.",
        "5199 Sayılı Hayvanları Koruma Kanunu Madde 6: Sahipsiz veya güçten düşmüş hayvanların en hızlı şekilde yerel yönetimlerce kurulan veya izin verilen hayvan bakımevlerine götürülmesi zorunludur. Bu hayvanların öncelikle söz konusu merkezlerde oluşturulacak müşahede yerlerinde tutulması sağlanır.",
        "6502 Sayılı Tüketicinin Korunması Hakkında Kanun Madde 11: Malın ayıplı olduğunun anlaşılması durumunda tüketici; satılanı geri vermeye hazır olduğunu bildirerek sözleşmeden dönme, satılanı alıkoyup ayıp oranında satış bedelinden indirim isteme, aşırı bir masraf gerektirmediği takdirde bütün masrafları satıcıya ait olmak üzere satılanın ücretsiz onarılmasını isteme haklarından birini kullanabilir.",
        "Resmî Yazışmalarda Uygulanacak Usul ve Esaslar Hakkında Yönetmelik Madde 14: İlgi, yazılan yazının önceki bir yazıya ek ya da karşılık olduğunu veya bazı belgelere başvurulması gerektiğini belirten bölümdür. İlgi yan başlığı, muhatap bölümünün son satırından itibaren iki satır boşluk bırakılarak ve yazı alanının sol sınırından başlanarak yazılır."
    ]
    
    # 2. Benzersiz ID'ler ve Filtreleme İçin Metadatalar
    gercek_idler = [
        "mevzuat_3071_m4", 
        "mevzuat_4982_m6", 
        "mevzuat_5199_m6", 
        "mevzuat_6502_m11", 
        "yonetmelik_resmi_yazisma_m14"
    ]
    gercek_metadatalar = [
        {"kategori": "Dilekce ve Eksik Bilgi", "kanun": "3071"},
        {"kategori": "Bilgi Edinme", "kanun": "4982"},
        {"kategori": "Sokak Hayvanlari", "kanun": "5199"},
        {"kategori": "Tuketici Haklari", "kanun": "6502"},
        {"kategori": "Yazisma Kurallari", "yonetmelik": "Resmi Yazisma"}
    ]
    
    # Veritabanında bu ID'ler yoksa ekle (Hata almamak için basit bir kontrol)
    mevcut_idler = rag_sistemi.koleksiyon.get()["ids"]
    eklenecek_metinler = []
    eklenecek_idler = []
    eklenecek_metadatalar = []
    
    for i in range(len(gercek_idler)):
        if gercek_idler[i] not in mevcut_idler:
            eklenecek_metinler.append(gercek_mevzuat_metinleri[i])
            eklenecek_idler.append(gercek_idler[i])
            eklenecek_metadatalar.append(gercek_metadatalar[i])
            
    if eklenecek_metinler:
        rag_sistemi.mevzuat_ekle(eklenecek_metinler, eklenecek_idler, eklenecek_metadatalar)
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