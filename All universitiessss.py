import requests
import math
import pandas as pd
from time import sleep

# API bilgileri
BASE_URL = "https://api.clarivate.com/apis/wos-starter/v1/documents"
API_KEY = "2911c678b48cde2e576cc471cac3d27759f5328d"
HEADERS = {"X-ApiKey": API_KEY}

# Üniversite listesi: "OG" alanında kullanılacak şekilde
universities = [
    {"og_query": "Reichman University", "name": "Reichman University"},
    {"og_query": "Sabanci University", "name": "Sabancı University"},
    {"og_query": "TOBB Ekonomi ve Teknoloji University", "name": "TOBB Ekonomi ve Teknoloji Üniversitesi"},
    {"og_query": "University of Navarra", "name": "University of Navarra"},
    {"og_query": "Universitat Internacional de Catalunya (UIC)", "name": "Universitat Internacional de Catalunya (UIC)"},
    {"og_query": "Ozyegin University", "name": "Özyeğin University"},
    {"og_query": "Kadir Has University", "name": "Kadir Has University"},
    {"og_query": "Izmir Ekonomi Universitesi", "name": "İzmir Ekonomi Üniversitesi"},
    {"og_query": "Jacobs University", "name": "Jacobs University"},
    {"og_query": "Ihsan Dogramaci Bilkent University", "name": "İhsan Doğramacı Bilkent University"},
    {"og_query": "Bahcesehir University", "name": "Bahçeşehir University"},
    {"og_query": "Atilim University", "name": "Atılım University"},
    {"og_query": "Koc University", "name": "Koç University"},
    {"og_query": "Universitat Ramon Llull", "name": "Universitat Ramon Llull"},
    {"og_query": "Yasar University", "name": "Yaşar Üniversitesi"},
    {"og_query": "Dogus University", "name": "Doğuş University"},
    {"og_query": "Ted University", "name": "TED University"},
    {"og_query": "Ege University", "name": "Ege Üniversitesi"},
    {"og_query": "Dokuz Eylul University", "name": "Dokuz Eylül Üniversitesi"}
]

# Sorgu dönemi ve sonuç limiti
YEAR_RANGE = "1900-2030"
RECORD_LIMIT = 50

# Tüm verileri birleştirmek için
all_universities_data = []

for uni in universities:
    print(f"\nFetching records for {uni['name']}")

    QUERY_PARAMS = {
        "db": "WOS",
        "q": f'OG="{uni["og_query"]}" AND FPY={YEAR_RANGE}',
        "limit": RECORD_LIMIT,
        "page": 1
    }

    # İlk sayfayı çek
    response = requests.get(BASE_URL, headers=HEADERS, params=QUERY_PARAMS)
    data = response.json()

    total_records = data.get("metadata", {}).get("total", 0)
    records_per_page = data.get("metadata", {}).get("limit", RECORD_LIMIT)
    total_pages = max(1, math.ceil(total_records / records_per_page))

    print(f"Total records: {total_records} | Total pages: {total_pages}")

    university_items = []

    for page in range(1, total_pages + 1):
        print(f"  > Fetching page {page}")
        QUERY_PARAMS["page"] = page
        resp = requests.get(BASE_URL, headers=HEADERS, params=QUERY_PARAMS)
        page_data = resp.json().get("hits", [])
        university_items.extend(page_data)
        sleep(1)  # API'den banlanmamak için küçük bekleme

    # JSON verisini DataFrame'e dönüştür
    df = pd.json_normalize(university_items)

    # Gerekli sütunları ayıkla
    columns_to_extract = [
        'uid', 'title', 'types', 'sourceTypes', 'source.sourceTitle', 'source.publishYear',
        'source.volume', 'source.issue', 'source.pages.range', 'names.authors',
        'citations', 'identifiers.doi', 'identifiers.issn', 'keywords.authorKeywords'
    ]
    df = df[[col for col in columns_to_extract if col in df.columns]]  # Eksik kolon varsa sorun çıkmasın

    # Yazar adlarını düzleştir
    if 'names.authors' in df.columns:
        df = df.explode('names.authors')
        df['Author Name and Surname'] = df['names.authors'].apply(
            lambda x: x.get('displayName') if isinstance(x, dict) else None
        )

    # Atıf sayısı
    df['Citation Count'] = df['citations'].apply(
        lambda x: x[0]['count'] if isinstance(x, list) and len(x) > 0 and 'count' in x[0] else None
    ) if 'citations' in df.columns else None

    # Üniversite Adı sabit sütun
    df['Üniversite Adı'] = uni['name']

    all_universities_data.append(df)

# Tüm üniversiteleri birleştir
final_df = pd.concat(all_universities_data, ignore_index=True)

# İsteğe bağlı: Excel'e yaz
# final_df.to_excel("tum_universiteler_wos_output.xlsx", index=False)

print("\nTOPLAM KAYIT SAYISI:", len(final_df))
print(final_df.head())
