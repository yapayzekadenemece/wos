import requests
import pandas as pd
import urllib3

# Uyarıyı kapat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API bilgileri
url = "https://api.springernature.com/sushi/reports/tr_j1"
params = {
    "customer_id": "3000165697",
    "api_key": "07dddba01274472787890be0405090b8",
    "begin_date": "2024-01-01",
    "end_date": "2024-12-31"
}

# Sertifika doğrulamasını kapat (test ortamı için uygundur)
response = requests.get(url, params=params, verify=False)

print("🔎 Yanıt durumu:", response.status_code)
print("🔎 Yanıt içeriği:")
print(response.text)
