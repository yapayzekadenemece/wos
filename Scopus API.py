import requests
import csv
import time
import urllib3

# SSL uyarılarını kapat (isteğe bağlı)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API bilgileri
API_KEY = "7f59af901d2d86f78a1fd60c1bf9426a"
BASE_URL = "https://api.elsevier.com/content/search/scopus"
HEADERS = {"Accept": "application/json"}

# Sorgu parametreleri
QUERY = 'affil("Yasar University") AND PUBYEAR > 2005'
COUNT = 25
MAX_RESULTS = 1000  # En fazla kaç kayıt çekilecek (örnek olarak 1000)

# CSV dosyası başlat
output_file = "yasar_yayinlar.csv"
with open(output_file, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["Başlık", "Yazar", "Yıl", "Dergi", "DOI", "Scopus URL"])

    for start in range(0, MAX_RESULTS, COUNT):
        params = {
            "query": QUERY,
            "apiKey": API_KEY,
            "count": COUNT,
            "start": start
        }

        print(f"🔄 Kayıtlar alınıyor: {start} - {start + COUNT}")

        response = requests.get(BASE_URL, headers=HEADERS, params=params, verify=False)

        if response.status_code == 200:
            data = response.json()
            entries = data.get("search-results", {}).get("entry", [])

            if not entries:
                print("✅ Tüm kayıtlar çekildi.")
                break

            for entry in entries:
                title = entry.get("dc:title", "")
                author = entry.get("dc:creator", "")
                year = entry.get("prism:coverDate", "")
                journal = entry.get("prism:publicationName", "")
                doi = entry.get("prism:doi", "")
                url = entry.get("prism:url", "")
                writer.writerow([title, author, year, journal, doi, url])

        else:
            print(f"❌ Hata oluştu ({response.status_code}): {response.text}")
            break

        # Scopus API sınırlamaları nedeniyle küçük bir bekleme süresi (isteğe bağlı)
        time.sleep(1)

print(f"\n📁 Tüm kayıtlar '{output_file}' dosyasına yazıldı.")
