import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_community.llms import OpenAI
import openai
import logging
import re  # Regex için eklendi
from unidecode import unidecode # Türkçe karakterler için eklendi

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔑 OpenAI API anahtarı
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# API anahtarı kontrolü
if not openai.api_key:
    st.error(
        "❌ OpenAI API anahtarı bulunamadı. Lütfen .env dosyasını kontrol edin ve 'OPENAI_API_KEY' değişkenini ekleyin.")
    st.stop()

# 📊 Analiz edilebilir sütunlar tanımı (Yinelenen anahtarlar düzeltildi)
ANALYZABLE_COLUMNS = {
    'uid': {
        'name': 'uid',
        'keywords': ['benzersiz kimlik', 'unique id', 'id', 'tanımlayıcı', 'yayın kimliği'],
        'description': 'Yayınlara ait benzersiz kimlik bazında analizler',
        'examples': ['ID\'si 1234 olan yayın nedir?', 'Kaç farklı UID var?', 'Bu UID kime ait?']
    },
    'title': {
        'name': 'title',
        'keywords': ['başlık', 'title', 'yayın adı', 'eser adı', 'makale başlığı'],
        'description': 'Yayın başlığı bazında analizler',
        'examples': ['"Machine Learning" başlıklı kaç yayın var?', 'En uzun başlıklı yayın hangisi?',
                     'Başlığı "Deep Learning" olan yayınları listele.']
    },
    'types': {
        'name': 'types',
        'keywords': ['tür', 'type', 'kategori', 'çeşit', 'yayın türü', 'belge türü'],
        'description': 'Yayın türü bazında analizler',
        'examples': ['Kaç tane makale var?', 'Hangi yayın türü en çok?', 'Konferans bildirileri nelerdir?']
    },
    'sourceTypes': {
        'name': 'sourceTypes',
        'keywords': ['kaynak türü', 'source type', 'dergi türü', 'platform'],
        'description': 'Kaynak türü bazında analizler (örn: dergi, konferans)',
        'examples': ['Hangi kaynak türleri mevcut?', 'Dergi türünde kaç yayın var?',
                     'Konferanslarda yayınlanan makaleler hangileri?']
    },
    'source.sourceTitle': {
        'name': 'source.sourceTitle',
        'keywords': ['dergi', 'journal', 'source', 'kaynak', 'yayın organı', 'dergi adı', 'kitap adı'],
        'description': 'Dergi/kaynak adı bazında analizler',
        'examples': ['Hangi dergide en çok yayın var?', 'Nature dergisinde kaç yayın var?',
                     'IEEE Access dergisindeki yayınları göster.']
    },
    'source.publishYear': {
        'name': 'source.publishYear',
        'keywords': ['yıl', 'year', 'tarih', 'zaman', 'yayın yılı', 'ne zaman'],
        'description': 'Yayın yılı bazında analizler',
        'examples': ['2023 yılında kaç yayın yapıldı?', 'En çok yayın hangi yılda yapıldı?',
                     'Yıllara göre yayın sayılarını listele.']
    },
    'source.volume': {
        'name': 'source.volume',
        'keywords': ['cilt', 'volume', 'dergi cildi', 'kaçıncı cilt'],
        'description': 'Dergi cilt numarası bazında analizler',
        'examples': ['Cilt 10\'da kaç yayın var?', 'En sık kullanılan cilt numarası nedir?',
                     'Cilt 15\'teki yayınları listele.']
    },
    'source.issue': {
        'name': 'source.issue',
        'keywords': ['sayı', 'issue', 'dergi sayısı', 'kaçıncı sayı'],
        'description': 'Dergi sayı numarası bazında analizler',
        'examples': ['Sayı 5\'te kaç yayın var?', 'En çok yayın hangi sayıda yapıldı?',
                     'Sayı 2\'deki makaleleri göster.']
    },
    'source.pages.range': {
        'name': 'source.pages.range',
        'keywords': ['sayfa aralığı', 'sayfa', 'pages', 'aralık', 'sayfa numarası'],
        'description': 'Yayınların sayfa aralığı bazında analizler',
        'examples': ['10-20 sayfa aralığındaki yayınlar hangileri?', 'Ortalama sayfa aralığı nedir?',
                     'Sayfa aralığı belirli olmayan yayınları bul.']
    },
    # Yazar sütunları tek bir girişte birleştirildi
    'Author Display Name': { # Ana yazar sütunu olarak Display Name kullanıldı
        'name': 'Author Display Name',
        'keywords': ['yazar adı', 'author display name', 'yazar', 'araştırmacı', 'akademisyen', 'kim', 'hangi yazar',
                     'yayın yapan', 'kişi', 'ad soyad'], # 'ad soyad' da eklendi
        'description': 'Yazarın görünen adı veya adı ve soyadı bazında analizler',
        'examples': ['Ahmet Yılmaz kaç yayın yapmış?', 'En çok yayın yapan yazar kim?',
                     'Yiğit Kazancıoğlu kaç yayını var?', 'Bu yazarın toplam yayın sayısı nedir?',
                     'Taşgetiren kaç yayını vardır?', 'Mehmet Demir kaç yayın yapmış?',
                     'Bu ad ve soyad ile en çok yayın yapan kim?']
    },
    'citations': {
        'name': 'citations',
        'keywords': ['atıflar', 'citations', 'referanslar', 'alıntılar'],
        'description': 'Atıf bilgileri bazında analizler (genellikle metinsel)',
        'examples': ['Hangi yayınlar en çok atıf almış?', 'Belirli bir atıf metnine göre filtrele.']
    },
    'identifiers.doi': {
        'name': 'identifiers.doi',
        'keywords': ['doi', 'tanımlayıcı', 'digital object identifier', 'makale kodu'],
        'description': 'DOI bazında analizler',
        'examples': ['Bu DOI\'ye sahip yayın nedir?', 'Eksik DOI\'si olan kaç yayın var?', 'Belirli bir DOI\'yi ara.']
    },
    'identifiers.issn': {
        'name': 'identifiers.issn',
        'keywords': ['issn', 'tanımlayıcı', 'international standard serial number', 'dergi kodu'],
        'description': 'ISSN bazında analizler',
        'examples': ['Bu ISSN\'e sahip dergiler hangileri?', 'En yaygın ISSN nedir?', 'ISSN\'e göre filtrele.']
    },
    'keywords.authorKeywords': {
        'name': 'keywords.authorKeywords',
        'keywords': ['anahtar kelime', 'keyword', 'konu', 'alan', 'yazar anahtar kelimeleri', 'konu alanı'],
        'description': 'Yazar anahtar kelimeleri bazında analizler',
        'examples': ['"Machine learning" konusunda kaç yayın var?', 'En çok kullanılan anahtar kelime nedir?',
                     'Robotik ile ilgili yayınları göster.']
    },
    'Author WoS Standard': {
        'name': 'Author WoS Standard',
        'keywords': ['wos yazar', 'web of science', 'wos standardı', 'standardize yazar'],
        'description': 'Web of Science standart yazar adı bazında analizler',
        'examples': ['WoS standardına göre en çok yayın yapan yazar kim?', 'Bu isme göre kaç WoS kaydı var?']
    },
    'Author Researcher ID': {
        'name': 'Author Researcher ID',
        'keywords': ['researcher id', 'yazar kimliği', 'orcid', 'kimlik numarası'],
        'description': 'Yazar Researcher ID bazında analizler',
        'examples': ['Bu Researcher ID\'ye sahip yazar kim?', 'Kaç farklı Researcher ID var?',
                     'ID\'si XXX olan yazarın yayınları.']
    },
    'Citation DB': {
        'name': 'Citation DB',
        'keywords': ['atıf veritabanı', 'citation database', 'db', 'veri tabanı'],
        'description': 'Atıf veritabanı bilgisi bazında analizler',
        'examples': ['Hangi atıf veritabanlarında yayınlar var?', 'Scopus\'ta kaç yayın listeleniyor?',
                     'Web of Science veritabanındaki yayınlar.']
    },
    'Citation Count': {
        'name': 'Citation Count',
        'keywords': ['atıf', 'citation', 'alıntı', 'referans', 'atıf sayısı', 'toplam atıf'],
        'description': 'Atıf sayısı bazında analizler',
        'examples': ['En çok atıf alan yayın hangisi?', 'Ortalama atıf sayısı kaç?',
                     'Yaşar Üniversitesinin atıflarının toplamı kaçtır?']
    },
    'Üniversite Adı': {
        'name': 'Üniversite Adı',
        'keywords': ['üniversite', 'university', 'uni', 'okul', 'kurum', 'üniversite adı', 'kuruluş'],
        'description': 'Üniversite adı bazında analizler',
        'examples': ['Yaşar Üniversitesi kaç yayın yapmış?', 'Yaşar Üniversitesinin kaç yayını var?',
                     'Hangi üniversite en çok yayın yapıyor?', 'Yaşar Üniversitesinin toplam yayın sayısı kaç?',
                     'İzmir Ekonomi Üniversitesinin toplam kaç yayını vardır?'] # Yeni örnek eklendi
    }
}

