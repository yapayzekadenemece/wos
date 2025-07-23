from flask import Flask, jsonify
import asyncio
import os
import pandas as pd # pandas'ı içe aktardığınızdan emin olun
from Atilim import main as fetch_Atilim_data # Atilim.py dosyan
import logging # Loglama için eklendi

# Temel loglama yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Global bir değişken, çekilen veriyi saklamak için
cached_data_df = None

async def load_initial_data():
    """Uygulama başladığında veriyi yüklemek için asenkron fonksiyon."""
    global cached_data_df
    logging.info("📦 Veri yükleme başlatılıyor...")
    try:
        # Atilim.py'deki main fonksiyonunu çağır
        df = await fetch_Atilim_data()
        if df is not None and not df.empty:
            cached_data_df = df
            logging.info("✅ Veriler başarıyla yüklendi ve önbelleğe alındı.")
        else:
            logging.warning("⚠️ İlk veri yüklemesi boş bir DataFrame ile sonuçlandı.")
            cached_data_df = pd.DataFrame() # Boşsa bile bir DataFrame nesnesi olsun
    except ValueError as ve: # Özellikle API anahtarı hatasını yakala
        logging.error(f"❌ Yapılandırma hatası: {ve}", exc_info=True)
        cached_data_df = pd.DataFrame() # Hata durumunda boş DataFrame döndür
    except Exception as e:
        logging.error(f"❌ İlk veri yüklenirken beklenmedik bir hata oluştu: {e}", exc_info=True)
        cached_data_df = pd.DataFrame() # Hata durumunda boş DataFrame döndür

@app.route('/atilim')
def get_atilim():
    # Eğer veri henüz yüklenmediyse veya boşsa, kullanıcıya bilgi ver
    if cached_data_df is None or cached_data_df.empty:
        # Veri yükleme hatası veya eksik yapılandırma nedeniyle servis kullanılamazsa 503
        if "CLARIVATE_API_KEY" not in os.environ:
             return jsonify({"message": "API yapılandırma hatası: CLARIVATE_API_KEY ortam değişkeni ayarlanmadı."}), 500
        else:
            return jsonify({"message": "Veri henüz yüklenmedi veya yüklenemedi. Lütfen daha sonra tekrar deneyin."}), 503

    # Doğrudan önbelleğe alınmış veriyi döndür
    return jsonify(cached_data_df.to_dict(orient="records"))

if __name__ == '__main__':
    # Uygulama başlamadan önce veriyi yükle
    loop = asyncio.get_event_loop()
    loop.run_until_complete(load_initial_data())

    port = int(os.environ.get("PORT", 5000))
    logging.info(f"Flask uygulaması {port} portunda başlatılıyor...")
    app.run(host="0.0.0.0", port=port)

    from flask import send_file


    @app.route("/openapi.yaml")
    def serve_openapi_spec():
        return send_file("openapi.yaml", mimetype="application/yaml")


    @app.route("/.well-known/ai-plugin.json")
    def serve_plugin_manifest():
        return send_file(".well-known/ai-plugin.json", mimetype="application/json")
