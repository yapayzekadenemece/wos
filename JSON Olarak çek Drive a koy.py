import requests
import math
import pandas as pd
import json

# API bilgileri
BASE_URL = "https://api.clarivate.com/apis/wos-starter/v1/documents"
API_KEY = "2911c678b48cde2e576cc471cac3d27759f5328d"
HEADERS = {"X-ApiKey": API_KEY}
QUERY_PARAMS = {
    "db": "WOS",
    "q": 'OG="Yasar University" AND FPY=1900-2030',
    "limit": 50
}

# İlk sayfayı al
response = requests.get(BASE_URL, headers=HEADERS, params={**QUERY_PARAMS, "page": 1})
data = response.json()

# Sayfa bilgileri
total_records = data.get("metadata", {}).get("total", 0)
records_per_page = data.get("metadata", {}).get("limit", 50)
total_pages = max(1, math.ceil(total_records / records_per_page))

# Tüm sayfalardaki verileri topla
all_items = []
for page in range(1, total_pages + 1):
    print(f"Fetching page {page} of {total_pages}")
    resp = requests.get(BASE_URL, headers=HEADERS, params={**QUERY_PARAMS, "page": page})
    page_data = resp.json().get("hits", [])
    all_items.extend(page_data)

# Veri tablosu oluştur
df = pd.json_normalize(all_items)

# Kullanılacak sütunlar
columns_to_extract = [
    'uid', 'title', 'types', 'sourceTypes', 'source.sourceTitle', 'source.publishYear',
    'source.volume', 'source.issue', 'source.pages.range', 'names.authors',
    'citations', 'identifiers.doi', 'identifiers.issn', 'keywords.authorKeywords'
]
df = df[columns_to_extract]

def extract_first_list_item(value):
    if isinstance(value, list) and len(value) > 0:
        return value[0]
    return None

for col in ['types', 'sourceTypes', 'keywords.authorKeywords']:
    df[col] = df[col].apply(extract_first_list_item)

# Yazarları satıra aç
df = df.explode('names.authors')

# names.authors içindeki dict'i sütunlara ayır
df['Author Display Name'] = df['names.authors'].apply(
    lambda x: x.get('displayName') if isinstance(x, dict) else None
)
df['Author WoS Standard'] = df['names.authors'].apply(
    lambda x: x.get('wosStandard') if isinstance(x, dict) else None
)
df['Author Researcher ID'] = df['names.authors'].apply(
    lambda x: x.get('researcherId') if isinstance(x, dict) else None
)

# citations içindeki ilk dict'i ayır
df['Citation DB'] = df['citations'].apply(
    lambda x: x[0].get('db') if isinstance(x, list) and len(x) > 0 else None
)
df['Citation Count'] = df['citations'].apply(
    lambda x: x[0].get('count') if isinstance(x, list) and len(x) > 0 else 0
)

# Yazar adları
df = df.explode('names.authors')
df['Author Name and Surname'] = df['names.authors'].apply(
    lambda x: x.get('displayName') if isinstance(x, dict) else None
)

# Atıf sayısı
df['Citation Count'] = df['citations'].apply(
    lambda x: x[0]['count'] if isinstance(x, list) and len(x) > 0 and 'count' in x[0] else 0
)

# Sabit Üniversite sütunu
df['Üniversite Adı'] = "Yasar"

# ✅ JSON dosyasına kayıt
df.drop(columns=["names.authors", "citations"], inplace=True)
df.to_json("yasar_wos.json", orient="records", force_ascii=False, indent=2)

# Ekrana örnek satırlar yazdır
print(df.head())