st.set_page_config(layout="wide", page_title="GPT ile Yayın Analizi")
st.title("📊 GPT ile Yayın Analizi (Doğal Dil İle)")
st.markdown("---")


# 📁 Excel dosyalarını oku
@st.cache_data
def load_excel_data():
    """Excel dosyalarını yükle ve birleştir"""
    EXCEL_FOLDER = "excel_data/"

    if not os.path.exists(EXCEL_FOLDER):
        st.error(
            f"❌ '{EXCEL_FOLDER}' klasörü bulunamadı. Lütfen 'excel_data' adında bir klasör oluşturun ve Excel dosyalarınızı içine koyun.")
        return None

    dfs = []
    loaded_files = []

    for file in os.listdir(EXCEL_FOLDER):
        if file.endswith((".xlsx", ".xls")) and not file.startswith("~$"):
            try:
                df_temp = pd.read_excel(os.path.join(EXCEL_FOLDER, file))
                dfs.append(df_temp)
                loaded_files.append(file)
                logger.info(f"✅ {file} yüklendi ({len(df_temp)} satır)")
            except Exception as e:
                st.warning(f"⚠️ {file} dosyası yüklenemedi: {e}")

    if not dfs:
        st.warning("❗ Klasörde hiç .xlsx veya .xls dosyası bulunamadı. Lütfen 'excel_data' klasörünüze dosya ekleyin.")
        return None

    st.sidebar.success(f"📁 {len(loaded_files)} dosya yüklendi:")
    for file in loaded_files:
        st.sidebar.write(f"• {file}")

    return pd.concat(dfs, ignore_index=True)


