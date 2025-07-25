import os  # Ortam değişkeni için eklendi
from dotenv import load_dotenv  # .env dosyasını okumak için
import httpx
import asyncio
import math
import pandas as pd
from tqdm.asyncio import tqdm
import time  # Üstel geri çekilme için eklendi

# .env dosyasını yükle
load_dotenv()

# API bilgileri
BASE_URL = "https://api.clarivate.com/apis/wos-starter/v1/documents"
API_KEY = os.environ.get("CLARIVATE_API_KEY")  # Artık API anahtarı ortam değişkeninden alınacak

# Eğer API_KEY bulunamazsa programı durdur
if API_KEY is None:
    raise ValueError("❌ Ortam değişkeni 'CLARIVATE_API_KEY' bulunamadı veya boş!")

HEADERS = {"X-ApiKey": API_KEY}
QUERY_PARAMS = {
    "db": "WOS",
    "q": 'OG="Atilim University" AND FPY=1900-2030',
    "limit": 50
}

async def fetch_page(client, page, total_pages, max_retries=5, base_delay=1):
    """
    Belirli bir sayfayı asenkron olarak çeker ve hız sınırlaması için yeniden deneme yapar.
    """
    for attempt in range(max_retries):
        print(f"Sayfa {page}/{total_pages} çekiliyor (Deneme {attempt + 1}/{max_retries})")
        try:
            resp = await client.get(BASE_URL, headers=HEADERS, params={**QUERY_PARAMS, "page": page})
            resp.raise_for_status()  # HTTP hatalarını (4xx veya 5xx) yakala
            return resp.json().get("hits", [])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                delay = min(base_delay * (2 ** attempt), 60)  # Maksimum 60 saniye beklesin
                print(f"🚫 Hata! Sayfa {page} için API limitine ulaşıldı (429). {delay:.2f} saniye bekleniyor...")
                await asyncio.sleep(delay)
                continue  # İsteği yeniden dene
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


async def main():
    """Tüm verileri çekmek için ana asenkron fonksiyon."""
    all_items = []

    async with httpx.AsyncClient() as client:
        # Adım 1: Toplam kayıt sayısını doğru bir şekilde hesaplamak için ilk sayfadan meta verileri al
        try:
            initial_metadata_response = await client.get(BASE_URL, headers=HEADERS, params={**QUERY_PARAMS, "page": 1})
            initial_metadata_response.raise_for_status()
            initial_data = initial_metadata_response.json()
            total_records = initial_data.get("metadata", {}).get("total", 0)
            records_per_page = initial_data.get("metadata", {}).get("limit", 50)
            total_pages = max(1, math.ceil(total_records / records_per_page))
            print(f"Toplam kayıt: {total_records}, Sayfa başına kayıt: {records_per_page}, Toplam sayfa: {total_pages}")
        except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as e:
            print(f"İlk sayfa veya meta veri alınırken hata oluştu: {e}")
            return pd.DataFrame()  # Hata varsa boş DataFrame döndür

        # Tüm sayfalar için görevleri oluştur
        pages_to_fetch = list(range(1, total_pages + 1))

        from tqdm import tqdm

        tasks = [fetch_page(client, page, total_pages, max_retries=100) for page in pages_to_fetch]

        results = []
        for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Sayfalar çekiliyor"):
            try:
                result = await coro
                if result:
                    results.append(result)
            except Exception as e:
                print(f"❌ Hata oluştu: {e}")

        for page_data in results:
            if page_data:
                all_items.extend(page_data)

    # Veri işleme mantığınızın geri kalanı aynı kalır
    df = pd.json_normalize(all_items)

    columns_to_extract = [
        'uid', 'title', 'types', 'sourceTypes', 'source.sourceTitle', 'source.publishYear',
        'source.volume', 'source.issue', 'source.pages.range', 'names.authors',
        'citations', 'identifiers.doi', 'identifiers.issn', 'keywords.authorKeywords'
    ]
    # Sütunları güvenli bir şekilde filtrele, bir sütunun eksik olabileceği durumları ele al
    existing_columns = [col for col in columns_to_extract if col in df.columns]
    df = df[existing_columns]

    def extract_first_list_item(value):
        if isinstance(value, list) and len(value) > 0:
            return value[0]
        return None

    # Liste olması beklenen sütunlara uygula
    for col in ['types', 'sourceTypes', 'keywords.authorKeywords']:
        if col in df.columns:  # Sütunun var olup olmadığını kontrol et
            df[col] = df[col].apply(extract_first_list_item)

    # Yazarları metin olarak birleştir ve gerekli sütunları oluştur
    if 'names.authors' in df.columns:
        df['Author Researcher ID'] = df['names.authors'].apply(
            lambda authors: ', '.join(
                a.get('researcherId', '')
                for a in authors if isinstance(a, dict) and 'researcherId' in a
            ) if isinstance(authors, list) else None
        )
        # 'displayName' alanı varsa 'Author Display Name' olarak kullan
        df['Author Display Name'] = df['names.authors'].apply(
            lambda authors: ', '.join(
                a.get('displayName', '')
                for a in authors if isinstance(a, dict) and 'displayName' in a
            ) if isinstance(authors, list) else None
        )
        # 'wosStd' alanı varsa 'Author WoS Standard' olarak kullan
        df['Author WoS Standard'] = df['names.authors'].apply(
            lambda authors: ', '.join(
                a.get('wosStd', '')
                for a in authors if isinstance(a, dict) and 'wosStd' in a
            ) if isinstance(authors, list) else None
        )
        # Author Name and Surname için en uygun olanı kullan (örn. displayName)
        df['Author Name and Surname'] = df['Author Display Name']
    else:
        # Eğer names.authors sütunu yoksa, ilgili sütunları None olarak ayarla
        df['Author Researcher ID'] = None
        df['Author Display Name'] = None
        df['Author WoS Standard'] = None
        df['Author Name and Surname'] = None

    # Atıf detaylarını çıkar
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

    df['Üniversite Adı'] = "Atilim"

    return df

if __name__ == "__main__":
    # Gerekli tüm kütüphanelerin yüklü olduğundan emin olun:
    # pip install httpx asyncio tqdm pandas openpyxl
    print("Veri çekme başlatılıyor...")
    final_df = asyncio.run(main())

    if not final_df.empty:
        print("\n--- Çekilen Veri Örneği ---")
        print(final_df.head())
        file_name = "Atilim_university_17.07.2025.xlsx"
        final_df.to_excel(file_name, index=False)
        print(f"\n✅ Veriler başarıyla '{file_name}' dosyasına kaydedildi.")
    else:
        print("\nℹ️ Veri çekilemedi veya boş DataFrame oluştu. Lütfen logları kontrol edin.")

