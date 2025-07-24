from flask import Flask, jsonify, send_file
import asyncio
import os
import pandas as pd
import logging
from Atilim import main as fetch_Atilim_data

# Loglama
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Global cache
cached_data_df = None

# Plugin routes (OpenAPI + Manifest)
@app.route("/openapi.yaml")
def serve_openapi_spec():
    return send_file("openapi.yaml", mimetype="application/yaml")

@app.route("/.well-known/ai-plugin.json")
def serve_plugin_manifest():
    return send_file(".well-known/ai-plugin.json", mimetype="application/json")

@app.route('/atilim')
def get_atilim():
    global cached_data_df

    if cached_data_df is None or cached_data_df.empty:
        if "CLARIVATE_API_KEY" not in os.environ:
            return jsonify({"message": "API yapılandırma hatası: CLARIVATE_API_KEY ortam değişkeni ayarlanmadı."}), 500
        else:
            return jsonify({"message": "Veri henüz yüklenmedi veya yüklenemedi. Lütfen daha sonra tekrar deneyin."}), 503

    return jsonify(cached_data_df.to_dict(orient="records"))

# İlk veri yüklemesi
async def load_initial_data():
    global cached_data_df
    logging.info("📦 Veri yükleme başlatılıyor...")
    try:
        df = await fetch_Atilim_data()
        if df is not None and not df.empty:
            cached_data_df = df
            logging.info("✅ Veriler başarıyla yüklendi.")
        else:
            logging.warning("⚠️ Veri boş geldi.")
            cached_data_df = pd.DataFrame()
    except ValueError as ve:
        logging.error(f"❌ API anahtarı hatası: {ve}", exc_info=True)
        cached_data_df = pd.DataFrame()
    except Exception as e:
        logging.error(f"❌ Veri yükleme hatası: {e}", exc_info=True)
        cached_data_df = pd.DataFrame()

# Ana uygulama çalıştırma
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(load_initial_data())

    port = int(os.environ.get("PORT", 5000))
    logging.info(f"🚀 Flask uygulaması {port} portunda başlıyor...")
    app.run(host="0.0.0.0", port=port)

