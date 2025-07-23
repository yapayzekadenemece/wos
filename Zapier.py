from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
from your_script_file import main as fetch_data  # Senin ana kodun burada

app = Flask(__name__)
CORS(app)

@app.route('/wos/atilim', methods=['GET'])
def get_atilim_data():
    try:
        df = asyncio.run(fetch_data())
        json_data = df.to_dict(orient="records")
        return jsonify(json_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