# Veriyi yükle
df = load_excel_data()
if df is None:
    st.stop()


# 🧹 Veri temizleme
def clean_data(df):
    """Veri temizleme işlemleri"""
    df_clean = df.copy()

    df_clean.columns = df_clean.columns.str.strip()

    # Otomatik olarak string sütunları tespit et ve temizle
    for col in df_clean.columns:
        if df_clean[col].dtype == 'object':
            df_clean[col] = df_clean[col].astype(str).str.strip().replace('nan', '')

    # Sayısal sütunları temizle ve eksik değerleri doldur
    numeric_cols_to_check = [
        'Citation Count', 'source.volume', 'source.issue', 'source.publishYear'
    ]
    for col in numeric_cols_to_check:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
            if col in ['Citation Count', 'source.volume', 'source.issue', 'source.publishYear']:
                df_clean[col] = df_clean[col].fillna(0).astype(int)
            else:
                df_clean[col] = df_clean[col].fillna(0)

    initial_count = len(df_clean)
    if 'title' in df_clean.columns:
        df_clean = df_clean.drop_duplicates(subset=['title'])
        removed_count = initial_count - len(df_clean)
        if removed_count > 0:
            st.info(f"🧹 {removed_count} tekrar eden yayın kaldırıldı (başlığa göre).")

    return df_clean


df_clean = clean_data(df)

# 📊 Veri özeti
st.subheader("📈 Veri Özeti")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("📝 Toplam Yayın", len(df_clean))

with col2:
    if 'Üniversite Adı' in df_clean.columns:
        unique_unis = df_clean['Üniversite Adı'].nunique()
        st.metric("🏫 Üniversite Sayısı", unique_unis)
    else:
        st.metric("🏫 Üniversite Sayısı", "N/A")

with col3:
    if 'source.sourceTitle' in df_clean.columns:
        unique_journals = df_clean['source.sourceTitle'].nunique()
        st.metric("📖 Dergi Sayısı", unique_journals)
    else:
        st.metric("📖 Dergi Sayısı", "N/A")

# Mevcut sütunları göster
st.subheader("📋 Analiz Edilebilir Sütunlar")
valid_analyzable_cols = {k: v for k, v in ANALYZABLE_COLUMNS.items() if k in df_clean.columns}

available_cols_list = list(valid_analyzable_cols.keys())
missing_cols_list = [col for col in ANALYZABLE_COLUMNS.keys() if col not in df_clean.columns]

if available_cols_list:
    st.success(f"✅ **Mevcut Sütunlar:** {', '.join(available_cols_list)}")
if missing_cols_list:
    st.warning(f"⚠️ **Eksik Sütunlar (Excel dosyanızda bulunmayanlar):** {', '.join(missing_cols_list)}")


