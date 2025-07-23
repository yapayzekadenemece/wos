import requests
import pandas as pd
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://api.springernature.com/sushi/reports/tr_j1"
params = {
    "customer_id": "3000165697",
    "api_key": "UM7RRtJ2DFgDdLbyHHxB8FZZDJbPGxAm",
    "begin_date": "2024-01-01",
    "end_date": "2024-12-31"
}

response = requests.get(url, params=params, verify=False)

# JSON varsa dönüştür
try:
    data = response.json()
    df = pd.json_normalize(data)
    df.to_csv("springer_report.csv", index=False)
    print("CSV başarıyla yazıldı.")
except Exception as e:
    print("🔎 Status:", response.status_code)
    print("🔎 Headers:", response.headers)
    print("🔎 Content-Type:", response.headers.get("Content-Type", "yok"))
    print("🔎 İlk 500 karakter:\n", response.text[:500])
