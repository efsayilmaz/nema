"""
Bu dosyadaki örnekler, arkadaşlarının hazırladığı Görev 1 / Görev 2 çıktı
örnekleriyle (gorev1.txt, gorev2.txt, string.txt) BİREBİR eşleşen, gerçek
girdi-çıktı üçlüleridir. Demo modunda bu metinlerden biri seçilirse, mock
katmanı arkadaşlarının verdiği GERÇEK örnek çıktıyı döndürür — böylece
arayüz, backend gelmeden önce bile gerçekçi ve şemaya %100 uygun bir demo
sunabilir.

Şema kaynağı: gorev1.txt ve gorev2.txt (ekip tarafından hazırlanan veri seti).
"""

SAMPLE_DOCS = [
    {
        "baslik": "Örnek 1 — CİMER: Başıboş sokak köpekleri şikayeti",
        "metin": (
            "CİMER BAŞVURU METNİ (Sokak Hayvanları Şikayeti)\n\n"
            "merhaba ben bu şikayeti mahallemizdeki başıboş köpekler için yazıyorum yaklaşık 2 aydır "
            "Yeşiltepe Mahallesi Gül Sokak civarında 8-10 tane köpek var geceleri sürekl havlıyorlar "
            "çocuklar korkuyor okula giderken bazı veliler yol değiştiriyor belediyeyi defalarca aradık "
            "\"kayıt aldık ekip gönderilecek\" diyorlar ama kimse gelmiyo!! bu köpekler kısırlaştırılmamış "
            "her ay yavrulıyorlar sayı gittikçe artıyo. geçen hafta komşumun kızını ısırdı neredeyse, "
            "hastaneye gittiler tedavi oldu. Hayvanları Koruma Kanunu falan var biliyorum ama uygulanmıyor "
            "sanki. ben vergi mükellefiyim bu ülkede güvenliğimizi istiyorum sadece. lütfen ilgili birim "
            "bir an önce müdahale etsin, köpekler barınağa alınsın veya kısırlaştırılıp mahalleye geri "
            "bırakılsın (kanunda öyle yazıyo galiba). Bu işi ciddiye alın artık, sadece formalite icabı "
            "cevap yazıp kapatmayın dosyayı. Teşekkürler."
        ),
        "gorev1": {
            "evrak_turu": "Şikayet / İhbar",
            "konu": "Başıboş Sokak Köpekleri Şikayeti",
            "evrak_tarihi": None,
            "sayi_veya_kayit_no": None,
            "gonderen": {
                "gonderen_tipi": "Gerçek Kişi",
                "ad_soyad_veya_unvan": None,
                "kimlik_veya_vergi_no": None,
                "iletisim_bilgisi": None,
            },
            "kisa_ozet": (
                "Yeşiltepe Mahallesi Gül Sokak civarında sayıları artan başıboş köpeklerin çevreye "
                "tehlike saçtığı, bir çocuğu ısırdığı ve belediyenin şikayetlere rağmen müdahale "
                "etmediği belirtilerek, hayvanların barınağa alınması veya kısırlaştırılması "
                "talep edilmektedir."
            ),
            "varliklar": {
                "kurumlar": ["Belediye"],
                "lokasyonlar": ["Yeşiltepe Mahallesi", "Gül Sokak"],
                "tarihler": ["Son 2 ay", "Geçen hafta"],
            },
            "ilgili_mevzuat_onerisi": [
                "5199 Sayılı Hayvanları Koruma Kanunu",
                "5393 Sayılı Belediye Kanunu",
            ],
            "eksik_bilgiler": [
                "Evrak Tarihi",
                "Başvuru Sahibinin Adı ve Soyadı",
                "T.C. Kimlik Numarası",
                "İletişim Bilgisi (Telefon/E-posta)",
            ],
            "aciliyet_durumu": "İvedi",
        },
        "gorev2": {
            "yonlendirme_karari": {
                "islem_yapacak_ana_kurum": "İlgili İlçe/Büyükşehir Belediye Başkanlığı",
                "geregi_icin_yonlendirilecek_birim": "Veteriner İşleri Müdürlüğü",
                "bilgi_icin_iletilecek_birimler": [
                    "Zabıta Müdürlüğü",
                    "Halkla İlişkiler Şube Müdürlüğü",
                ],
                "yonlendirme_gerekcesi": (
                    "Bölgedeki sahipsiz köpeklerin saldırgan tavırları, çocuklara yönelik bir ısırma "
                    "vakasının yaşanması ve halk sağlığı/güvenliği riski taşıması nedeniyle 5199 sayılı "
                    "kanun kapsamında ivedi müdahale gerekliliği."
                ),
            },
            "resmi_yazi_taslagi": {
                "yazi_turu": "Eksik Bilge/Belge Talebi",
                "konu": "Başıboş Sokak Köpekleri Şikayeti Hk.",
                "ilgi": "Tarihsiz, isimsiz ve imzasız başvuru.",
                "govde_metni": (
                    "İlgide kayıtlı başvurunuz incelenmiştir. Yeşiltepe Mahallesi Gül Sokak'taki başıboş "
                    "köpeklerle ilgili şikayetinizdeki 'ısırma vakası' beyanı nedeniyle durumun aciliyeti "
                    "göz önünde bulundurularak Veteriner İşleri Müdürlüğü'ne ön bilgilendirme yapılmıştır. "
                    "Ancak, 3071 sayılı Dilekçe Hakkının Kullanılmasına Dair Kanun gereğince ad, soyad, "
                    "T.C. Kimlik Numarası ve iletişim bilgilerinizin eksik olduğu tespit edilmiştir. "
                    "İşlemlerinizin resmiyet kazanabilmesi ve size geri dönüş sağlanabilmesi için bu "
                    "bilgileri tamamlamanız rica olunur."
                ),
                "imza_makami": "Birim Amiri",
            },
            "kullanici_bilgilendirme": {
                "kullaniciya_gosterilecek_mesaj": (
                    "Şikayetiniz sistemimize ulaşmış olup, 'ısırma vakası' beyanı nedeniyle acil "
                    "koduyla ilgili Veteriner İşleri birimine ön bildirim yapılmıştır. Sürecin resmi "
                    "olarak başlatılabilmesi için lütfen eksik olan T.C. Kimlik No, Ad-Soyad ve iletişim "
                    "bilgilerinizi güncelleyiniz."
                ),
                "sistem_aksiyon_durumu": "Kullanıcı Bekleniyor",
            },
        },
    },
    {
        "baslik": "Örnek 2 — Dilekçe: Ara sınav notuna itiraz",
        "metin": (
            "ATATÜRK ÜNİVERSİTESİ\nFEN FAKÜLTESİ DEKANLIĞI'NA\n\n"
            "Konu: Ara sınav notuna itiraz hk.\n\n"
            "Dekanlığınıza bağlı Fizik Bölümü, 2. sınıf öğrencisiyim. 2025-2026 Eğitim-Öğretim Yılı "
            "Güz Yarıyılı \"Klasik Mekanik\" dersi vize sınavından almış olduğum 42 (kırk iki) puanlık "
            "notun, sınav kağıdımdaki çözümlerle uyuşmadığını düşünmekteyim. Özellikle 3. ve 5. "
            "sorularda uyguladığım çözüm yöntemlerinin ders notlarında verilen yöntemle örtüştüğü "
            "halde puanlama yapılmadığını fark ettim. Atatürk Üniversitesi Önlisans ve Lisans "
            "Eğitim-Öğretim Yönetmeliği'nin ilgili maddeleri uyarınca sınav evrakımın yeniden "
            "incelenmesini (maddi hata incelemesi) ve sonucun tarafıma bildirilmesini saygılarımla "
            "arz ederim.\n\n"
            "Ad Soyad: Emre KARADAĞ\nÖğrenci No: 2023134028\nT.C. Kimlik No: 27584916302\n"
            "Tarih: 14.11.2025\n\nİmza: [imzalı]"
        ),
        "gorev1": {
            "evrak_turu": "Dilekçe",
            "konu": "Ara sınav notuna itiraz hk.",
            "evrak_tarihi": "14.11.2025",
            "sayi_veya_kayit_no": None,
            "gonderen": {
                "gonderen_tipi": "Gerçek Kişi",
                "ad_soyad_veya_unvan": "Emre KARADAĞ",
                "kimlik_veya_vergi_no": "27584916302",
                "iletisim_bilgisi": None,
            },
            "kisa_ozet": (
                "Fizik Bölümü 2. sınıf öğrencisi, Klasik Mekanik dersi vize sınavından aldığı 42 "
                "puana, özellikle 3. ve 5. sorulardaki çözümlerinin doğruluğunu gerekçe göstererek "
                "maddi hata incelemesi talebiyle itiraz etmektedir."
            ),
            "varliklar": {
                "kurumlar": ["Atatürk Üniversitesi Fen Fakültesi Dekanlığı", "Fizik Bölümü"],
                "lokasyonlar": [],
                "tarihler": ["2025-2026 Eğitim-Öğretim Yılı Güz Yarıyılı", "14.11.2025"],
            },
            "ilgili_mevzuat_onerisi": ["Atatürk Üniversitesi Önlisans ve Lisans Eğitim-Öğretim Yönetmeliği"],
            "eksik_bilgiler": ["İletişim Bilgisi (Telefon veya E-posta)"],
            "aciliyet_durumu": "Normal",
        },
        "gorev2": {
            "yonlendirme_karari": {
                "islem_yapacak_ana_kurum": "Atatürk Üniversitesi Fen Fakültesi Dekanlığı",
                "geregi_icin_yonlendirilecek_birim": "Fizik Bölümü Başkanlığı",
                "bilgi_icin_iletilecek_birimler": ["Öğrenci İşleri Dekanlık Birimi"],
                "yonlendirme_gerekcesi": (
                    "Öğrencinin ara sınav notuna ilişkin maddi hata itirazının, ilgili "
                    "eğitim-öğretim yönetmeliği gereğince dersin sorumlu öğretim üyesi tarafından "
                    "incelenmesi gerekliliği."
                ),
            },
            "resmi_yazi_taslagi": {
                "yazi_turu": "Üst Yazı",
                "konu": "Sınav Notuna İtiraz İncelemesi (Emre Karadağ)",
                "ilgi": "2023134028 numaralı öğrenci Emre Karadağ'ın 14.11.2025 tarihli dilekçesi.",
                "govde_metni": (
                    "İlgide kayıtlı dilekçe ile Bölümünüz 2. sınıf öğrencisi Emre Karadağ, 2025-2026 "
                    "Güz Yarıyılı 'Klasik Mekanik' dersi ara sınav notuna maddi hata itirazında "
                    "bulunmaktadır. İlgili yönetmelik hükümleri uyarınca ekte gönderilen sınav "
                    "evrakının dersin sorumlu öğretim üyesi tarafından maddi hata yönünden "
                    "incelenerek, sonucun Dekanlığımıza bildirilmesi hususunda gereğini rica ederim."
                ),
                "imza_makami": "Dekan Yardımcısı",
            },
            "kullanici_bilgilendirme": {
                "kullaniciya_gosterilecek_mesaj": (
                    "Klasik Mekanik dersine ait sınav itiraz dilekçeniz dekanlık kayıtlarına alınmış "
                    "olup, maddi hata incelemesi yapılmak üzere Fizik Bölümü Başkanlığına iletilmiştir. "
                    "İnceleme sonucu tarafınıza bildirilecektir."
                ),
                "sistem_aksiyon_durumu": "İşleme Alındı",
            },
        },
    },
    {
        "baslik": "Örnek 3 — İtiraz Metni: Yapı Kayıt Belgesi iptaline itiraz",
        "metin": (
            "İMAR VE ŞEHİRCİLİK MÜDÜRLÜĞÜ'NE\n(YAPI KAYIT BELGESİ İTİRAZ DİLEKÇESİ)\n\n"
            "Konu: 7143 Sayılı Kanun Kapsamında Düzenlenen Yapı Kayıt Belgesinin İptali İşlemine "
            "İtiraz Hakkında\n\nI. TALEBİN KONUSU VE GEREKÇESİ\n\n"
            "Müdürlüğünüzce, mülkiyetimde bulunan ve ..... İli, ..... İlçesi, ..... Mahallesi, 3287 "
            "ada, 14 parsel sayılı taşınmaz üzerinde yer alan yapı için 2018 yılında 7143 sayılı Vergi "
            "ve Diğer Bazı Alacakların Yeniden Yapılandırılması ile Bazı Kanunlarda Değişiklik "
            "Yapılmasına İlişkin Kanun kapsamında tarafıma \"Yapı Kayıt Belgesi\" (Belge No: "
            "YKB-2018-0447215) düzenlenmiş ve gerekli harç bedeli tarafımca eksiksiz olarak "
            "ödenmiştir. Ancak Müdürlüğünüzün 11.02.2026 tarihli ve 2026/1187 sayılı yazısı ile, söz "
            "konusu yapının \"dere yatağına 3 metre mesafede bulunduğu\" gerekçesiyle Yapı Kayıt "
            "Belgesinin iptaline karar verildiği tarafıma tebliğ edilmiştir.\n\n"
            "Ad Soyad: Necati DEMİRTAŞ\nT.C. Kimlik No: 38291047562\nAynı ilçede ikamet etmekteyim."
        ),
        "gorev1": {
            "evrak_turu": "İtiraz Metni",
            "konu": "Yapı Kayıt Belgesi İptaline İtiraz ve İptalin Durdurulması Talebi",
            "evrak_tarihi": None,
            "sayi_veya_kayit_no": None,
            "gonderen": {
                "gonderen_tipi": "Gerçek Kişi",
                "ad_soyad_veya_unvan": "Necati DEMİRTAŞ",
                "kimlik_veya_vergi_no": "38291047562",
                "iletisim_bilgisi": "Aynı ilçede ikamet etmekteyim.",
            },
            "kisa_ozet": (
                "Başvuru sahibi, 7143 sayılı Kanun kapsamında aldığı Yapı Kayıt Belgesi'nin dere "
                "yatağına yakınlık gerekçesiyle iptal edilmesine itiraz etmekte; fiili mesafenin "
                "11,4 metre olduğunu öne sürerek yeniden keşif yapılmasını ve yıkım işlemlerinin "
                "durdurulmasını talep etmektedir."
            ),
            "varliklar": {
                "kurumlar": ["İmar ve Şehircilik Müdürlüğü", "Çevre ve Şehircilik Bakanlığı", "Devlet Su İşleri Genel Müdürlüğü"],
                "lokasyonlar": ["3287 ada, 14 parsel"],
                "tarihler": ["2018", "11.02.2026", "2016"],
            },
            "ilgili_mevzuat_onerisi": [
                "7143 Sayılı Vergi ve Diğer Bazı Alacakların Yeniden Yapılandırılması Kanunu",
                "2577 Sayılı İdari Yargılama Usulü Kanunu",
                "İmar Barışı Uygulama Yönetmeliği",
            ],
            "eksik_bilgiler": ["Evrak Tarihi", "Tam İkametgah Adresi", "İletişim Bilgisi (Telefon/E-posta)"],
            "aciliyet_durumu": "İvedi",
        },
        "gorev2": {
            "yonlendirme_karari": {
                "islem_yapacak_ana_kurum": "İlgili Belediye İmar ve Şehircilik Müdürlüğü",
                "geregi_icin_yonlendirilecek_birim": "Yapı Kontrol Şube Müdürlüğü",
                "bilgi_icin_iletilecek_birimler": ["Hukuk İşleri Müdürlüğü", "Harita İşleri Şube Müdürlüğü"],
                "yonlendirme_gerekcesi": (
                    "Vatandaşın Yapı Kayıt Belgesi iptaline itiraz etmesi, resmi ölçüm değerleri "
                    "arasında farklılık iddia etmesi ve yıkım/mühürleme işlemlerinin durdurulmasını "
                    "talep etmesi."
                ),
            },
            "resmi_yazi_taslagi": {
                "yazi_turu": "Üst Yazı",
                "konu": "YKB İptali İtirazı ve Keşif Talebi Hk. (Necati Demirtaş)",
                "ilgi": "11.02.2026 tarihli YKB iptal yazımız ve Necati Demirtaş'ın itiraz dilekçesi.",
                "govde_metni": (
                    "İlgide kayıtlı dilekçe ile Necati Demirtaş, 3287 ada 14 parseldeki yapısına ait "
                    "iptal edilen Yapı Kayıt Belgesine itiraz etmekte ve fiili dere mesafesinin 11,4 "
                    "metre olduğunu iddia ederek yeni bir ortak ölçüm/keşif talep etmektedir. İlgilinin "
                    "mağduriyetine yol açmamak adına, Harita İşleri birimince acilen yerinde ölçüm "
                    "yapılması ve süreç sonuçlanana kadar yıkım/mühürleme işlemlerinin durdurulması "
                    "hususunda gereğini rica ederim."
                ),
                "imza_makami": "İmar ve Şehircilik Müdürü",
            },
            "kullanici_bilgilendirme": {
                "kullaniciya_gosterilecek_mesaj": (
                    "Yapı Kayıt Belgesi iptaline ilişkin itirazınız kayda alınmıştır. Yeniden yerinde "
                    "keşif/ölçüm yapılması için Harita birimimiz görevlendirilmiştir. Tarafınıza resmi "
                    "tebligat yapılabilmesi için lütfen en kısa sürede tam adresinizi ve iletişim "
                    "numaranızı güncelleyiniz."
                ),
                "sistem_aksiyon_durumu": "İşleme Alındı",
            },
        },
    },
    {
        "baslik": "Örnek 4 — Kurumlararası Resmî Yazı: Sunucu donanımı satın alma",
        "metin": (
            "T.C.\nİÇİŞLERİ BAKANLIĞI\nBilgi Teknolojileri Genel Müdürlüğü\n\n"
            "Sayı: E-11223344-934.01-2026/0055\nTarih: 14.08.2026\n\n"
            "Bakanlığımız veri merkezinde artan işlem yükünü karşılamak amacıyla, 2 adet yeni sunucu "
            "donanımına ihtiyaç duyulmaktadır. Söz konusu alımın 4734 Sayılı Kamu İhale Kanunu "
            "gereğince yapılması ve satın alma sürecinin başlatılması hususunda bilgilerinizi ve "
            "gereğini arz ederim.\n\nİmza\nZeynep Çelik\nDaire Başkanı"
        ),
        "gorev1": {
            "evrak_turu": "Kurumlararası Resmî Yazı",
            "konu": "Sunucu Donanımı Satın Alma Talebi",
            "evrak_tarihi": "14.08.2026",
            "sayi_veya_kayit_no": "E-11223344-934.01-2026/0055",
            "gonderen": {
                "gonderen_tipi": "Kamu Kurumu",
                "ad_soyad_veya_unvan": "İçişleri Bakanlığı Bilgi Teknolojileri Genel Müdürlüğü (Zeynep Çelik - Daire Başkanı)",
                "kimlik_veya_vergi_no": None,
                "iletisim_bilgisi": None,
            },
            "kisa_ozet": "Veri merkezindeki işlem yükünü karşılamak amacıyla 4734 Sayılı Kanun kapsamında 2 adet yeni sunucu donanımı satın alınması talebi.",
            "varliklar": {
                "kurumlar": ["İçişleri Bakanlığı", "Bilgi Teknolojileri Genel Müdürlüğü"],
                "lokasyonlar": [],
                "tarihler": ["14.08.2026"],
            },
            "ilgili_mevzuat_onerisi": ["4734 Sayılı Kamu İhale Kanunu"],
            "eksik_bilgiler": ["Evrakın antet bölümünde 'Konu' başlığı bulunmamaktadır."],
            "aciliyet_durumu": "Normal",
        },
        "gorev2": {
            "yonlendirme_karari": {
                "islem_yapacak_ana_kurum": "İçişleri Bakanlığı",
                "geregi_icin_yonlendirilecek_birim": "Destek Hizmetleri Dairesi Başkanlığı",
                "bilgi_icin_iletilecek_birimler": ["Strateji Geliştirme Başkanlığı", "Bilgi Teknolojileri Genel Müdürlüğü"],
                "yonlendirme_gerekcesi": (
                    "4734 Sayılı Kamu İhale Kanunu kapsamındaki donanım ve mal alım süreçleri Destek "
                    "Hizmetleri birimi tarafından yürütüldüğü için evrak bu birime sevk edilmiştir."
                ),
            },
            "resmi_yazi_taslagi": {
                "yazi_turu": "Üst Yazı",
                "konu": "Sunucu Donanımı Satın Alma Talebi",
                "ilgi": "Bilgi Teknolojileri Genel Müdürlüğünün 14.08.2026 tarihli ve E-11223344-934.01-2026/0055 sayılı yazısı.",
                "govde_metni": (
                    "İlgide kayıtlı yazı ile Bakanlığımız veri merkezinin artan işlem yükünü karşılamak "
                    "amacıyla 2 adet yeni sunucu donanımı alımı talep edilmiştir. Söz konusu alım "
                    "işlemlerinin 4734 Sayılı Kamu İhale Kanunu hükümleri çerçevesinde başlatılması "
                    "hususunda gereğini arz/rica ederim."
                ),
                "imza_makami": "Destek Hizmetleri Dairesi Başkanı",
            },
            "kullanici_bilgilendirme": {
                "kullaniciya_gosterilecek_mesaj": (
                    "Sunucu donanımı satın alma talebiniz alınmış olup, ihale sürecinin başlatılması "
                    "için Destek Hizmetleri birimine sevk edilmiştir."
                ),
                "sistem_aksiyon_durumu": "İşleme Alındı",
            },
        },
    },
]
