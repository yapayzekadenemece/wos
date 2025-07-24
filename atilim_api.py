from flask import Flask, jsonify, request
import asyncio
import os
import json # Eğer Atilim.py'den veri çekiyorsanız veya JSON kaydediyorsanız
import httpx # Clarivate API çağrıları için

# Eğer Atilim.py dosyanızdaki Clarivate çekme mantığını modül olarak kullanıyorsanız:
# from Atilim import get_university_publications_from_clarivate 

app = Flask(__name__)

# GLOBAL DEĞİŞKENLER VE ÖNBELLEK
UNIVERSITY_PUBLICATIONS = {}
UNIVERSITY_SUMMARIES = {}
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

CLARIVATE_API_KEY = os.getenv("CLARIVATE_API_KEY", "YOUR_DEFAULT_API_KEY")
CLARIVATE_SID = os.getenv("CLARIVATE_SID", "YOUR_DEFAULT_SID")

# Clarivate'tan veri çekme fonksiyonu (Bu, Atilim.py'den import edilen veya buraya kopyalanan fonk olmalı)
# Eğer Atilim.py'yi import ediyorsanız, bu fonksiyon tanımını buradan kaldırın ve import ettiğiniz fonksiyonu kullanın.
async def get_university_publications_from_clarivate(university_name, api_key, sid):
    print(f"Clarivate API'den '{university_name}' için yayın verileri çekiliyor...")
    # Lütfen buraya kendi Clarivate API çekme mantığınızı KESİNLİKLE koyun.
    # Bu sadece bir yer tutucudur. Örnek:
    # response = await httpx.AsyncClient().post(...)
    # return response.json()['results']

    # Geçici dummy veri döndürelim, böylece API çalışıyor mu test edebiliriz
    await asyncio.sleep(0.5) # Gerçek API çağrısı gibi gecikme
    return [
        {"uid": f"WOS:{university_name}_A1", "title": f"Başlık A {university_name}", "source": {"sourceTitle": "Dergi X", "publishYear": "2023"}, "Author Name and Surname": "Yazar 1", "Citation Count": 15},
        {"uid": f"WOS:{university_name}_B2", "title": f"Başlık B {university_name}", "source": {"sourceTitle": "Dergi Y", "publishYear": "2022"}, "Author Name and Surname": "Yazar 2", "Citation Count": 8}
    ]

# Özet oluşturma fonksiyonu (önceki yanıtımdaki gibi)
def generate_summary(publications, university_name):
    # ... (buraya önceki yanıttaki generate_summary fonksiyonunuzun tüm içeriğini yapıştırın)
    total_publications = len(publications)
    publications_by_year = {}
    author_counts = {}
    total_citations = 0

    for pub in publications:
        year = pub.get("source", {}).get("publishYear")
        if year:
            publications_by_year[year] = publications_by_year.get(year, 0) + 1

        author = pub.get("Author Name and Surname")
        if author:
            # Birden fazla yazar varsa virgülle ayrılmış olabilir, ilkini alalım
            main_author = author.split(',')[0].strip()
            author_counts[main_author] = author_counts.get(main_author, 0) + 1

        citation_count = pub.get("Citation Count", 0)
        total_citations += citation_count

    top_5_authors = dict(sorted(author_counts.items(), key=lambda item: item[1], reverse=True)[:5])
    avg_citations = total_citations / total_publications if total_publications > 0 else 0

    return {
        "university": university_name,
        "total_publications": total_publications,
        "publications_by_year": publications_by_year,
        "top_5_authors": top_5_authors,
        "top_5_keywords": {}, # Eğer API'nizden keyword almıyorsanız boş bırakın
        "average_citations": round(avg_citations, 2)
    }


# BAŞLATMA VE VERİ YÜKLEME
async def load_initial_data_for_all_universities():
    print("Tüm üniversiteler için başlangıç verileri yükleniyor...")
    for uni in SUPPORTED_UNIVERSITIES:
        try:
            data = await get_university_publications_from_clarivate(uni, CLARIVATE_API_KEY, CLARIVATE_SID)
            UNIVERSITY_PUBLICATIONS[uni] = data
            UNIVERSITY_SUMMARIES[uni] = generate_summary(data, uni)
            print(f"{uni} verileri yüklendi. Yayın sayısı: {len(data)}")
        except Exception as e:
            print(f"Hata: {uni} verileri yüklenemedi: {e}")
    print("Tüm üniversite verileri yükleme tamamlandı.")

# Flask uygulamasının ilk isteği gelmeden önce veriyi yüklemesini sağlar
# Bu satırın app.before_first_request dekoratörünün altında olduğundan emin olun
@app.before_first_request
def startup_load_data():
    print("API başlangıcı: Veri yükleme tetiklendi.")
    asyncio.run(load_initial_data_for_all_universities())

# ------------ API ENDPOINT'LERİ ------------

# /universities endpoint'i
@app.route('/universities', methods=['GET'])
def get_universities_list():
    print("'/universities' endpoint'ine istek geldi.")
    return jsonify({"universities": SUPPORTED_UNIVERSITIES})

# /publications endpoint'i
@app.route('/publications', methods=['GET'])
def get_publications():
    print("'/publications' endpoint'ine istek geldi.")
    university = request.args.get('university')
    year = request.args.get('year', type=int)
    author = request.args.get('author')
    limit = request.args.get('limit', default=50, type=int)

    if not university:
        return jsonify({"error": "University parameter is required."}), 400

    if university not in UNIVERSITY_PUBLICATIONS:
        return jsonify({"error": f"Veri henüz {university} için yüklenmedi veya bulunamadı. Lütfen daha sonra tekrar deneyin ya da geçerli bir üniversite seçin."}), 503

    publications = UNIVERSITY_PUBLICATIONS.get(university, [])
    filtered_publications = []

    for pub in publications:
        match = True
        if year and pub.get("source", {}).get("publishYear") != str(year):
            match = False
        if author and author.lower() not in pub.get("Author Name and Surname", "").lower():
            match = False
        if match:
            filtered_publications.append(pub)

    filtered_publications.sort(key=lambda x: x.get("Citation Count", 0), reverse=True)

    return jsonify(filtered_publications[:limit])

# /publications/summary endpoint'i
@app.route('/publications/summary', methods=['GET'])
def get_publications_summary():
    print("'/publications/summary' endpoint'ine istek geldi.")
    university = request.args.get('university')

    if not university:
        return jsonify({"error": "University parameter is required."}), 400

    if university not in UNIVERSITY_SUMMARIES:
        return jsonify({"error": f"Özet veri henüz {university} için yüklenmedi veya bulunamadı. Lütfen daha sonra tekrar deneyin ya da geçerli bir üniversite seçin."}), 503

    summary = UNIVERSITY_SUMMARIES.get(university)
    return jsonify(summary)

# Ana sayfa (sağlık kontrolü için)
@app.route('/')
def home():
    return "Üniversite Yayınları API çalışıyor!"

# Uygulamayı başlat
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)