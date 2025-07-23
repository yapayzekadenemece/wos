import requests
import math
import pandas as pd
import os

# --- AYARLAR ---
# API anahtarını bir ortam değişkeni (environment variable) olarak ayarlamak en iyi yöntemdir.
# Eğer ortam değişkeni bulunamazsa, kod içindeki varsayılan değeri kullanır.
API_KEY = os.getenv("WOS_API_KEY", "2911c678b48cde2e576cc471cac3d27759f5328d")
BASE_URL = "https://api.clarivate.com/apis/wos-starter/v1/documents"
HEADERS = {"X-ApiKey": API_KEY}

# Üniversite listesi
universities = [
    "Reichman University", "Sabanci University", "TOBB Ekonomi ve Teknoloji University",
    "University of Navarra", "Universitat Internacional de Catalunya (UIC)",
    "Ozyegin University", "Kadir Has University", "Izmir Ekonomi Universitesi",
    "Jacobs University", "Ihsan Dogramaci Bilkent University", "Bahcesehir University",
    "Atilim University", "Koc University", "Universitat Ramon Llull", "Yasar University"
]


# --- VERİ ÇEKME FONKSİYONU ---
def fetch_all_data(universities_list):
    """
    Belirtilen üniversiteler için Web of Science API'sinden tüm yayın verilerini çeker.
    """
    all_items = []

    for uni in universities_list:
        print(f"\n⏳ {uni} için veri çekme işlemi başlıyor...")

        page = 1
        total_pages = 1

        while page <= total_pages:
            query = f'OG="{uni}" AND FPY=1900-2030'
            params = {"db": "WOS", "q": query, "limit": 50, "page": page}

            try:
                response = requests.get(BASE_URL, headers=HEADERS, params=params)
                response.raise_for_status()
                data = response.json()

                if page == 1:
                    metadata = data.get("metadata", {})
                    total_records = metadata.get("total", 0)
                    if total_records == 0:
                        print(f"⚠️ {uni} için hiç kayıt bulunamadı.")
                        break

                    per_page = metadata.get("limit", 50)
                    total_pages = math.ceil(total_records / per_page)
                    print(f"🔍 Toplam {total_records} kayıt {total_pages} sayfada bulundu.")

                print(f"📄 Sayfa {page}/{total_pages} işleniyor...")

                page_hits = data.get("hits", [])
                for item in page_hits:
                    item["source_university"] = uni
                all_items.extend(page_hits)

                page += 1

            except requests.exceptions.HTTPError as http_err:
                print(f"❌ HTTP Hatası: {http_err} - {response.text}")
                break
            except Exception as err:
                print(f"❌ Genel bir hata oluştu: {err}")
                break

    return all_items


# --- VERİ İŞLEME FONKSİYONU ---
def process_data_to_dataframe(items):
    """
    Çekilen ham veriyi işleyerek temiz bir Pandas DataFrame'ine dönüştürür.
    """
    if not items:
        print("İşlenecek veri bulunamadı.")
        return pd.DataFrame()

    df = pd.json_normalize(items)

    required_cols = [
        'uid', 'title', 'types', 'sourceTypes', 'source.sourceTitle',
        'source.publishYear', 'source.volume', 'source.issue',
        'source.pages.range', 'names.authors', 'citations',
        'identifiers.doi', 'identifiers.issn', 'keywords.authorKeywords',
        'source_university'
    ]

    existing_cols = [col for col in required_cols if col in df.columns]
    df = df[existing_cols]

    def get_first_or_none(value):
        return value[0] if isinstance(value, list) and value else None

    for col in ['types', 'sourceTypes']:
        if col in df.columns:
            df[col] = df[col].apply(get_first_or_none)

    if 'keywords.authorKeywords' in df.columns:
        df['keywords.authorKeywords'] = df['keywords.authorKeywords'].apply(
            lambda x: ', '.join(x) if isinstance(x, list) and x else None
        )

    if 'names.authors' in df.columns:
        df = df.explode('names.authors').reset_index(drop=True)
        df['Author Display Name'] = df['names.authors'].apply(
            lambda x: x.get('displayName') if isinstance(x, dict) else None)
        df['Author WoS Standard'] = df['names.authors'].apply(
            lambda x: x.get('wosStandard') if isinstance(x, dict) else None)
        df['Author Researcher ID'] = df['names.authors'].apply(
            lambda x: x.get('researcherId') if isinstance(x, dict) else None)

    if 'citations' in df.columns:
        df['Citation DB'] = df['citations'].apply(lambda x: x[0].get('db') if isinstance(x, list) and x else None)
        df['Citation Count'] = df['citations'].apply(lambda x: x[0].get('count') if isinstance(x, list) and x else 0)

    df.rename(columns={
        'source_university': 'Üniversite Adı',
        'title': 'Başlık',
        'source.sourceTitle': 'Kaynak Başlığı',
        'source.publishYear': 'Yayın Yılı',
        'identifiers.doi': 'DOI',
        'keywords.authorKeywords': 'Yazar Anahtar Kelimeleri'
    }, inplace=True)

    cols_to_drop = ['names.authors', 'citations']
    df.drop(columns=[col for col in cols_to_drop if col in df.columns], inplace=True)

    return df


# --- ANA AKIŞ ---
if __name__ == "__main__":
    raw_data = fetch_all_data(universities)
    final_df = process_data_to_dataframe(raw_data)

    if not final_df.empty:
        print("\n--- İŞLENMİŞ VERİ ÖNİZLEMESİ ---")

        preview_cols = ['Üniversite Adı', 'Author Display Name', 'Başlık', 'Citation Count']
        existing_preview_cols = [col for col in preview_cols if col in final_df.columns]

        if existing_preview_cols:
            print(final_df[existing_preview_cols].head())
        else:
            print("Önizleme için gerekli sütunlar oluşturulamadı.")

        try:
            output_filename = "wos_tum_universiteler.xlsx"
            final_df.to_excel(output_filename, index=False)
            print(f"\n✅ Veriler başarıyla '{output_filename}' dosyasına aktarıldı.")
        except Exception as e:
            print(f"\n❌ Dosyaya yazma hatası: {e}")