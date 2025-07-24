import os
from dotenv import load_dotenv
import httpx
import asyncio
import math
import pandas as pd
from tqdm.asyncio import tqdm
import time
from datetime import datetime

# .env dosyasını yükle (yerelde çalışırken)
load_dotenv()

# API bilgileri
BASE_URL = "https://api.clarivate.com/apis/wos-starter/v1/documents"
API_KEY = os.environ.get("CLARIVATE_API_KEY")

if API_KEY is None:
    raise ValueError("❌ Ortam değişkeni 'CLARIVATE_API_KEY' bulunamadı veya boş!")

HEADERS = {"X-ApiKey": API_KEY}


async def fetch_page(client, query_params, page, total_pages, max_retries=5, base_delay=1):
    for attempt in range(max_retries):
        try:
            resp = await client.get(BASE_URL, headers=HEADERS, params={**query_params, "page": page})
            resp.raise_for_status()
            return resp.json().get("hits", [])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                delay = min(base_delay * (2 ** attempt), 60)
                print(f"🚫 Hata! Sayfa {page} için API limitine ulaşıldı (429). {delay:.2f} saniye bekleniyor...")
                await asyncio.sleep(delay)
                continue
            else:
                print(f"🚫 Hata! Sayfa {page} alınamadı. Durum kodu: {e.response.status_code}")
                print(f"Yanıt içeriği:\n{e.response.text}")
                return None
        except httpx.RequestError as e:
            print(f"❌ Sayfa {page} için istek hatası: {e}")
            return None
        except ValueError:
            print(f"❌ Sayfa {page} için JSON çözme hatası. Yanıt metni:\n{resp.text}")
            return None
    print(f"⚠️ Sayfa {page}, {max_retries} denemeden sonra hala alınamadı. Atlanıyor.")
    return None


