from flask import Flask, jsonify
import asyncio
from Atilim import main as fetch_Atilim_data  # Atilim.py dosyan

app = Flask(__name__)


@app.route('/atilim')
def get_atilim():
    try:
        df = asyncio.run(fetch_Atilim_data())

        # 📭 Eğer veri çekilemediyse veya boşsa kullanıcıya bilgi ver
        if df is None or df.empty:
            return jsonify({"message": "Veri çerçevesi boş veya çekilemedi."})

        # 🧠 Eğer 'Author Display Name' sütunu eksikse, names.authors üzerinden oluştur
        if 'Author Display Name' not in df.columns and 'names.authors' in df.columns:
            df['Author Display Name'] = df['names.authors'].apply(
                lambda authors: ', '.join(
                    a.get('displayName', '') for a in authors
                    if isinstance(a, dict) and 'displayName' in a
                ) if isinstance(authors, list) else None
            )

        # 🏷 'Author Name and Surname' oluşturuluyor (varsa 'Author Display Name' kullan)
        if 'Author Display Name' in df.columns:
            df['Author Name and Surname'] = df['Author Display Name']
        else:
            df['Author Name and Surname'] = None

        # JSON olarak döndür
        return jsonify(df.to_dict(orient="records"))

    except Exception as e:
        return jsonify({"error": str(e)}), 500


import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)