# Soru türü tespiti (güncellenmiş ve daha sağlam)
def detect_question_column(question):
    """Sorudan hangi sütunla ilgili olduğunu tespit et ve niyet belirle"""
    question_lower = question.lower()
    detected_columns_and_scores = {}

    # 1. Aşama: Özel ve yüksek öncelikli durumlar (üniversite, atıf sayısı, yazar adı)
    # Üniversite Adı tespiti
    if 'Üniversite Adı' in df_clean.columns:
        uni_keywords = ['üniversite', 'university', 'uni', 'okul', 'kurum', 'üniversite adı', 'kuruluş']
        if any(kw in question_lower for kw in uni_keywords):
            detected_columns_and_scores['Üniversite Adı'] = 10 # En yüksek öncelik

    # Yazar Adı tespiti
    # Yazar anahtar kelimeleri ve potansiyel büyük harfle başlayan isimler
    author_keywords = ['yazar', 'araştırmacı', 'akademisyen', 'kim', 'yayın yapan', 'kişi', 'ad soyad']
    has_author_keyword = any(kw in question_lower for kw in author_keywords)
    potential_name_found = False

    # Regex ile büyük harfle başlayan kelimeleri (isimleri) bulmaya çalış
    # 'kaç' gibi soru kelimelerini dışarıda bırak
    clean_words = [word for word in re.findall(r'\b[A-ZÇĞİÖŞÜ][a-zA-Zçğıiöşü]*\b', question) if word.lower() not in ['kaç', 'kim']]
    if len(clean_words) > 0:
        potential_name_found = True

    if has_author_keyword or potential_name_found:
        # 'Author Display Name' veya 'Author Name and Surname' sütunu mevcutsa öncelik ver
        if 'Author Display Name' in df_clean.columns:
            detected_columns_and_scores['Author Display Name'] = 9 # Yüksek öncelik
        elif 'Author Name and Surname' in df_clean.columns: # Eğer Author Display Name yoksa veya daha az uygunsa
            detected_columns_and_scores['Author Name and Surname'] = 9

        # Eğer yazar soruluyorsa ve spesifik bir ölçüt sütunu yoksa, yayın sayısını saymak için title'ı varsayalım
        if 'title' in df_clean.columns and 'title' not in detected_columns_and_scores:
            if 'kaç yayın' in question_lower or 'yayın sayısı' in question_lower:
                detected_columns_and_scores['title'] = 1 # Yazarın yayın sayısını bulmak için uygun

    # Atıf Sayısı tespiti
    if 'Citation Count' in df_clean.columns and any(
            kw in question_lower for kw in ANALYZABLE_COLUMNS['Citation Count']['keywords']):
        detected_columns_and_scores['Citation Count'] = 8 # Yüksek öncelik

    # Yayın Yılı tespiti
    if 'source.publishYear' in df_clean.columns and any(
            kw in question_lower for kw in ANALYZABLE_COLUMNS['source.publishYear']['keywords']):
        detected_columns_and_scores['source.publishYear'] = 7 # Yüksek öncelik

    # 2. Aşama: Diğer genel sütunlar için anahtar kelime tabanlı tespit
    # Mevcut öncelikleri ezmemek için 'if col_name not in detected_columns_and_scores' kontrolü önemli.
    for col_name, col_info in ANALYZABLE_COLUMNS.items():
        if col_name in df_clean.columns and col_name not in detected_columns_and_scores:
            if any(keyword in question_lower for keyword in col_info['keywords']):
                # Daha genel sütunlara düşük öncelik ver
                if col_name in ['title', 'uid']: # title ve uid çok geneldir
                    detected_columns_and_scores[col_name] = max(detected_columns_and_scores.get(col_name, 0), 0.5)
                else:
                    detected_columns_and_scores[col_name] = max(detected_columns_and_scores.get(col_name, 0), 2) # Orta düzey

    # En yüksek puanlı sütunu seç
    if detected_columns_and_scores:
        sorted_cols = sorted(detected_columns_and_scores.items(), key=lambda item: item[1], reverse=True)
        top_col_name = sorted_cols[0][0]
        return top_col_name, ANALYZABLE_COLUMNS[top_col_name]

    return None, None


# 🤖 GPT ajanı
# 🤖 GPT ajanı
@st.cache_resource
def create_agent():
    """GPT ajanını oluştur"""
    try:
        llm = OpenAI(temperature=0, model_name="gpt-3.5-turbo-instruct")
        agent = create_pandas_dataframe_agent(
            llm,
            df_clean,
            verbose=False,
            allow_dangerous_code=True,
            handle_parsing_errors=True,  # ✅ bu da doğrudan verilebilir
            max_iterations=10,
            max_execution_time=30
        )
        return agent
    except Exception as e:
        st.error(
            f"❌ GPT ajanı oluşturulamadı: {e}. Lütfen OpenAI API anahtarınızın geçerli olduğundan ve internet bağlantınızın olduğundan emin olun.")
        return None

agent = create_agent()
if agent is None:
    st.stop()

# 💬 Soru-cevap arayüzü
st.subheader("🤖 Soru Sor")