async def main(university_name: str):  # university_name artık zorunlu bir parametre
    all_items = []

    current_query_params = {
        "db": "WOS",
        "q": f'OG="{university_name}" AND FPY=1900-2030',
        "limit": 50
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            initial_metadata_response = await client.get(BASE_URL, headers=HEADERS,
                                                         params={**current_query_params, "page": 1})
            initial_metadata_response.raise_for_status()
            initial_data = initial_metadata_response.json()
            total_records = initial_data.get("metadata", {}).get("total", 0)
            records_per_page = initial_data.get("metadata", {}).get("limit", 50)
            total_pages = max(1, math.ceil(total_records / records_per_page))
            print(
                f"Üniversite: {university_name}, Toplam kayıt: {total_records}, Sayfa başına kayıt: {records_per_page}, Toplam sayfa: {total_pages}")
        except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as e:
            print(f"İlk sayfa veya meta veri alınırken hata oluştu: {e}")
            return pd.DataFrame()

        pages_to_fetch = list(range(1, total_pages + 1))
        tasks = [fetch_page(client, current_query_params, page, total_pages, max_retries=10) for page in pages_to_fetch]

        results = []
        for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks),
                         desc=f"{university_name} için sayfalar çekiliyor"):
            try:
                result = await coro
                if result:
                    results.append(result)
            except Exception as e:
                print(f"❌ Sayfa çekme görevi sırasında hata oluştu: {e}")

        for page_data in results:
            if page_data:
                all_items.extend(page_data)

    df = pd.json_normalize(all_items)

    if df.empty:
        print(f"Çekilen veri boş. Boş DataFrame döndürülüyor. Üniversite: {university_name}")
        return pd.DataFrame()

    columns_to_extract = [
        'uid', 'title', 'types', 'sourceTypes', 'source.sourceTitle', 'source.publishYear',
        'source.volume', 'source.issue', 'source.pages.range', 'names.authors',
        'citations', 'identifiers.doi', 'identifiers.issn', 'keywords.authorKeywords'
    ]

    existing_columns = [col for col in columns_to_extract if col in df.columns]
    df = df[existing_columns]

    def extract_first_list_item(value):
        if isinstance(value, list) and len(value) > 0:
            return value[0]
        return None

    def join_list_items_or_nan(value):
        if isinstance(value, list) and value:
            return ', '.join(map(str, value))
        return None

    for col in ['types', 'sourceTypes']:
        if col in df.columns:
            df[col] = df[col].apply(extract_first_list_item)

    if 'keywords.authorKeywords' in df.columns:
        df['keywords.authorKeywords'] = df['keywords.authorKeywords'].apply(join_list_items_or_nan)

    if 'names.authors' in df.columns:
        df['Author Researcher ID'] = df['names.authors'].apply(
            lambda authors: ', '.join(
                a.get('researcherId', '')
                for a in authors if isinstance(a, dict) and 'researcherId' in a
            ) if isinstance(authors, list) else None
        )
        df['Author Display Name'] = df['names.authors'].apply(
            lambda authors: ', '.join(
                a.get('displayName', '')
                for a in authors if isinstance(a, dict) and 'displayName' in a
            ) if isinstance(authors, list) else None
        )
        df['Author WoS Standard'] = df['names.authors'].apply(
            lambda authors: ', '.join(
                a.get('wosStd', '')
                for a in authors if isinstance(a, dict) and 'wosStd' in a
            ) if isinstance(authors, list) else None
        )
        df['Author Name and Surname'] = df.apply(
            lambda row: row['Author Display Name'] if pd.notna(row['Author Display Name']) and row[
                'Author Display Name'] else row['Author WoS Standard'],
            axis=1
        )
    else:
        df['Author Researcher ID'] = None
        df['Author Display Name'] = None
        df['Author WoS Standard'] = None
        df['Author Name and Surname'] = None

    if 'citations' in df.columns:
        df['Citation DB'] = df['citations'].apply(
            lambda x: x[0].get('db') if isinstance(x, list) and len(x) > 0 else None
        )
        df['Citation Count'] = df['citations'].apply(
            lambda x: x[0].get('count') if isinstance(x, list) and len(x) > 0 and 'count' in x[0] else 0
        )
    else:
        df['Citation DB'] = None
        df['Citation Count'] = 0

    df['Üniversite Adı'] = university_name

    df = df.drop(columns=['names.authors', 'citations'], errors='ignore')

    df = df.rename(columns={
        'source.sourceTitle': 'Kaynak Başlığı',
        'source.publishYear': 'Yayın Yılı',
        'source.volume': 'Cilt',
        'source.issue': 'Sayı',
        'source.pages.range': 'Sayfa Aralığı',
        'identifiers.doi': 'DOI',
        'identifiers.issn': 'ISSN',
        'keywords.authorKeywords': 'Yazar Anahtar Kelimeleri',
        'types': 'Belge Türü',
        'sourceTypes': 'Kaynak Türü',
        'uid': 'UID',
        'title': 'Başlık'
    })

    return df


if __name__ == "__main__":
    # Yeni üniversite listeniz
    SUPPORTED_UNIVERSITIES = [
        "Reichman University",
        "Sabanci University",
        "TOBB Ekonomi ve Teknoloji University",
        "University of Navarra",
        "Universitat Internacional de Catalunya (UIC)",
        "Ozyegin University",
        "Kadir Has University",
        "Izmir Ekonomi Universitesi",
        "Jacobs University",
        "Ihsan Dogramaci Bilkent University",
        "Bahcesehir University"
    ]

    print("Veri çekme başlatılıyor...")

    all_universities_data = []
    for uni in SUPPORTED_UNIVERSITIES:
        df_uni = asyncio.run(main(university_name=uni))
        if not df_uni.empty:
            all_universities_data.append(df_uni)
        else:
            print(f"⚠️ '{uni}' için veri çekilemedi.")

    if all_universities_data:
        combined_df = pd.concat(all_universities_data, ignore_index=True)
        print("\n--- Tüm Çekilen Verilerin Birleşimi (Örnek) ---")
        print(combined_df.head())
        current_date = datetime.now().strftime("%d.%m.%Y")
        file_name = f"All_Universities_Publications_{current_date}.xlsx"
        # combined_df.to_excel(file_name, index=False)
        print(f"\n✅ Tüm üniversitelerden veriler başarıyla çekildi.")
    else:
        print("\nℹ️ Hiçbir üniversite için veri çekilemedi. Lütfen logları kontrol edin.")