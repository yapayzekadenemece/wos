import pandas as pd
import requests
import time

# Scopus API bilgisi
SCOPUS_API_KEY = "952d3886777f669ddf805045b5224e25"
DOAJ_BASE_URL = "https://doaj.org/api/v2/search/journals/"
CROSSREF_BASE_URL = "https://api.crossref.org/journals"

# Excel dosyasını oku
df = pd.read_excel("C:/Users/ece.helvacioglu/Desktop/tr_j1_2024-01_2024-05.xlsx")
df.columns = df.columns.str.strip()  # Sütun adlarını temizle

def fetch_from_scopus(title):
    url = f"https://api.elsevier.com/content/serial/title?title={title}"
    headers = {
        "X-ELS-APIKey": SCOPUS_API_KEY,
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            entries = data.get("serial-metadata-response", {}).get("entry", [])
            if entries:
                subjects = entries[0].get("subject-area", [])
                if subjects:
                    return ", ".join(sorted(set(area.get("$") for area in subjects if area.get("$"))))
    except:
        return None
    return None

def fetch_from_doaj(title):
    try:
        response = requests.get(f"{DOAJ_BASE_URL}title:{title}", timeout=15)
        if response.status_code == 200:
            data = response.json()
            if "results" in data and data["results"]:
                subjects = data["results"][0]["bibjson"].get("keywords", [])
                if subjects:
                    return ", ".join(subjects)
    except:
        return None
    return None

def fetch_from_crossref(title):
    try:
        response = requests.get(f"{CROSSREF_BASE_URL}?query={title}", timeout=15)
        if response.status_code == 200:
            data = response.json()
            items = data.get("message", {}).get("items", [])
            if items:
                subject = items[0].get("subjects", [])
                if subject:
                    return ", ".join(subject)
    except:
        return None
    return None

# Birleşik konu başlığı çekme fonksiyonu
def get_subject(title):
    for fetcher in [fetch_from_scopus, fetch_from_doaj, fetch_from_crossref]:
        result = fetcher(title)
        if result:
            return result
        time.sleep(1)  # API'lere yüklenmemek için bekleme
    return "Konu bulunamadı"

# Tüm başlıklar için uygula
df["Subject"] = df["Title"].apply(get_subject)

# Sonucu dışa aktar
import ace_tools as tools; tools.display_dataframe_to_user(name="Tamamlanmış Dergi Konuları", dataframe=df)