# Örnek soruları sekmeler halinde göster
st.write("**📝 Örnek Sorular:**")
tab_names = [info['name'] for col_name, info in ANALYZABLE_COLUMNS.items() if col_name in df_clean.columns]
# Sekme adlarında tekrarı önlemek için set kullanabiliriz, ancak sıralamayı bozabilir.
# Bu durumda, ANALYZABLE_COLUMNS'ı düzeltmek en doğrusu oldu.
tabs = st.tabs(tab_names)

for i, (col_name, col_info) in enumerate(ANALYZABLE_COLUMNS.items()):
    if col_name in df_clean.columns and i < len(tabs): # Index hatasını önlemek için kontrol
        with tabs[i]:
            st.write(f"**{col_info['name']} için örnekler:**")
            for example in col_info['examples']:
                if st.button(example,
                             key=f"example_{col_name}_{example.replace(' ', '_').replace('?', '').replace('.', '').replace('"', '')}"): # Özel karakterleri temizle
                    st.session_state.question = example

# Kullanıcıdan soru al
question = st.text_input(
    "📥 Soru sorun:",
    value=st.session_state.get('question', ''),
    placeholder="Örneğin: Yaşar Üniversitesinin kaç yayını var? Veya: Taşgetiren kaç yayını vardır?"
)

if question:
    target_column, col_info = detect_question_column(question)
    question_lower = question.lower()

    # Yazar bazlı toplam yayın sayısı sorgularını özel olarak ele alalım
    is_author_publication_count_query = False
    if target_column in ['Author Display Name', 'Author Name and Surname'] and \
            any(kw in question_lower for kw in
                ['kaç yayını var', 'toplam yayını kaç', 'yayın sayısı', 'yayın sayısı nedir']):
        is_author_publication_count_query = True
        st.info(
            f"💡 **Özel Durum Algılandı:** Yazarın toplam yayın sayısı sorgusu. '{target_column}' sütunu kullanılacak.")

    if target_column:
        st.info(f"🎯 **Tespit edilen kategori:** **{col_info['description']}**")
        st.info(f"🔍 **Analiz edilecek sütun:** **`{target_column}`**")

        instruction = ""

        if is_author_publication_count_query:
            # Yazar adını sorudan çekmek için daha sağlam bir yöntem
            # unidecode kullanarak Türkçe karakterleri standardize et
            potential_name_parts = [unidecode(word) for word in re.findall(r'\b[A-ZÇĞİÖŞÜ][a-zA-Zçğıiöşü]*\b', question) if
                                    word.lower() not in ['kaç', 'kim', 'var', 'vardır', 'adlı']]
            author_name = " ".join(potential_name_parts).strip()

            if not author_name:
                # Eğer regex ile isim bulunamazsa, sorudan genel bir metin olarak çekmeyi dene
                # "kaç yayını var" gibi ifadeleri çıkararak kalanı isim kabul et
                temp_name = question_lower.replace('kaç yayını var', '').replace('toplam yayını kaç', '').replace(
                    'yayın sayısı', '').replace('yayın sayısı nedir', '').strip()
                author_name = unidecode(temp_name) # Burayı da unidecode ile normalize et
                if not author_name: # Hala boşsa, varsayılan bir terim kullan
                    author_name = "belirtilen yazar" # Modelin kendisi tespit etmeye çalışsın

            # Ajanın kullanacağı prompt
            instruction = f"""
            ÇOK ÖNEMLİ KURALLAR:

            1. Kullanıcının sorusu '{author_name}' adlı yazarın toplam yayın sayısıyla ilgili.
            2. Bu soruyu cevaplamak için SADECE '{target_column}' sütununu kullan.
            3. DataFrame'i '{author_name}' ismini içeren yayınları bulmak için filtrele. Arama yaparken, hem aranan terimi hem de sütun içeriğini Türkçe karakterlerden arındırarak (unidecode kullanarak) ve büyük/küçük harf duyarsız (case=False) bir şekilde karşılaştır. Boş değerleri (na=False) yok say.
            4. Daha sonra, bu filtrelenmiş yayınların SATIR SAYISINI (örneğin `.shape[0]` veya `len()`) döndür.
            5. Eğer belirtilen yazara ait yayın bulunamazsa, uygun bir mesajla yanıt ver.
            6. Cevabını Türkçe ver ve sayısal sonucu açıkça belirt.
            7. **Sakın herhangi bir Python kodu üretme veya kod şablonu verme.**

            DataFrame adı: df
            Hedef sütun: {target_column}

            Kullanıcı sorusu: {question}

            Şimdi bu kurallara göre soruyu cevapla.
            """
        elif "en çok atıf aldığı yayın" in question_lower or "en çok atıf alan yayın" in question_lower:
            st.info(
                "💡 **Özel Durum Algılandı:** 'En çok atıf alan yayın' sorgusu algılandı. Analiz 'Citation Count' ve 'title' sütunlarını içerecektir.")

            uni_filter_term = ""
            # unidecode ile üniversite adlarını normalize et
            if "yaşar üniversitesi" in unidecode(question_lower):
                uni_filter_term = "yaşar üniversitesi"
            elif "yaşar" in unidecode(question_lower):
                uni_filter_term = "yaşar"
            elif "izmir ekonomi üniversitesi" in unidecode(question_lower):
                uni_filter_term = "izmir ekonomi üniversitesi"
            elif "izmir ekonomi" in unidecode(question_lower):
                uni_filter_term = "izmir ekonomi"

            uni_filter_clause = ""
            if uni_filter_term and 'Üniversite Adı' in df_clean.columns:
                uni_filter_clause = f"""
                from unidecode import unidecode
                search_uni_normalized = unidecode('{uni_filter_term}').lower()
                df_filtered = df[df['Üniversite Adı'].astype(str).apply(lambda x: search_uni_normalized in unidecode(str(x)).lower() if pd.notna(x) else False)]
                if not df_filtered.empty:
                    most_cited = df_filtered.loc[df_filtered['Citation Count'].idxmax()]
                    print(f"En çok atıf alan yayın ({uni_filter_term}): {{most_cited['title']}} (Atıf Sayısı: {{most_cited['Citation Count']}})")
                else:
                    print(f"'{uni_filter_term}' üniversitesine ait yayın bulunamadı.")
                """
            else:
                uni_filter_clause = """
                most_cited = df.loc[df['Citation Count'].idxmax()]
                print(f"En çok atıf alan yayın: {most_cited['title']} (Atıf Sayısı: {most_cited['Citation Count']})")
                """

            instruction = f"""
            ÇOK ÖNEMLİ KURALLAR:

            1. Kullanıcının sorusu "en çok atıf alan yayın" ile ilgili.
            2. Bu soruyu cevaplamak için 'Citation Count' ve 'title' sütunlarını kullanmalısın. Eğer üniversite belirtilmişse 'Üniversite Adı' sütununu da kullan.
            3. Öncelikle eğer bir üniversite adı belirtilmişse (örn. 'Yaşar Üniversitesi'), DataFrame'i bu üniversiteye göre filtrele. Türkçe karakterleri de göz önünde bulundurarak unidecode ile normalizasyon yap.
            4. Sonra, bu filtrelenmiş verideki 'Citation Count' sütununa göre azalan sırada sırala.
            5. En yüksek atıf sayısına sahip yayının BAŞLIĞINI ('title' sütunu) ve ATIF SAYISINI ('Citation Count' sütununu) döndür.
            6. Eğer birden fazla yayın aynı en yüksek atıf sayısına sahipse, sadece ilkini döndürmen yeterlidir.
            7. Sadece bu sütunları kullan ve başka sütunlara odaklanma.

            DataFrame adı: df
            Hedef sütunlar: Citation Count, title, (isteğe bağlı olarak Üniversite Adı)

            Örnek kod şablonu:
            {uni_filter_clause}

            Kullanıcı sorusu: {question}

            Cevabını Türkçe ver ve yayının başlığını ve atıf sayısını açıkça belirt.
            """
            university_name = "yaşar"
            yasar_count = \
            df_clean[df_clean['Üniversite Adı'].astype(str).str.lower().str.contains(university_name)].shape[0]
            # Üniversite toplam yayın sayısı sorgusu için özel instruction
            uni_name_match = re.search(r'(?P<uni>[\w\sğüşöçıİ]+)\s+üniversite(?:si)?(?:sinin)?', question_lower)
            university_name = ""
            if uni_name_match:
                university_name = unidecode(uni_name_match.group('uni').strip())
            else:
                # Eğer regex ile bulunamazsa, anahtar kelimeleri çıkararak geri kalanı üniversite adı olarak al
                temp_uni_name = question_lower.replace('kaç yayını var', '').replace('yayın sayısı', '').replace('toplam yayın', '').strip()
                university_name = unidecode(temp_uni_name)
                if not university_name:
                    university_name = "belirtilen üniversite"

            instruction = f"""
            ÇOK ÖNEMLİ KURALLAR:

            1. Kullanıcının sorusu '{university_name}' adlı üniversitenin toplam yayın sayısıyla ilgili.
            2. Bu soruyu cevaplamak için SADECE '{target_column}' sütununu kullanmalısın.
            3. Öncelikle DataFrame'i '{university_name}' ismini içeren yayınları bulmak için filtrele (unidecode kullanarak Türkçe karakterleri normalize et, büyük/küçük harf duyarsız ve boş değerleri yok sayarak).
            4. Daha sonra, bu filtrelenmiş yayınların SATIR SAYISINI (örneğin `.shape[0]` veya `len()`) döndür.
            5. Eğer belirtilen üniversiteye ait yayın bulunamazsa, uygun bir mesajla yanıt ver.
            6. Cevabını Türkçe ver ve sayısal sonucu açıkça belirt.

            DataFrame adı: df
            Hedef sütun: {target_column}

            Örnek kod şablonu:
            from unidecode import unidecode
            search_uni_normalized = unidecode('{university_name}').lower()
            df_filtered = df[df['{target_column}'].astype(str).apply(lambda x: search_uni_normalized in unidecode(str(x)).lower() if pd.notna(x) else False)]
            if not df_filtered.empty:
                print(f"'{university_name}' adlı üniversitenin toplam {{len(df_filtered)}} yayını bulunmaktadır.")
            else:
                print(f"'{university_name}' adlı üniversiteye ait yayın bulunamadı.")

            Kullanıcı sorusu: {question}

            Şimdi bu kurallara göre soruyu cevapla.
            """
        else:  # Diğer genel sorgular için mevcut talimat
            instruction = f"""
            ÇOK ÖNEMLİ KURALLAR:

            1. SADECE '{target_column}' sütununa odaklan.
            2. DİĞER TÜM SÜTUNLARI GÖRMEZDEN GEL.
            3. Filtreleme veya hesaplama yaparken sadece bu sütunu kullan.
            4. Bu sütun dışındaki hiçbir sütuna bakma.
            5. Cevabını Türkçe ver ve mümkünse sayısal sonuçları göster.

            DataFrame adı: df
            Hedef sütun: {target_column}
            Veri tipi: {df_clean[target_column].dtype}

            # Önemli Çıkarsama ve Talimatlar:
            # Eğer kullanıcının sorusu "toplam yayın", "kaç yayın", "yayın sayısı" gibi ifadeler içeriyorsa,
            # ve hedef sütun 'Üniversite Adı' veya 'title' gibi yayınları saymaya uygun bir sütun ise,
            # ilgili filtrelenmiş DataFrame'in SATIR SAYISINI (örneğin .shape[0] veya len()) döndür.
            # Örneğin: df[df['Üniversite Adı'].str.contains('yaşar', case=False, na=False)].shape[0]

            # Eğer kullanıcının sorusu "toplam atıf", "atıflarının toplamı" gibi ifadeler içeriyorsa,
            # ve hedef sütun 'Citation Count' ise, bu sütundaki sayısal değerlerin TOPLAMINI (SUM) hesapla.
            # Örneğin: df[df['Üniversite Adı'].str.contains('yaşar', case=False, na=False)]['Citation Count'].sum()

            Kullanıcı sorusu: {question}

            Şimdi bu kurallara göre soruyu cevapla.
            """

        with st.spinner("🤖 GPT analiz ediyor..."):
            try:
                response = agent.run(instruction)

                st.success("🧠 GPT Cevabı:")
                st.write(response)

                # Sonuç doğrulama
                if st.checkbox("🔍 Sonuç Doğrulama"):
                    st.write(f"**Kullanılan sütun:** `{target_column}`")
                    if target_column in df_clean.columns:
                        st.write(f"**Sütun veri tipi:** `{df_clean[target_column].dtype}`")
                        st.write(f"**Örnek değerler (ilk 10):**")
                        st.write(df_clean[target_column].dropna().head(10).tolist())

                        if pd.api.types.is_numeric_dtype(df_clean[target_column]):
                            st.write(
                                f"**Doğrulama - {target_column} ortalaması:** `{df_clean[target_column].mean():.2f}`")
                            st.write(f"**Doğrulama - {target_column} toplamı:** `{df_clean[target_column].sum():.0f}`")
                        elif df_clean[target_column].dtype == 'object':
                            if not df_clean[target_column].dropna().empty:
                                top_value = df_clean[target_column].value_counts().index[0]
                                top_count = df_clean[target_column].value_counts().iloc[0]
                                st.write(
                                    f"**Doğrulama - En sık {target_column} değeri:** `'{top_value}'` ({top_count} adet)")
                            else:
                                st.write(f"**Doğrulama:** `{target_column}` sütununda geçerli değer bulunamadı.")

                        # Yazar sorgusu için manuel doğrulama
                        if is_author_publication_count_query and author_name != "belirtilen yazar":
                            st.write(f"**Manuel Doğrulama - '{author_name}' yayınları:**")
                            # unidecode kullanarak manuel doğrulama yap
                            search_term_normalized_manual = unidecode(author_name).lower()
                            df_filtered_manual = df_clean[
                                df_clean[target_column].astype(str).apply(lambda x: search_term_normalized_manual in unidecode(str(x)).lower() if pd.notna(x) else False)
                            ]
                            st.write(f"Manuel olarak bulunan yayın sayısı: **{len(df_filtered_manual)}**")

                        # "En çok atıf alan yayın" için manuel doğrulama
                        if ("en çok atıf aldığı yayın" in question_lower or "en çok atıf alan yayın" in question_lower) \
                                and 'Üniversite Adı' in df_clean.columns and 'Citation Count' in df_clean.columns and 'title' in df_clean.columns:

                            uni_search_term = ""
                            if "yaşar üniversitesi" in unidecode(question_lower):
                                uni_search_term = "yaşar üniversitesi"
                            elif "yaşar" in unidecode(question_lower):
                                uni_search_term = "yaşar"
                            elif "izmir ekonomi üniversitesi" in unidecode(question_lower):
                                uni_search_term = "izmir ekonomi üniversitesi"
                            elif "izmir ekonomi" in unidecode(question_lower):
                                uni_search_term = "izmir ekonomi"

                            df_filtered_uni_manual = df_clean
                            if uni_search_term:
                                search_uni_normalized_manual = unidecode(uni_search_term).lower()
                                df_filtered_uni_manual = df_clean[
                                    df_clean['Üniversite Adı'].astype(str).apply(lambda x: search_uni_normalized_manual in unidecode(str(x)).lower() if pd.notna(x) else False)
                                ]

                            if not df_filtered_uni_manual.empty:
                                most_cited_manual = df_filtered_uni_manual.loc[
                                    df_filtered_uni_manual['Citation Count'].idxmax()]
                                st.write(
                                    f"**Manuel Doğrulama - En çok atıf alan yayın ({'genel' if not uni_search_term else uni_search_term}):**")
                                st.write(f"Başlık: **{most_cited_manual['title']}**")
                                st.write(f"Atıf Sayısı: **{most_cited_manual['Citation Count']}**")
                            else:
                                st.write(f"**Manuel Doğrulama:** Belirtilen kritere göre yayın bulunamadı.")
                    else:
                        st.warning(f"Seçilen sütun `{target_column}` DataFrame'de bulunamadı, doğrulama yapılamadı.")

            except Exception as e:
                st.error(f"❌ Analiz sırasında bir hata oluştu: **{e}**")
                logger.error(f"Agent error: {e}", exc_info=True)

    else:
        st.warning("❓ Soru hangi kategori ile ilgili olduğu tespit edilemedi.")
        st.write("**Lütfen sorunuzu şu anahtar kelimelerle belirginleştirin:**")

        for col_name, col_info in ANALYZABLE_COLUMNS.items():
            if col_name in df_clean.columns:
                keywords_str = ', '.join(col_info['keywords'])
                st.write(f"• **{col_name}** için: {keywords_str}")


# 📊 Hızlı istatistikler
st.subheader("📊 Hızlı İstatistikler")

selected_stat_col = st.selectbox(
    "İstatistik görmek istediğiniz sütunu seçin:",
    ['Seçiniz'] + [col for col in ANALYZABLE_COLUMNS.keys() if col in df_clean.columns]
)

if selected_stat_col != 'Seçiniz':
    st.write(f"**{selected_stat_col} sütunu istatistikleri:**")

    if df_clean[selected_stat_col].dtype == 'object':
        value_counts = df_clean[selected_stat_col].value_counts().head(10)
        st.bar_chart(value_counts)
        st.write(f"**Toplam benzersiz değer:** {df_clean[selected_stat_col].nunique()}")
    else:
        st.write(df_clean[selected_stat_col].describe())
        st.histogram(df_clean[selected_stat_col].dropna())

# Sidebar - Sütun Detayları
st.sidebar.subheader("📋 Sütun Detayları")
for col_name, col_info in ANALYZABLE_COLUMNS.items():
    if col_name in df_clean.columns:
        with st.sidebar.expander(f"🔍 {col_name}"):
            st.write(f"**Açıklama:** {col_info['description']}")
            st.write(f"**Anahtar kelimeler:** {', '.join(col_info['keywords'])}")
            st.write(f"**Veri tipi:** {df_clean[col_name].dtype}")
            st.write(f"**Null değer:** {df_clean[col_name].isnull().sum()}")
            st.write(f"**Benzersiz değer:** {df_clean[col_name].nunique()}")