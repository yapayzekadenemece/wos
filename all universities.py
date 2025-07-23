import requests
import math
import pandas as pd

# Web of Science API ayarları
BASE_URL = "https://api.clarivate.com/apis/wos-starter/v1/documents"
API_KEY = "2911c678b48cde2e576cc471cac3d27759f5328d"
HEADERS = {"X-ApiKey": API_KEY}

# Üniversite listesi
universities = {
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
    "Bahcesehir University",
    "Atilim University",
    "Koc University",
    "Universitat Ramon Llull",
    "Yasar University"
}

# Tüm verileri birleştirmek için liste
all_items = []

# Her üniversite için veri çek
for uni in universities:
    print(f"\n⏳ Fetching data for: {uni}")
    query = f'OG="{uni}" AND FPY=1900-2030'
    params = {"db": "WOS", "q": query, "limit": 50, "page": 1}
    response = requests.get(BASE_URL, headers=HEADERS, params=params)
    data = response.json()

    total_records = data.get("metadata", {}).get("total", 0)
    per_page = data.get("metadata", {}).get("limit", 50)
    total_pages = max(1, math.ceil(total_records / per_page))

    for page in range(1, total_pages + 1):
        print(f"📄 Page {page}/{total_pages}")
        params["page"] = page
        resp = requests.get(BASE_URL, headers=HEADERS, params=params)
        page_data = resp.json().get("hits", [])
        for item in page_data:
            item["source_university"] = uni
        all_items.extend(page_data)

# DataFrame oluştur
df = pd.json_normalize(all_items)

# Gerekli sütunlar
df = df[[
    'uid', 'title', 'types', 'sourceTypes', 'source.sourceTitle', 'source.publishYear',
    'source.volume', 'source.issue', 'source.pages.range',
    'names.authors', 'citations', 'identifiers.doi', 'identifiers.issn',
    'keywords.authorKeywords', 'source_university'
]]

# Tekil değer almak için liste olan bazı sütunları sadeleştir
def get_first(value):
    if isinstance(value, list) and len(value) > 0:
        return value[0]
    return None

for col in ['types', 'sourceTypes', 'keywords.authorKeywords']:
    df[col] = df[col].apply(get_first)

# Yazarları satıra aç
df = df.explode('names.authors')

# Yazar bilgilerini ayır
df['Author Display Name'] = df['names.authors'].apply(lambda x: x.get('displayName') if isinstance(x, dict) else None)
df['Author WoS Standard'] = df['names.authors'].apply(lambda x: x.get('wosStandard') if isinstance(x, dict) else None)
df['Author Researcher ID'] = df['names.authors'].apply(lambda x: x.get('researcherId') if isinstance(x, dict) else None)

# Atıf bilgilerini ayır
df['Citation DB'] = df['citations'].apply(lambda x: x[0].get('db') if isinstance(x, list) and len(x) > 0 else None)
df['Citation Count'] = df['citations'].apply(lambda x: x[0].get('count') if isinstance(x, list) and len(x) > 0 else 0)

# Üniversite adını yaz
df.rename(columns={'source_university': 'Üniversite Adı'}, inplace=True)

# Gereksiz sütunları çıkar
df.drop(columns=['names.authors', 'citations'], inplace=True)

# 🟢 Örnek çıktı
print(df[['Üniversite Adı', 'Author Display Name', 'title', 'Citation Count']].head())

# 💾 Dışa aktarmak istersen:
# df.to_excel("wos_tum_universiteler.xlsx", index=False)
df.to_json("wos_tum_universiteler.json", orient="records", indent=2, force_ascii=False)
