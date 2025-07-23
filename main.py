import pandas as pd
import requests
import time

# 🔐 API anahtarınız
API_KEY = "952d3886777f669ddf805045b5224e25"

# 📂 Excel dosyasını oku
df = pd.read_excel("C:\\Users\\ece.helvacioglu\\Desktop\\tr_j1_2024-01_2024-05.xlsx")
df.columns = df.columns.str.strip()  # Sütun adlarını temizle

# 🎯 Scopus API'den dergi adına göre konu başlığı getiren fonksiyon
def fetch_subject_area_by_title(title):
    url = f"https://api.elsevier.com/content/serial/title?title={title}"
    headers = {
        "X-ELS-APIKey": API_KEY,
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            entries = data.get("serial-metadata-response", {}).get("entry", [])
            if entries:
                subjects = entries[0].get("subject-area", [])
                if subjects:
                    return ", ".join(sorted(set(area.get("$") for area in subjects if area.get("$"))))
                else:
                    return "Konu bulunamadı"
            else:
                return "Dergi bulunamadı"
        else:
            return f"Hata: {response.status_code}"
    except Exception as e:
        return f"İstek hatası: {e}"

# 🔁 Her başlık için konuyu çek
df["Subject"] = df["Title"].apply(fetch_subject_area_by_title)
    # → Eğer bu işlem uzun sürerse, `time.sleep(1)` ekleyebilirsin

# 💾 Sonuçları CSV'ye yaz
df.to_csv("journals_with_subjects_by_title.csv", index=False, encoding="utf-8-sig")
print("✅ Konular eklendi ve dosya kaydedildi: journals_with_subjects_by_title.csv")
