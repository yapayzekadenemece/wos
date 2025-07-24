from flask import Flask, jsonify, send_file, request
import asyncio
import os
import pandas as pd
import logging
from Atilim import main as fetch_university_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

cached_data_by_university = {}

# Yeni üniversite listeniz
SUPPORTED_UNIVERSITIES = [
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
    "Bahcesehir University"
]


@app.route("/openapi.yaml")
def serve_openapi_spec():
    # Bu dosyanın içeriği, aşağıdaki güncellenmiş YAML'den gelmeli.
    return send_file("openapi.yaml", mimetype="application/yaml")


@app.route("/.well-known/ai-plugin.json")
def serve_plugin_manifest():
    # Bu dosyanın içeriği, aşağıdaki güncellenmiş JSON'dan gelmeli.
    return send_file(".well-known/ai-plugin.json", mimetype="application/json")


@app.route('/universities')
def get_universities():
    return jsonify({"universities": SUPPORTED_UNIVERSITIES})


@app.route('/publications')
def get_publications():
    university_name = request.args.get('university')
    year = request.args.get('year', type=int)
    author_name = request.args.get('author')
    limit = request.args.get('limit', type=int, default=50)

    if not university_name:
        return jsonify({"message": "Lütfen 'university' parametresini belirtin."}), 400

    if university_name not in SUPPORTED_UNIVERSITIES:
        return jsonify({
                           "message": f"'{university_name}' desteklenen bir üniversite değildir. Desteklenen üniversiteler için /universities adresini kontrol edin."}), 400

    df = cached_data_by_university.get(university_name)

    if df is None or df.empty:
        if "CLARIVATE_API_KEY" not in os.environ:
            return jsonify({"message": "API yapılandırma hatası: CLARIVATE_API_KEY ortam değişkeni ayarlanmadı."}), 500
        else:
            return jsonify({
                               "message": f"'{university_name}' için veri henüz yüklenmedi veya yüklenemedi. Lütfen daha sonra tekrar deneyin."}), 503

    filtered_df = df.copy()

    if year:
        filtered_df = filtered_df[filtered_df['Yayın Yılı'] == year]

    if author_name:
        filtered_df = filtered_df[
            (filtered_df['Author Name and Surname'].astype(str).str.contains(author_name, case=False, na=False)) |
            (filtered_df['Author Display Name'].astype(str).str.contains(author_name, case=False, na=False))
            ]

    if limit and limit > 0:
        filtered_df = filtered_df.head(limit)

    if filtered_df.empty:
        return jsonify({"message": f"'{university_name}' için belirtilen kriterlere göre yayın bulunamadı."}), 200

    response_columns = [
        'Başlık', 'Yayın Yılı', 'Author Name and Surname', 'Kaynak Başlığı',
        'Citation Count', 'DOI', 'Yazar Anahtar Kelimeleri', 'Üniversite Adı'
    ]
    response_columns = [col for col in response_columns if col in filtered_df.columns]

    return jsonify(filtered_df[response_columns].to_dict(orient="records"))


@app.route('/publications/summary')
def get_publications_summary():
    university_name = request.args.get('university')

    if not university_name:
        return jsonify({"message": "Lütfen 'university' parametresini belirtin."}), 400
    if university_name not in SUPPORTED_UNIVERSITIES:
        return jsonify({
                           "message": f"'{university_name}' desteklenen bir üniversite değildir. Desteklenen üniversiteler için /universities adresini kontrol edin."}), 400

    df = cached_data_by_university.get(university_name)

    if df is None or df.empty:
        return jsonify({"message": f"'{university_name}' için veri henüz yüklenmedi veya yüklenemedi."}), 503

    total_publications = len(df)
    publications_by_year = df['Yayın Yılı'].value_counts().sort_index(ascending=False).to_dict()

    # En çok yayın yapan yazarlar (top 5) - NaN değerleri atıldı
    top_authors_series = df['Author Name and Surname'].dropna().str.split(', ').explode().value_counts()
    top_authors = top_authors_series.head(5).to_dict()

    # En popüler anahtar kelimeler (top 5) - NaN değerleri atıldı
    top_keywords_series = df['Yazar Anahtar Kelimeleri'].dropna().str.split(', ').explode().value_counts()
    top_keywords = top_keywords_series.head(5).to_dict()

    average_citations = df['Citation Count'].mean() if not df['Citation Count'].empty else 0

    summary = {
        "university": university_name,
        "total_publications": total_publications,
        "publications_by_year": publications_by_year,
        "top_5_authors": top_authors,
        "top_5_keywords": top_keywords,
        "average_citations": round(average_citations, 2)
    }
    return jsonify(summary)


async def load_initial_data_for_all_universities():
    logging.info("📦 Tüm üniversiteler için veri yükleme başlatılıyor...")
    global cached_data_by_university

    tasks = []
    for uni_name in SUPPORTED_UNIVERSITIES:
        tasks.append(fetch_university_data(university_name=uni_name))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(results):
        uni_name = SUPPORTED_UNIVERSITIES[i]
        if isinstance(result, Exception):
            logging.error(f"❌ '{uni_name}' için ilk veri yüklenirken hata oluştu: {result}", exc_info=True)
            cached_data_by_university[uni_name] = pd.DataFrame()
        elif result is not None and not result.empty:
            cached_data_by_university[uni_name] = result
            logging.info(f"✅ '{uni_name}' verileri başarıyla yüklendi ve önbelleğe alındı. Yayın sayısı: {len(result)}")
        else:
            logging.warning(f"⚠️ '{uni_name}' için ilk veri yüklemesi boş bir DataFrame ile sonuçlandı.")
            cached_data_by_university[uni_name] = pd.DataFrame()

    logging.info("✅ Tüm üniversiteler için ilk veri yükleme tamamlandı.")


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(load_initial_data_for_all_universities())

    port = int(os.environ.get("PORT", 5000))
    logging.info(f"🚀 Flask uygulaması {port} portunda başlıyor...")
    app.run(host="0.0.0.0", port=port)