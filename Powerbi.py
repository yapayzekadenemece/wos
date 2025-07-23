import requests
import math
import pandas as pd

# API bilgileri
BASE_URL = "https://api.clarivate.com/apis/wos-starter/v1/documents"
API_KEY = "2911c678b48cde2e576cc471cac3d27759f5328d"
HEADERS = {"X-ApiKey": API_KEY}
QUERY_PARAMS = {
    "db": "WOS",
    "q": 'OG="Yasar University" AND FPY=1900-2030',
    "limit": 50
}

# İlk sayfayı çek
response = requests.get(BASE_URL, headers=HEADERS, params={**QUERY_PARAMS, "page": 1})
data = response.json()

# Sayfa bilgileri
total_records = data.get("metadata", {}).get("total", 0)
records_per_page = data.get("metadata", {}).get("limit", 50)
total_pages = max(1, math.ceil(total_records / records_per_page))

# Sayfaları döngüyle çek
all_items = []
for page in range(1, total_pages + 1):
    print(f"Fetching page {page} of {total_pages}")
    resp = requests.get(BASE_URL, headers=HEADERS, params={**QUERY_PARAMS, "page": page})
    page_data = resp.json().get("hits", [])
    all_items.extend(page_data)

# Ana veri tablosunu oluştur
df = pd.json_normalize(all_items)

# Gerekli sütunları seç
columns_to_extract = [
    'uid', 'title', 'types', 'sourceTypes', 'source.sourceTitle', 'source.publishYear',
    'source.volume', 'source.issue', 'source.pages.range', 'names.authors',
    'citations', 'identifiers.doi', 'identifiers.issn', 'keywords.authorKeywords'
]
df = df[columns_to_extract]

# Yazar adlarını düzleştir (isteğe bağlı)
df = df.explode('names.authors')
df['Author Name and Surname'] = df['names.authors'].apply(lambda x: x.get('displayName') if isinstance(x, dict) else None)

# Atıf sayısını çek (ilk citation kaydından)
df['Citation Count'] = df['citations'].apply(
    lambda x: x[0]['count'] if isinstance(x, list) and len(x) > 0 and 'count' in x[0] else None
)

# Sabit "Üniversite Adı" sütunu ekle
df['Üniversite Adı'] = "Yasar"

# İsteğe bağlı: Excel/CSV’ye aktar
# df.to_excel("yasar_university_wos_output.xlsx", index=False)

print(df.head())
